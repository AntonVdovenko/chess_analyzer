# Chess Analyzer Phase 2: Advanced Analysis - Design Specification

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add advanced ML-based analysis capabilities (move prediction, anomaly detection, position embeddings, enhanced pattern exploration) to provide deeper insights into player weaknesses.

**Architecture:** Modular Phase 2 components (MovePredictor, AnomalyDetector, PositionEmbedder, PatternExplorer) that extend Phase 1 results without modifying existing code. Separate `/api/advanced-analysis` endpoint keeps advanced features opt-in.

**Tech Stack:** scikit-learn (Isolation Forest), numpy (embeddings), React 19 (UI enhancements), PostgreSQL (new tables), FastAPI (new endpoints)

---

## System Architecture

### High-Level Data Flow

```
Phase 1 Results (games, positions, patterns)
           ↓
AdvancedAnalysisPipeline
├── MovePredictor → move_predictions table
├── AnomalyDetector → anomalies table
├── PositionEmbedder → embeddings table
└── PatternExplorer → Enhanced UI
           ↓
Enhanced React Dashboard with deep-dive analysis
```

### Component Breakdown

**Backend Components** (Python/FastAPI):
1. **MovePredictor** - Learn player move patterns, detect unusual moves
2. **AnomalyDetector** - Isolation Forest for rare, costly mistakes
3. **PositionEmbedder** - Semantic position similarity via embeddings
4. **AdvancedAnalysisPipeline** - Orchestrate all three components

**Frontend Component** (React):
1. **PatternExplorer** - Enhanced dashboard with filtering and drill-down

### Key Design Decisions

**Modular Architecture:**
- Each ML component is independent, testable, swappable
- Reuses Phase 1 data (games, positions) without modification
- New results stored in separate tables
- No breaking changes to Phase 1 API

**Backward Compatibility:**
- Phase 1 endpoints unchanged
- Advanced features opt-in via new endpoints
- Old dashboard continues to work
- New dashboard integrates both Phase 1 + Phase 2 results

**Separate Analysis Endpoint:**
- `/api/advanced-analysis` runs independently from Phase 1
- Users choose when to run expensive ML models
- Phase 1 analysis remains fast (<2 min)
- Phase 2 analysis takes ~5-10 minutes

---

## Component Specifications

### 1. MovePredictor

**File:** `src/chess_analyzer/ml_models/move_predictor.py`

**Purpose:** Learn player's typical move distribution. Detect unusual moves that deviate from player's style.

**Algorithm:**
1. For each position type (by piece placement + material), collect all moves the player made
2. Build probability distribution (e.g., "in rook endgames, player plays Kg3 60%, Kh4 30%, Kg4 10%")
3. Score new moves: P(actual_move | position_type) = probability
4. Unusual moves: probability < threshold (e.g., < 0.2)

**Class: MovePredictor**

```python
class MovePredictor:
    def __init__(self, min_position_frequency: int = 5):
        """
        min_position_frequency: Only learn patterns from positions seen 5+ times
        """
        self.move_distributions = {}  # {position_hash: {move: probability}}
    
    def fit(self, games: List[Game]) -> None:
        """Learn move patterns from games"""
        # Extract positions and moves from games
        # Build probability distributions
    
    def predict(self, position_fen: str, move: str) -> float:
        """Return probability of this move in this position (0-1)"""
        # Return probability or 0.0 if position not in training data
    
    def get_unusual_moves(self, game: Game, threshold: float = 0.2) -> List[Dict]:
        """Return moves with probability < threshold"""
        # Returns: [{"move_number": 15, "move": "e2e4", "probability": 0.1, "expected_moves": ["e2e3", "d2d4"]}]
```

**Database Output:**
```sql
move_predictions table:
- game_id (FK to games)
- position_fen
- actual_move
- predicted_move (most likely alternative)
- probability_score (0-1)
- is_unusual (bool)
```

**API Endpoint:**
```
GET /api/move-predictions?username=hikaru&game_id=5
Response: [
  { game_id, position_fen, actual_move, predicted_move, probability_score, is_unusual }
]
```

---

### 2. AnomalyDetector

**File:** `src/chess_analyzer/ml_models/anomaly_detector.py`

**Purpose:** Identify statistically rare, costly mistakes using Isolation Forest.

**Algorithm:**
1. Extract features for each position: CPL, material_loss, king_exposure_change, eval_drop
2. Train Isolation Forest (unsupervised anomaly detection)
3. Score each position: anomaly_score 0-1 (0=normal, 1=highly anomalous)
4. Flag as anomaly if score > threshold (e.g., > 0.7)

**Why Isolation Forest:**
- No need for labeled data
- Detects rare patterns (exactly what we need)
- Fast and handles high dimensions
- Outliers = rarest, most unusual mistakes

**Class: AnomalyDetector**

