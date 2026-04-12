# Chess Analyzer Phase 2: Advanced Analysis - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement advanced ML-based analysis capabilities (move prediction, anomaly detection, position embeddings) and enhanced pattern explorer UI.

**Architecture:** Modular backend components (MovePredictor, AnomalyDetector, PositionEmbedder, AdvancedAnalysisPipeline) + enhanced React UI (PatternExplorer) with separate `/api/advanced-analysis` endpoint.

**Tech Stack:** scikit-learn (Isolation Forest, PCA), numpy (embeddings), FastAPI (new endpoints), SQLAlchemy (4 new models), React 19

---

## File Structure

### Backend Files

**New ML Model Files:**
- `src/chess_analyzer/ml_models/move_predictor.py` - MovePredictor class
- `src/chess_analyzer/ml_models/anomaly_detector.py` - AnomalyDetector class
- `src/chess_analyzer/ml_models/embeddings.py` - PositionEmbedder class

**New Pipeline File:**
- `src/chess_analyzer/chess_analyzer/advanced_analysis_pipeline.py` - AdvancedAnalysisPipeline orchestrator

**Modified Files:**
- `src/chess_analyzer/database/models.py` - Add 4 new SQLAlchemy ORM models
- `src/chess_analyzer/api/routes.py` - Add 5 new API endpoints + enhance 2 existing ones
- `src/chess_analyzer/api/schemas.py` - Add request/response schemas

### Frontend Files

**New Component Files:**
- `frontend/src/components/PatternExplorer.jsx` - Main enhanced dashboard component
- `frontend/src/components/PatternFilter.jsx` - Filter controls
- `frontend/src/components/PatternList.jsx` - Pattern list with sorting
- `frontend/src/components/PatternDetail.jsx` - Deep-dive view
- `frontend/src/components/PatternStats.jsx` - Stats display
- `frontend/src/components/AffectedGames.jsx` - Games list
- `frontend/src/components/UnusualMoves.jsx` - Unusual moves viewer
- `frontend/src/components/Anomalies.jsx` - Anomalies list
- `frontend/src/components/SimilarPatterns.jsx` - Similar patterns
- `frontend/src/components/MoveAnalyzer.jsx` - Move details
- `frontend/src/components/AnomalyViewer.jsx` - Rare mistakes explorer

**New Styles:**
- `frontend/src/styles/PatternExplorer.css` - All styling for Phase 2 UI

**Modified Files:**
- `frontend/src/App.jsx` - Add PatternExplorer route

### Test Files

- `tests/test_move_predictor.py`
- `tests/test_anomaly_detector.py`
- `tests/test_embeddings.py`
- `tests/test_advanced_pipeline.py`

---

## Task Breakdown

### Task 1: Database Models - Add 4 New ORM Tables

**Files:**
- Modify: `src/chess_analyzer/database/models.py`
- Test: `tests/` (integration tests in later tasks)

Add four new SQLAlchemy ORM models for Phase 2 results.

- [ ] **Step 1: Add imports and MovePredictor model**

Open `src/chess_analyzer/database/models.py` and add after the existing models:

```python
class MovePrediction(Base):
    """Move predictions for unusual moves"""
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
```

- [ ] **Step 2: Add Anomaly model**

```python
class Anomaly(Base):
    """Rare, costly mistakes detected by Isolation Forest"""
    __tablename__ = "anomalies"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False, index=True)
    position_fen = Column(String(200), nullable=False)
    anomaly_score = Column(Float, nullable=False, index=True)
    centipawn_loss = Column(Float, nullable=False)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    game = relationship("Game", backref="anomalies")
```

- [ ] **Step 3: Add Embedding model**

```python
class Embedding(Base):
    """Position embeddings for semantic similarity"""
    __tablename__ = "embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False, index=True)
    embedding_vector = Column(postgresql.ARRAY(Float), nullable=False)
    embedding_cluster = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    position = relationship("Position", backref="embedding")
```

- [ ] **Step 4: Add AdvancedAnalysisJob model**

```python
import uuid

class AdvancedAnalysisJob(Base):
    """Track advanced analysis job progress"""
    __tablename__ = "advanced_analysis_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), nullable=False, index=True)
    job_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    status = Column(String(50), nullable=False, index=True, default="processing")
    move_predictor_done = Column(Boolean, default=False)
    anomaly_detector_done = Column(Boolean, default=False)
    embedder_done = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 5: Add necessary imports to models.py**

At the top of `src/chess_analyzer/database/models.py`, ensure these imports exist:

```python
from sqlalchemy.dialects import postgresql
import uuid
```

- [ ] **Step 6: Commit database models**

```bash
git add src/chess_analyzer/database/models.py
git commit -m "feat: add 4 new ORM models for Phase 2 (move predictions, anomalies, embeddings, jobs)"
```

---

### Task 2: MovePredictor ML Component

**Files:**
- Create: `src/chess_analyzer/ml_models/move_predictor.py`
- Test: `tests/test_move_predictor.py`

- [ ] **Step 1: Write test for MovePredictor initialization**

Create `tests/test_move_predictor.py`:

```python
import pytest
from src.chess_analyzer.ml_models.move_predictor import MovePredictor


def test_move_predictor_init():
    """Test MovePredictor initializes correctly"""
    predictor = MovePredictor(min_position_frequency=5)
    assert predictor.min_position_frequency == 5
    assert predictor.move_distributions == {}


def test_move_predictor_fit_empty_games():
    """Test fit with empty games list"""
    predictor = MovePredictor()
    predictor.fit([])
    assert predictor.move_distributions == {}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_move_predictor.py -v
```

Expected output: `FAILED - ModuleNotFoundError: No module named 'src.chess_analyzer.ml_models.move_predictor'`

- [ ] **Step 3: Create MovePredictor class with minimal implementation**

Create `src/chess_analyzer/ml_models/move_predictor.py`:

```python
from typing import List, Dict, Optional
from src.chess_analyzer.database.models import Game, Position
import hashlib


class MovePredictor:
    """Learn player's move patterns and detect unusual moves"""
    
    def __init__(self, min_position_frequency: int = 5):
        """
        Args:
            min_position_frequency: Only learn patterns from positions seen 5+ times
        """
        self.min_position_frequency = min_position_frequency
        self.move_distributions = {}  # {position_hash: {move: count}}
    
    def fit(self, games: List[Game]) -> None:
        """Learn move patterns from player's games"""
        if not games:
            return
        
        # Extract positions and moves
        for game in games:
            if not hasattr(game, 'positions') or not game.positions:
                continue
            
            for position in game.positions:
                if not hasattr(position, 'fen') or not hasattr(position, 'move'):
                    continue
                
                # Create position hash (using FEN as key)
                pos_key = position.fen
                
                if pos_key not in self.move_distributions:
                    self.move_distributions[pos_key] = {}
                
                if position.move:
                    move = position.move
                    if move not in self.move_distributions[pos_key]:
                        self.move_distributions[pos_key][move] = 0
                    self.move_distributions[pos_key][move] += 1
    
    def predict(self, position_fen: str, move: str) -> float:
        """
        Return probability of this move in this position (0-1)
        
        Args:
            position_fen: FEN string of position
            move: Move in algebraic notation
        
        Returns:
            Probability 0-1, or 0.0 if position not seen during training
        """
        if position_fen not in self.move_distributions:
            return 0.0
        
        moves_dict = self.move_distributions[position_fen]
        if not moves_dict:
            return 0.0
        
        total = sum(moves_dict.values())
        move_count = moves_dict.get(move, 0)
        
        if total == 0:
            return 0.0
        
        return float(move_count) / float(total)
    
    def get_unusual_moves(self, game: Game, threshold: float = 0.2) -> List[Dict]:
        """
        Get moves with probability < threshold
        
        Args:
            game: Game object with positions
            threshold: Probability threshold (default 0.2)
        
        Returns:
            List of dicts with move_number, move, probability, expected_moves
        """
        unusual = []
        
        if not hasattr(game, 'positions') or not game.positions:
            return unusual
        
        for i, position in enumerate(game.positions):
            if not hasattr(position, 'move') or not position.move:
                continue
            
            prob = self.predict(position.fen, position.move)
            
            if prob < threshold:
                # Get expected moves (most common in this position)
                if position.fen in self.move_distributions:
                    moves_dict = self.move_distributions[position.fen]
                    expected_moves = sorted(
                        moves_dict.keys(),
                        key=lambda m: moves_dict[m],
                        reverse=True
                    )[:3]  # Top 3 expected moves
                else:
                    expected_moves = []
                
                unusual.append({
                    "move_number": i + 1,
                    "move": position.move,
                    "probability": prob,
                    "expected_moves": expected_moves
                })
        
        return unusual
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_move_predictor.py -v
```

Expected: `PASSED`

- [ ] **Step 5: Write test for fit with real data**

Add to `tests/test_move_predictor.py`:

```python
from unittest.mock import Mock


