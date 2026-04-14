"""API routes for Chess Analyzer."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import numpy as np

from src.chess_analyzer.api.schemas import (
    AnalyzeRequest,
    AnalysisStatus,
    GameResponse,
    PatternResponse,
    StatsResponse,
    StudyPlanResponse,
    AdvancedAnalysisRequest,
    AdvancedAnalysisResponse,
    AdvancedAnalysisStatusResponse,
    MovePredictionResponse,
    AnomalyResponse,
    SimilarPositionResponse,
    PatternDetailResponse,
    StudyPlanGenerateRequest,
    StudyPlanGenerateResponse,
    MarkStudiedRequest,
    MarkStudiedResponse,
    ConceptListResponse,
    StudyProgressResponse,
    StudyGameDetailResponse,
)
from src.chess_analyzer.game_fetcher import ChessComFetcher
from src.chess_analyzer.database.models import (
    Game,
    Pattern,
    Stats,
    Position,
    MovePrediction,
    Anomaly,
    Embedding,
    AdvancedAnalysisJob,
    StudyPlan,
    ConceptMap,
    StudySession,
)
from src.chess_analyzer.database.session import get_db
from src.chess_analyzer.advanced_analysis_pipeline import AdvancedAnalysisPipeline
from src.chess_analyzer.study_planning.study_plan_generator import StudyPlanGenerator

router = APIRouter()

# NOTE: Phase 1 uses in-memory dict for task tracking (temporary, not scalable).
# Phase 2+ uses database-backed job tracking (AdvancedAnalysisJob).
# In production, implement a task queue (Celery with Redis) for all endpoints.
analysis_tasks = {}


@router.get("/")
async def root():
    """Root API endpoint."""
    return {"message": "Chess Analyzer API"}


@router.post("/analyze", response_model=AnalysisStatus)
def analyze_games(request: AnalyzeRequest, db: Session = Depends(get_db)):
    """Start analysis job for a player's chess.com games.

    Args:
        request: AnalyzeRequest containing username and optional game limit
        db: Database session dependency

    Returns:
        AnalysisStatus with task_id to track progress

    Raises:
        HTTPException: If fetching games fails
    """
    task_id = str(uuid.uuid4())

    try:
        # Fetch games from chess.com
        fetcher = ChessComFetcher()
        games = fetcher.fetch_games(request.username, limit=request.limit)

        # Store games in database
        for game_data in games:
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

        db.commit()

        # Track task status
        analysis_tasks[task_id] = {
            "status": "analyzing",
            "games_analyzed": len(games),
            "patterns_found": 0,
        }

        return AnalysisStatus(
            status="analyzing",
            task_id=task_id,
            games_analyzed=len(games),
            patterns_found=0,
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch games: {str(e)}",
        ) from e


@router.get("/analysis/{task_id}", response_model=AnalysisStatus)
def get_analysis_status(task_id: str):
    """Check the progress of an analysis task.

    Args:
        task_id: The task ID to check

    Returns:
        AnalysisStatus with current progress

    Raises:
        HTTPException: If task not found
    """
    if task_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = analysis_tasks[task_id]
    return AnalysisStatus(
        status=task["status"],
        task_id=task_id,
        games_analyzed=task["games_analyzed"],
        patterns_found=task["patterns_found"],
    )


@router.get("/games", response_model=List[GameResponse])
def list_games(
    username: str,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List all analyzed games for a player.

    Args:
        username: Chess.com username
        limit: Number of games to return (default 20)
        offset: Number of games to skip (default 0)
        db: Database session dependency

    Returns:
        List of GameResponse objects
    """
    games = (
        db.query(Game)
        .filter(Game.username == username)
        .order_by(Game.date.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    # Calculate accuracy for each game (placeholder - would come from Position analysis)
    result = []
    for game in games:
        accuracy = 85.0  # Placeholder - would be calculated from positions
        result.append(
            GameResponse(
                id=game.id,
                opponent_username=game.opponent_username,
                result=game.result,
                date=game.date,
                accuracy=accuracy,
            )
        )

    return result


@router.get("/stats", response_model=StatsResponse)
def get_stats(username: str, db: Session = Depends(get_db)):
    """Get dashboard statistics for a player.

    Args:
        username: Chess.com username
        db: Database session dependency

    Returns:
        StatsResponse with aggregated player statistics

    Raises:
        HTTPException: If no stats found for player
    """
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
        weakness_summary=[
            {"weakness": "King safety", "frequency": 5, "avg_loss": 150},
        ],
    )


@router.get("/patterns", response_model=List[PatternResponse])
def get_patterns(
    username: str,
    weakness_type: str = None,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """Get discovered weakness patterns for a player.

    Args:
        username: Chess.com username
        weakness_type: Optional filter by weakness type
        limit: Maximum patterns to return (default 10)
        db: Database session dependency

    Returns:
        List of PatternResponse objects
    """
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


# Phase 2 Advanced Analysis Endpoints


@router.post("/advanced-analysis", response_model=AdvancedAnalysisResponse)
async def start_advanced_analysis(
    request: AdvancedAnalysisRequest, db: Session = Depends(get_db)
):
    """Start advanced analysis for a player.

    Args:
        request: AdvancedAnalysisRequest containing username and game_limit
        db: Database session dependency

    Returns:
        AdvancedAnalysisResponse with job_id and status
    """
    job_id = str(uuid.uuid4())
    job = AdvancedAnalysisJob(username=request.username, job_id=job_id, status="processing")
    db.add(job)
    db.commit()

    try:
        pipeline = AdvancedAnalysisPipeline(db)
        pipeline.analyze_player(request.username)
        job.status = "completed"
        job.move_predictor_done = True
        job.anomaly_detector_done = True
        job.embedder_done = True
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as e:
        job.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e)) from e

    return AdvancedAnalysisResponse(job_id=job_id, status="processing", username=request.username)


