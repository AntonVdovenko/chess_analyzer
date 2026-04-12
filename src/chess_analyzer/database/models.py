"""SQLAlchemy ORM models for chess analyzer."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Game(Base):
    """Represents a chess.com game."""

    __tablename__ = "games"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String(50), unique=True, nullable=False, index=True)
    player_username = Column(String(100), nullable=False, index=True)
    opponent_username = Column(String(100), nullable=False)
    player_color = Column(String(5), nullable=False)  # "white" or "black"
    result = Column(String(10), nullable=False)  # "win", "loss", "draw"
    time_control = Column(String(50), nullable=False)  # e.g. "bullet", "blitz", "rapid"
    played_at = Column(DateTime, nullable=False, index=True)
    pgn = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    positions = relationship("Position", back_populates="game", cascade="all, delete-orphan")
    stats = relationship("Stats", back_populates="game", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("game_id", "player_username", name="uq_game_player"),)


class Position(Base):
    """Represents a position within a game."""

    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False, index=True)
    move_number = Column(Integer, nullable=False)  # 1-indexed
    fen = Column(String(100), nullable=False)
    player_side = Column(String(5), nullable=False)  # "white" or "black"
    best_move = Column(String(10), nullable=True)  # e.g. "e2e4"
    actual_move = Column(String(10), nullable=False)
    centipawn_loss = Column(Float, nullable=True)  # Difference in eval before/after move
    is_blunder = Column(Integer, nullable=False, default=0)  # Boolean: 1 or 0
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    game = relationship("Game", back_populates="positions")
    pattern = relationship("Pattern", back_populates="position", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("game_id", "move_number", name="uq_game_move"),)


class Pattern(Base):
    """Represents a weakness pattern identified in positions."""

    __tablename__ = "patterns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False, index=True)
    cluster_id = Column(Integer, nullable=False)  # K-means cluster assignment
    pattern_type = Column(String(50), nullable=False)  # e.g. "opening_mistake", "tactical_miss"
    severity = Column(Float, nullable=False)  # 0.0 to 1.0 - how severe the weakness
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    position = relationship("Position", back_populates="pattern")


class Stats(Base):
    """Represents aggregated statistics for a game analysis."""

    __tablename__ = "stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False, unique=True, index=True)
    total_blunders = Column(Integer, nullable=False, default=0)
    total_centipawn_loss = Column(Float, nullable=False, default=0.0)
    average_centipawn_loss = Column(Float, nullable=False, default=0.0)
    accuracy = Column(Float, nullable=False, default=0.0)  # Percentage 0-100
    weak_phases = Column(String(100), nullable=True)  # JSON-encoded list of phases
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    game = relationship("Game", back_populates="stats")