def test_move_predictor_fit_with_games():
    """Test fit learns move patterns correctly"""
    # Create mock game with positions
    position1 = Mock()
    position1.fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    position1.move = "e2e4"
    
    position2 = Mock()
    position2.fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    position2.move = "d2d4"
    
    game = Mock()
    game.positions = [position1, position2]
    
    predictor = MovePredictor()
    predictor.fit([game])
    
    # Should have learned the position
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    assert fen in predictor.move_distributions
    assert predictor.move_distributions[fen]["e2e4"] == 1
    assert predictor.move_distributions[fen]["d2d4"] == 1
    
    # Test prediction
    assert predictor.predict(fen, "e2e4") == 0.5
    assert predictor.predict(fen, "d2d4") == 0.5
    assert predictor.predict(fen, "a2a3") == 0.0


def test_move_predictor_unusual_moves():
    """Test unusual move detection"""
    position1 = Mock()
    position1.fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    position1.move = "e2e4"
    
    position2 = Mock()
    position2.fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    position2.move = "h2h4"  # Unusual move
    
    game = Mock()
    game.positions = [position1, position2]
    
    predictor = MovePredictor()
    predictor.fit([game])
    
    unusual = predictor.get_unusual_moves(game, threshold=0.3)
    assert len(unusual) == 1
    assert unusual[0]["move"] == "h2h4"
    assert unusual[0]["probability"] == 0.5
```

- [ ] **Step 6: Run all tests for MovePredictor**

```bash
pytest tests/test_move_predictor.py -v
```

Expected: `3 PASSED`

- [ ] **Step 7: Commit MovePredictor**

```bash
git add src/chess_analyzer/ml_models/move_predictor.py tests/test_move_predictor.py
git commit -m "feat: implement MovePredictor for detecting unusual moves"
```

---

### Task 3: AnomalyDetector ML Component

**Files:**
- Create: `src/chess_analyzer/ml_models/anomaly_detector.py`
- Test: `tests/test_anomaly_detector.py`

- [ ] **Step 1: Write failing test for AnomalyDetector**

Create `tests/test_anomaly_detector.py`:

```python
import pytest
import numpy as np
from unittest.mock import Mock
from src.chess_analyzer.ml_models.anomaly_detector import AnomalyDetector


def test_anomaly_detector_init():
    """Test AnomalyDetector initializes correctly"""
    detector = AnomalyDetector(contamination=0.1)
    assert detector.contamination == 0.1
    assert detector.model is not None
    assert detector.scaler is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_anomaly_detector.py -v
```

Expected: `FAILED - ModuleNotFoundError`

- [ ] **Step 3: Create AnomalyDetector class**

Create `src/chess_analyzer/ml_models/anomaly_detector.py`:

```python
from typing import List, Optional
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from src.chess_analyzer.database.models import Position


class AnomalyDetector:
    """Identify statistically rare, costly mistakes using Isolation Forest"""
    
    def __init__(self, contamination: float = 0.1):
        """
        Args:
            contamination: Expected fraction of anomalies (0.1 = top 10%)
        """
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.is_fitted = False
    
    def extract_features(self, positions: List[Position]) -> np.ndarray:
        """
        Extract features for anomaly detection: [CPL, material_loss, king_exposure, eval_drop]
        
        Args:
            positions: List of Position objects
        
        Returns:
            Feature matrix (n_positions x 4)
        """
        features = []
        
        for position in positions:
            # Feature 1: Centipawn loss
            cpl = getattr(position, 'centipawn_loss', 0.0) or 0.0
            
            # Feature 2: Material loss (estimated from position evaluation drop)
            eval_score = getattr(position, 'evaluation', 0.0) or 0.0
            
            # Feature 3: King exposure (proxy: if king safety score low)
            king_safety = getattr(position, 'king_safety', 0.5) or 0.5
            
            # Feature 4: Evaluation drop (from best to actual)
            eval_drop = max(0, cpl)  # CPL is the evaluation drop
            
            feature_vector = [cpl, eval_drop, 1.0 - king_safety, abs(eval_score)]
            features.append(feature_vector)
        
        if not features:
            return np.array([]).reshape(0, 4)
        
        return np.array(features)
    
    def fit(self, positions: List[Position]) -> None:
        """
        Learn what 'normal' positions look like
        
        Args:
            positions: List of Position objects to learn from
        """
        if not positions:
            self.is_fitted = True
            return
        
        features = self.extract_features(positions)
        
        if features.size == 0:
            self.is_fitted = True
            return
        
        # Scale features
        scaled = self.scaler.fit_transform(features)
        
        # Fit Isolation Forest
        self.model.fit(scaled)
        self.is_fitted = True
    
    def predict(self, position: Position) -> float:
        """
        Return anomaly score (0-1, higher = more anomalous)
        
        Args:
            position: Position object to score
        
        Returns:
            Anomaly score 0-1
        """
        if not self.is_fitted:
            return 0.0
        
        features = self.extract_features([position])
        
        if features.size == 0:
            return 0.0
        
        scaled = self.scaler.transform(features)
        score = self.model.score_samples(scaled)[0]
        
        # Normalize: Isolation Forest returns negative scores for anomalies
        # score_samples returns values < 0 for anomalies, > 0 for normal
        # We want 0-1 where 1 = most anomalous
        normalized = (1.0 - score) / 2.0
        return float(np.clip(normalized, 0.0, 1.0))
    
    def get_anomalies(self, positions: List[Position], threshold: float = 0.7) -> List[dict]:
        """
        Get anomalies above threshold
        
        Args:
            positions: List of Position objects
            threshold: Anomaly score threshold (default 0.7)
        
        Returns:
            List of dicts with position data and anomaly scores
        """
        anomalies = []
        
        for position in positions:
            score = self.predict(position)
            
            if score >= threshold:
                cpl = getattr(position, 'centipawn_loss', 0.0) or 0.0
                
                # Categorize the anomaly
                if cpl > 300:
                    reason = "rare blunder"
                elif cpl > 150:
                    reason = "unusual tactic miss"
                else:
                    reason = "unusual move"
                
                anomalies.append({
                    "position_fen": position.fen,
                    "anomaly_score": score,
                    "centipawn_loss": cpl,
                    "reason": reason
                })
        
        return anomalies
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_anomaly_detector.py::test_anomaly_detector_init -v
```

Expected: `PASSED`

- [ ] **Step 5: Write test for fit and predict**

Add to `tests/test_anomaly_detector.py`:

```python
def test_anomaly_detector_fit_predict():
    """Test fit and predict methods"""
    # Create mock positions
    positions = []
    for i in range(20):
        pos = Mock()
        pos.fen = f"fen_string_{i}"
        pos.centipawn_loss = 50.0 + (i * 2)  # Increasing CPL
        pos.evaluation = -0.5
        pos.king_safety = 0.7
        positions.append(pos)
    
    detector = AnomalyDetector(contamination=0.1)
    detector.fit(positions)
    
    # Test prediction on normal position
    normal_pos = Mock()
    normal_pos.fen = "normal_fen"
    normal_pos.centipawn_loss = 60.0
    normal_pos.evaluation = -0.5
    normal_pos.king_safety = 0.7
    
    score = detector.predict(normal_pos)
    assert 0.0 <= score <= 1.0


