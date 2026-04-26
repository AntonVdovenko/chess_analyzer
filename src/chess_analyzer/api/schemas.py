"""Pydantic schemas for API request and response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    """Base model configured for ORM serialization."""

    model_config = ConfigDict(from_attributes=True)


class AnalyzeRequest(BaseModel):
    """Request body for starting a game analysis job."""

    username: str = Field(..., description="Chess.com username to analyze")
    limit: int = Field(
        100,
        description="Maximum number of games to analyze",
        ge=1,
        le=5000,
    )


class AnalysisStatus(BaseModel):
    """Status of an ongoing analysis task."""

    status: str = Field(..., description="Current status: analyzing, completed, failed")
    task_id: str = Field(..., description="Unique task identifier")
    games_analyzed: int = Field(0, description="Number of games analyzed so far")
    patterns_found: int = Field(0, description="Number of patterns discovered")


class GameResponse(ORMModel):
    """Response model for a single analyzed game."""

    id: int = Field(..., description="Game database ID")
    opponent_username: str | None = Field(
        None,
        description="Opponent's chess.com username",
    )
    result: str = Field(..., description="Game result")
    date: datetime | None = Field(None, description="When the game was played")
    accuracy: float = Field(
        ...,
        description="Player's move accuracy percentage",
        ge=0,
        le=100,
    )


class PatternResponse(ORMModel):
    """Response model for a discovered weakness pattern."""

    id: int = Field(..., description="Pattern database ID")
    name: str = Field(..., description="Human-readable pattern name")
    weakness_type: str = Field(..., description="Type of weakness")
    frequency: int = Field(..., description="How many games show this pattern")
    average_eval_loss: float = Field(
        ...,
        description="Average centipawn loss from this weakness",
    )


class StatsResponse(BaseModel):
    """Response model for player statistics."""

    total_games: int = Field(..., description="Total games analyzed")
    overall_accuracy: float = Field(
        ...,
        description="Overall move accuracy percentage",
        ge=0,
        le=100,
    )
    accuracy_by_phase: dict[str, float] = Field(
        ...,
        description="Accuracy in opening, middlegame, and endgame",
    )
    weakness_summary: list[dict[str, object]] = Field(
        ...,
        description="Summary of top weaknesses",
    )


class MovePredictionResponse(ORMModel):
    """Response for unusual move predictions."""

    game_id: int = Field(..., description="Game database ID")
    position_fen: str = Field(..., description="FEN string of the position")
    actual_move: str = Field(..., description="The move that was actually played")
    predicted_move: str | None = Field(None, description="The predicted best move")
    probability_score: float = Field(..., description="Probability score (0-1)")
    is_unusual: bool = Field(..., description="Whether move is classified as unusual")


class AnomalyResponse(ORMModel):
    """Response for detected anomalies (rare mistakes)."""

    game_id: int = Field(..., description="Game database ID")
    position_fen: str = Field(..., description="FEN string of the position")
    anomaly_score: float = Field(..., description="Anomaly score (0-1)")
    centipawn_loss: float = Field(..., description="Centipawn loss from this move")
    reason: str | None = Field(None, description="Human-readable reason for anomaly")


class AdvancedAnalysisRequest(BaseModel):
    """Request to start advanced analysis for a player."""

    username: str = Field(..., description="Chess.com username")
    game_limit: int | None = Field(100, description="Maximum games to analyze")


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
    move_predictor_done: bool = Field(False, description="Move prediction complete")
    anomaly_detector_done: bool = Field(False, description="Anomaly detection complete")
    embedder_done: bool = Field(False, description="Position embedding complete")
    unusual_moves_count: int | None = Field(None, description="Count of unusual moves found")
    anomalies_count: int | None = Field(None, description="Count of anomalies found")
    embeddings_count: int | None = Field(None, description="Count of embeddings created")


class SimilarPositionResponse(ORMModel):
    """Response for semantically similar positions."""

    position_id: int = Field(..., description="Position database ID")
    similarity_score: float = Field(..., description="Similarity score (0-1)")
    game_id: int = Field(..., description="Game database ID")
    centipawn_loss: float = Field(..., description="Centipawn loss in this position")
    position_fen: str = Field(..., description="FEN string of the position")


class PatternDetailResponse(ORMModel):
    """Detailed response for a weakness pattern with phase 2 data."""

    id: int = Field(..., description="Pattern database ID")
    name: str = Field(..., description="Pattern name")
    type: str = Field(..., description="Pattern type")
    frequency: int = Field(..., description="Frequency in games")
    avg_loss: float = Field(..., description="Average centipawn loss")
    affected_games: int = Field(..., description="Number of games with this pattern")
    unusual_moves_in_pattern: int = Field(0, description="Count of unusual moves in pattern")
    anomaly_count: int = Field(0, description="Count of anomalies in pattern")
    similar_patterns: list[int] = Field(
        default_factory=list,
        description="IDs of similar patterns",
    )
    study_priority: str = Field(..., description="Priority: critical, high, or medium")


class StudyPlanGenerateRequest(BaseModel):
    """Request to generate a personalized study plan for a player."""

    username: str = Field(..., description="Chess.com username to generate a plan for")
    game_limit: int = Field(
        100,
        description="Maximum games to consider for analysis",
        ge=1,
        le=5000,
    )


class StudyPlanGenerateResponse(BaseModel):
    """Response from generating a study plan."""

    username: str = Field(..., description="Username for which study plan was generated")
    total_weaknesses: int = Field(..., description="Total weakness patterns found", ge=0)
    study_plans_created: int = Field(..., description="Number of study plans created", ge=0)
    priority_distribution: dict[str, int] = Field(
        ...,
        description="Distribution of plans: {high, medium, low}",
    )


class StudyPlanResponse(ORMModel):
    """Response model for a single study plan."""

    id: str = Field(..., description="UUID of the study plan")
    user_id: str = Field(..., description="User identifier")
    weakness_id: int = Field(..., description="Database ID of weakness pattern")
    weakness_name: str | None = Field(None, description="Human-readable weakness name")
    weakness_type: str | None = Field(None, description="Weakness type")
    priority_score: float = Field(..., description="Priority score (0-1)", ge=0, le=1)
    status: str = Field(..., description="Plan status: active, completed, paused")
    concept_count: int = Field(..., description="Number of learning concepts", ge=0)
    created_at: datetime = Field(..., description="When plan was created")


class MarkStudiedRequest(BaseModel):
    """Request body for marking a study plan as studied."""


class MarkStudiedResponse(ORMModel):
    """Response when marking a study plan as studied."""

    id: str = Field(..., description="UUID of the study plan")
    status: str = Field(..., description="New status of plan")
    marked_studied_at: datetime = Field(..., description="When plan was marked as studied")


class ConceptListResponse(BaseModel):
    """Response with list of learning concepts."""

    concepts: list[dict[str, str]] = Field(
        ...,
        description="List of concepts with structure {type, name}",
    )


class StudyProgressResponse(BaseModel):
    """Response for study progress tracking."""

    user_id: str = Field(..., description="User identifier")
    total_plans: int = Field(..., description="Total study plans created", ge=0)
    active_plans: int = Field(..., description="Number of active plans", ge=0)
    completed_plans: int = Field(..., description="Number of completed plans", ge=0)
    completion_rate: float = Field(
        ...,
        description="Percentage of plans completed",
        ge=0,
        le=100,
    )


class StudyGameDetailResponse(ORMModel):
    """Response with detailed game information for a study plan."""

    game_id: int = Field(..., description="Database ID of the game")
    study_plan_id: str = Field(..., description="UUID of related study plan")
    weakness_id: int = Field(..., description="Database ID of weakness pattern")
    result: str = Field(..., description="Game result: win, loss, draw")
    accuracy: float = Field(..., description="Player move accuracy (%)", ge=0, le=100)
    eval_loss: float = Field(..., description="Average centipawn loss in game", ge=0)
    position_fen: str = Field(..., description="FEN string of critical position")