@router.get("/advanced-analysis/{job_id}", response_model=AdvancedAnalysisStatusResponse)
async def get_advanced_analysis_status(job_id: str, db: Session = Depends(get_db)):
    """Check advanced analysis job status.

    Args:
        job_id: The job ID to check
        db: Database session dependency

    Returns:
        AdvancedAnalysisStatusResponse with job status and progress

    Raises:
        HTTPException: If job not found
    """
    job = db.query(AdvancedAnalysisJob).filter(AdvancedAnalysisJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get counts for this user
    user_games = db.query(Game).filter(Game.username == job.username).all()
    game_ids = [g.id for g in user_games]

    unusual_moves = db.query(MovePrediction).filter(
        MovePrediction.game_id.in_(game_ids)
    ).count() if game_ids else 0

    anomalies = db.query(Anomaly).filter(
        Anomaly.game_id.in_(game_ids)
    ).count() if game_ids else 0

    embeddings = db.query(Embedding).count()

    return AdvancedAnalysisStatusResponse(
        job_id=job_id,
        status=job.status,
        username=job.username,
        move_predictor_done=job.move_predictor_done,
        anomaly_detector_done=job.anomaly_detector_done,
        embedder_done=job.embedder_done,
        unusual_moves_count=unusual_moves,
        anomalies_count=anomalies,
        embeddings_count=embeddings,
    )


@router.get("/move-predictions", response_model=List[MovePredictionResponse])
async def get_move_predictions(
    username: Optional[str] = None,
    game_id: Optional[int] = None,
    min_probability: float = 0.0,
    db: Session = Depends(get_db),
):
    """Get unusual move predictions.

    Args:
        username: Optional filter by username
        game_id: Optional filter by game ID
        min_probability: Minimum probability score (0-1)
        db: Database session dependency

    Returns:
        List of MovePredictionResponse objects
    """
    query = db.query(MovePrediction)

    if username:
        query = query.join(Game).filter(Game.username == username)

    if game_id:
        query = query.filter(MovePrediction.game_id == game_id)

    predictions = query.filter(MovePrediction.probability_score >= min_probability).all()
    return predictions


@router.get("/anomalies", response_model=List[AnomalyResponse])
async def get_anomalies(
    username: Optional[str] = None,
    game_id: Optional[int] = None,
    min_score: float = 0.0,
    db: Session = Depends(get_db),
):
    """Get detected anomalies (rare mistakes).

    Args:
        username: Optional filter by username
        game_id: Optional filter by game ID
        min_score: Minimum anomaly score (0-1)
        db: Database session dependency

    Returns:
        List of AnomalyResponse objects sorted by anomaly score
    """
    query = db.query(Anomaly)

    if username:
        query = query.join(Game).filter(Game.username == username)

    if game_id:
        query = query.filter(Anomaly.game_id == game_id)

    anomalies = query.filter(Anomaly.anomaly_score >= min_score).order_by(
        Anomaly.anomaly_score.desc()
    ).all()
    return anomalies


@router.get("/similar-positions", response_model=List[SimilarPositionResponse])
async def get_similar_positions(
    position_fen: str, limit: int = 10, db: Session = Depends(get_db)
):
    """Find semantically similar positions.

    Args:
        position_fen: FEN string of the reference position
        limit: Maximum number of similar positions to return
        db: Database session dependency

    Returns:
        List of SimilarPositionResponse objects

    Raises:
        HTTPException: If position or embedding not found
    """
    input_pos = db.query(Position).filter(Position.fen == position_fen).first()
    if not input_pos:
        raise HTTPException(status_code=404, detail="Position not found")

    input_embedding = db.query(Embedding).filter(Embedding.position_id == input_pos.id).first()
    if not input_embedding:
        raise HTTPException(status_code=404, detail="Embedding not found")

    all_embeddings = db.query(Embedding).all()
    if not all_embeddings:
        return []

    pipeline = AdvancedAnalysisPipeline(db)
    all_vectors = np.array([e.embedding_vector for e in all_embeddings])

    similar_indices = pipeline.embedder.find_similar(
        np.array(input_embedding.embedding_vector), all_vectors, k=min(limit, len(all_embeddings))
    )

    results = []
    for idx in similar_indices:
        emb = all_embeddings[idx]
        pos = emb.position
        similarity = pipeline.embedder.get_similarity_score(
            np.array(input_embedding.embedding_vector), np.array(emb.embedding_vector)
        )
        results.append(
            SimilarPositionResponse(
                position_id=pos.id,
                similarity_score=float(similarity),
                game_id=pos.game_id,
                centipawn_loss=float(pos.evaluation_loss or 0.0),
                position_fen=pos.fen,
            )
        )

    return results


@router.get("/pattern-details/{pattern_id}", response_model=PatternDetailResponse)
async def get_pattern_details(pattern_id: int, db: Session = Depends(get_db)):
    """Get detailed pattern information with Phase 2 data.

    Args:
        pattern_id: The pattern ID to get details for
        db: Database session dependency

    Returns:
        PatternDetailResponse with comprehensive pattern information

    Raises:
        HTTPException: If pattern not found
    """
    pattern = db.query(Pattern).filter(Pattern.id == pattern_id).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    # Determine study priority based on frequency and average loss
    frequency = pattern.frequency or 0
    avg_loss = pattern.average_eval_loss or 0.0

    if frequency > 10 and avg_loss > 200:
        study_priority = "critical"
    elif frequency > 5 or avg_loss > 150:
        study_priority = "high"
    else:
        study_priority = "medium"

    return PatternDetailResponse(
        id=pattern.id,
        name=pattern.pattern_name,
        type=pattern.weakness_type,
        frequency=frequency,
        avg_loss=avg_loss,
        affected_games=len(pattern.game_ids) if pattern.game_ids else 0,
        unusual_moves_in_pattern=0,
        anomaly_count=0,
        similar_patterns=[],
        study_priority=study_priority,
    )


# Phase 3 Study Plan API Endpoints


@router.post("/study-plan/generate", response_model=StudyPlanGenerateResponse)
def generate_study_plan(
    request: StudyPlanGenerateRequest, db: Session = Depends(get_db)
):
    """Generate a personalized study plan for a player.

    Creates study plans from weakness patterns with frequency-based prioritization.

    Args:
        request: StudyPlanGenerateRequest with username and optional game_limit
        db: Database session dependency

    Returns:
        StudyPlanGenerateResponse with summary of created plans and distribution

    Raises:
        HTTPException: If generation fails
    """
    try:
        generator = StudyPlanGenerator(db)
        result = generator.generate_study_plan(request.username, request.game_limit)

        return StudyPlanGenerateResponse(
            username=result["username"],
            total_weaknesses=result["total_weaknesses"],
            study_plans_created=result["study_plans_created"],
            priority_distribution=result["priority_distribution"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate study plan: {str(e)}",
        ) from e


@router.get("/study-plan", response_model=List[StudyPlanResponse])
def list_study_plans(
    user_id: str,
    status: Optional[str] = None,
    concept_type: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    db: Session = Depends(get_db),
):
    """List study plans for a user with optional filtering and sorting.

    Args:
        user_id: User identifier
        status: Filter by status (active, completed, paused)
        concept_type: Filter by concept type
        sort_by: Sort field (priority_score, created_at, etc.)
        db: Database session dependency

    Returns:
        List of StudyPlanResponse objects

    Raises:
        HTTPException: If query fails
    """
    try:
        query = db.query(StudyPlan).filter(StudyPlan.user_id == user_id)

        if status:
            query = query.filter(StudyPlan.status == status)

        # Handle sorting
        if sort_by == "priority_score":
            query = query.order_by(StudyPlan.priority_score.desc())
        else:
            query = query.order_by(StudyPlan.created_at.desc())

        plans = query.all()

        # Batch query concepts instead of per-plan queries (prevents N+1 pattern)
        weakness_ids = [plan.weakness_id for plan in plans]
        concept_counts = {wid: 0 for wid in weakness_ids}
        if weakness_ids:
            concepts = (
                db.query(ConceptMap)
                .filter(ConceptMap.weakness_id.in_(weakness_ids))
                .all()
            )
            for concept in concepts:
                concept_counts[concept.weakness_id] = concept_counts.get(concept.weakness_id, 0) + 1

        result = []
        for plan in plans:
            result.append(
                StudyPlanResponse(
                    id=str(plan.id),
                    user_id=plan.user_id,
                    weakness_id=plan.weakness_id,
                    priority_score=plan.priority_score,
                    status=plan.status,
                    concept_count=concept_counts.get(plan.weakness_id, 0),
                    created_at=plan.created_at,
                )
            )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list study plans: {str(e)}",
        ) from e


@router.patch("/study-plan/{study_plan_id}/mark-studied", response_model=MarkStudiedResponse)
def mark_study_plan_studied(
    study_plan_id: str, request: MarkStudiedRequest, db: Session = Depends(get_db)
):
    """Mark a study plan as studied.

    Updates plan status to completed and sets marked_studied_at timestamp.

    Args:
        study_plan_id: UUID of the study plan
        request: MarkStudiedRequest (empty body)
        db: Database session dependency

    Returns:
        MarkStudiedResponse with updated plan details

    Raises:
        HTTPException: If plan not found or update fails
    """
    try:
        # Convert string ID to UUID
        try:
            plan_uuid = uuid.UUID(study_plan_id)
        except (ValueError, AttributeError):
            raise HTTPException(status_code=400, detail="Invalid study plan ID format")

        plan = db.query(StudyPlan).filter(StudyPlan.id == plan_uuid).first()

        if not plan:
            raise HTTPException(status_code=404, detail="Study plan not found")

        now = datetime.now(timezone.utc)
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
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark study plan as studied: {str(e)}",
        ) from e