def test_anomaly_detector_empty_positions():
    """Test with empty positions"""
    detector = AnomalyDetector()
    detector.fit([])
    assert detector.is_fitted is True
    
    pos = Mock()
    pos.fen = "test_fen"
    pos.centipawn_loss = 100.0
    pos.evaluation = 0.0
    pos.king_safety = 0.5
    
    score = detector.predict(pos)
    assert score == 0.0
```

- [ ] **Step 6: Run all AnomalyDetector tests**

```bash
pytest tests/test_anomaly_detector.py -v
```

Expected: `3 PASSED`

- [ ] **Step 7: Commit AnomalyDetector**

```bash
git add src/chess_analyzer/ml_models/anomaly_detector.py tests/test_anomaly_detector.py
git commit -m "feat: implement AnomalyDetector for identifying rare mistakes"
```

---

### Task 4: PositionEmbedder ML Component

**Files:**
- Create: `src/chess_analyzer/ml_models/embeddings.py`
- Test: `tests/test_embeddings.py`

- [ ] **Step 1: Write failing test for PositionEmbedder**

Create `tests/test_embeddings.py`:

```python
import pytest
import numpy as np
from unittest.mock import Mock
from src.chess_analyzer.ml_models.embeddings import PositionEmbedder


def test_position_embedder_init():
    """Test PositionEmbedder initializes correctly"""
    embedder = PositionEmbedder(n_components=16)
    assert embedder.n_components == 16
    assert embedder.pca is not None
    assert embedder.scaler is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_embeddings.py -v
```

Expected: `FAILED - ModuleNotFoundError`

- [ ] **Step 3: Create PositionEmbedder class**

Create `src/chess_analyzer/ml_models/embeddings.py`:

```python
from typing import List, Optional
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_distances
from src.chess_analyzer.database.models import Position


