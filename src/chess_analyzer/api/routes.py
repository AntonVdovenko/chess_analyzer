"""API routes for Chess Analyzer."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from statistics import mean
from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.chess_analyzer.advanced_analysis_pipeline import AdvancedAnalysisPipeline
from src.chess_analyzer.analysis_pipeline import AnalysisPipeline
from src.chess_analyzer.api.schemas import (
    AdvancedAnalysisRequest,
    AdvancedAnalysisResponse,
    AdvancedAnalysisStatusResponse,
    AnalysisStatus,
    AnalyzeRequest,
    AnomalyResponse,
    ConceptListResponse,
    GameResponse,
    MarkStudiedRequest,
    MarkStudiedResponse,
    MovePredictionResponse,
    PatternDetailResponse,
    PatternResponse,
    SimilarPositionResponse,
    StatsResponse,
    StudyGameDetailResponse,
    StudyPlanGenerateRequest,
    StudyPlanGenerateResponse,
    StudyPlanResponse,
    StudyProgressResponse,
)
from src.chess_analyzer.database.models import (
    AdvancedAnalysisJob,
    Anomaly,
    ConceptMap,
    Embedding,
    Game,
    MovePrediction,
    Pattern,
    Position,
    Stats,
    StudyPlan,
    StudySession,
)
from src.chess_analyzer.database.session import get_db
from src.chess_analyzer.game_fetcher import ChessComFetcher
from src.chess_analyzer.ml_models.embeddings import PositionEmbedder
from src.chess_analyzer.study_planning.study_plan_generator import StudyPlanGenerator

router = APIRouter()

PRIORITY_CRITICAL_FREQUENCY = 10
PRIORITY_CRITICAL_LOSS = 200
PRIORITY_HIGH_FREQUENCY = 5
PRIORITY_HIGH_LOSS = 150

analysis_tasks: dict[str, dict[str, int | str]] = {}
DbSession = Annotated[Session, Depends(get_db)]


def validate_uuid_param(value: str, param_name: str = "ID") -> str:
    """Validate and normalize a UUID string."""
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {param_name} format",
        ) from exc


def _estimate_accuracy_from_acpl(acpl: float) -> float:
    """Estimate a player-friendly accuracy score from ACPL."""
    return max(0.0, min(100.0, 100.0 - (acpl / 10.0)))


def _estimate_move_accuracy(eval_loss: float) -> float:
    """Convert a move's evaluation loss into a rough accuracy percentage."""
    return max(0.0, min(100.0, 100.0 - (eval_loss / 10.0)))


def _get_player_color(game_data: dict[str, object], username: str) -> str:
    """Determine whether the analyzed player was white or black."""
    white_player = str(game_data.get("white", "")).lower()
    if white_player == username.lower():
        return "white"
    return "black"


def _get_game_acpl(game: Game) -> float:
    """Calculate ACPL from a game's persisted positions."""
    eval_losses = [
        position.evaluation_loss
        for position in game.positions
        if position.evaluation_loss is not None
    ]
    if not eval_losses:
        return 0.0
    return float(mean(eval_losses))


def _build_accuracy_by_phase(positions: list[Position]) -> dict[str, float]:
    """Aggregate accuracy percentages by game phase."""
    phase_buckets: dict[str, list[float]] = {
        "opening": [],
        "middlegame": [],
        "endgame": [],
    }
    for position in positions:
        if position.evaluation_loss is None:
            continue
        if position.is_opening:
            phase_buckets["opening"].append(_estimate_move_accuracy(position.evaluation_loss))
        elif position.is_endgame:
            phase_buckets["endgame"].append(_estimate_move_accuracy(position.evaluation_loss))
        else:
            phase_buckets["middlegame"].append(_estimate_move_accuracy(position.evaluation_loss))

    return {
        phase: float(mean(values))
        for phase, values in phase_buckets.items()
        if values
    }