@router.get("/study-plan/progress", response_model=StudyProgressResponse)
def get_study_progress(user_id: str, db: Session = Depends(get_db)):
    """Get study progress for a user.

    Returns completion metrics and progress on study plans.

    Args:
        user_id: User identifier
        db: Database session dependency

    Returns:
        StudyProgressResponse with progress metrics

    Raises:
        HTTPException: If query fails
    """
    try:
        total_plans = db.query(StudyPlan).filter(StudyPlan.user_id == user_id).count()

        active_plans = (
            db.query(StudyPlan)
            .filter(StudyPlan.user_id == user_id, StudyPlan.status == "active")
            .count()
        )

        completed_plans = (
            db.query(StudyPlan)
            .filter(StudyPlan.user_id == user_id, StudyPlan.status == "completed")
            .count()
        )

        completion_rate = (
            (completed_plans / total_plans * 100) if total_plans > 0 else 0.0
        )

        return StudyProgressResponse(
            user_id=user_id,
            total_plans=total_plans,
            active_plans=active_plans,
            completed_plans=completed_plans,
            completion_rate=completion_rate,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get study progress: {str(e)}",
        ) from e


@router.get("/study-plan/{study_plan_id}/concepts", response_model=ConceptListResponse)
def get_study_plan_concepts(
    study_plan_id: str, db: Session = Depends(get_db)
):
    """Get learning concepts for a study plan.

    Returns concepts mapped to the weakness pattern.

    Args:
        study_plan_id: UUID of the study plan
        db: Database session dependency

    Returns:
        ConceptListResponse with list of concepts

    Raises:
        HTTPException: If plan not found or query fails
    """
    try:
        # Convert string ID to UUID
        try:
            plan_uuid = uuid.UUID(study_plan_id)
        except (ValueError, AttributeError):
            raise HTTPException(status_code=400, detail="Invalid study plan ID format")

        plan = db.query(StudyPlan).filter(StudyPlan.id == plan_uuid).first()

        if not plan:
            raise HTTPException(status_code=404, detail="Study plan not found")

        concept_maps = (
            db.query(ConceptMap)
            .filter(ConceptMap.weakness_id == plan.weakness_id)
            .all()
        )

        concepts = [
            {"type": cm.concept_type, "name": cm.concept_name} for cm in concept_maps
        ]

        return ConceptListResponse(concepts=concepts)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get study plan concepts: {str(e)}",
        ) from e