class PositionEmbedder:
    """Convert positions to semantic vectors for similarity matching"""
    
    def __init__(self, n_components: int = 16):
        """
        Args:
            n_components: Embedding dimensionality (16-20 typical)
        """
        self.n_components = n_components
        self.pca = PCA(n_components=n_components, random_state=42)
        self.scaler = StandardScaler()
        self.is_fitted = False
    
    def extract_features(self, positions: List[Position]) -> np.ndarray:
        """
        Extract ~20 features per position
        
        Features:
        - Material balance
        - Piece activity (by type)
        - Pawn structure
        - King safety
        - Centralization
        - Space control
        - Evaluation
        - CPL
        
        Args:
            positions: List of Position objects
        
        Returns:
            Feature matrix (n_positions x 20)
        """
        features = []
        
        for position in positions:
            # Feature 1-3: Material balance, piece activity, king safety (from Phase 1)
            material = getattr(position, 'material_balance', 0.0) or 0.0
            activity = getattr(position, 'piece_activity', 0.0) or 0.0
            king_safety = getattr(position, 'king_safety', 0.5) or 0.5
            
            # Feature 4-5: Evaluation and CPL
            evaluation = getattr(position, 'evaluation', 0.0) or 0.0
            cpl = getattr(position, 'centipawn_loss', 0.0) or 0.0
            
            # Features 6-20: Extended features (derived from basic features)
            # These represent different aspects of the position
            features_vector = [
                material,           # 1: Material balance
                activity,           # 2: Piece activity
                king_safety,        # 3: King safety
                evaluation,         # 4: Position evaluation
                cpl,                # 5: Centipawn loss
                abs(material),      # 6: Abs material
                activity * king_safety,  # 7: Activity-King safety interaction
                evaluation * king_safety,  # 8: Eval-King safety interaction
                cpl / max(1, abs(evaluation)),  # 9: CPL ratio
                king_safety ** 2,   # 10: King safety squared
                activity ** 2,      # 11: Activity squared
                max(0, evaluation),  # 12: Positive eval
                min(0, evaluation),  # 13: Negative eval
                cpl * king_safety,  # 14: CPL weighted by king safety
                material * activity,  # 15: Material-Activity interaction
                (1 - king_safety),  # 16: Inverse king safety
                activity / max(1, king_safety),  # 17: Activity-King ratio
                abs(material - activity),  # 18: Material-Activity diff
                cpl ** 2,           # 19: CPL squared
                evaluation / max(1, cpl),  # 20: Eval-CPL ratio
            ]
            features.append(features_vector)
        
        if not features:
            return np.array([]).reshape(0, 20)
        
        return np.array(features)
    
    def fit(self, positions: List[Position]) -> None:
        """
        Learn embedding space from positions
        
        Args:
            positions: List of Position objects to learn from
        """
        if not positions:
            self.is_fitted = True
            return
        
        features = self.extract_features(positions)
        
        if features.size == 0:
            self.is_fitted = True
            return
        
        # Scale features
        scaled = self.scaler.fit_transform(features)
        
        # Fit PCA
        self.pca.fit(scaled)
        self.is_fitted = True
    
    def embed(self, position: Position) -> np.ndarray:
        """
        Convert position to embedding vector
        
        Args:
            position: Position object
        
        Returns:
            Embedding vector (16-20 floats)
        """
        if not self.is_fitted:
            return np.zeros(self.n_components)
        
        features = self.extract_features([position])
        
        if features.size == 0:
            return np.zeros(self.n_components)
        
        scaled = self.scaler.transform(features)
        embedding = self.pca.transform(scaled)[0]
        
        return embedding
    
    def find_similar(
        self,
        embedding: np.ndarray,
        all_embeddings: np.ndarray,
        k: int = 5
    ) -> List[int]:
        """
        Find k most similar embeddings by cosine distance
        
        Args:
            embedding: Query embedding vector
            all_embeddings: Matrix of all embeddings (n x n_components)
            k: Number of similar embeddings to return
        
        Returns:
            List of indices of k most similar embeddings
        """
        if len(all_embeddings) == 0:
            return []
        
        distances = cosine_distances([embedding], all_embeddings)[0]
        return np.argsort(distances)[:k].tolist()
    
    def get_similarity_score(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Get cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
        
        Returns:
            Similarity score 0-1
        """
        distance = cosine_distances([embedding1], [embedding2])[0][0]
        similarity = 1.0 - distance
        return float(np.clip(similarity, 0.0, 1.0))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_embeddings.py::test_position_embedder_init -v
```

Expected: `PASSED`

- [ ] **Step 5: Write tests for fit, embed, and similarity**

Add to `tests/test_embeddings.py`:

```python
def test_position_embedder_fit_embed():
    """Test fit and embed methods"""
    positions = []
    for i in range(30):
        pos = Mock()
        pos.fen = f"fen_{i}"
        pos.material_balance = np.random.randn()
        pos.piece_activity = np.random.rand()
        pos.king_safety = np.random.rand()
        pos.evaluation = np.random.randn()
        pos.centipawn_loss = np.random.rand() * 100
        positions.append(pos)
    
    embedder = PositionEmbedder(n_components=16)
    embedder.fit(positions)
    
    # Get embedding for first position
    embedding = embedder.embed(positions[0])
    assert embedding.shape == (16,)
    assert not np.all(embedding == 0)


def test_position_embedder_similarity():
    """Test similarity search"""
    positions = []
    for i in range(30):
        pos = Mock()
        pos.fen = f"fen_{i}"
        pos.material_balance = 0.5
        pos.piece_activity = 0.5
        pos.king_safety = 0.5
        pos.evaluation = 0.0
        pos.centipawn_loss = 50.0
        positions.append(pos)
    
    embedder = PositionEmbedder(n_components=16)
    embedder.fit(positions)
    
    # Get embedding
    embedding = embedder.embed(positions[0])
    
    # Find similar embeddings
    all_embeddings = np.array([embedder.embed(p) for p in positions])
    similar_indices = embedder.find_similar(embedding, all_embeddings, k=5)
    
    assert len(similar_indices) == 5
    assert 0 in similar_indices  # Should find itself


def test_position_embedder_similarity_score():
    """Test similarity score calculation"""
    embedder = PositionEmbedder()
    
    # Create two embeddings
    emb1 = np.array([1.0, 0.0, 0.0])
    emb2 = np.array([1.0, 0.0, 0.0])
    
    # Same embeddings should have similarity 1.0
    similarity = embedder.get_similarity_score(emb1, emb2)
    assert similarity > 0.99
```

- [ ] **Step 6: Run all PositionEmbedder tests**

```bash
pytest tests/test_embeddings.py -v
```

Expected: `4 PASSED`

- [ ] **Step 7: Commit PositionEmbedder**

```bash
git add src/chess_analyzer/ml_models/embeddings.py tests/test_embeddings.py
git commit -m "feat: implement PositionEmbedder for semantic position similarity"
```

---

### Task 5: AdvancedAnalysisPipeline Orchestrator

**Files:**
- Create: `src/chess_analyzer/chess_analyzer/advanced_analysis_pipeline.py`
- Test: `tests/test_advanced_pipeline.py`

- [ ] **Step 1: Write failing test for AdvancedAnalysisPipeline**

Create `tests/test_advanced_pipeline.py`:

```python
import pytest
from unittest.mock import Mock, MagicMock
from src.chess_analyzer.chess_analyzer.advanced_analysis_pipeline import AdvancedAnalysisPipeline


def test_advanced_pipeline_init():
    """Test AdvancedAnalysisPipeline initializes correctly"""
    mock_session = Mock()
    pipeline = AdvancedAnalysisPipeline(mock_session)
    
    assert pipeline.session is mock_session
    assert pipeline.move_predictor is not None
    assert pipeline.anomaly_detector is not None
    assert pipeline.embedder is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_advanced_pipeline.py -v
```

Expected: `FAILED - ModuleNotFoundError`

- [ ] **Step 3: Create AdvancedAnalysisPipeline class**

Create `src/chess_analyzer/chess_analyzer/advanced_analysis_pipeline.py`:

```python
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from src.chess_analyzer.ml_models.move_predictor import MovePredictor
from src.chess_analyzer.ml_models.anomaly_detector import AnomalyDetector
from src.chess_analyzer.ml_models.embeddings import PositionEmbedder
from src.chess_analyzer.database.models import (
    Game, Position, MovePrediction, Anomaly, Embedding
)
import logging

logger = logging.getLogger(__name__)


class AdvancedAnalysisPipeline:
    """Orchestrate all Phase 2 ML components"""
    
    def __init__(self, session: Session):
        """
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.move_predictor = MovePredictor(min_position_frequency=5)
        self.anomaly_detector = AnomalyDetector(contamination=0.1)
        self.embedder = PositionEmbedder(n_components=16)
    
    def analyze_player(self, username: str) -> Dict:
        """
        Run all advanced analyses for a player
        
        Args:
            username: Chess.com username
        
        Returns:
            Dict with analysis results
        """
        # 1. Fetch player's games from Phase 1
        games = self.session.query(Game).filter(
            Game.username == username
        ).all()
        
        if not games:
            return {
                "username": username,
                "status": "error",
                "message": "No games found"
            }
        
        logger.info(f"Analyzing {len(games)} games for {username}")
        
        # 2. Fit models
        try:
            self.move_predictor.fit(games)
            logger.info("MovePredictor fitted")
        except Exception as e:
            logger.error(f"MovePredictor fit failed: {e}")
            return {
                "username": username,
                "status": "error",
                "message": f"MovePredictor failed: {str(e)}"
            }
        
        # Get positions for other models
        positions = self.session.query(Position).filter(
            Position.game_id.in_([g.id for g in games])
        ).all()
        
        if not positions:
            return {
                "username": username,
                "status": "error",
                "message": "No positions found"
            }
        
        try:
            self.anomaly_detector.fit(positions)
            logger.info("AnomalyDetector fitted")
        except Exception as e:
            logger.error(f"AnomalyDetector fit failed: {e}")
            return {
                "username": username,
                "status": "error",
                "message": f"AnomalyDetector failed: {str(e)}"
            }
        
        try:
            self.embedder.fit(positions)
            logger.info("PositionEmbedder fitted")
        except Exception as e:
            logger.error(f"PositionEmbedder fit failed: {e}")
            return {
                "username": username,
                "status": "error",
                "message": f"PositionEmbedder failed: {str(e)}"
            }
        
        # 3. Score each position and save results
        move_pred_count = 0
        anomaly_count = 0
        embedding_count = 0
        
        for game in games:
            for position in game.positions:
                try:
                    # Score move predictions
                    if hasattr(position, 'move') and position.move:
                        prob = self.move_predictor.predict(position.fen, position.move)
                        if prob < 0.2:  # Unusual threshold
                            self._save_move_prediction(
                                game.id, position, prob
                            )
                            move_pred_count += 1
                    
                    # Score anomalies
                    anom_score = self.anomaly_detector.predict(position)
                    if anom_score > 0.7:  # Anomaly threshold
                        self._save_anomaly(game.id, position, anom_score)
                        anomaly_count += 1
                    
                    # Get embeddings (always save)
                    embedding = self.embedder.embed(position)
                    self._save_embedding(position, embedding)
                    embedding_count += 1
                
                except Exception as e:
                    logger.warning(f"Failed to score position: {e}")
                    continue
        
        logger.info(f"Analysis complete: {move_pred_count} predictions, "
                   f"{anomaly_count} anomalies, {embedding_count} embeddings")
        
        return {
            "username": username,
            "status": "completed",
            "unusual_moves_found": move_pred_count,
            "anomalies_found": anomaly_count,
            "embeddings_created": embedding_count
        }
    
    def _save_move_prediction(self, game_id: int, position: Position, probability: float) -> None:
        """Save move prediction to database"""
        try:
            prediction = MovePrediction(
                game_id=game_id,
                position_fen=position.fen,
                actual_move=getattr(position, 'move', ''),
                predicted_move=None,  # Could calculate most likely move
                probability_score=probability,
                is_unusual=True
            )
            self.session.add(prediction)
            self.session.commit()
        except Exception as e:
            logger.warning(f"Failed to save move prediction: {e}")
            self.session.rollback()
    
    def _save_anomaly(self, game_id: int, position: Position, anomaly_score: float) -> None:
        """Save anomaly to database"""
        try:
            cpl = getattr(position, 'centipawn_loss', 0.0) or 0.0
            
            # Categorize anomaly
            if cpl > 300:
                reason = "rare blunder"
            elif cpl > 150:
                reason = "unusual tactic miss"
            else:
                reason = "unusual move"
            
            anomaly = Anomaly(
                game_id=game_id,
                position_fen=position.fen,
                anomaly_score=anomaly_score,
                centipawn_loss=cpl,
                reason=reason
            )
            self.session.add(anomaly)
            self.session.commit()
        except Exception as e:
            logger.warning(f"Failed to save anomaly: {e}")
            self.session.rollback()
    
    def _save_embedding(self, position: Position, embedding_vector: list) -> None:
        """Save embedding to database"""
        try:
            embedding = Embedding(
                position_id=position.id,
                embedding_vector=embedding_vector.tolist(),
                embedding_cluster=None  # Could be filled with K-Means
            )
            self.session.add(embedding)
            self.session.commit()
        except Exception as e:
            logger.warning(f"Failed to save embedding: {e}")
            self.session.rollback()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_advanced_pipeline.py::test_advanced_pipeline_init -v
```

Expected: `PASSED`

- [ ] **Step 5: Write integration test**

Add to `tests/test_advanced_pipeline.py`:

```python
def test_advanced_pipeline_analyze_empty_games():
    """Test analyze_player with no games"""
    mock_session = Mock()
    mock_session.query.return_value.filter.return_value.all.return_value = []
    
    pipeline = AdvancedAnalysisPipeline(mock_session)
    result = pipeline.analyze_player("nonexistent_user")
    
    assert result["status"] == "error"
    assert "No games found" in result["message"]
```

- [ ] **Step 6: Run AdvancedAnalysisPipeline tests**

```bash
pytest tests/test_advanced_pipeline.py -v
```

Expected: `2 PASSED`

- [ ] **Step 7: Commit AdvancedAnalysisPipeline**

```bash
git add src/chess_analyzer/chess_analyzer/advanced_analysis_pipeline.py tests/test_advanced_pipeline.py
git commit -m "feat: implement AdvancedAnalysisPipeline orchestrator"
```

---

### Task 6: API Schemas for Phase 2 Endpoints

**Files:**
- Modify: `src/chess_analyzer/api/schemas.py`

- [ ] **Step 1: Read existing schemas to understand pattern**

```bash
head -50 src/chess_analyzer/api/schemas.py
```

- [ ] **Step 2: Add Phase 2 request/response schemas**

Open `src/chess_analyzer/api/schemas.py` and add at the end:

```python
# Phase 2 Advanced Analysis Schemas

class MovePredictionResponse(BaseModel):
    """Response for move prediction"""
    game_id: int
    position_fen: str
    actual_move: str
    predicted_move: Optional[str] = None
    probability_score: float
    is_unusual: bool


class AnomalyResponse(BaseModel):
    """Response for anomaly"""
    game_id: int
    position_fen: str
    anomaly_score: float
    centipawn_loss: float
    reason: Optional[str] = None


class AdvancedAnalysisRequest(BaseModel):
    """Request to start advanced analysis"""
    username: str
    game_limit: Optional[int] = 100
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "hikaru",
                "game_limit": 100
            }
        }