def _build_weakness_summary(db: Session, username: str) -> list[dict[str, object]]:
    """Build a stats-friendly weakness summary from persisted patterns."""
    patterns = (
        db.query(Pattern)
        .filter(Pattern.player_username == username)
        .order_by(Pattern.frequency.desc(), Pattern.average_eval_loss.desc())
        .limit(5)
        .all()
    )
    return [
        {
            "weakness": pattern.pattern_name,
            "frequency": pattern.frequency,
            "avg_loss": pattern.average_eval_loss,
            "type": pattern.weakness_type,
        }
        for pattern in patterns
    ]


def _clear_player_analysis_data(db: Session, username: str) -> None:
    """Delete existing analysis artifacts for a user before re-analysis."""
    pattern_ids = [
        pattern_id
        for (pattern_id,) in db.query(Pattern.id)
        .filter(Pattern.player_username == username)
        .all()
    ]
    study_plan_ids = [
        study_plan_id
        for (study_plan_id,) in db.query(StudyPlan.id)
        .filter(StudyPlan.user_id == username)
        .all()
    ]
    game_ids = [
        game_id
        for (game_id,) in db.query(Game.id).filter(Game.username == username).all()
    ]
    position_ids: list[int] = []
    if game_ids:
        position_ids = [
            position_id
            for (position_id,) in db.query(Position.id)
            .filter(Position.game_id.in_(game_ids))
            .all()
        ]

    if study_plan_ids:
        db.query(StudySession).filter(StudySession.study_plan_id.in_(study_plan_ids)).delete(
            synchronize_session=False
        )
    db.query(StudyPlan).filter(StudyPlan.user_id == username).delete(
        synchronize_session=False
    )

    if pattern_ids:
        db.query(ConceptMap).filter(ConceptMap.weakness_id.in_(pattern_ids)).delete(
            synchronize_session=False
        )
    db.query(Pattern).filter(Pattern.player_username == username).delete(
        synchronize_session=False
    )
    db.query(Stats).filter(Stats.player_username == username).delete(
        synchronize_session=False
    )

    if game_ids:
        db.query(MovePrediction).filter(MovePrediction.game_id.in_(game_ids)).delete(
            synchronize_session=False
        )
        db.query(Anomaly).filter(Anomaly.game_id.in_(game_ids)).delete(
            synchronize_session=False
        )
    if position_ids:
        db.query(Embedding).filter(Embedding.position_id.in_(position_ids)).delete(
            synchronize_session=False
        )
    if game_ids:
        db.query(Position).filter(Position.game_id.in_(game_ids)).delete(
            synchronize_session=False
        )
    db.query(Game).filter(Game.username == username).delete(synchronize_session=False)
    db.flush()


def _create_stats_record(
    db: Session,
    username: str,
    games: list[Game],
) -> Stats:
    """Build a Stats row from persisted games and positions."""
    all_positions = [position for game in games for position in game.positions]
    game_accuracies = [_estimate_accuracy_from_acpl(_get_game_acpl(game)) for game in games]
    wins = sum(game.result == "win" for game in games)
    losses = sum(game.result == "loss" for game in games)
    win_loss_ratio = float(wins) if losses == 0 else wins / losses

    stats = Stats(
        player_username=username,
        total_games=len(games),
        total_accuracy=float(mean(game_accuracies)) if game_accuracies else 0.0,
        accuracy_by_phase=_build_accuracy_by_phase(all_positions),
        win_loss_ratio=win_loss_ratio,
    )
    db.add(stats)
    return stats


@router.get("/")
async def root():
    """Root API endpoint."""
    return {"message": "Chess Analyzer API"}