```python
class AnomalyDetector:
    def __init__(self, contamination: float = 0.1):
        """
        contamination: Expected fraction of anomalies (0.1 = top 10% are anomalies)
        """
        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.scaler = StandardScaler()
    
    def fit(self, positions: List[Position]) -> None:
        """Learn what 'normal' positions look like"""
        features = self.extract_features(positions)
        scaled = self.scaler.fit_transform(features)
        self.model.fit(scaled)
    
    def predict(self, position: Position) -> float:
        """Return anomaly score (0-1, higher = more anomalous)"""
        features = self.extract_features([position])
        scaled = self.scaler.transform(features)
        score = self.model.score_samples(scaled)[0]
        return (1 - score) / 2  # Normalize to 0-1
    
    def extract_features(self, positions: List[Position]) -> np.ndarray:
        """Extract: [CPL, material_loss, king_exposure, eval_drop]"""
        # 4 features per position
        # Normalized/scaled
```

**Database Output:**
```sql
anomalies table:
- game_id (FK to games)
- position_fen
- anomaly_score (0-1)
- centipawn_loss
- reason (e.g., "rare blunder", "unusual tactic miss")
```

**API Endpoint:**
```
GET /api/anomalies?username=hikaru&min_score=0.7
Response: [
  { game_id, position_fen, anomaly_score, centipawn_loss, reason }
]
```

---

### 3. PositionEmbedder

**File:** `src/chess_analyzer/ml_models/embeddings.py`

**Purpose:** Convert positions to semantic vectors. Find similar positions even if they look visually different.

**Algorithm:**
1. Extract rich features per position (material, piece placement, pawn structure, king safety, etc.)
2. Use PCA to compress to 10-20 dimensions (embeddings)
3. Store embeddings, enable similarity search via cosine distance
4. Optional: K-Means cluster embeddings for position families

**Why Embeddings:**
- Positions with similar strategic properties map to nearby vectors
- "Weak king safety in middlegame" will cluster together even with different piece placements
- Enables semantic pattern discovery beyond K-Means clustering

**Class: PositionEmbedder**

```python
class PositionEmbedder:
    def __init__(self, n_components: int = 16):
        """
        n_components: Embedding dimensionality (16-20 typical)
        """
        self.pca = PCA(n_components=n_components)
        self.scaler = StandardScaler()
    
    def fit(self, positions: List[Position]) -> None:
        """Learn embedding space from positions"""
        features = self.extract_features(positions)
        scaled = self.scaler.fit_transform(features)
        self.pca.fit(scaled)
    
    def embed(self, position: Position) -> np.ndarray:
        """Convert position to embedding vector (16-20 floats)"""
        features = self.extract_features([position])
        scaled = self.scaler.transform(features)
        return self.pca.transform(scaled)[0]
    
    def find_similar(self, embedding: np.ndarray, all_embeddings: np.ndarray, k: int = 5) -> List[int]:
        """Return indices of k most similar embeddings (by cosine distance)"""
        from sklearn.metrics.pairwise import cosine_distances
        distances = cosine_distances([embedding], all_embeddings)[0]
        return np.argsort(distances)[:k]
    
    def extract_features(self, positions: List[Position]) -> np.ndarray:
        """Extract ~20 features: material, piece activity, pawn structure, king safety, etc."""
        # Build feature matrix (n_positions x n_features)
```

**Database Output:**
```sql
embeddings table:
- position_id (FK to positions)
- embedding_vector (16-20 floats, stored as FLOAT8[])
- embedding_cluster (optional, k-means on embeddings)
```

**API Endpoint:**
```
GET /api/similar-positions?position_fen=<fen>&limit=10
Response: [
  { position_id, similarity_score, game_id, centipawn_loss }
]
```

---

### 4. AdvancedAnalysisPipeline

**File:** `src/chess_analyzer/chess_analyzer/advanced_analysis_pipeline.py`

**Purpose:** Orchestrate all three ML components and store results.

**Workflow:**
```
1. Get stored games/positions from Phase 1
2. Fit MovePredictor on player's games
3. Fit AnomalyDetector on positions
4. Fit PositionEmbedder on positions
5. Predict/score each position
6. Store results in respective tables
7. Return analysis job summary
```

**Class: AdvancedAnalysisPipeline**

