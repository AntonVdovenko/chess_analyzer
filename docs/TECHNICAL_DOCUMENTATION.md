# Chess Analyzer - Technical Documentation

**Date**: April 12, 2026  
**Version**: Phase 1 Complete  
**Status**: Production Ready

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Component Documentation](#component-documentation)
3. [API Reference](#api-reference)
4. [Database Schema](#database-schema)
5. [Code Organization](#code-organization)
6. [Configuration](#configuration)
7. [Installation & Deployment](#installation--deployment)
8. [Development Workflow](#development-workflow)
9. [Testing Strategy](#testing-strategy)
10. [Performance Considerations](#performance-considerations)
11. [Security Considerations](#security-considerations)
12. [Troubleshooting](#troubleshooting)
13. [Future Enhancements](#future-enhancements)

---

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend Layer                           │
│         React 19 Dashboard (localhost:3000)                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Components: Dashboard.jsx, API wrapper (Fetch)       │   │
│  │ Styles: CSS3 Grid, Responsive Layout                │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/JSON (CORS-enabled)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Layer                               │
│         FastAPI Backend (localhost:8000)                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Routes: 7 endpoints with Pydantic validation         │   │
│  │ Schemas: Request/Response models                      │   │
│  │ Middleware: CORS for localhost:3000                  │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
    ┌────────┐  ┌──────────┐  ┌────────────┐
    │  Data  │  │ Analysis │  │ Database   │
    │ Layer  │  │  Engine  │  │   Layer    │
    └────────┘  └──────────┘  └────────────┘
        │              │              │
        ▼              ▼              ▼
    ┌────────────────────────────────────────┐
    │  PostgreSQL (chess_analyzer database)  │
    │  Tables: games, positions, patterns,   │
    │          stats                         │
    └────────────────────────────────────────┘
        │              │
        ▼              ▼
    ┌────────┐  ┌──────────────────┐
    │chess.  │  │   Stockfish      │
    │com API │  │  Chess Engine    │
    └────────┘  └──────────────────┘
```

### Data Flow

1. **User Input** → Dashboard form captures chess.com username
2. **API Call** → Frontend sends POST request to `/api/analyze`
3. **Analysis Pipeline** → Backend orchestrates:
   - Game Fetcher → Retrieve games from chess.com
   - PGN Parser → Extract positions and moves
   - Position Analyzer → Evaluate positions with Stockfish
   - Feature Extractor → Calculate features (material, activity, king safety)
   - ML Clustering → Group similar weaknesses
4. **Database Storage** → Results saved to PostgreSQL
5. **Response** → Frontend displays stats and patterns
6. **Display** → User sees statistics, patterns, and study recommendations

---

## Component Documentation

### Backend Components

#### 1. Game Fetcher (`chess_analyzer/game_fetcher.py`)

**Purpose**: Retrieve games from chess.com API

**Class**: `ChessComFetcher`

**Key Methods**:
- `fetch_games(username: str, limit: int = 100) -> List[Dict]`
  - Fetches games for a player
  - Handles pagination automatically
  - Filters out incomplete games
  - Returns normalized game data

**Dependencies**:
- `chess.com` Python package
- Network connectivity to chess.com

**Error Handling**:
- Catches API timeout errors
- Handles rate limiting
- Returns empty list on network failure

**Example Usage**:
```python
from src.chess_analyzer.chess_analyzer.game_fetcher import ChessComFetcher

fetcher = ChessComFetcher()
games = fetcher.fetch_games("hikaru", limit=100)
```

---

#### 2. PGN Parser (`chess_analyzer/pgn_parser.py`)

**Purpose**: Parse PGN notation and extract positions

**Class**: `PGNParser`

**Key Methods**:
- `parse_pgn(pgn_string: str) -> Dict`
  - Parses PGN notation
  - Extracts all positions
  - Captures game metadata (date, players, result)
  - Returns structured data

**Dependencies**:
- `python-chess` library

**Supported**:
- Standard PGN format (1.e4 e5 2.Nf3 ...)
- Metadata tags ([Site], [Date], etc.)
- Multiple games in single file

**Example Usage**:
```python
from src.chess_analyzer.chess_analyzer.pgn_parser import PGNParser

parser = PGNParser()
result = parser.parse_pgn(pgn_string)
print(result['positions'])  # List of FEN strings
```

---

#### 3. Position Analyzer (`chess_analyzer/position_analyzer.py`)

**Purpose**: Evaluate positions using Stockfish engine

**Class**: `PositionAnalyzer`

**Key Methods**:
- `evaluate_position(fen: str) -> float`
  - Returns evaluation in centipawns
  - Positive = white advantage
  - Negative = black advantage

- `calculate_move_loss(fen: str, move: str, best_eval: float) -> float`
  - Calculates centipawn loss (CPL) for a move
  - CPL = evaluation_before - evaluation_after
  - Higher CPL = worse move

- `aggregate_game_loss(game_data: Dict) -> float`
  - Calculates ACPL (Average CPL) for entire game
  - Used to assess overall game quality

**Configuration**:
- Stockfish path (from environment variable `STOCKFISH_PATH`)
- Search depth: 20 plies (adjustable)
- Time limit: 1 second per position (configurable)

**Dependencies**:
- Stockfish chess engine (binary)
- `python-chess` library

**Example Usage**:
```python
from src.chess_analyzer.chess_analyzer.position_analyzer import PositionAnalyzer

analyzer = PositionAnalyzer()
eval_score = analyzer.evaluate_position("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
loss = analyzer.calculate_move_loss(fen, "e2e4", best_eval)
```

---

#### 4. Feature Extractor (`chess_analyzer/feature_extractor.py`)

**Purpose**: Extract numerical features from positions

**Class**: `FeatureExtractor`

**Key Methods**:
- `extract_features(fen: str) -> Dict[str, float]`
  - Material balance (pawn-weighted piece count difference)
  - Piece activity (mobility and positional scores)
  - King safety (pawn shield evaluation)
  - Returns feature vector

**Features Extracted**:
1. **Material Balance**: Difference in material (P=1, N=3, B=3, R=5, Q=9)
2. **Piece Activity**: Weighted by number of squares controlled
3. **King Safety**: Evaluated by pawn shield integrity and piece proximity

**Usage in ML**:
- Input to K-Means clustering
- Helps identify position types in patterns
- Scales 0-100 for normalization

**Example Usage**:
```python
from src.chess_analyzer.chess_analyzer.feature_extractor import FeatureExtractor

extractor = FeatureExtractor()
features = extractor.extract_features(fen)
# Returns: {'material_balance': 0.5, 'piece_activity': 0.75, 'king_safety': 0.6}
```

---

#### 5. K-Means Clustering (`chess_analyzer/ml_models/clustering.py`)

**Purpose**: Group similar weak positions using ML

**Class**: `WeaknessClustering`

**Key Methods**:
- `fit_clusters(features: np.ndarray, max_k: int = 10) -> Dict`
  - Uses elbow method to find optimal K
  - Fits K-Means model
  - Returns cluster assignments and centers

- `generate_labels(features: np.ndarray, clusters: np.ndarray) -> List[str]`
  - Creates human-readable weakness labels
  - Examples: "Weak King Safety", "Material Disadvantage"
  - Based on cluster centers and feature importance

**Parameters**:
- `max_k`: Maximum number of clusters to test (default: 10)
- `n_init`: Number of random initializations (default: 10)
- `random_state`: Seed for reproducibility (default: 42)

**Algorithm**:
1. Standardize features using StandardScaler
2. Test K=1 to max_k
3. Calculate inertia for each K
4. Identify "elbow point" (optimal K)
5. Fit final K-Means model
6. Generate interpretable labels

**Dependencies**:
- `scikit-learn` (KMeans, StandardScaler)
- `numpy`

**Example Usage**:
```python
from src.chess_analyzer.chess_analyzer.ml_models.clustering import WeaknessClustering

clusterer = WeaknessClustering()
clusters = clusterer.fit_clusters(feature_matrix)
labels = clusterer.generate_labels(feature_matrix, clusters)
```

---

#### 6. Analysis Pipeline (`chess_analyzer/analysis_pipeline.py`)

**Purpose**: Orchestrate all components end-to-end

**Class**: `AnalysisPipeline`

**Workflow**:
```
1. Fetch games from chess.com
   ↓
2. Parse each game (PGN → positions)
   ↓
3. Evaluate each position (Stockfish)
   ↓
4. Calculate centipawn loss per move
   ↓
5. Extract features for weak positions (CPL > threshold)
   ↓
6. Cluster weak positions (K-Means)
   ↓
7. Generate patterns and labels
   ↓
8. Save to database
```

**Key Method**:
- `analyze_player(username: str, game_limit: int = 100) -> Dict`
  - Complete analysis pipeline
  - Returns aggregated stats and patterns
  - Handles all error cases

**Configuration**:
- `weak_threshold`: CPL > 100 centipawns = weak move (configurable)
- `clustering_max_k`: Maximum clusters for elbow method

**Database Integration**:
- Saves games to `games` table
- Saves positions to `positions` table
- Saves patterns to `patterns` table
- Saves stats to `stats` table

**Example Usage**:
```python
from src.chess_analyzer.chess_analyzer.analysis_pipeline import AnalysisPipeline

pipeline = AnalysisPipeline()
result = pipeline.analyze_player("hikaru", game_limit=50)
```

---

### Frontend Components

#### 1. Dashboard Component (`frontend/src/components/Dashboard.jsx`)

**Purpose**: Main user interface for analysis

**State Management**:
```javascript
const [username, setUsername] = useState('');
const [stats, setStats] = useState(null);
const [patterns, setPatterns] = useState([]);
const [loading, setLoading] = useState(false);
const [error, setError] = useState(null);
```

**Key Features**:
- Username input form
- Analysis trigger button
- Statistics display (total games, accuracy, phase breakdown)
- Weakness summary (frequency + impact)
- Patterns visualization (card-based layout)

**Event Handlers**:
- `handleAnalyze`: Initiates analysis, fetches stats and patterns

**Styling**:
- `Dashboard.css`: Grid layout, card styling, responsive design
- Mobile-friendly with 1-2 column layout

---

#### 2. API Wrapper (`frontend/src/api.js`)

**Purpose**: Centralized API communication

**Methods**:
- `analyzeGames(username: string, limit: number)`: POST /api/analyze
- `getStats(username: string)`: GET /api/stats
- `getPatterns(username: string)`: GET /api/patterns
- `getAnalysisStatus(taskId: string)`: GET /api/analysis/{task_id}
- `getGames(username: string)`: GET /api/games
- `getStudyPlan(username: string)`: GET /api/study-plan

**Error Handling**:
- Catches network errors
- Provides error messages to UI
- Handles JSON parsing failures

**Example Usage**:
```javascript
import { chessAPI } from '../api';

const result = await chessAPI.analyzeGames('hikaru', 100);
```

---

## API Reference

### Base URL
```
http://localhost:8000
```

### Authentication
None (all endpoints public)

### Content-Type
All requests and responses use `application/json`

---

### Endpoint: Analyze Games

**POST** `/api/analyze`

**Request**:
```json
{
  "username": "hikaru",
  "game_limit": 100
}
```

**Response** (200):
```json
{
  "task_id": "abc123def456",
  "status": "processing",
  "username": "hikaru"
}
```

**Errors**:
- `400`: Invalid username or game limit
- `404`: Player not found on chess.com
- `500`: Analysis engine error

---

### Endpoint: Check Analysis Status

**GET** `/api/analysis/{task_id}`

**Parameters**:
- `task_id` (path): Unique analysis task ID

**Response** (200):
```json
{
  "task_id": "abc123def456",
  "status": "completed",
  "progress": 100,
  "games_analyzed": 50,
  "patterns_found": 3
}
```

**Status Values**:
- `processing`: Analysis in progress
- `completed`: Analysis finished
- `failed`: Analysis encountered error

---

### Endpoint: Get Games

**GET** `/api/games`

**Query Parameters**:
- `username` (optional): Filter by player

**Response** (200):
```json
{
  "games": [
    {
      "id": 1,
      "username": "hikaru",
      "url": "https://chess.com/game/live/12345",
      "white_username": "hikaru",
      "black_username": "opponent",
      "result": "win",
      "accuracy": 85.5,
      "date_played": "2026-04-10T14:30:00"
    }
  ],
  "total": 50
}
```

---

### Endpoint: Get Statistics

**GET** `/api/stats`

**Query Parameters**:
- `username` (optional): Filter by player

**Response** (200):
```json
{
  "username": "hikaru",
  "total_games": 50,
  "overall_accuracy": 85.5,
  "accuracy_by_phase": {
    "opening": 90.2,
    "middlegame": 82.1,
    "endgame": 75.3
  },
  "weakness_summary": [
    {
      "weakness": "Weak King Safety",
      "frequency": 12,
      "avg_loss": 150
    }
  ]
}
```

---

### Endpoint: Get Patterns

**GET** `/api/patterns`

**Query Parameters**:
- `username` (optional): Filter by player

**Response** (200):
```json
{
  "patterns": [
    {
      "id": 1,
      "name": "Weak King Safety",
      "type": "positional",
      "frequency": 12,
      "avg_loss": 150.5,
      "affected_games": 8,
      "sample_fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    }
  ],
  "total": 3
}
```

---

### Endpoint: Get Study Plan

**GET** `/api/study-plan`

**Query Parameters**:
- `username` (optional): Filter by player

**Response** (200):
```json
{
  "username": "hikaru",
  "recommended_games": [
    {
      "game_id": 5,
      "weakness": "Weak King Safety",
      "impact": "high",
      "moves_affected": 3
    }
  ],
  "study_order": ["Weak King Safety", "Material Handling"]
}
```

---

## Database Schema

### Database: `chess_analyzer`

#### Table: `games`

**Purpose**: Store analyzed games

```sql
CREATE TABLE games (
  id SERIAL PRIMARY KEY,
  username VARCHAR(255) NOT NULL,
  url VARCHAR(500) NOT NULL,
  white_username VARCHAR(255),
  black_username VARCHAR(255),
  result VARCHAR(50),
  accuracy FLOAT,
  date_played TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_username (username),
  INDEX idx_date (date_played)
);
```

**Columns**:
- `id`: Unique game identifier
- `username`: Player being analyzed
- `url`: Link to game on chess.com
- `white_username`: White player
- `black_username`: Black player
- `result`: Game result (white/black/draw)
- `accuracy`: Move accuracy percentage
- `date_played`: When game was played
- `created_at`: When record was created

---

#### Table: `positions`

**Purpose**: Store evaluated positions

```sql
CREATE TABLE positions (
  id SERIAL PRIMARY KEY,
  game_id INTEGER NOT NULL REFERENCES games(id),
  fen VARCHAR(200) NOT NULL,
  move_number INTEGER,
  evaluation FLOAT,
  centipawn_loss FLOAT,
  material_balance FLOAT,
  piece_activity FLOAT,
  king_safety FLOAT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_game (game_id),
  INDEX idx_cpl (centipawn_loss)
);
```

**Columns**:
- `id`: Unique position identifier
- `game_id`: Reference to game
- `fen`: Board position in FEN notation
- `move_number`: Move sequence number
- `evaluation`: Stockfish evaluation (centipawns)
- `centipawn_loss`: Loss on this move
- `material_balance`: Material balance feature
- `piece_activity`: Activity feature
- `king_safety`: King safety feature
- `created_at`: Record creation timestamp

---

#### Table: `patterns`

**Purpose**: Store discovered weakness patterns

```sql
CREATE TABLE patterns (
  id SERIAL PRIMARY KEY,
  username VARCHAR(255) NOT NULL,
  name VARCHAR(255) NOT NULL,
  type VARCHAR(100),
  frequency INTEGER,
  avg_loss FLOAT,
  affected_games INTEGER,
  sample_fen VARCHAR(200),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_username (username),
  INDEX idx_frequency (frequency)
);
```

**Columns**:
- `id`: Pattern identifier
- `username`: Player associated with pattern
- `name`: Human-readable pattern name
- `type`: Pattern type (tactical/positional/opening)
- `frequency`: How many times observed
- `avg_loss`: Average centipawn loss
- `affected_games`: Number of games affected
- `sample_fen`: Example position
- `created_at`: Record creation timestamp

---

#### Table: `stats`

**Purpose**: Store aggregated player statistics

```sql
CREATE TABLE stats (
  id SERIAL PRIMARY KEY,
  username VARCHAR(255) NOT NULL UNIQUE,
  total_games INTEGER,
  overall_accuracy FLOAT,
  opening_accuracy FLOAT,
  middlegame_accuracy FLOAT,
  endgame_accuracy FLOAT,
  total_patterns INTEGER,
  last_analyzed TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_username (username)
);
```

**Columns**:
- `id`: Stats record identifier
- `username`: Player
- `total_games`: Games analyzed
- `overall_accuracy`: Average move accuracy
- `opening_accuracy`: Accuracy in opening phase
- `middlegame_accuracy`: Accuracy in middlegame
- `endgame_accuracy`: Accuracy in endgame
- `total_patterns`: Number of patterns found
- `last_analyzed`: Timestamp of last analysis
- `created_at`: Record creation timestamp

---

## Code Organization

### Directory Structure

```
chess_analyzer/
├── src/chess_analyzer/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app entry point
│   ├── config.py                        # Configuration (Pydantic)
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py                    # SQLAlchemy ORM models (4 tables)
│   │   └── session.py                   # Database connection/dependency
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py                    # 7 REST endpoints
│   │   └── schemas.py                   # Pydantic request/response models
│   │
│   ├── chess_analyzer/
│   │   ├── __init__.py
│   │   ├── game_fetcher.py              # Chess.com API integration
│   │   ├── pgn_parser.py                # PGN parsing
│   │   ├── position_analyzer.py         # Stockfish integration + CPL
│   │   ├── feature_extractor.py         # Position feature engineering
│   │   ├── analysis_pipeline.py         # Orchestration
│   │   └── ml_models/
│   │       ├── __init__.py
│   │       ├── clustering.py            # K-Means clustering
│   │       └── embeddings.py            # (Future) position embeddings
│   │
│   └── utils/
│       ├── __init__.py
│       └── chess_utils.py               # Helper functions
│
├── tests/
│   ├── __init__.py
│   ├── test_game_fetcher.py
│   ├── test_position_analyzer.py
│   ├── test_pgn_parser.py
│   ├── test_feature_extractor.py
│   ├── test_clustering.py
│   └── test_analysis_pipeline.py
│
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── api.js                       # API wrapper (Fetch)
│   │   ├── App.jsx                      # Root component
│   │   ├── App.css
│   │   ├── index.js
│   │   ├── index.css
│   │   ├── components/
│   │   │   └── Dashboard.jsx
│   │   └── styles/
│   │       └── Dashboard.css
│   ├── package.json
│   └── build/                           # Production build output
│
├── docs/
│   ├── ML_TECHNIQUES_LITERATURE_REVIEW.md
│   ├── TECHNICAL_DOCUMENTATION.md       # This file
│   ├── superpowers/
│   │   ├── specs/
│   │   │   └── 2026-04-12-chess-analyzer-design.md
│   │   └── plans/
│   │       └── 2026-04-12-chess-analyzer-implementation.md
│   └── README.md
│
├── README.md
├── QUICKSTART.md
├── PHASE_1_COMPLETE.md
├── pyproject.toml
├── .env
└── .gitignore
```

---

## Configuration

### Environment Variables

Create `.env` file in project root:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/chess_analyzer

# Chess Engine
STOCKFISH_PATH=/usr/games/stockfish

# Application
DEBUG=True
ENVIRONMENT=development
```

### Configuration Class (`config.py`)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = Field(..., alias="DATABASE_URL")
    stockfish_path: str = Field(..., alias="STOCKFISH_PATH")
    debug: bool = Field(default=False, alias="DEBUG")
    
    class Config:
        env_file = ".env"

settings = Settings()
```

---

## Installation & Deployment

### Local Development

**1. Clone repository**:
```bash
git clone <repo-url>
cd chess_analyzer
```

**2. Set up virtual environment**:
```bash
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**3. Install dependencies**:
```bash
pip install -e .
```

**4. Create `.env` file**:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

**5. Start database** (Docker):
```bash
docker run -d --name chess-db \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=chess_analyzer \
  -p 5432:5432 \
  postgres:15
```

**6. Initialize database**:
```bash
python -c "from src.chess_analyzer.database.models import Base; from src.chess_analyzer.database.session import engine; Base.metadata.create_all(engine)"
```

**7. Start backend**:
```bash
python -m uvicorn src.chess_analyzer.main:app --reload
```

**8. Start frontend** (new terminal):
```bash
cd frontend
npm install
npm start
```

**9. Access application**:
- Frontend: http://localhost:3000
- API: http://localhost:8000
- Swagger API docs: http://localhost:8000/docs

---

### Production Deployment

**Build frontend**:
```bash
cd frontend
npm run build
# Output: build/ directory ready for deployment
```

**Run backend**:
```bash
python -m uvicorn src.chess_analyzer.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4
```

**Docker deployment** (Phase 2):
```bash
docker-compose up -d
```

---

## Development Workflow

### Adding a Feature

**1. Create test**:
```python
# tests/test_feature.py
def test_new_feature():
    # Arrange
    input_data = ...
    
    # Act
    result = function(input_data)
    
    # Assert
    assert result == expected_value
```

**2. Run test** (should fail):
```bash
pytest tests/test_feature.py::test_new_feature -v
```

**3. Implement feature**:
```python
# src/chess_analyzer/module.py
def function(input_data):
    return expected_value
```

**4. Run test** (should pass):
```bash
pytest tests/test_feature.py::test_new_feature -v
```

**5. Check code quality**:
```bash
ruff check src/
ruff format src/
```

**6. Commit**:
```bash
git add .
git commit -m "feat: add new feature"
```

---

## Testing Strategy

### Test Framework
- **pytest**: Test runner
- **pytest-cov**: Coverage reporting

### Test Organization

```
tests/
├── test_game_fetcher.py       # 4 tests
├── test_position_analyzer.py  # 12 tests
├── test_pgn_parser.py         # 2 tests
├── test_feature_extractor.py  # 3 tests
├── test_clustering.py         # 2 tests
└── test_analysis_pipeline.py  # 5 tests
```

### Running Tests

**All tests**:
```bash
pytest tests/ -v
```

**With coverage**:
```bash
pytest tests/ --cov=src --cov-report=html
```

**Specific test file**:
```bash
pytest tests/test_game_fetcher.py -v
```

**Specific test function**:
```bash
pytest tests/test_game_fetcher.py::test_fetch_games -v
```

### Test Coverage
- Target: 100% of critical paths
- Current: 28+ tests passing
- All core components tested

---

## Performance Considerations

### Optimization Strategies

**1. Engine Evaluation**:
- Depth: 20 plies (adjustable)
- Time limit: 1 second per position
- Can reduce depth for faster analysis

**2. Feature Extraction**:
- Vectorized operations using NumPy
- StandardScaler for normalization
- Single pass over positions

**3. Database Queries**:
- Indexed columns: username, date, CPL
- Connection pooling enabled
- Pre-ping for stale connections

**4. Frontend Rendering**:
- React 19 with optimization
- Card-based layout avoids large tables
- Pagination recommended for 100+ patterns

### Scaling Recommendations

**Current**:
- Handles 50-100 games per analysis
- ~5-10 minutes per analysis (Stockfish-limited)
- Single-threaded analysis

**Phase 2 (Planned)**:
- Async analysis jobs with Celery
- Redis caching for position evaluations
- Distributed Stockfish (multiple instances)
- Background job queue

---

## Security Considerations

### Input Validation
- All API inputs validated with Pydantic
- Username length limits (255 chars max)
- FEN string length verified (200 chars max)
- Game limit capped at 1000

### Database Security
- Credentials loaded from environment variables
- Connection pooling with timeout
- Prepared statements prevent SQL injection
- No sensitive data stored

### API Security
- CORS restricted to localhost:3000
- No authentication required (internal use)
- JSON request/response only
- Rate limiting recommended for production

### Frontend Security
- Fetch API used (no XSS-prone eval)
- No localStorage of sensitive data
- Content Security Policy headers (Phase 2)
- Input sanitization via Pydantic

### Dependency Security
- Regular dependency updates
- Axios vulnerability avoided (using Fetch)
- pinned versions in pyproject.toml
- npm audit for frontend

---

## Troubleshooting

### Backend Won't Start

**Error**: `ModuleNotFoundError: No module named 'src.chess_analyzer'`

**Solution**:
```bash
pip install -e .
```

**Error**: Database connection refused

**Solution**:
```bash
# Check PostgreSQL is running
docker ps
# Or start it:
docker run -d --name chess-db -e POSTGRES_USER=user -e POSTGRES_PASSWORD=password -e POSTGRES_DB=chess_analyzer -p 5432:5432 postgres:15
```

---

### Frontend Won't Start

**Error**: Port 3000 already in use

**Solution**:
```bash
lsof -i :3000  # Find process
kill -9 <PID>  # Kill it
npm start      # Try again
```

**Error**: Dependencies not installed

**Solution**:
```bash
rm -rf node_modules package-lock.json
npm install
npm start
```

---

### Analysis Fails

**Error**: Stockfish not found

**Solution**:
```bash
# Install Stockfish
brew install stockfish      # Mac
sudo apt-get install stockfish  # Linux

# Set path in .env
STOCKFISH_PATH=/usr/games/stockfish  # Linux
STOCKFISH_PATH=/usr/local/bin/stockfish  # Mac
```

**Error**: Chess.com API rate limit hit

**Solution**:
- Wait 1 hour before retrying
- Reduce game_limit parameter
- Use different username

---

### Tests Failing

**Error**: Database connection error in tests

**Solution**:
```bash
# Ensure PostgreSQL running
docker ps
# Or create test database
createdb chess_analyzer_test
```

**Error**: Stockfish not found during tests

**Solution**:
```bash
# Install Stockfish if not already
brew install stockfish
```

---

## Future Enhancements

### Phase 2: Advanced Analysis

1. **Move Prediction Model**
   - Fine-tune Maia Chess-inspired model
   - Detect unusual moves
   - Learn player's style

2. **Anomaly Detection**
   - Isolation Forest for rare mistakes
   - Statistical outlier detection
   - Anomaly scoring

3. **Position Embeddings**
   - Word2vec-style position encoding
   - Semantic similarity matching
   - Advanced pattern grouping

4. **Enhanced UI**
   - Interactive pattern explorer
   - Game replay visualization
   - Study plan recommendations

### Phase 3: Study Planning

1. **AI-Powered Study Plan**
   - Ranked recommendations
   - Learning path generation
   - Progress tracking

2. **Study Materials**
   - Game reviews with engine lines
   - Themed study sets
   - Spaced repetition

### Phase 4: Scale & Polish

1. **Performance**
   - Async analysis (Celery)
   - Caching layer (Redis)
   - Distributed processing

2. **Deployment**
   - Docker containerization
   - Kubernetes orchestration
   - Cloud hosting (AWS/GCP/Azure)

3. **Monitoring**
   - Logging and metrics
   - Health checks
   - Error tracking

---

## References

- **Chess.com API**: https://www.chess.com/news/view/chess-com-public-data-api
- **Stockfish**: https://stockfishchess.org/
- **python-chess**: https://python-chess.readthedocs.io/
- **FastAPI**: https://fastapi.tiangolo.com/
- **React**: https://react.dev/
- **PostgreSQL**: https://www.postgresql.org/
- **scikit-learn**: https://scikit-learn.org/

---

**Document Version**: 1.0  
**Last Updated**: April 12, 2026  
**Status**: Complete - Phase 1 Ready