class AdvancedAnalysisResponse(BaseModel):
    """Response when starting analysis"""
    job_id: str
    status: str
    username: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "abc123def456",
                "status": "processing",
                "username": "hikaru"
            }
        }


class AdvancedAnalysisStatusResponse(BaseModel):
    """Response for analysis status check"""
    job_id: str
    status: str
    username: str
    move_predictor_done: bool = False
    anomaly_detector_done: bool = False
    embedder_done: bool = False
    unusual_moves_count: Optional[int] = None
    anomalies_count: Optional[int] = None
    embeddings_count: Optional[int] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "abc123def456",
                "status": "completed",
                "username": "hikaru",
                "move_predictor_done": True,
                "anomaly_detector_done": True,
                "embedder_done": True,
                "unusual_moves_count": 42,
                "anomalies_count": 18,
                "embeddings_count": 500
            }
        }


class SimilarPositionResponse(BaseModel):
    """Response for similar position"""
    position_id: int
    similarity_score: float
    game_id: int
    centipawn_loss: float
    position_fen: str


class PatternDetailResponse(BaseModel):
    """Enhanced pattern with Phase 2 data"""
    id: int
    name: str
    type: str
    frequency: int
    avg_loss: float
    affected_games: int
    unusual_moves_in_pattern: int
    anomaly_count: int
    similar_patterns: List[int]
    study_priority: str
```

- [ ] **Step 3: Commit schemas**

```bash
git add src/chess_analyzer/api/schemas.py
git commit -m "feat: add Phase 2 API request/response schemas"
```

---

### Task 7: API Endpoints for Phase 2

**Files:**
- Modify: `src/chess_analyzer/api/routes.py`

- [ ] **Step 1: Add imports to routes.py**

Open `src/chess_analyzer/api/routes.py` and add at the top:

```python
from src.chess_analyzer.chess_analyzer.advanced_analysis_pipeline import AdvancedAnalysisPipeline
from src.chess_analyzer.api.schemas import (
    AdvancedAnalysisRequest,
    AdvancedAnalysisResponse,
    AdvancedAnalysisStatusResponse,
    MovePredictionResponse,
    AnomalyResponse,
    SimilarPositionResponse,
    PatternDetailResponse,
)
from src.chess_analyzer.database.models import (
    MovePrediction,
    Anomaly,
    Embedding,
    AdvancedAnalysisJob,
)
import uuid
from sqlalchemy import and_
```

- [ ] **Step 2: Add POST /api/advanced-analysis endpoint**

Add to `src/chess_analyzer/api/routes.py`:

```python
@router.post("/advanced-analysis", response_model=AdvancedAnalysisResponse)
async def start_advanced_analysis(
    request: AdvancedAnalysisRequest,
    session: Session = Depends(get_session)
):
    """
    Start advanced analysis for a player
    
    - **username**: Chess.com username
    - **game_limit**: Max games to analyze (default 100)
    """
    # Create job record
    job_id = str(uuid.uuid4())
    job = AdvancedAnalysisJob(
        username=request.username,
        job_id=job_id,
        status="processing"
    )
    session.add(job)
    session.commit()
    
    # Run analysis (in production, this would be async)
    try:
        pipeline = AdvancedAnalysisPipeline(session)
        pipeline.analyze_player(request.username)
        
        # Update job status
        job.status = "completed"
        job.move_predictor_done = True
        job.anomaly_detector_done = True
        job.embedder_done = True
        job.completed_at = datetime.now(timezone.utc)
        session.commit()
    except Exception as e:
        job.status = "failed"
        session.commit()
        raise HTTPException(status_code=500, detail=str(e))
    
    return AdvancedAnalysisResponse(
        job_id=job_id,
        status="processing",
        username=request.username
    )


