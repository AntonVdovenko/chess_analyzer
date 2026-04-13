"""SQLAlchemy ORM models for chess analyzer."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Game(Base):
    """Represents a chess.com game."""

    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), index=True)
    opponent_username = Column(String(100))
    opponent_rating = Column(Integer, nullable=True)
    time_control = Column(String(50))
    result = Column(String(10))  # "win", "loss", "draw"
    date = Column(DateTime, index=True)
    pgn = Column(Text)
    white_elo = Column(Integer, nullable=True)
    black_elo = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    positions = relationship("Position", back_populates="game", cascade="all, delete-orphan")


class Position(Base):
    """Represents a position within a game."""

    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), index=True)
    move_number = Column(Integer)
    fen = Column(String(200), index=True)
    player_move = Column(String(10))
    engine_best_move = Column(String(10))
    evaluation_loss = Column(Float)
    evaluation_before = Column(Float)
    evaluation_after = Column(Float)
    is_opening = Column(Boolean, default=False)
    is_middlegame = Column(Boolean, default=False)
    is_endgame = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    game = relationship("Game", back_populates="positions")


class Pattern(Base):
    """Represents aggregated weakness patterns across multiple games."""

    __tablename__ = "patterns"

    id = Column(Integer, primary_key=True, index=True)
    pattern_name = Column(String(200))
    weakness_type = Column(String(50))
    frequency = Column(Integer)
    game_ids = Column(JSON)
    position_features = Column(JSON)
    average_eval_loss = Column(Float)
    player_username = Column(String(100), index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Stats(Base):
    """Represents aggregated statistics per player."""

    __tablename__ = "stats"

    id = Column(Integer, primary_key=True, index=True)
    player_username = Column(String(100), index=True)
    opening_name = Column(String(200), nullable=True)
    total_games = Column(Integer)
    total_accuracy = Column(Float)
    accuracy_by_phase = Column(JSON)
    win_loss_ratio = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class MovePrediction(Base):
    """Move predictions for unusual moves."""

    __tablename__ = "move_predictions"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False, index=True)
    position_fen = Column(String(200), nullable=False)
    actual_move = Column(String(10), nullable=False)
    predicted_move = Column(String(10), nullable=True)
    probability_score = Column(Float, nullable=False)
    is_unusual = Column(Boolean, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    game = relationship("Game", backref="move_predictions")


class Anomaly(Base):
    """Rare, costly mistakes detected by Isolation Forest."""

    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False, index=True)
    position_fen = Column(String(200), nullable=False)
    anomaly_score = Column(Float, nullable=False, index=True)
    centipawn_loss = Column(Float, nullable=False)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    game = relationship("Game", backref="anomalies")


class Embedding(Base):
    """Position embeddings for semantic similarity."""

    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, index=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False, index=True)
    embedding_vector = Column(postgresql.ARRAY(Float), nullable=False)
    embedding_cluster = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    position = relationship("Position", backref="embedding")


class AdvancedAnalysisJob(Base):
    """Track advanced analysis job progress."""

    __tablename__ = "advanced_analysis_jobs"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), nullable=False, index=True)
    job_id = Column(postgresql.UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    status = Column(String(50), nullable=False, index=True, default="processing")
    move_predictor_done = Column(Boolean, default=False)
    anomaly_detector_done = Column(Boolean, default=False)
    embedder_done = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class StudyPlan(Base):
    """Represents a study plan for addressing a weakness pattern."""

    __tablename__ = "study_plans"

    id = Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    weakness_id = Column(Integer, ForeignKey("patterns.id"), nullable=False)
    priority_score = Column(Float, nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)
    marked_studied_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(DateTime, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow())

    # Relationships
    weakness = relationship("Pattern", foreign_keys=[weakness_id])
    study_sessions = relationship("StudySession", back_populates="study_plan", cascade="all, delete-orphan")


class ConceptMap(Base):
    """Represents a concept related to a weakness pattern."""

    __tablename__ = "concept_maps"

    id = Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    weakness_id = Column(Integer, ForeignKey("patterns.id"), nullable=False, index=True)
    concept_type = Column(String(100), nullable=False)
    concept_name = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())


class StudySession(Base):
    """Represents a session of study for a study plan."""

    __tablename__ = "study_sessions"

    id = Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    study_plan_id = Column(postgresql.UUID(as_uuid=True), ForeignKey("study_plans.id"), nullable=False, index=True)
    games_reviewed = Column(JSON, default=list)
    engine_analysis_count = Column(Integer, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    # Relationships
    study_plan = relationship("StudyPlan", back_populates="study_sessions")