@router.post("/analyze", response_model=AnalysisStatus)
def analyze_games(request: AnalyzeRequest, db: DbSession):
    """Fetch games, analyze them, and persist derived data."""
    task_id = str(uuid.uuid4())

    try:
        fetcher = ChessComFetcher()
        fetched_games = fetcher.fetch_games(request.username, limit=request.limit)
    except Exception as exc:
        analysis_tasks[task_id] = {
            "status": "failed",
            "games_analyzed": 0,
            "patterns_found": 0,
        }
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch games: {exc}",
        ) from exc

    try:
        _clear_player_analysis_data(db, request.username)

        db_games: list[Game] = []
        pipeline_input: list[dict[str, object]] = []
        for game_data in fetched_games:
            db_game = Game(
                username=request.username,
                opponent_username=game_data.get("opponent"),
                opponent_rating=game_data.get("opponent_elo"),
                time_control=game_data.get("time_control"),
                result=game_data.get("result"),
                date=game_data.get("date"),
                pgn=game_data.get("pgn"),
                white_elo=game_data.get("white_elo"),
                black_elo=game_data.get("black_elo"),
            )
            db.add(db_game)
            db.flush()
            db_games.append(db_game)
            pipeline_input.append(
                {
                    "game_id": db_game.id,
                    "pgn": db_game.pgn,
                    "player_color": _get_player_color(game_data, request.username),
                }
            )

        with AnalysisPipeline() as pipeline:
            analysis_result = pipeline.analyze_games(pipeline_input)

        for game_summary in analysis_result["games"]:
            for position_data in game_summary["positions"]:
                db.add(
                    Position(
                        game_id=position_data["game_id"],
                        move_number=position_data["move_number"],
                        fen=position_data["fen"],
                        player_move=position_data["player_move"],
                        engine_best_move=position_data["engine_best_move"],
                        evaluation_loss=position_data["evaluation_loss"],
                        evaluation_before=position_data["evaluation_before"],
                        evaluation_after=position_data["evaluation_after"],
                        is_opening=position_data["is_opening"],
                        is_middlegame=position_data["is_middlegame"],
                        is_endgame=position_data["is_endgame"],
                    )
                )

        for pattern_data in analysis_result["pattern_candidates"]:
            db.add(
                Pattern(
                    pattern_name=pattern_data["name"],
                    weakness_type=pattern_data["weakness_type"],
                    frequency=pattern_data["frequency"],
                    game_ids=pattern_data["game_ids"],
                    position_features=pattern_data["position_features"],
                    average_eval_loss=pattern_data["average_eval_loss"],
                    player_username=request.username,
                )
            )

        db.flush()
        for game in db_games:
            db.refresh(game)
        _create_stats_record(db, request.username, db_games)
        db.commit()

        analysis_tasks[task_id] = {
            "status": "completed",
            "games_analyzed": len(fetched_games),
            "patterns_found": len(analysis_result["pattern_candidates"]),
        }

        return AnalysisStatus(
            status="completed",
            task_id=task_id,
            games_analyzed=len(fetched_games),
            patterns_found=len(analysis_result["pattern_candidates"]),
        )
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        analysis_tasks[task_id] = {
            "status": "failed",
            "games_analyzed": len(fetched_games),
            "patterns_found": 0,
        }
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze games: {exc}",
        ) from exc


@router.get("/analysis/{task_id}", response_model=AnalysisStatus)
def get_analysis_status(task_id: str):
    """Check the progress of an analysis task."""
    if task_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = analysis_tasks[task_id]
    return AnalysisStatus(
        status=str(task["status"]),
        task_id=task_id,
        games_analyzed=int(task["games_analyzed"]),
        patterns_found=int(task["patterns_found"]),
    )


