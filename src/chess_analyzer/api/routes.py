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
)
from src.chess_analyzer.database.session import get_db
from src.chess_analyzer.advanced_analysis_pipeline import AdvancedAnalysisPipeline

router = APIRouter()

# In-memory task tracking (in production, use a task queue like Celery)
analysis_tasks = {}
task_counter = 0


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
    global task_counter
    task_counter += 1
    task_id = f"task_{task_counter}"

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


@router.get("/study-plan", response_model=StudyPlanResponse)
def get_study_plan(username: str, db: Session = Depends(get_db)):
    """Get a personalized study plan based on identified weaknesses.

    Args:
        username: Chess.com username
        db: Database session dependency

    Returns:
        StudyPlanResponse with recommended games and study areas

    Raises:
        HTTPException: If user has no games
    """
    games = db.query(Game).filter(Game.username == username).all()

    if not games:
        raise HTTPException(
            status_code=404,
            detail=f"No games found for player {username}",
        )

    patterns = (
        db.query(Pattern)
        .filter(Pattern.player_username == username)
        .order_by(Pattern.frequency.desc())
        .limit(5)
        .all()
    )

    # Determine games with most losses (focus on improvement)
    games_to_review = [
        {
            "game_id": g.id,
            "opponent": g.opponent_username,
            "result": g.result,
            "date": g.date.isoformat() if g.date else None,
        }
        for g in sorted(games, key=lambda g: g.date, reverse=True)[:5]
    ]

    weak_points = [
        {
            "pattern": p.pattern_name,
            "type": p.weakness_type,
            "frequency": p.frequency,
            "avg_loss": p.average_eval_loss,
        }
        for p in patterns
    ]

    return StudyPlanResponse(
        games_to_review=games_to_review,
        weak_points=weak_points,
    )


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
