"""API routes for Chess Analyzer."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.chess_analyzer.api.schemas import (
    AnalyzeRequest,
    AnalysisStatus,
    GameResponse,
    PatternResponse,
    StatsResponse,
    StudyPlanResponse,
)
from src.chess_analyzer.game_fetcher import ChessComFetcher
from src.chess_analyzer.database.models import Game, Pattern, Stats
from src.chess_analyzer.database.session import get_db

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
