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
