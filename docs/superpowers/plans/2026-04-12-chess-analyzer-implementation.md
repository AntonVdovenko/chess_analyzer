# Chess Analyzer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web-based chess analyzer that identifies repeated player mistakes and weaknesses through ML analysis of chess.com games.

**Architecture:** FastAPI backend performs game fetching, centipawn loss analysis, and ML-based pattern detection. PostgreSQL stores games and analysis results. React frontend visualizes stats, patterns, and study recommendations.

**Tech Stack:** FastAPI, PostgreSQL, Stockfish (self-hosted), python-chess, scikit-learn, React, Fetch API

---

## File Structure

```
chess_analyzer/
├── src/chess_analyzer/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app
│   ├── config.py                        # Configuration
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py                   # SQLAlchemy ORM models
│   │   └── session.py                  # DB connection
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py                   # REST endpoints
│   │   └── schemas.py                  # Pydantic models
│   ├── chess_analyzer/
│   │   ├── __init__.py
│   │   ├── game_fetcher.py             # Chess.com API
│   │   ├── position_analyzer.py        # Stockfish integration
│   │   ├── feature_extractor.py        # Feature engineering
│   │   ├── ml_models/
│   │   │   ├── __init__.py
│   │   │   ├── clustering.py           # K-Means
│   │   │   └── embeddings.py           # Position embeddings
│   │   └── study_planner.py            # Study plan generation
│   └── utils/
│       ├── __init__.py
│       └── chess_utils.py              # Chess helpers
├── tests/
│   ├── __init__.py
│   ├── test_position_analyzer.py
│   ├── test_feature_extractor.py
│   └── test_api.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── PatternExplorer.jsx
│   │   │   ├── GameReview.jsx
│   │   │   └── Settings.jsx
│   │   ├── api.js                      # Fetch wrapper
│   │   ├── App.jsx
│   │   └── index.js
│   ├── package.json
│   └── .gitignore
└── docker-compose.yml
```

---

# PHASE 1: MVP - CORE ANALYSIS ENGINE

This phase builds the end-to-end analysis pipeline for a single player's games.

## Backend Infrastructure Setup

### Task 1: PostgreSQL Database Schema & SQLAlchemy Models

**Files:**
- Create: `src/chess_analyzer/database/models.py`
- Create: `src/chess_analyzer/database/session.py`
- Modify: `pyproject.toml` (add dependencies)

- [ ] **Step 1: Add database dependencies to pyproject.toml**

```toml
dependencies = [
    "fastapi>=0.100.0",
    "uvicorn>=0.24.0",
    "sqlalchemy>=2.0.0",
    "psycopg2-binary>=2.9.0",
    "pydantic>=2.0.0",
    "python-chess>=1.10.0",
    "chess.com>=1.4.1",
    "scikit-learn>=1.3.0",
    "pandas>=2.0.0",
    "numpy>=1.24.0",
    "stockfish>=3.28.0",
]
```

- [ ] **Step 2: Create session.py for database connection**