@router.get("/games", response_model=list[GameResponse])
def list_games(
    username: str,
    db: DbSession,
    limit: int = 20,
    offset: int = 0,
):
    """List all analyzed games for a player."""
    games = (
        db.query(Game)
        .filter(Game.username == username)
        .order_by(Game.date.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return [
        GameResponse(
            id=game.id,
            opponent_username=game.opponent_username,
            result=game.result,
            date=game.date,
            accuracy=_estimate_accuracy_from_acpl(_get_game_acpl(game)),
        )
        for game in games
    ]


@router.get("/stats", response_model=StatsResponse)
def get_stats(username: str, db: DbSession):
    """Get dashboard statistics for a player."""
    stats = db.query(Stats).filter(Stats.player_username == username).first()
    if not stats:
        raise HTTPException(
            status_code=404,
            detail=f"No statistics available for player {username}",
        )

    return StatsResponse(
        total_games=stats.total_games,
        overall_accuracy=stats.total_accuracy,
        accuracy_by_phase=stats.accuracy_by_phase or {},
        weakness_summary=_build_weakness_summary(db, username),
    )


@router.get("/patterns", response_model=list[PatternResponse])
def get_patterns(
    username: str,
    db: DbSession,
    weakness_type: str | None = None,
    limit: int = 10,
):
    """Get discovered weakness patterns for a player."""
    query = db.query(Pattern).filter(Pattern.player_username == username)
    if weakness_type:
        query = query.filter(Pattern.weakness_type == weakness_type)

    patterns = query.order_by(Pattern.frequency.desc()).limit(limit).all()
    return [
        PatternResponse(
            id=pattern.id,
            name=pattern.pattern_name,
            weakness_type=pattern.weakness_type,
            frequency=pattern.frequency,
            average_eval_loss=pattern.average_eval_loss,
        )
        for pattern in patterns
    ]


@router.post("/advanced-analysis", response_model=AdvancedAnalysisResponse)
async def start_advanced_analysis(
    request: AdvancedAnalysisRequest,
    db: DbSession,
):
    """Run advanced ML analyses for an already-analyzed player."""
    job = AdvancedAnalysisJob(username=request.username)
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        pipeline = AdvancedAnalysisPipeline(db)
        result = pipeline.analyze_player(request.username)
        if result["status"] != "completed":
            job.status = "failed"
            db.commit()
            raise HTTPException(status_code=400, detail=result["message"])

        job.status = "completed"
        job.move_predictor_done = True
        job.anomaly_detector_done = True
        job.embedder_done = True
        job.completed_at = datetime.now(UTC)
        db.commit()
        return AdvancedAnalysisResponse(
            job_id=str(job.job_id),
            status=job.status,
            username=request.username,
        )
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        job.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/advanced-analysis/{job_id}", response_model=AdvancedAnalysisStatusResponse)
async def get_advanced_analysis_status(job_id: str, db: DbSession):
    """Check advanced analysis job status."""
    job = db.query(AdvancedAnalysisJob).filter(AdvancedAnalysisJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    game_ids = [
        game_id
        for (game_id,) in db.query(Game.id).filter(Game.username == job.username).all()
    ]
    position_ids: list[int] = []
    if game_ids:
        position_ids = [
            position_id
            for (position_id,) in db.query(Position.id)
            .filter(Position.game_id.in_(game_ids))
            .all()
        ]

    unusual_moves = 0
    anomalies = 0
    embeddings = 0
    if game_ids:
        unusual_moves = db.query(MovePrediction).filter(
            MovePrediction.game_id.in_(game_ids)
        ).count()
        anomalies = db.query(Anomaly).filter(Anomaly.game_id.in_(game_ids)).count()
    if position_ids:
        embeddings = db.query(Embedding).filter(
            Embedding.position_id.in_(position_ids)
        ).count()

    return AdvancedAnalysisStatusResponse(
        job_id=str(job.job_id),
        status=job.status,
        username=job.username,
        move_predictor_done=job.move_predictor_done,
        anomaly_detector_done=job.anomaly_detector_done,
        embedder_done=job.embedder_done,
        unusual_moves_count=unusual_moves,
        anomalies_count=anomalies,
        embeddings_count=embeddings,
    )


@router.get("/move-predictions", response_model=list[MovePredictionResponse])
async def get_move_predictions(
    db: DbSession,
    username: str | None = None,
    game_id: int | None = None,
    min_probability: float = 0.0,
):
    """Get unusual move predictions."""
    query = db.query(MovePrediction)
    if username:
        query = query.join(Game).filter(Game.username == username)
    if game_id:
        query = query.filter(MovePrediction.game_id == game_id)

    return query.filter(MovePrediction.probability_score >= min_probability).all()


@router.get("/anomalies", response_model=list[AnomalyResponse])
async def get_anomalies(
    db: DbSession,
    username: str | None = None,
    game_id: int | None = None,
    min_score: float = 0.0,
):
    """Get detected anomalies."""
    query = db.query(Anomaly)
    if username:
        query = query.join(Game).filter(Game.username == username)
    if game_id:
        query = query.filter(Anomaly.game_id == game_id)

    return (
        query.filter(Anomaly.anomaly_score >= min_score)
        .order_by(Anomaly.anomaly_score.desc())
        .all()
    )


@router.get("/similar-positions", response_model=list[SimilarPositionResponse])
async def get_similar_positions(
    position_fen: str,
    db: DbSession,
    limit: int = 10,
):
    """Find semantically similar positions."""
    input_position = db.query(Position).filter(Position.fen == position_fen).first()
    if not input_position:
        raise HTTPException(status_code=404, detail="Position not found")

    input_embedding = db.query(Embedding).filter(Embedding.position_id == input_position.id).first()
    if not input_embedding:
        raise HTTPException(status_code=404, detail="Embedding not found")

    all_embeddings = db.query(Embedding).all()
    if not all_embeddings:
        return []

    embedder = PositionEmbedder()
    candidate_vectors = np.array([embedding.embedding_vector for embedding in all_embeddings])
    similar_indices = embedder.find_similar(
        np.array(input_embedding.embedding_vector),
        candidate_vectors,
        k=min(limit + 1, len(all_embeddings)),
    )

    results: list[SimilarPositionResponse] = []
    for idx in similar_indices:
        embedding = all_embeddings[idx]
        if embedding.position_id == input_position.id:
            continue
        position = embedding.position
        similarity = embedder.get_similarity_score(
            np.array(input_embedding.embedding_vector),
            np.array(embedding.embedding_vector),
        )
        results.append(
            SimilarPositionResponse(
                position_id=position.id,
                similarity_score=similarity,
                game_id=position.game_id,
                centipawn_loss=float(position.evaluation_loss or 0.0),
                position_fen=position.fen,
            )
        )
        if len(results) >= limit:
            break

    return results


@router.get("/pattern-details/{pattern_id}", response_model=PatternDetailResponse)
async def get_pattern_details(pattern_id: int, db: DbSession):
    """Get detailed pattern information with phase 2 data."""
    pattern = db.query(Pattern).filter(Pattern.id == pattern_id).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    game_ids = pattern.game_ids or []
    unusual_moves = 0
    anomalies = 0
    if game_ids:
        unusual_moves = db.query(MovePrediction).filter(
            MovePrediction.game_id.in_(game_ids)
        ).count()
        anomalies = db.query(Anomaly).filter(Anomaly.game_id.in_(game_ids)).count()

    similar_patterns = (
        db.query(Pattern.id)
        .filter(
            Pattern.player_username == pattern.player_username,
            Pattern.weakness_type == pattern.weakness_type,
            Pattern.id != pattern.id,
        )
        .order_by(Pattern.frequency.desc(), Pattern.average_eval_loss.desc())
        .limit(3)
        .all()
    )

    frequency = pattern.frequency or 0
    avg_loss = pattern.average_eval_loss or 0.0
    if frequency > PRIORITY_CRITICAL_FREQUENCY and avg_loss > PRIORITY_CRITICAL_LOSS:
        study_priority = "critical"
    elif frequency > PRIORITY_HIGH_FREQUENCY or avg_loss > PRIORITY_HIGH_LOSS:
        study_priority = "high"
    else:
        study_priority = "medium"

    return PatternDetailResponse(
        id=pattern.id,
        name=pattern.pattern_name,
        type=pattern.weakness_type,
        frequency=frequency,
        avg_loss=avg_loss,
        affected_games=len(game_ids),
        unusual_moves_in_pattern=unusual_moves,
        anomaly_count=anomalies,
        similar_patterns=[similar_pattern_id for (similar_pattern_id,) in similar_patterns],
        study_priority=study_priority,
    )


@router.post("/study-plan/generate", response_model=StudyPlanGenerateResponse)
def generate_study_plan(
    request: StudyPlanGenerateRequest,
    db: DbSession,
):
    """Generate a personalized study plan for a player."""
    try:
        generator = StudyPlanGenerator(db)
        result = generator.generate_study_plan(request.username, request.game_limit)
        return StudyPlanGenerateResponse(
            username=result["username"],
            total_weaknesses=result["total_weaknesses"],
            study_plans_created=result["study_plans_created"],
            priority_distribution=result["priority_distribution"],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate study plan: {exc}",
        ) from exc


@router.get("/study-plan", response_model=list[StudyPlanResponse])
def list_study_plans(
    db: DbSession,
    user_id: str | None = None,
    username: str | None = None,
    status: str | None = None,
    concept_type: str | None = None,
    sort_by: str = "created_at",
):
    """List study plans for a user with optional filtering and sorting."""
    resolved_user_id = user_id or username
    if not resolved_user_id:
        raise HTTPException(status_code=400, detail="Missing user identifier")

    try:
        query = db.query(StudyPlan).filter(StudyPlan.user_id == resolved_user_id)
        if status and status != "all":
            query = query.filter(StudyPlan.status == status)
        if concept_type and concept_type != "all":
            query = (
                query.join(ConceptMap, ConceptMap.weakness_id == StudyPlan.weakness_id)
                .filter(ConceptMap.concept_type == concept_type)
                .distinct()
            )

        if sort_by == "priority_score":
            query = query.order_by(StudyPlan.priority_score.desc())
        else:
            query = query.order_by(StudyPlan.created_at.desc())

        plans = query.all()
        weakness_ids = [plan.weakness_id for plan in plans]
        concept_counts = dict.fromkeys(weakness_ids, 0)
        patterns_by_id = {}
        if weakness_ids:
            patterns_by_id = {
                pattern.id: pattern
                for pattern in db.query(Pattern).filter(Pattern.id.in_(weakness_ids)).all()
            }
        if weakness_ids:
            concepts = (
                db.query(ConceptMap)
                .filter(ConceptMap.weakness_id.in_(weakness_ids))
                .all()
            )
            for concept in concepts:
                concept_counts[concept.weakness_id] = concept_counts.get(concept.weakness_id, 0) + 1

        return [
            StudyPlanResponse(
                id=str(plan.id),
                user_id=plan.user_id,
                weakness_id=plan.weakness_id,
                weakness_name=patterns_by_id.get(plan.weakness_id).pattern_name
                if patterns_by_id.get(plan.weakness_id)
                else None,
                weakness_type=patterns_by_id.get(plan.weakness_id).weakness_type
                if patterns_by_id.get(plan.weakness_id)
                else None,
                priority_score=plan.priority_score,
                status=plan.status,
                concept_count=concept_counts.get(plan.weakness_id, 0),
                created_at=plan.created_at,
            )
            for plan in plans
        ]
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list study plans: {exc}",
        ) from exc


@router.patch("/study-plan/{study_plan_id}/mark-studied", response_model=MarkStudiedResponse)
def mark_study_plan_studied(
    study_plan_id: str,
    request: MarkStudiedRequest,
    db: DbSession,
):
    """Mark a study plan as studied."""
    _ = request
    try:
        plan_uuid = uuid.UUID(validate_uuid_param(study_plan_id, "study plan ID"))
        plan = db.query(StudyPlan).filter(StudyPlan.id == plan_uuid).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Study plan not found")

        now = datetime.now(UTC)
        plan.status = "completed"
        plan.marked_studied_at = now
        plan.updated_at = now
        db.commit()
        db.refresh(plan)
        return MarkStudiedResponse(
            id=str(plan.id),
            status=plan.status,
            marked_studied_at=plan.marked_studied_at,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark study plan as studied: {exc}",
        ) from exc


@router.get("/study-plan/progress", response_model=StudyProgressResponse)
def get_study_progress(
    db: DbSession,
    user_id: str | None = None,
    username: str | None = None,
):
    """Get study progress for a user."""
    resolved_user_id = user_id or username
    if not resolved_user_id:
        raise HTTPException(status_code=400, detail="Missing user identifier")

    try:
        total_plans = db.query(StudyPlan).filter(StudyPlan.user_id == resolved_user_id).count()
        active_plans = (
            db.query(StudyPlan)
            .filter(StudyPlan.user_id == resolved_user_id, StudyPlan.status == "active")
            .count()
        )
        completed_plans = (
            db.query(StudyPlan)
            .filter(
                StudyPlan.user_id == resolved_user_id,
                StudyPlan.status == "completed",
            )
            .count()
        )
        completion_rate = (completed_plans / total_plans * 100.0) if total_plans else 0.0
        return StudyProgressResponse(
            user_id=resolved_user_id,
            total_plans=total_plans,
            active_plans=active_plans,
            completed_plans=completed_plans,
            completion_rate=completion_rate,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get study progress: {exc}",
        ) from exc


@router.get("/study-plan/{study_plan_id}/concepts", response_model=ConceptListResponse)
def get_study_plan_concepts(study_plan_id: str, db: DbSession):
    """Get learning concepts for a study plan."""
    try:
        plan_uuid = uuid.UUID(validate_uuid_param(study_plan_id, "study plan ID"))
        plan = db.query(StudyPlan).filter(StudyPlan.id == plan_uuid).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Study plan not found")

        concept_maps = db.query(ConceptMap).filter(ConceptMap.weakness_id == plan.weakness_id).all()
        concepts = [
            {"type": concept.concept_type, "name": concept.concept_name}
            for concept in concept_maps
        ]
        return ConceptListResponse(concepts=concepts)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get study plan concepts: {exc}",
        ) from exc


@router.get("/study-plan/{study_plan_id}/games", response_model=list[StudyGameDetailResponse])
def get_study_plan_games(study_plan_id: str, db: DbSession):
    """Get games associated with a study plan's weakness pattern."""
    try:
        plan_uuid = uuid.UUID(validate_uuid_param(study_plan_id, "study plan ID"))
        plan = db.query(StudyPlan).filter(StudyPlan.id == plan_uuid).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Study plan not found")

        pattern = db.query(Pattern).filter(Pattern.id == plan.weakness_id).first()
        if not pattern or not pattern.game_ids:
            return []

        games = db.query(Game).filter(Game.id.in_(pattern.game_ids)).all()
        positions = db.query(Position).filter(Position.game_id.in_(pattern.game_ids)).all()
        positions_by_game: dict[int, list[Position]] = {}
        for position in positions:
            positions_by_game.setdefault(position.game_id, []).append(position)

        results: list[StudyGameDetailResponse] = []
        for game in games:
            game_positions = positions_by_game.get(game.id, [])
            eval_losses = [
                position.evaluation_loss
                for position in game_positions
                if position.evaluation_loss is not None
            ]
            avg_eval_loss = float(mean(eval_losses)) if eval_losses else 0.0
            accuracy = _estimate_accuracy_from_acpl(avg_eval_loss)
            position_fen = (
                max(
                    game_positions,
                    key=lambda position: position.evaluation_loss or 0.0,
                ).fen
                if game_positions
                else "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            )
            results.append(
                StudyGameDetailResponse(
                    game_id=game.id,
                    study_plan_id=str(plan.id),
                    weakness_id=plan.weakness_id,
                    result=game.result,
                    accuracy=accuracy,
                    eval_loss=avg_eval_loss,
                    position_fen=position_fen,
                )
            )

        return results
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get study plan games: {exc}",
        ) from exc