```python
class AdvancedAnalysisPipeline:
    def __init__(self, session: Session):
        self.move_predictor = MovePredictor()
        self.anomaly_detector = AnomalyDetector()
        self.embedder = PositionEmbedder()
        self.session = session
    
    def analyze_player(self, username: str) -> Dict:
        """Run all advanced analyses for a player"""
        # 1. Fetch player's games from Phase 1
        games = self.session.query(Game).filter(Game.username == username).all()
        
        # 2. Fit models
        self.move_predictor.fit(games)
        positions = self.session.query(Position).filter(
            Position.game_id.in_([g.id for g in games])
        ).all()
        self.anomaly_detector.fit(positions)
        self.embedder.fit(positions)
        
        # 3. Score each position
        move_pred_count = 0
        anomaly_count = 0
        for game in games:
            for position in game.positions:
                # Score move predictions
                if position.move:
                    prob = self.move_predictor.predict(position.fen, position.move)
                    if prob < 0.2:  # Unusual
                        self.save_move_prediction(position, prob)
                        move_pred_count += 1
                
                # Score anomalies
                anom_score = self.anomaly_detector.predict(position)
                if anom_score > 0.7:  # Anomalous
                    self.save_anomaly(position, anom_score)
                    anomaly_count += 1
                
                # Get embeddings
                embedding = self.embedder.embed(position)
                self.save_embedding(position, embedding)
        
        return {
            "username": username,
            "unusual_moves_found": move_pred_count,
            "anomalies_found": anomaly_count,
            "embeddings_created": len(positions)
        }
```

**API Endpoint:**
```
POST /api/advanced-analysis
Request: { "username": "hikaru", "game_limit": 100 }
Response: { "job_id": "abc123", "status": "processing" }

GET /api/advanced-analysis/{job_id}
Response: {
  "job_id": "abc123",
  "status": "completed",
  "move_predictor": { "done": true, "unusual_moves": 42 },
  "anomaly_detector": { "done": true, "anomalies": 18 },
  "embedder": { "done": true, "positions_embedded": 500 }
}
```

---

### 5. PatternExplorer UI Component

**File:** `frontend/src/components/PatternExplorer.jsx`

**Purpose:** Enhanced dashboard showing Phase 1 patterns + Phase 2 advanced insights.

**Features:**
1. **Pattern List** - All discovered patterns with filters
   - Filter by type (tactical, positional, opening)
   - Sort by frequency, impact, study priority
   - Show unusual moves count, anomaly count

2. **Pattern Details** - Deep dive into single pattern
   - Affected games with specific moves
   - Compare actual moves vs engine recommendations
   - Show anomalies in this pattern
   - List similar patterns (by embedding)

3. **Move Analysis** - Show unusual moves
   - Position visualization
   - What player played vs what they typically play
   - Engine evaluation

4. **Anomaly Viewer** - Show rare mistakes
   - Sorted by anomaly score
   - Context (which pattern, which game)
   - Link to full game analysis

**Component Structure:**
```
PatternExplorer.jsx
├── PatternFilter.jsx        (Filter UI)
├── PatternList.jsx          (Scrollable list with sorting)
├── PatternDetail.jsx        (Deep-dive view)
│   ├── PatternStats.jsx     (Frequency, impact, etc.)
│   ├── AffectedGames.jsx    (List of games with pattern)
│   ├── UnusualMoves.jsx     (Move deviations)
│   ├── Anomalies.jsx        (Rare mistakes in pattern)
│   └── SimilarPatterns.jsx  (By embedding similarity)
├── MoveAnalyzer.jsx         (Unusual move details)
└── AnomalyViewer.jsx        (Rare mistake explorer)
```

**Data from Enhanced API Responses:**

The existing `/api/stats` and `/api/patterns` endpoints return enhanced data:

```json
{
  "patterns": [
    {
      "id": 1,
      "name": "Weak King Safety",
      "type": "positional",
      "frequency": 12,
      "avg_loss": 150.5,
      
      // Phase 2 additions
      "unusual_moves_in_pattern": 5,
      "anomaly_count": 2,
      "similar_patterns": ["pattern_3", "pattern_7"],
      "study_priority": "high"  // Ranked by impact
    }
  ]
}
```

---

## Database Schema

### New Tables

```sql
-- Move predictions
CREATE TABLE move_predictions (
  id SERIAL PRIMARY KEY,
  game_id INTEGER NOT NULL REFERENCES games(id),
  position_fen VARCHAR(200),
  actual_move VARCHAR(10),
  predicted_move VARCHAR(10),
  probability_score FLOAT,
  is_unusual BOOLEAN,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_game (game_id),
  INDEX idx_unusual (is_unusual)
);

-- Anomalies
CREATE TABLE anomalies (
  id SERIAL PRIMARY KEY,
  game_id INTEGER NOT NULL REFERENCES games(id),
  position_fen VARCHAR(200),
  anomaly_score FLOAT,
  centipawn_loss FLOAT,
  reason VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_game (game_id),
  INDEX idx_score (anomaly_score)
);

-- Position embeddings
CREATE TABLE embeddings (
  id SERIAL PRIMARY KEY,
  position_id INTEGER NOT NULL REFERENCES positions(id),
  embedding_vector FLOAT8[],
  embedding_cluster INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_position (position_id),
  INDEX idx_cluster (embedding_cluster)
);

-- Advanced analysis jobs
CREATE TABLE advanced_analysis_jobs (
  id SERIAL PRIMARY KEY,
  username VARCHAR(255),
  job_id UUID UNIQUE,
  status VARCHAR(50),
  move_predictor_done BOOLEAN DEFAULT FALSE,
  anomaly_detector_done BOOLEAN DEFAULT FALSE,
  embedder_done BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMP,
  INDEX idx_username (username),
  INDEX idx_status (status)
);
```

