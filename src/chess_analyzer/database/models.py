"""SQLAlchemy ORM models for chess analyzer."""

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
)
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