```python
# src/chess_analyzer/database/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator

DATABASE_URL = "postgresql://user:password@localhost:5432/chess_analyzer"

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator:
    """Dependency for FastAPI to get DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 3: Create models.py with SQLAlchemy ORM models**

```python
# src/chess_analyzer/database/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Game(Base):
    __tablename__ = "games"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), index=True)
    opponent_username = Column(String(100))
    opponent_rating = Column(Integer, nullable=True)
    time_control = Column(String(50))  # "blitz", "rapid", "classical"
    result = Column(String(10))  # "win", "loss", "draw"
    date = Column(DateTime, index=True)
    pgn = Column(Text)  # Raw PGN notation
    white_elo = Column(Integer, nullable=True)
    black_elo = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Position(Base):
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), index=True)
    move_number = Column(Integer)
    fen = Column(String(100), index=True)
    player_move = Column(String(10))  # UCI notation (e.g., "e2e4")
    engine_best_move = Column(String(10))
    evaluation_loss = Column(Float)  # Centipawn loss
    evaluation_before = Column(Float)
    evaluation_after = Column(Float)
    is_opening = Column(Boolean, default=False)
    is_middlegame = Column(Boolean, default=False)
    is_endgame = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Pattern(Base):
    __tablename__ = "patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    pattern_name = Column(String(200))
    weakness_type = Column(String(50))  # "tactical", "positional", "opening", "endgame"
    frequency = Column(Integer)  # How many times this pattern appears
    game_ids = Column(JSON)  # List of game IDs where this occurs
    position_features = Column(JSON)  # Characteristics of positions
    average_eval_loss = Column(Float)
    player_username = Column(String(100), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Stats(Base):
    __tablename__ = "stats"
    
    id = Column(Integer, primary_key=True, index=True)
    player_username = Column(String(100), index=True)
    opening_name = Column(String(200), nullable=True)
    total_games = Column(Integer)
    total_accuracy = Column(Float)  # Average CPL across all games
    accuracy_by_phase = Column(JSON)  # {"opening": 90.2, "middlegame": 80.1, ...}
    win_loss_ratio = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 4: Create database and verify schema**

Run locally:
```bash
cd /Users/User/Workspace/Python/chess_analyzer

# Start PostgreSQL (via Docker or local)
docker run -d --name chess-db \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=chess_analyzer \
  -p 5432:5432 \
  postgres:15

# Create tables
python -c "from src.chess_analyzer.database.models import Base; from src.chess_analyzer.database.session import engine; Base.metadata.create_all(bind=engine)"
```

Expected: No errors, tables created in PostgreSQL

- [ ] **Step 5: Commit**

```bash
git add src/chess_analyzer/database/
git add pyproject.toml
git commit -m "feat: add database models and session management"
```

---

### Task 2: FastAPI Application Setup

**Files:**
- Create: `src/chess_analyzer/main.py`
- Create: `src/chess_analyzer/config.py`

- [ ] **Step 1: Create config.py for settings**

```python
# src/chess_analyzer/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/chess_analyzer"
    STOCKFISH_PATH: str = "/usr/games/stockfish"  # Or wherever stockfish is installed
    CHESS_COM_API_BASE: str = "https://api.chess.com/pub"
    DEBUG: bool = False
    
    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 2: Create main.py for FastAPI app**

```python
# src/chess_analyzer/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.chess_analyzer.api.routes import router as api_router
from src.chess_analyzer.config import settings

app = FastAPI(
    title="Chess Analyzer",
    description="Analyze chess.com games to identify weaknesses",
    version="0.1.0"
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

- [ ] **Step 3: Create .env file with database credentials**

```
DATABASE_URL=postgresql://user:password@localhost:5432/chess_analyzer
STOCKFISH_PATH=/usr/games/stockfish
DEBUG=True
```

- [ ] **Step 4: Test FastAPI starts without errors**

```bash
cd /Users/User/Workspace/Python/chess_analyzer
python -m uvicorn src.chess_analyzer.main:app --reload
```

Expected: Server starts at http://localhost:8000, `/health` returns `{"status": "ok"}`

- [ ] **Step 5: Commit**

```bash
git add src/chess_analyzer/main.py src/chess_analyzer/config.py .env
git commit -m "feat: initialize FastAPI application"
```

---

## Chess Analysis Core

### Task 3: Game Fetcher - Download Games from Chess.com

**Files:**
- Create: `src/chess_analyzer/chess_analyzer/game_fetcher.py`
- Create: `tests/test_game_fetcher.py`

- [ ] **Step 1: Write integration test for game fetching**

```python
# tests/test_game_fetcher.py
import pytest
from src.chess_analyzer.chess_analyzer.game_fetcher import ChessComFetcher

def test_fetch_games_returns_list():
    """Test that fetch_games returns a list of games."""
    fetcher = ChessComFetcher()
    games = fetcher.fetch_games("hikaru", limit=5)
    
    assert isinstance(games, list)
    assert len(games) > 0
    assert all('pgn' in game for game in games)
    assert all('date' in game for game in games)

def test_fetch_games_parsing():
    """Test that games have expected fields."""
    fetcher = ChessComFetcher()
    games = fetcher.fetch_games("hikaru", limit=1)
    
    game = games[0]
    assert 'pgn' in game
    assert 'white' in game
    assert 'black' in game
    assert 'result' in game
    assert 'time_control' in game
```

- [ ] **Step 2: Implement game fetcher**

```python
# src/chess_analyzer/chess_analyzer/game_fetcher.py
from chessdotcom import ChessDotComClient, client
from chess.pgn import StringIO
import chess.pgn
from datetime import datetime
from typing import List, Dict

class ChessComFetcher:
    """Fetch games from chess.com API."""
    
    def __init__(self):
        self.client = ChessDotComClient()
    
    def fetch_games(self, username: str, limit: int = 100) -> List[Dict]:
        """
        Fetch games for a player from chess.com.
        
        Args:
            username: Chess.com username
            limit: Maximum number of games to fetch
        
        Returns:
            List of game dictionaries with pgn, players, result, etc.
        """
        games = []
        
        try:
            # Fetch recent games (chess.com API returns games in reverse chronological order)
            player_data = self.client.get_player_games(username)
            
            for game_data in player_data.json['games'][:limit]:
                game = {
                    'pgn': game_data.get('pgn'),
                    'url': game_data.get('url'),
                    'white': game_data.get('white', {}).get('username'),
                    'black': game_data.get('black', {}).get('username'),
                    'white_elo': game_data.get('white', {}).get('rating'),
                    'black_elo': game_data.get('black', {}).get('rating'),
                    'result': game_data.get('white', {}).get('result'),  # 'win', 'loss', 'draw', 'checkmated', etc.
                    'time_control': game_data.get('time_class'),  # 'blitz', 'rapid', 'classical'
                    'end_time': datetime.fromtimestamp(game_data.get('end_time')),
                }
                games.append(game)
        
        except Exception as e:
            print(f"Error fetching games: {e}")
            raise
        
        return games
```

- [ ] **Step 3: Run test to verify it works**

```bash
cd /Users/User/Workspace/Python/chess_analyzer
pytest tests/test_game_fetcher.py -v
```

Expected: Tests pass (actually fetches from chess.com API)

- [ ] **Step 4: Commit**

```bash
git add src/chess_analyzer/chess_analyzer/game_fetcher.py tests/test_game_fetcher.py
git commit -m "feat: implement chess.com game fetcher"
```

---

### Task 4: Position Analyzer - Stockfish Integration & Centipawn Loss

**Files:**
- Create: `src/chess_analyzer/chess_analyzer/position_analyzer.py`
- Create: `tests/test_position_analyzer.py`

- [ ] **Step 1: Write unit tests for position analyzer**

```python
# tests/test_position_analyzer.py
import pytest
from src.chess_analyzer.chess_analyzer.position_analyzer import PositionAnalyzer

def test_calculate_centipawn_loss():
    """Test centipawn loss calculation."""
    analyzer = PositionAnalyzer()
    
    # Example: eval before move is +0.3, after is -0.8
    loss = analyzer.calculate_centipawn_loss(eval_before=0.3, eval_after=-0.8)
    assert loss == 1.1  # |0.3 - (-0.8)| = 1.1

def test_calculate_centipawn_loss_zero():
    """Test that perfect move has zero loss."""
    analyzer = PositionAnalyzer()
    loss = analyzer.calculate_centipawn_loss(eval_before=0.5, eval_after=0.5)
    assert loss == 0.0

def test_analyze_position_returns_best_move():
    """Test that analyze_position returns engine's best move."""
    analyzer = PositionAnalyzer()
    
    # Starting position
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    result = analyzer.analyze_position(fen, depth=10)
    
    assert 'best_move' in result
    assert 'evaluation' in result
    assert isinstance(result['best_move'], str)
    assert isinstance(result['evaluation'], float)

def test_get_acpl():
    """Test ACPL (average centipawn loss) calculation."""
    analyzer = PositionAnalyzer()
    
    positions = [
        {'eval_before': 0.0, 'eval_after': 0.0},  # CPL = 0
        {'eval_before': 0.5, 'eval_after': 0.2},  # CPL = 0.3
        {'eval_before': 1.0, 'eval_after': 0.0},  # CPL = 1.0
    ]
    
    acpl = analyzer.get_acpl(positions)
    expected_acpl = (0.0 + 0.3 + 1.0) / 3
    assert acpl == pytest.approx(expected_acpl, rel=0.01)
```

- [ ] **Step 2: Implement position analyzer with Stockfish**

```python
# src/chess_analyzer/chess_analyzer/position_analyzer.py
import chess
import chess.engine
from typing import Dict, List, Optional
from src.chess_analyzer.config import settings

class PositionAnalyzer:
    """Analyze chess positions using Stockfish engine."""
    
    def __init__(self, stockfish_path: str = settings.STOCKFISH_PATH):
        self.engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
    
    def calculate_centipawn_loss(self, eval_before: float, eval_after: float) -> float:
        """
        Calculate centipawn loss for a move.
        
        Args:
            eval_before: Evaluation before the move
            eval_after: Evaluation after the move
        
        Returns:
            Centipawn loss (absolute difference)
        """
        return abs(eval_before - eval_after)
    
    def analyze_position(self, fen: str, depth: int = 20, time_limit: float = 1.0) -> Dict:
        """
        Analyze a position using Stockfish.
        
        Args:
            fen: FEN notation of position
            depth: Search depth
            time_limit: Time limit in seconds
        
        Returns:
            Dictionary with best_move, evaluation, etc.
        """
        board = chess.Board(fen)
        
        # Analyze with time limit
        info = self.engine.analyze(board, chess.engine.Limit(time=time_limit))
        
        best_move = info.get("bestmove")
        evaluation = self._evaluation_to_float(info.get("score"))
        
        return {
            'best_move': best_move.uci() if best_move else None,
            'evaluation': evaluation,
            'depth': info.get("depth"),
        }
    
    def _evaluation_to_float(self, score) -> float:
        """Convert Stockfish evaluation to float (centipawns)."""
        if score is None:
            return 0.0
        
        # Score.is_mate() returns True if position is checkmate
        if score.is_mate():
            # Mate: return large positive or negative value
            mate_in_n = score.mate()
            return 10000.0 if mate_in_n > 0 else -10000.0
        
        # Regular evaluation in centipawns
        return float(score.cp) / 100.0
    
    def get_acpl(self, positions: List[Dict]) -> float:
        """
        Calculate ACPL (Average Centipawn Loss) for a game.
        
        Args:
            positions: List of position dicts with eval_before and eval_after
        
        Returns:
            Average centipawn loss
        """
        if not positions:
            return 0.0
        
        cpls = [self.calculate_centipawn_loss(pos['eval_before'], pos['eval_after']) 
                for pos in positions]
        return sum(cpls) / len(cpls)
    
    def close(self):
        """Close the engine."""
        self.engine.quit()
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_position_analyzer.py -v
```

Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add src/chess_analyzer/chess_analyzer/position_analyzer.py tests/test_position_analyzer.py
git commit -m "feat: implement Stockfish integration and centipawn loss calculation"
```

---

### Task 5: PGN Parser - Extract Positions from Games

**Files:**
- Create: `src/chess_analyzer/chess_analyzer/pgn_parser.py`
- Create: `tests/test_pgn_parser.py`

- [ ] **Step 1: Write tests for PGN parsing**

```python
# tests/test_pgn_parser.py
import pytest
from src.chess_analyzer.chess_analyzer.pgn_parser import PGNParser

def test_parse_pgn_returns_moves():
    """Test that parse_pgn extracts moves from PGN."""
    parser = PGNParser()
    
    # Sample PGN (fool's mate)
    pgn_string = """[Event "Casual Game"]
[Site "https://www.chess.com"]
[White "Player1"]
[Black "Player2"]

1. f3 e5 2. g4 Qh4# 0-1"""
    
    result = parser.parse_pgn(pgn_string)
    
    assert 'moves' in result
    assert len(result['moves']) > 0
    assert all('move' in m for m in result['moves'])
    assert all('fen' in m for m in result['moves'])

def test_parse_pgn_extracts_metadata():
    """Test that parse_pgn extracts game metadata."""
    parser = PGNParser()
    
    pgn_string = """[Event "Casual Game"]
[White "Player1"]
[Black "Player2"]
[Result "0-1"]

1. e4 c5 0-1"""
    
    result = parser.parse_pgn(pgn_string)
    
    assert result['white'] == "Player1"
    assert result['black'] == "Player2"
    assert result['result'] == "0-1"
```

- [ ] **Step 2: Implement PGN parser**

```python
# src/chess_analyzer/chess_analyzer/pgn_parser.py
import chess.pgn
from chess.pgn import StringIO
from typing import Dict, List

class PGNParser:
    """Parse PGN files and extract positions."""
    
    def parse_pgn(self, pgn_string: str) -> Dict:
        """
        Parse a PGN string and extract moves and positions.
        
        Args:
            pgn_string: PGN notation as string
        
        Returns:
            Dictionary with metadata and list of moves with positions
        """
        game = chess.pgn.read_game(StringIO(pgn_string))
        
        if game is None:
            raise ValueError("Invalid PGN")
        
        # Extract metadata
        headers = game.headers
        
        # Extract moves and positions
        moves_with_positions = []
        board = game.board()
        move_number = 0
        
        for move in game.mainline_moves():
            move_number += 1
            
            # Position BEFORE the move
            fen_before = board.fen()
            eval_before = None  # Will be filled in by position analyzer
            
            # Make the move
            board.push(move)
            
            # Position AFTER the move
            fen_after = board.fen()
            eval_after = None  # Will be filled in by position analyzer
            
            moves_with_positions.append({
                'move_number': move_number,
                'uci_move': move.uci(),
                'san_move': game.san(move),
                'fen_before': fen_before,
                'fen_after': fen_after,
                'eval_before': eval_before,
                'eval_after': eval_after,
            })
        
        return {
            'white': headers.get('White', 'Unknown'),
            'black': headers.get('Black', 'Unknown'),
            'event': headers.get('Event', 'Unknown'),
            'date': headers.get('Date', 'Unknown'),
            'result': headers.get('Result', '*'),
            'time_control': headers.get('TimeControl', 'Unknown'),
            'white_elo': int(headers.get('WhiteElo', 0)) if headers.get('WhiteElo', '').isdigit() else None,
            'black_elo': int(headers.get('BlackElo', 0)) if headers.get('BlackElo', '').isdigit() else None,
            'moves': moves_with_positions,
        }
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_pgn_parser.py -v
```

Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add src/chess_analyzer/chess_analyzer/pgn_parser.py tests/test_pgn_parser.py
git commit -m "feat: implement PGN parser to extract positions"
```

---

### Task 6: Feature Extractor - Extract Position Features

**Files:**
- Create: `src/chess_analyzer/chess_analyzer/feature_extractor.py`
- Create: `tests/test_feature_extractor.py`

- [ ] **Step 1: Write tests for feature extraction**

```python
# tests/test_feature_extractor.py
import pytest
from src.chess_analyzer.chess_analyzer.feature_extractor import FeatureExtractor

def test_extract_material_balance():
    """Test material count extraction."""
    extractor = FeatureExtractor()
    
    # Starting position
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    material = extractor.extract_material_balance(fen)
    
    assert material == 0.0  # Equal material

def test_extract_material_balance_endgame():
    """Test material count in endgame."""
    extractor = FeatureExtractor()
    
    # White has queen, black has rook
    fen = "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1"
    material = extractor.extract_material_balance(fen)
    
    assert material > 0  # White is ahead

def test_extract_all_features():
    """Test that extract_all_features returns expected fields."""
    extractor = FeatureExtractor()
    
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    features = extractor.extract_all_features(fen)
    
    assert 'material_balance' in features
    assert 'piece_activity' in features
    assert 'king_safety' in features
    assert isinstance(features['material_balance'], (int, float))
```

- [ ] **Step 2: Implement feature extractor**

```python
# src/chess_analyzer/chess_analyzer/feature_extractor.py
import chess
from typing import Dict

class FeatureExtractor:
    """Extract numerical features from chess positions."""
    
    def extract_material_balance(self, fen: str) -> float:
        """
        Extract material balance (white - black).
        
        Piece values: Pawn=1, Knight=3, Bishop=3, Rook=5, Queen=9
        """
        board = chess.Board(fen)
        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 0,
        }
        
        white_material = sum(piece_values[piece.piece_type] 
                            for piece in board.pieces_mask(chess.WHITE))
        black_material = sum(piece_values[piece.piece_type] 
                            for piece in board.pieces_mask(chess.BLACK))
        
        return float(white_material - black_material)
    
    def extract_piece_activity(self, fen: str) -> float:
        """
        Extract piece activity (number of legal moves available).
        Normalized to 0-100 scale.
        """
        board = chess.Board(fen)
        num_moves = board.legal_moves.count()
        
        # Typical game has 30-60 legal moves available
        # Normalize to 0-100
        return min(100.0, (num_moves / 60.0) * 100.0)
    
    def extract_king_safety(self, fen: str) -> float:
        """
        Extract king safety metric (0-100).
        Lower = safer king.
        
        Considers: king in center, castling rights, pawn shield
        """
        board = chess.Board(fen)
        
        white_king_pos = board.king(chess.WHITE)
        black_king_pos = board.king(chess.BLACK)
        
        safety_score = 0.0
        
        # King in center is dangerous
        white_king_file = chess.square_file(white_king_pos)
        white_king_rank = chess.square_rank(white_king_pos)
        
        # Distance from center (center is file 3-4, rank 3-4)
        center_distance = abs(white_king_file - 3.5) + abs(white_king_rank - 3.5)
        
        # King safety: higher score = more exposed
        safety_score = 100.0 - (center_distance * 10.0)
        
        return max(0.0, min(100.0, safety_score))
    
    def extract_all_features(self, fen: str) -> Dict[str, float]:
        """Extract all relevant features from a position."""
        return {
            'material_balance': self.extract_material_balance(fen),
            'piece_activity': self.extract_piece_activity(fen),
            'king_safety': self.extract_king_safety(fen),
        }
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_feature_extractor.py -v
```

Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add src/chess_analyzer/chess_analyzer/feature_extractor.py tests/test_feature_extractor.py
git commit -m "feat: implement chess position feature extraction"
```

---

## ML Analysis Core

### Task 7: K-Means Clustering for Weakness Patterns

**Files:**
- Create: `src/chess_analyzer/chess_analyzer/ml_models/clustering.py`
- Create: `tests/test_clustering.py`

- [ ] **Step 1: Write tests for clustering**

```python
# tests/test_clustering.py
import pytest
import numpy as np
from src.chess_analyzer.chess_analyzer.ml_models.clustering import WeaknessClustering

def test_kmeans_clustering():
    """Test K-Means clustering on mistake positions."""
    clusterer = WeaknessClustering()
    
    # Create sample features (3 positions with 3 features each)
    features = np.array([
        [1.0, 2.0, 3.0],
        [1.1, 2.1, 3.1],
        [10.0, 20.0, 30.0],
    ])
    
    clusters = clusterer.cluster_positions(features, n_clusters=2)
    
    assert len(clusters) == 2
    assert 0 in clusters  # Cluster 0
    assert 1 in clusters  # Cluster 1

def test_elbow_method():
    """Test elbow method for finding optimal K."""
    clusterer = WeaknessClustering()
    
    # Create sample data with clear structure
    features = np.vstack([
        np.random.randn(20, 2) + [0, 0],   # Cluster 1
        np.random.randn(20, 2) + [10, 10], # Cluster 2
        np.random.randn(20, 2) + [20, 0],  # Cluster 3
    ])
    
    optimal_k = clusterer.find_optimal_k(features, k_range=range(2, 6))
    
    # Should find around 3 clusters
    assert 2 <= optimal_k <= 4
```

- [ ] **Step 2: Implement K-Means clustering**

```python
# src/chess_analyzer/chess_analyzer/ml_models/clustering.py
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from typing import List, Dict

class WeaknessClustering:
    """Cluster positions into weakness themes using K-Means."""
    
    def cluster_positions(self, features: np.ndarray, n_clusters: int = 4) -> List[int]:
        """
        Cluster positions using K-Means.
        
        Args:
            features: Array of shape (n_positions, n_features)
            n_clusters: Number of clusters
        
        Returns:
            List of cluster labels for each position
        """
        # Standardize features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        # Fit K-Means
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(features_scaled)
        
        return clusters.tolist()
    
    def find_optimal_k(self, features: np.ndarray, k_range: range = range(2, 7)) -> int:
        """
        Find optimal number of clusters using elbow method.
        
        Args:
            features: Array of shape (n_positions, n_features)
            k_range: Range of K values to test
        
        Returns:
            Optimal number of clusters
        """
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        inertias = []
        
        for k in k_range:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(features_scaled)
            inertias.append(kmeans.inertia_)
        
        # Find elbow point (where inertia decreases slowest)
        # Simple heuristic: steepest decrease is the elbow
        diffs = np.diff(inertias)
        elbow_idx = np.argmin(np.diff(diffs)) + 1
        
        optimal_k = list(k_range)[elbow_idx]
        return optimal_k
    
    def label_clusters(self, clusters: List[int], position_features: List[Dict]) -> Dict[int, Dict]:
        """
        Generate human-readable labels for clusters.
        
        Args:
            clusters: List of cluster IDs for each position
            position_features: List of feature dicts for each position
        
        Returns:
            Dictionary mapping cluster ID to cluster info
        """
        cluster_info = {}
        
        for cluster_id in set(clusters):
            # Get all positions in this cluster
            cluster_positions = [
                position_features[i] for i, c in enumerate(clusters) if c == cluster_id
            ]
            
            # Calculate cluster characteristics
            avg_material = np.mean([p.get('material_balance', 0) for p in cluster_positions])
            avg_king_safety = np.mean([p.get('king_safety', 50) for p in cluster_positions])
            
            # Generate label based on characteristics
            label = self._generate_label(avg_material, avg_king_safety)
            
            cluster_info[cluster_id] = {
                'label': label,
                'size': len(cluster_positions),
                'avg_material': float(avg_material),
                'avg_king_safety': float(avg_king_safety),
                'positions': len(cluster_positions),
            }
        
        return cluster_info
    
    def _generate_label(self, avg_material: float, avg_king_safety: float) -> str:
        """Generate human-readable label for a cluster."""
        if avg_king_safety > 60:
            return "Weak king safety"
        elif avg_material < -2:
            return "Material disadvantage"
        elif avg_material > 2:
            return "Material advantage / overextended"
        else:
            return "Tactical positions"
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_clustering.py -v
```

Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add src/chess_analyzer/chess_analyzer/ml_models/clustering.py tests/test_clustering.py
git commit -m "feat: implement K-Means clustering for weakness patterns"
```

---

### Task 8: Analysis Pipeline - Orchestrate All Analysis Steps

**Files:**
- Create: `src/chess_analyzer/chess_analyzer/analysis_pipeline.py`
- Create: `tests/test_analysis_pipeline.py`

- [ ] **Step 1: Write integration test for analysis pipeline**

```python
# tests/test_analysis_pipeline.py
import pytest
from src.chess_analyzer.chess_analyzer.analysis_pipeline import AnalysisPipeline

def test_analyze_games_end_to_end():
    """Test complete analysis pipeline."""
    pipeline = AnalysisPipeline()
    
    # Sample PGN
    pgn_data = [
        {
            'pgn': """[White "Player1"][Black "Player2"]\n1. e4 e5 2. Nf3 Nc6 0-1""",
            'white': 'Player1',
            'black': 'Player2',
            'result': '0-1',
        }
    ]
    
    result = pipeline.analyze_games(pgn_data, player_perspective='white')
    
    assert 'games_analyzed' in result
    assert 'total_acpl' in result
    assert 'patterns' in result
    assert result['games_analyzed'] == 1
```

- [ ] **Step 2: Implement analysis pipeline**

```python
# src/chess_analyzer/chess_analyzer/analysis_pipeline.py
from src.chess_analyzer.chess_analyzer.pgn_parser import PGNParser
from src.chess_analyzer.chess_analyzer.position_analyzer import PositionAnalyzer
from src.chess_analyzer.chess_analyzer.feature_extractor import FeatureExtractor
from src.chess_analyzer.chess_analyzer.ml_models.clustering import WeaknessClustering
from typing import List, Dict
import numpy as np

class AnalysisPipeline:
    """Orchestrate the complete analysis pipeline."""
    
    def __init__(self):
        self.pgn_parser = PGNParser()
        self.position_analyzer = PositionAnalyzer()
        self.feature_extractor = FeatureExtractor()
        self.clusterer = WeaknessClustering()
    
    def analyze_games(self, pgn_data: List[Dict], player_perspective: str = 'white') -> Dict:
        """
        Analyze a list of games and extract patterns.
        
        Args:
            pgn_data: List of dicts with 'pgn', 'white', 'black', 'result' keys
            player_perspective: 'white' or 'black' - which side to analyze
        
        Returns:
            Dictionary with analysis results
        """
        all_positions = []
        mistake_positions = []
        acpls = []
        
        for game_pgn_dict in pgn_data:
            # Parse PGN
            parsed = self.pgn_parser.parse_pgn(game_pgn_dict['pgn'])
            
            # Analyze each position
            game_positions = []
            for pos_idx, move_data in enumerate(parsed['moves']):
                fen = move_data['fen_before']
                
                # Analyze position with engine
                analysis = self.position_analyzer.analyze_position(fen, depth=15, time_limit=0.5)
                
                # Position after move (where we evaluate the move quality)
                fen_after = move_data['fen_after']
                analysis_after = self.position_analyzer.analyze_position(fen_after, depth=15, time_limit=0.5)
                
                # Centipawn loss
                eval_before = analysis['evaluation']
                eval_after = analysis_after['evaluation']
                cpl = self.position_analyzer.calculate_centipawn_loss(eval_before, eval_after)
                
                # Store position data
                position_record = {
                    'move_number': move_data['move_number'],
                    'fen': fen_after,
                    'move': move_data['uci_move'],
                    'cpl': cpl,
                    'eval_before': eval_before,
                    'eval_after': eval_after,
                }
                
                # Extract features
                features = self.feature_extractor.extract_all_features(fen_after)
                position_record.update(features)
                
                game_positions.append(position_record)
                all_positions.append(position_record)
                
                # Identify mistakes (CPL > 50 centipawns)
                if cpl > 50:
                    mistake_positions.append(position_record)
            
            # Calculate ACPL for game
            game_acpl = self.position_analyzer.get_acpl([
                {'eval_before': p['eval_before'], 'eval_after': p['eval_after']}
                for p in game_positions
            ])
            acpls.append(game_acpl)
        
        # Cluster mistake positions
        if mistake_positions:
            features_array = np.array([
                [p['material_balance'], p['piece_activity'], p['king_safety']]
                for p in mistake_positions
            ])
            
            optimal_k = self.clusterer.find_optimal_k(features_array, k_range=range(2, min(6, len(mistake_positions))))
            clusters = self.clusterer.cluster_positions(features_array, n_clusters=optimal_k)
            
            # Create cluster info
            cluster_info = self.clusterer.label_clusters(clusters, mistake_positions)
        else:
            cluster_info = {}
        
        return {
            'games_analyzed': len(pgn_data),
            'total_acpl': float(np.mean(acpls)) if acpls else 0.0,
            'total_positions': len(all_positions),
            'mistake_positions': len(mistake_positions),
            'patterns': cluster_info,
            'all_positions': all_positions,
            'mistake_positions_list': mistake_positions,
        }
    
    def close(self):
        """Clean up resources."""
        self.position_analyzer.close()
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_analysis_pipeline.py -v
```

Expected: Test passes (may take a while due to engine analysis)

- [ ] **Step 4: Commit**

```bash
git add src/chess_analyzer/chess_analyzer/analysis_pipeline.py tests/test_analysis_pipeline.py
git commit -m "feat: implement analysis pipeline orchestration"
```

---

## API Layer

### Task 9: REST API Endpoints - Game Analysis

**Files:**
- Create: `src/chess_analyzer/api/schemas.py`
- Create: `src/chess_analyzer/api/routes.py`

- [ ] **Step 1: Create Pydantic schemas for request/response**

```python
# src/chess_analyzer/api/schemas.py
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

class AnalyzeRequest(BaseModel):
    username: str
    limit: int = 100

class AnalysisStatus(BaseModel):
    status: str  # "pending", "analyzing", "completed"
    task_id: str
    games_analyzed: int = 0
    patterns_found: int = 0

class GameResponse(BaseModel):
    id: int
    opponent_username: str
    result: str
    date: datetime
    accuracy: float

class PatternResponse(BaseModel):
    id: int
    name: str
    weakness_type: str
    frequency: int
    average_eval_loss: float

class StatsResponse(BaseModel):
    total_games: int
    overall_accuracy: float
    accuracy_by_phase: Dict[str, float]
    weakness_summary: List[Dict]

class StudyPlanResponse(BaseModel):
    games_to_review: List[Dict]
    weak_points: List[Dict]
```

- [ ] **Step 2: Create API routes**

```python
# src/chess_analyzer/api/routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.chess_analyzer.database.session import get_db
from src.chess_analyzer.database.models import Game, Position, Pattern, Stats
from src.chess_analyzer.api.schemas import AnalyzeRequest, GameResponse, StatsResponse
from src.chess_analyzer.chess_analyzer.game_fetcher import ChessComFetcher
from src.chess_analyzer.chess_analyzer.analysis_pipeline import AnalysisPipeline
from datetime import datetime
from typing import List

router = APIRouter()

# In-memory task tracker (replace with Celery in production)
analysis_tasks = {}
task_counter = 0

@router.post("/analyze")
def analyze_games(request: AnalyzeRequest, db: Session = Depends(get_db)):
    """Start analysis job for a player."""
    global task_counter
    task_counter += 1
    task_id = f"task_{task_counter}"
    
    # Fetch games
    fetcher = ChessComFetcher()
    games = fetcher.fetch_games(request.username, limit=request.limit)
    
    # Store in DB
    for game in games:
        db_game = Game(
            username=request.username,
            opponent_username=game.get('black') if game.get('white') == request.username else game.get('white'),
            opponent_rating=game.get('black_elo') if game.get('white') == request.username else game.get('white_elo'),
            time_control=game.get('time_control'),
            result=game.get('result'),
            date=game.get('end_time'),
            pgn=game.get('pgn'),
            white_elo=game.get('white_elo'),
            black_elo=game.get('black_elo'),
        )
        db.add(db_game)
    
    db.commit()
    
    # Store task status
    analysis_tasks[task_id] = {
        'status': 'analyzing',
        'games_analyzed': len(games),
        'patterns_found': 0,
    }
    
    return {
        'status': 'analyzing',
        'task_id': task_id,
        'message': f'Analyzing {len(games)} games...'
    }

@router.get("/analysis/{task_id}")
def get_analysis_status(task_id: str):
    """Check analysis progress."""
    if task_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return analysis_tasks[task_id]

@router.get("/games")
def list_games(username: str, limit: int = 20, offset: int = 0, db: Session = Depends(get_db)):
    """List all analyzed games for a player."""
    games = db.query(Game).filter(Game.username == username).limit(limit).offset(offset).all()
    
    return [
        {
            'id': g.id,
            'opponent': g.opponent_username,
            'result': g.result,
            'date': g.date.isoformat(),
            'accuracy': 85.0,  # Placeholder
        }
        for g in games
    ]

@router.get("/stats")
def get_stats(username: str, db: Session = Depends(get_db)):
    """Get dashboard statistics."""
    stats = db.query(Stats).filter(Stats.player_username == username).first()
    
    if not stats:
        raise HTTPException(status_code=404, detail="No stats for this player")
    
    return {
        'total_games': stats.total_games,
        'overall_accuracy': stats.total_accuracy,
        'accuracy_by_phase': stats.accuracy_by_phase,
        'weakness_summary': [
            {'weakness': 'King safety', 'frequency': 5, 'avg_loss': 150},
            {'weakness': 'Endgame', 'frequency': 3, 'avg_loss': 200},
        ]
    }
```

- [ ] **Step 3: Test API endpoints**

```bash
# Start server
python -m uvicorn src.chess_analyzer.main:app --reload

# In another terminal
curl http://localhost:8000/health
# Expected: {"status": "ok"}

curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"username": "hikaru", "limit": 5}'
# Expected: {"status": "analyzing", "task_id": "task_1", ...}
```

- [ ] **Step 4: Commit**

```bash
git add src/chess_analyzer/api/
git commit -m "feat: implement REST API endpoints for game analysis"
```

---

## Frontend

### Task 10: React Setup & Dashboard Component

**Files:**
- Create: `frontend/` directory with React app
- Create: `frontend/src/api.js`
- Create: `frontend/src/components/Dashboard.jsx`

- [ ] **Step 1: Initialize React app**

```bash
cd /Users/User/Workspace/Python/chess_analyzer
npx create-react-app frontend
cd frontend
npm install react-router-dom recharts
```

- [ ] **Step 2: Create API wrapper with Fetch**

```javascript
// frontend/src/api.js
const API_BASE = 'http://localhost:8000/api';

export async function apiCall(endpoint, options = {}) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  
  if (!response.ok) {
    throw new Error(`API error ${response.status}`);
  }
  
  return response.json();
}

export const chessAPI = {
  analyzeGames: (username, limit = 100) =>
    apiCall('/analyze', {
      method: 'POST',
      body: JSON.stringify({ username, limit }),
    }),
  
  getAnalysisStatus: (taskId) =>
    apiCall(`/analysis/${taskId}`),
  
  listGames: (username, limit = 20, offset = 0) =>
    apiCall(`/games?username=${username}&limit=${limit}&offset=${offset}`),
  
  getStats: (username) =>
    apiCall(`/stats?username=${username}`),
};
```

- [ ] **Step 3: Create Dashboard component**

```jsx
// frontend/src/components/Dashboard.jsx
import React, { useState, useEffect } from 'react';
import { chessAPI } from '../api';

export default function Dashboard() {
  const [username, setUsername] = useState('');
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const handleAnalyze = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      const result = await chessAPI.analyzeGames(username, 100);
      console.log('Analysis started:', result);
      
      // Fetch stats after analysis
      const statsData = await chessAPI.getStats(username);
      setStats(statsData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div style={{ padding: '20px' }}>
      <h1>Chess Analyzer</h1>
      
      <form onSubmit={handleAnalyze}>
        <input
          type="text"
          placeholder="Enter chess.com username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Analyzing...' : 'Analyze Games'}
        </button>
      </form>
      
      {error && <div style={{ color: 'red' }}>Error: {error}</div>}
      
      {stats && (
        <div style={{ marginTop: '20px' }}>
          <h2>Statistics</h2>
          <p>Total Games: {stats.total_games}</p>
          <p>Overall Accuracy: {stats.overall_accuracy.toFixed(1)}%</p>
          
          <h3>Accuracy by Phase</h3>
          <ul>
            {Object.entries(stats.accuracy_by_phase).map(([phase, acc]) => (
              <li key={phase}>{phase}: {acc.toFixed(1)}%</li>
            ))}
          </ul>
          
          <h3>Top Weaknesses</h3>
          <ul>
            {stats.weakness_summary.map((w, idx) => (
              <li key={idx}>{w.weakness}: {w.frequency} occurrences</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Create App.jsx**

```jsx
// frontend/src/App.jsx
import React from 'react';
import Dashboard from './components/Dashboard';
import './App.css';

function App() {
  return (
    <div className="App">
      <Dashboard />
    </div>
  );
}

export default App;
```

- [ ] **Step 5: Run React app**

```bash
cd /Users/User/Workspace/Python/chess_analyzer/frontend
npm start
```

Expected: App runs at http://localhost:3000

- [ ] **Step 6: Commit frontend code**

```bash
cd /Users/User/Workspace/Python/chess_analyzer
git add frontend/
git commit -m "feat: initialize React dashboard with analysis UI"
```

---

# SUCCESS CRITERIA - PHASE 1 MVP

After completing all Phase 1 tasks, you should be able to:

✅ **Backend:**
- [ ] FastAPI server runs without errors
- [ ] PostgreSQL database has correct schema
- [ ] Can fetch games from chess.com API
- [ ] Can parse PGN and extract positions
- [ ] Can analyze positions with Stockfish
- [ ] Can calculate centipawn loss (CPL) and ACPL
- [ ] Can cluster weakness positions with K-Means
- [ ] REST endpoints respond with correct data

✅ **Frontend:**
- [ ] React app loads at localhost:3000
- [ ] Can input chess.com username
- [ ] Can trigger analysis via API
- [ ] Can display stats and weaknesses
- [ ] Uses Fetch API (no Axios)

✅ **End-to-End:**
- [ ] Analyze 50+ games from chess.com
- [ ] Identify 4-6 weakness patterns
- [ ] Generate ACPL statistics
- [ ] Display patterns on dashboard

---

# NEXT PHASES (Phase 2, 3, 4)

Once Phase 1 is complete:

**Phase 2: Advanced Analysis**
- Move prediction model (Maia-inspired)
- Anomaly detection (Isolation Forest)
- Position embeddings (cosine similarity)
- Pattern explorer UI with filtering

**Phase 3: Study Planning**
- Study plan generation algorithm
- Thematic grouping of weaknesses
- Game recommendations
- Study plan UI page

**Phase 4: Polish & Scale**
- Async analysis jobs (Celery/Redis)
- Performance optimization
- Mobile responsiveness
- Docker deployment

---

**Document Version**: 1.0  
**Status**: Ready for execution  
**Execution Method**: Use superpowers:subagent-driven-development or superpowers:executing-plans