**No changes to Phase 1 tables** (games, positions, patterns, stats)

---

## API Specification

### New Endpoints

**POST /api/advanced-analysis**
- Start advanced analysis job
- Request: `{ "username": "hikaru", "game_limit": 100 }`
- Response: `{ "job_id": "uuid", "status": "processing" }`
- Status codes: 200 (started), 400 (invalid input), 404 (player not found)

**GET /api/advanced-analysis/{job_id}**
- Check job progress
- Response: Job status, component completion, counts
- Status codes: 200 (found), 404 (not found)

**GET /api/move-predictions**
- Get unusual moves for player/game
- Query params: `username`, `game_id`, `min_probability` (optional)
- Response: Array of move predictions
- Status codes: 200

**GET /api/anomalies**
- Get rare mistakes
- Query params: `username`, `game_id`, `min_score` (optional)
- Response: Array of anomalies
- Status codes: 200

**GET /api/similar-positions**
- Find semantically similar positions
- Query params: `position_fen`, `limit` (default 10)
- Response: Array of similar positions with similarity scores
- Status codes: 200

**GET /api/pattern-details/{pattern_id}**
- Deep dive into pattern with Phase 2 data
- Response: Pattern + unusual moves + anomalies + similar patterns
- Status codes: 200, 404

### Enhanced Endpoints (Phase 1)

**GET /api/stats** - Enhanced response
```json
{
  "username": "hikaru",
  "total_games": 50,
  "overall_accuracy": 85.5,
  // ... existing fields ...
  "phase_2_available": true,
  "unusual_moves_total": 42,
  "anomalies_total": 18
}
```

**GET /api/patterns** - Enhanced response
```json
{
  "patterns": [
    {
      // ... Phase 1 fields ...
      "unusual_moves_in_pattern": 5,
      "anomaly_count": 2,
      "similar_patterns": ["pattern_3", "pattern_7"],
      "study_priority": "high"
    }
  ]
}
```

---

## Integration Points

### With Phase 1
- Reuses `games`, `positions`, `patterns`, `stats` tables
- No modifications to Phase 1 code
- Phase 1 endpoints unchanged
- Phase 2 is optional/independent

### With React Dashboard
- New "Advanced Analysis" button in dashboard
- PatternExplorer replaces/extends Dashboard component
- Backward compatible (old dashboard still works)
- New tabs: "Basic Patterns" (Phase 1), "Deep Analysis" (Phase 2)

---

## Success Criteria

- [ ] All 3 ML models (MovePredictor, AnomalyDetector, Embedder) implemented and tested
- [ ] AdvancedAnalysisPipeline orchestrates all components
- [ ] 5 new API endpoints fully functional
- [ ] Database schema added (4 new tables)
- [ ] PatternExplorer UI component displays Phase 2 results
- [ ] 50-game analysis completes in <10 minutes
- [ ] All new code has 90%+ test coverage
- [ ] No breaking changes to Phase 1 API
- [ ] Documentation updated

---

## Testing Strategy

**Unit Tests** (per component):
- `test_move_predictor.py` - fit/predict, unusual move detection
- `test_anomaly_detector.py` - fit/predict, anomaly scoring
- `test_embeddings.py` - fit/embed, similarity search
- `test_advanced_pipeline.py` - orchestration, DB integration

**Integration Tests**:
- Full pipeline on 50-game dataset
- API endpoint contract tests
- Database persistence tests

**Performance Benchmarks**:
- 50-game analysis: <10 minutes
- Move prediction: <0.1s per game
- Anomaly detection: <1s per 100 positions
- Embedding: <0.5s per 100 positions

---

## Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| Analysis too slow | Optimize Stockfish depth in Phase 1, consider async jobs |
| ML models overfit | Use cross-validation, generous contamination threshold |
| Embeddings not interpretable | Validate with manual position inspection, visualize t-SNE |
| Database bloat | Index aggressively, consider archival strategy |

---

## Future Enhancements (Phase 2b)

- Background job processing (Celery)
- Async analysis with progress streaming
- Move prediction model fine-tuning
- Position embedding visualization (t-SNE/UMAP)
- Study plan generation from anomalies
- Benchmark against other players

---

**Document Version:** 1.0  
**Created:** April 12, 2026  
**Status:** Design Complete - Ready for Implementation
