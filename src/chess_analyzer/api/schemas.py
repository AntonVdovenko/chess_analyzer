"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Request body for starting a game analysis job."""

    username: str = Field(..., description="Chess.com username to analyze")
    limit: int = Field(100, description="Maximum number of games to analyze", ge=1, le=5000)


class AnalysisStatus(BaseModel):
    """Status of an ongoing analysis task."""

    status: str = Field(..., description="Current status: analyzing, completed, failed")
    task_id: str = Field(..., description="Unique task identifier")
    games_analyzed: int = Field(0, description="Number of games analyzed so far")
    patterns_found: int = Field(0, description="Number of patterns discovered")


class GameResponse(BaseModel):
    """Response model for a single analyzed game."""

    id: int = Field(..., description="Game database ID")
    opponent_username: str = Field(..., description="Opponent's chess.com username")
    result: str = Field(..., description="Game result: win, loss, draw")
    date: datetime = Field(..., description="When the game was played")
    accuracy: float = Field(..., description="Player's move accuracy percentage", ge=0, le=100)

    class Config:
        from_attributes = True


class PatternResponse(BaseModel):
    """Response model for a discovered weakness pattern."""

    id: int = Field(..., description="Pattern database ID")
    name: str = Field(..., description="Human-readable pattern name")
    weakness_type: str = Field(..., description="Type of weakness (e.g., king_safety, material_loss)")
    frequency: int = Field(..., description="How many games show this pattern")
    average_eval_loss: float = Field(..., description="Average centipawn loss from this weakness")

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    """Response model for player statistics."""

    total_games: int = Field(..., description="Total games analyzed")
    overall_accuracy: float = Field(..., description="Overall move accuracy percentage", ge=0, le=100)
    accuracy_by_phase: Dict[str, float] = Field(..., description="Accuracy in opening, middlegame, endgame")
    weakness_summary: List[Dict] = Field(..., description="Summary of top weaknesses")


class StudyPlanResponse(BaseModel):
    """Response model for personalized study plan."""

    games_to_review: List[Dict] = Field(..., description="Games that should be reviewed")
    weak_points: List[Dict] = Field(..., description="Key areas to study")


# Phase 2 Advanced Analysis Schemas

class MovePredictionResponse(BaseModel):
    """Response for unusual move predictions."""

    game_id: int = Field(..., description="Game database ID")
    position_fen: str = Field(..., description="FEN string of the position")
    actual_move: str = Field(..., description="The move that was actually played")
    predicted_move: Optional[str] = Field(None, description="The predicted best move")
    probability_score: float = Field(..., description="Probability score (0-1)")
    is_unusual: bool = Field(..., description="Whether move is classified as unusual")

    class Config:
        from_attributes = True


class AnomalyResponse(BaseModel):
    """Response for detected anomalies (rare mistakes)."""

    game_id: int = Field(..., description="Game database ID")
    position_fen: str = Field(..., description="FEN string of the position")
    anomaly_score: float = Field(..., description="Anomaly score (0-1)")
    centipawn_loss: float = Field(..., description="Centipawn loss from this move")
    reason: Optional[str] = Field(None, description="Human-readable reason for anomaly")

    class Config:
        from_attributes = True


class AdvancedAnalysisRequest(BaseModel):
    """Request to start advanced analysis for a player."""

    username: str = Field(..., description="Chess.com username")
    game_limit: Optional[int] = Field(100, description="Maximum games to analyze")


class AdvancedAnalysisResponse(BaseModel):
    """Response when advanced analysis job starts."""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status: processing, completed, failed")
    username: str = Field(..., description="Username being analyzed")


class AdvancedAnalysisStatusResponse(BaseModel):
    """Response for checking advanced analysis job status."""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status: processing, completed, failed")
    username: str = Field(..., description="Username being analyzed")
    move_predictor_done: bool = Field(False, description="Move prediction analysis complete")
    anomaly_detector_done: bool = Field(False, description="Anomaly detection analysis complete")
    embedder_done: bool = Field(False, description="Position embedding analysis complete")
    unusual_moves_count: Optional[int] = Field(None, description="Count of unusual moves found")
    anomalies_count: Optional[int] = Field(None, description="Count of anomalies found")
    embeddings_count: Optional[int] = Field(None, description="Count of embeddings created")


class SimilarPositionResponse(BaseModel):
    """Response for semantically similar positions."""

    position_id: int = Field(..., description="Position database ID")
    similarity_score: float = Field(..., description="Similarity score (0-1)")
    game_id: int = Field(..., description="Game database ID")
    centipawn_loss: float = Field(..., description="Centipawn loss in this position")
    position_fen: str = Field(..., description="FEN string of the position")

    class Config:
        from_attributes = True


class PatternDetailResponse(BaseModel):
    """Detailed response for a weakness pattern with Phase 2 data."""

    id: int = Field(..., description="Pattern database ID")
    name: str = Field(..., description="Pattern name")
    type: str = Field(..., description="Pattern type")
    frequency: int = Field(..., description="Frequency in games")
    avg_loss: float = Field(..., description="Average centipawn loss")
    affected_games: int = Field(..., description="Number of games with this pattern")
    unusual_moves_in_pattern: int = Field(0, description="Count of unusual moves in pattern")
    anomaly_count: int = Field(0, description="Count of anomalies in pattern")
    similar_patterns: List[int] = Field(default_factory=list, description="IDs of similar patterns")
    study_priority: str = Field(..., description="Priority: critical, high, or medium")

    class Config:
        from_attributes = True