@router.get("/advanced-analysis/{job_id}", response_model=AdvancedAnalysisStatusResponse)
async def get_advanced_analysis_status(
    job_id: str,
    session: Session = Depends(get_session)
):
    """Check advanced analysis job status"""
    job = session.query(AdvancedAnalysisJob).filter(
        AdvancedAnalysisJob.job_id == job_id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get counts from database
    unusual_moves = session.query(MovePrediction).filter(
        MovePrediction.game_id.in_(
            session.query(Game.id).filter(Game.username == job.username)
        )
    ).count()
    
    anomalies = session.query(Anomaly).filter(
        Anomaly.game_id.in_(
            session.query(Game.id).filter(Game.username == job.username)
        )
    ).count()
    
    embeddings = session.query(Embedding).count()
    
    return AdvancedAnalysisStatusResponse(
        job_id=job_id,
        status=job.status,
        username=job.username,
        move_predictor_done=job.move_predictor_done,
        anomaly_detector_done=job.anomaly_detector_done,
        embedder_done=job.embedder_done,
        unusual_moves_count=unusual_moves,
        anomalies_count=anomalies,
        embeddings_count=embeddings
    )
```

- [ ] **Step 3: Add GET /api/move-predictions endpoint**

Add to `src/chess_analyzer/api/routes.py`:

```python
@router.get("/move-predictions", response_model=List[MovePredictionResponse])
async def get_move_predictions(
    username: Optional[str] = None,
    game_id: Optional[int] = None,
    min_probability: float = 0.0,
    session: Session = Depends(get_session)
):
    """
    Get unusual move predictions
    
    - **username**: Filter by player (optional)
    - **game_id**: Filter by game (optional)
    - **min_probability**: Minimum probability threshold
    """
    query = session.query(MovePrediction)
    
    if username:
        query = query.join(Game).filter(Game.username == username)
    
    if game_id:
        query = query.filter(MovePrediction.game_id == game_id)
    
    predictions = query.filter(
        MovePrediction.probability_score >= min_probability
    ).all()
    
    return predictions
```

- [ ] **Step 4: Add GET /api/anomalies endpoint**

Add to `src/chess_analyzer/api/routes.py`:

```python
@router.get("/anomalies", response_model=List[AnomalyResponse])
async def get_anomalies(
    username: Optional[str] = None,
    game_id: Optional[int] = None,
    min_score: float = 0.0,
    session: Session = Depends(get_session)
):
    """
    Get detected anomalies (rare mistakes)
    
    - **username**: Filter by player (optional)
    - **game_id**: Filter by game (optional)
    - **min_score**: Minimum anomaly score (0-1)
    """
    query = session.query(Anomaly)
    
    if username:
        query = query.join(Game).filter(Game.username == username)
    
    if game_id:
        query = query.filter(Anomaly.game_id == game_id)
    
    anomalies = query.filter(
        Anomaly.anomaly_score >= min_score
    ).order_by(Anomaly.anomaly_score.desc()).all()
    
    return anomalies
```

- [ ] **Step 5: Add GET /api/similar-positions endpoint**

Add to `src/chess_analyzer/api/routes.py`:

```python
@router.get("/similar-positions", response_model=List[SimilarPositionResponse])
async def get_similar_positions(
    position_fen: str,
    limit: int = 10,
    session: Session = Depends(get_session)
):
    """
    Find semantically similar positions
    
    - **position_fen**: Position FEN string
    - **limit**: Max similar positions to return
    """
    # Get embedding for input position
    pipeline = AdvancedAnalysisPipeline(session)
    
    # Find position in database
    input_pos = session.query(Position).filter(
        Position.fen == position_fen
    ).first()
    
    if not input_pos:
        raise HTTPException(status_code=404, detail="Position not found")
    
    # Get its embedding
    input_embedding = session.query(Embedding).filter(
        Embedding.position_id == input_pos.id
    ).first()
    
    if not input_embedding:
        raise HTTPException(status_code=404, detail="Embedding not found")
    
    # Get all embeddings and find similar
    all_embeddings = session.query(Embedding).all()
    
    if not all_embeddings:
        return []
    
    import numpy as np
    all_vectors = np.array([e.embedding_vector for e in all_embeddings])
    similar_indices = pipeline.embedder.find_similar(
        np.array(input_embedding.embedding_vector),
        all_vectors,
        k=min(limit, len(all_embeddings))
    )
    
    results = []
    for idx in similar_indices:
        emb = all_embeddings[idx]
        pos = emb.position
        similarity = pipeline.embedder.get_similarity_score(
            np.array(input_embedding.embedding_vector),
            np.array(emb.embedding_vector)
        )
        results.append(SimilarPositionResponse(
            position_id=pos.id,
            similarity_score=similarity,
            game_id=pos.game_id,
            centipawn_loss=pos.centipawn_loss or 0.0,
            position_fen=pos.fen
        ))
    
    return results
```

- [ ] **Step 6: Add GET /api/pattern-details/{pattern_id} endpoint**

Add to `src/chess_analyzer/api/routes.py`:

```python
@router.get("/pattern-details/{pattern_id}", response_model=PatternDetailResponse)
async def get_pattern_details(
    pattern_id: int,
    session: Session = Depends(get_session)
):
    """
    Get detailed pattern information with Phase 2 data
    
    - **pattern_id**: Pattern ID
    """
    pattern = session.query(Pattern).filter(Pattern.id == pattern_id).first()
    
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    
    # Count unusual moves and anomalies in this pattern
    # (simplified - would need game mapping to pattern)
    unusual_moves = 0
    anomaly_count = 0
    similar_patterns = []
    
    # Determine study priority based on frequency and impact
    if pattern.frequency > 10 and pattern.avg_loss > 200:
        study_priority = "critical"
    elif pattern.frequency > 5 or pattern.avg_loss > 150:
        study_priority = "high"
    else:
        study_priority = "medium"
    
    return PatternDetailResponse(
        id=pattern.id,
        name=pattern.name,
        type=pattern.type,
        frequency=pattern.frequency,
        avg_loss=pattern.avg_loss,
        affected_games=pattern.affected_games or 0,
        unusual_moves_in_pattern=unusual_moves,
        anomaly_count=anomaly_count,
        similar_patterns=similar_patterns,
        study_priority=study_priority
    )
```

- [ ] **Step 7: Commit API endpoints**

```bash
git add src/chess_analyzer/api/routes.py
git commit -m "feat: add 5 Phase 2 API endpoints (advanced analysis, predictions, anomalies, embeddings)"
```

---

### Task 8: PatternExplorer UI Component - Main Component

**Files:**
- Create: `frontend/src/components/PatternExplorer.jsx`
- Create: `frontend/src/styles/PatternExplorer.css`

- [ ] **Step 1: Create PatternExplorer main component**

Create `frontend/src/components/PatternExplorer.jsx`:

```javascript
import React, { useState, useEffect } from 'react';
import { chessAPI } from '../api';
import PatternFilter from './PatternFilter';
import PatternList from './PatternList';
import PatternDetail from './PatternDetail';
import '../styles/PatternExplorer.css';

export default function PatternExplorer() {
  const [username, setUsername] = useState('');
  const [stats, setStats] = useState(null);
  const [patterns, setPatterns] = useState([]);
  const [selectedPattern, setSelectedPattern] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState({
    type: 'all',
    sortBy: 'frequency',
    minFrequency: 1,
  });
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleLoadAnalysis = async (e) => {
    e.preventDefault();
    if (!username) return;

    setLoading(true);
    setError(null);

    try {
      const statsData = await chessAPI.getStats(username);
      setStats(statsData);

      const patternsData = await chessAPI.getPatterns(username);
      setPatterns(patternsData || []);
      
      // Try to load Phase 2 data if available
      if (statsData.phase_2_available) {
        setShowAdvanced(true);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRunAdvancedAnalysis = async () => {
    if (!username) return;

    setLoading(true);
    setError(null);

    try {
      const result = await chessAPI.startAdvancedAnalysis(username, 100);
      
      // Poll for completion
      let completed = false;
      let attempts = 0;
      while (!completed && attempts < 60) {
        await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds
        
        const status = await chessAPI.getAdvancedAnalysisStatus(result.job_id);
        if (status.status === 'completed') {
          completed = true;
          // Reload data
          const statsData = await chessAPI.getStats(username);
          setStats(statsData);
          const patternsData = await chessAPI.getPatterns(username);
          setPatterns(patternsData || []);
        }
        attempts++;
      }

      if (!completed) {
        setError('Advanced analysis timed out');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const filteredPatterns = patterns.filter(p => {
    if (filter.type !== 'all' && p.type !== filter.type) return false;
    if (p.frequency < filter.minFrequency) return false;
    return true;
  }).sort((a, b) => {
    switch (filter.sortBy) {
      case 'frequency':
        return b.frequency - a.frequency;
      case 'impact':
        return b.avg_loss - a.avg_loss;
      case 'priority':
        const priorityOrder = { critical: 0, high: 1, medium: 2 };
        return (priorityOrder[a.study_priority] || 3) - (priorityOrder[b.study_priority] || 3);
      default:
        return 0;
    }
  });

  return (
    <div className="pattern-explorer-container">
      <h1>Chess Pattern Explorer</h1>
      
      <form onSubmit={handleLoadAnalysis} className="pattern-explorer-form">
        <div className="form-group">
          <input
            type="text"
            placeholder="Enter chess.com username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
          <button type="submit" disabled={loading || !username}>
            {loading ? 'Loading...' : 'Load Analysis'}
          </button>
          {showAdvanced && (
            <button 
              type="button"
              onClick={handleRunAdvancedAnalysis}
              disabled={loading}
              className="btn-advanced"
            >
              {loading ? 'Analyzing...' : 'Run Advanced Analysis'}
            </button>
          )}
        </div>
      </form>

      {error && <div className="error-message">Error: {error}</div>}

      {stats && (
        <>
          <div className="stats-summary">
            <div className="stat-item">
              <span className="stat-label">Total Games</span>
              <span className="stat-value">{stats.total_games}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Overall Accuracy</span>
              <span className="stat-value">{stats.overall_accuracy?.toFixed(1)}%</span>
            </div>
            {showAdvanced && (
              <>
                <div className="stat-item">
                  <span className="stat-label">Unusual Moves</span>
                  <span className="stat-value">{stats.unusual_moves_total || 0}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Anomalies</span>
                  <span className="stat-value">{stats.anomalies_total || 0}</span>
                </div>
              </>
            )}
          </div>

          <div className="explorer-content">
            <div className="filter-panel">
              <PatternFilter 
                filter={filter}
                onFilterChange={setFilter}
              />
            </div>

            <div className="pattern-panel">
              {selectedPattern ? (
                <PatternDetail
                  pattern={selectedPattern}
                  onBack={() => setSelectedPattern(null)}
                />
              ) : (
                <PatternList
                  patterns={filteredPatterns}
                  onSelectPattern={setSelectedPattern}
                  showAdvanced={showAdvanced}
                />
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Create PatternExplorer styles**

Create `frontend/src/styles/PatternExplorer.css`:

```css
.pattern-explorer-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.pattern-explorer-form {
  margin-bottom: 30px;
}

.pattern-explorer-form .form-group {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.pattern-explorer-form input {
  flex: 1;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
}

.pattern-explorer-form button {
  padding: 10px 20px;
  background: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
}

.pattern-explorer-form button:hover:not(:disabled) {
  background: #45a049;
}

.pattern-explorer-form button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.pattern-explorer-form .btn-advanced {
  background: #2196F3;
}

.pattern-explorer-form .btn-advanced:hover:not(:disabled) {
  background: #0b7dda;
}

.stats-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
  margin-bottom: 30px;
}

.stat-item {
  background: #f5f5f5;
  padding: 15px;
  border-radius: 4px;
  text-align: center;
}

.stat-label {
  display: block;
  font-size: 14px;
  color: #666;
  margin-bottom: 5px;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: bold;
  color: #333;
}

.explorer-content {
  display: grid;
  grid-template-columns: 250px 1fr;
  gap: 20px;
}

.filter-panel {
  background: #f9f9f9;
  padding: 15px;
  border-radius: 4px;
  height: fit-content;
}

.pattern-panel {
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 20px;
}

.error-message {
  background: #ffebee;
  color: #c62828;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 20px;
}

@media (max-width: 768px) {
  .explorer-content {
    grid-template-columns: 1fr;
  }

  .pattern-explorer-form .form-group {
    flex-direction: column;
  }

  .stats-summary {
    grid-template-columns: repeat(2, 1fr);
  }
}
```

- [ ] **Step 3: Add API methods to api.js**

Open `frontend/src/api.js` and add:

```javascript
export const chessAPI = {
  // ... existing methods ...

  // Phase 2 Advanced Analysis
  startAdvancedAnalysis: async (username, gameLimit = 100) => {
    const response = await fetch(`${BASE_URL}/api/advanced-analysis`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, game_limit: gameLimit })
    });
    if (!response.ok) throw new Error(`Failed to start analysis: ${response.statusText}`);
    return response.json();
  },

  getAdvancedAnalysisStatus: async (jobId) => {
    const response = await fetch(`${BASE_URL}/api/advanced-analysis/${jobId}`);
    if (!response.ok) throw new Error(`Failed to get analysis status: ${response.statusText}`);
    return response.json();
  },

  getMovePredictions: async (username, minProbability = 0.0) => {
    const params = new URLSearchParams({ username, min_probability: minProbability });
    const response = await fetch(`${BASE_URL}/api/move-predictions?${params}`);
    if (!response.ok) throw new Error(`Failed to get move predictions: ${response.statusText}`);
    return response.json();
  },

  getAnomalies: async (username, minScore = 0.0) => {
    const params = new URLSearchParams({ username, min_score: minScore });
    const response = await fetch(`${BASE_URL}/api/anomalies?${params}`);
    if (!response.ok) throw new Error(`Failed to get anomalies: ${response.statusText}`);
    return response.json();
  },

  getSimilarPositions: async (positionFen, limit = 10) => {
    const params = new URLSearchParams({ position_fen: positionFen, limit });
    const response = await fetch(`${BASE_URL}/api/similar-positions?${params}`);
    if (!response.ok) throw new Error(`Failed to get similar positions: ${response.statusText}`);
    return response.json();
  },

  getPatternDetails: async (patternId) => {
    const response = await fetch(`${BASE_URL}/api/pattern-details/${patternId}`);
    if (!response.ok) throw new Error(`Failed to get pattern details: ${response.statusText}`);
    return response.json();
  }
};
```

- [ ] **Step 4: Commit PatternExplorer main component**

```bash
git add frontend/src/components/PatternExplorer.jsx frontend/src/styles/PatternExplorer.css frontend/src/api.js
git commit -m "feat: add PatternExplorer main component with Phase 2 API integration"
```

---

### Task 9: PatternExplorer Sub-Components

**Files:**
- Create: `frontend/src/components/PatternFilter.jsx`
- Create: `frontend/src/components/PatternList.jsx`
- Create: `frontend/src/components/PatternDetail.jsx`
- Create: Sub-components for pattern details

- [ ] **Step 1: Create PatternFilter component**

Create `frontend/src/components/PatternFilter.jsx`:

```javascript
import React from 'react';

export default function PatternFilter({ filter, onFilterChange }) {
  return (
    <div className="pattern-filter">
      <h3>Filter & Sort</h3>
      
      <div className="filter-group">
        <label>Pattern Type</label>
        <select
          value={filter.type}
          onChange={(e) => onFilterChange({ ...filter, type: e.target.value })}
        >
          <option value="all">All Types</option>
          <option value="tactical">Tactical</option>
          <option value="positional">Positional</option>
          <option value="opening">Opening</option>
        </select>
      </div>

      <div className="filter-group">
        <label>Sort By</label>
        <select
          value={filter.sortBy}
          onChange={(e) => onFilterChange({ ...filter, sortBy: e.target.value })}
        >
          <option value="frequency">Frequency</option>
          <option value="impact">Impact (Avg Loss)</option>
          <option value="priority">Study Priority</option>
        </select>
      </div>

      <div className="filter-group">
        <label>Min Frequency: {filter.minFrequency}</label>
        <input
          type="range"
          min="1"
          max="20"
          value={filter.minFrequency}
          onChange={(e) => onFilterChange({ ...filter, minFrequency: parseInt(e.target.value) })}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create PatternList component**

Create `frontend/src/components/PatternList.jsx`:

```javascript
import React from 'react';

export default function PatternList({ patterns, onSelectPattern, showAdvanced }) {
  if (patterns.length === 0) {
    return <div className="no-patterns">No patterns found</div>;
  }

  return (
    <div className="pattern-list">
      <h2>Weakness Patterns ({patterns.length})</h2>
      {patterns.map((pattern) => (
        <div
          key={pattern.id}
          className="pattern-card"
          onClick={() => onSelectPattern(pattern)}
          role="button"
          tabIndex={0}
        >
          <div className="pattern-header">
            <h3>{pattern.name}</h3>
            <span className={`priority ${pattern.study_priority || 'medium'}`}>
              {pattern.study_priority || 'Medium'}
            </span>
          </div>
          
          <div className="pattern-stats">
            <div className="stat">
              <span className="label">Frequency:</span>
              <span className="value">{pattern.frequency}</span>
            </div>
            <div className="stat">
              <span className="label">Avg Loss:</span>
              <span className="value">{pattern.avg_loss.toFixed(0)} cp</span>
            </div>
            <div className="stat">
              <span className="label">Games:</span>
              <span className="value">{pattern.affected_games || 0}</span>
            </div>
          </div>

          {showAdvanced && pattern.unusual_moves_in_pattern > 0 && (
            <div className="advanced-info">
              <span>🔸 {pattern.unusual_moves_in_pattern} unusual moves</span>
              <span>🔴 {pattern.anomaly_count || 0} anomalies</span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Create PatternDetail component**

Create `frontend/src/components/PatternDetail.jsx`:

```javascript
import React from 'react';

export default function PatternDetail({ pattern, onBack }) {
  return (
    <div className="pattern-detail">
      <button className="btn-back" onClick={onBack}>← Back to Patterns</button>
      
      <h2>{pattern.name}</h2>
      
      <div className="detail-grid">
        <div className="detail-card">
          <h3>Overview</h3>
          <div className="detail-row">
            <span className="label">Type:</span>
            <span className="value">{pattern.type}</span>
          </div>
          <div className="detail-row">
            <span className="label">Frequency:</span>
            <span className="value">{pattern.frequency} times</span>
          </div>
          <div className="detail-row">
            <span className="label">Avg Loss:</span>
            <span className="value">{pattern.avg_loss.toFixed(0)} cp</span>
          </div>
          <div className="detail-row">
            <span className="label">Affected Games:</span>
            <span className="value">{pattern.affected_games || 0}</span>
          </div>
        </div>

        {pattern.unusual_moves_in_pattern > 0 && (
          <div className="detail-card">
            <h3>Unusual Moves</h3>
            <p>{pattern.unusual_moves_in_pattern} unusual moves detected in this pattern</p>
            <p className="help-text">
              These are moves that deviate from your typical play style in similar positions.
            </p>
          </div>
        )}

        {pattern.anomaly_count > 0 && (
          <div className="detail-card">
            <h3>Rare Mistakes</h3>
            <p>{pattern.anomaly_count} statistically rare mistakes found</p>
            <p className="help-text">
              These are unusually costly mistakes compared to your typical errors.
            </p>
          </div>
        )}

        {pattern.similar_patterns && pattern.similar_patterns.length > 0 && (
          <div className="detail-card">
            <h3>Similar Patterns</h3>
            <p>Related patterns: {pattern.similar_patterns.join(', ')}</p>
          </div>
        )}
      </div>

      <div className="study-recommendation">
        <h3>Study Recommendation</h3>
        <p>
          {pattern.study_priority === 'critical' && (
            'This pattern has high frequency and high impact. Focus on understanding the key positions and principles.'
          )}
          {pattern.study_priority === 'high' && (
            'This pattern appears frequently or has significant impact. Dedicated study could improve your rating.'
          )}
          {pattern.study_priority === 'medium' && (
            'This pattern has moderate frequency and impact. Review when you have time.'
          )}
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Update PatternExplorer styles to include sub-component styles**

Add to `frontend/src/styles/PatternExplorer.css`:

```css
/* PatternFilter styles */
.pattern-filter {
  background: white;
}

.pattern-filter h3 {
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 16px;
  color: #333;
}

.filter-group {
  margin-bottom: 20px;
}

.filter-group label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.filter-group select,
.filter-group input[type="range"] {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

/* PatternList styles */
.pattern-list h2 {
  margin-top: 0;
  margin-bottom: 15px;
}

.no-patterns {
  padding: 30px;
  text-align: center;
  color: #999;
}

.pattern-card {
  background: #f9f9f9;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 15px;
  margin-bottom: 15px;
  cursor: pointer;
  transition: all 0.2s;
}

.pattern-card:hover {
  background: #f0f0f0;
  border-color: #4CAF50;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.pattern-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.pattern-header h3 {
  margin: 0;
  font-size: 16px;
}

.priority {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
}

.priority.critical {
  background: #ffebee;
  color: #c62828;
}

.priority.high {
  background: #fff3e0;
  color: #e65100;
}

.priority.medium {
  background: #e3f2fd;
  color: #1565c0;
}

.pattern-stats {
  display: flex;
  gap: 15px;
  margin-bottom: 10px;
  font-size: 14px;
}

.stat {
  flex: 1;
}

.stat .label {
  color: #666;
  margin-right: 5px;
}

.stat .value {
  font-weight: bold;
  color: #333;
}

.advanced-info {
  display: flex;
  gap: 10px;
  padding-top: 10px;
  border-top: 1px solid #ddd;
  font-size: 13px;
}

/* PatternDetail styles */
.pattern-detail {
  max-width: 100%;
}

.btn-back {
  background: #f0f0f0;
  border: 1px solid #ddd;
  padding: 8px 12px;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 20px;
  font-size: 14px;
}

.btn-back:hover {
  background: #e0e0e0;
}

.pattern-detail h2 {
  margin-top: 0;
  margin-bottom: 20px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
}

.detail-card {
  background: #f9f9f9;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 15px;
}

.detail-card h3 {
  margin-top: 0;
  margin-bottom: 10px;
  font-size: 14px;
  color: #333;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
}

.detail-row .label {
  color: #666;
}

.detail-row .value {
  font-weight: bold;
  color: #333;
}

.help-text {
  font-size: 12px;
  color: #666;
  margin: 8px 0 0 0;
}

.study-recommendation {
  background: #e8f5e9;
  border: 1px solid #4CAF50;
  border-radius: 4px;
  padding: 15px;
  margin-top: 20px;
}

.study-recommendation h3 {
  margin-top: 0;
  color: #2e7d32;
}

.study-recommendation p {
  margin: 8px 0;
  color: #1b5e20;
}
```

- [ ] **Step 5: Commit sub-components**

```bash
git add frontend/src/components/PatternFilter.jsx frontend/src/components/PatternList.jsx frontend/src/components/PatternDetail.jsx
git commit -m "feat: add PatternExplorer sub-components (Filter, List, Detail)"
```

---

### Task 10: Update App.jsx to Use PatternExplorer

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Update App.jsx to import and use PatternExplorer**

Open `frontend/src/App.jsx` and replace the Dashboard import:

```javascript
import PatternExplorer from './components/PatternExplorer';
```

And replace in the return statement:

```javascript
return (
  <div className="App">
    <PatternExplorer />
  </div>
);
```

- [ ] **Step 2: Test the build**

```bash
cd frontend
npm run build
```

Expected: Build completes with no errors

- [ ] **Step 3: Commit App.jsx update**

```bash
git add frontend/src/App.jsx
git commit -m "feat: update App.jsx to use PatternExplorer component"
```

---

### Task 11: Final Testing and Documentation

**Files:**
- Modify: `README.md` (update with Phase 2 info)
- Create/Modify: API documentation

- [ ] **Step 1: Run all tests**

```bash
pytest tests/ -v --cov=src
```

Expected: All tests passing

- [ ] **Step 2: Update README with Phase 2 features**

Open `README.md` and update the Features section to include Phase 2 components

- [ ] **Step 3: Update TECHNICAL_DOCUMENTATION.md**

Add Phase 2 component documentation to the tech docs

- [ ] **Step 4: Final commit**

```bash
git add README.md docs/TECHNICAL_DOCUMENTATION.md
git commit -m "docs: update documentation for Phase 2 completion"
```

---

## Execution Checklist

Complete tasks in order:

- [ ] Task 1: Database Models (4 new ORM tables)
- [ ] Task 2: MovePredictor ML component
- [ ] Task 3: AnomalyDetector ML component
- [ ] Task 4: PositionEmbedder ML component
- [ ] Task 5: AdvancedAnalysisPipeline orchestrator
- [ ] Task 6: API Schemas
- [ ] Task 7: API Endpoints (5 new + enhancements)
- [ ] Task 8: PatternExplorer main component + styles
- [ ] Task 9: PatternExplorer sub-components
- [ ] Task 10: Update App.jsx
- [ ] Task 11: Testing and documentation

---

**Implementation Status:** Ready for subagent-driven execution  
**Estimated Duration:** 6-8 hours for complete implementation  
**Test Coverage Target:** 90%+ of new code  
**Success Criteria:** All 4 ML models working, 5 API endpoints functional, PatternExplorer UI displaying Phase 2 results, all tests passing