@router.get("/study-plan/{study_plan_id}/games", response_model=List[StudyGameDetailResponse])
def get_study_plan_games(
    study_plan_id: str, db: Session = Depends(get_db)
):
    """Get games associated with a study plan's weakness pattern.

    Returns game details for games that contain the weakness.

    Args:
        study_plan_id: UUID of the study plan
        db: Database session dependency

    Returns:
        List of StudyGameDetailResponse objects

    Raises:
        HTTPException: If plan not found or query fails
    """
    try:
        # Convert string ID to UUID
        try:
            plan_uuid = uuid.UUID(study_plan_id)
        except (ValueError, AttributeError):
            raise HTTPException(status_code=400, detail="Invalid study plan ID format")

        plan = db.query(StudyPlan).filter(StudyPlan.id == plan_uuid).first()

        if not plan:
            raise HTTPException(status_code=404, detail="Study plan not found")

        # Get pattern details
        pattern = db.query(Pattern).filter(Pattern.id == plan.weakness_id).first()

        if not pattern:
            return []

        # Get game IDs from pattern
        game_ids = pattern.game_ids if pattern.game_ids else []

        if not game_ids:
            return []

        # Fetch games
        games = db.query(Game).filter(Game.id.in_(game_ids)).all()

        result = []
        for game in games:
            # Get positions for this game
            positions = db.query(Position).filter(Position.game_id == game.id).all()

            # Calculate accuracy
            eval_losses = [p.evaluation_loss for p in positions if p.evaluation_loss]
            avg_eval_loss = (
                sum(eval_losses) / len(eval_losses) if eval_losses else 0.0
            )
            accuracy = max(0, 100 - (avg_eval_loss / 50))  # Rough approximation

            # Get best move position FEN
            position_fen = (
                positions[0].fen if positions else "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            )

            result.append(
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

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get study plan games: {str(e)}",
        ) from e
