# Machine Learning Techniques Literature Review

## Chess Analyzer: ML Methods for Weakness Detection

**Date**: April 12, 2026  
**Project**: Chess Analyzer MVP  
**Focus**: Practical ML techniques for identifying player weaknesses in chess games

---

## 1. Introduction

This literature review examines machine learning techniques used in the Chess Analyzer to identify repeated player mistakes and weakness patterns from chess.com game history. The goal is to help players improve by breaking bad habits through pattern recognition and statistical analysis.

**Core Challenge**: How can we automatically detect recurring weaknesses in a player's game when analyzing 50-200+ games?

**Approach**: Multi-faceted ML system combining supervised metrics, unsupervised clustering, and feature engineering.

---

## 2. Move Quality Metrics: Centipawn Loss (CPL)

### 2.1 What is Centipawn Loss?

**Definition**: Centipawn loss measures the evaluation difference between the position before a move and after, compared to what a perfect engine move would achieve.

**Formula**:
```
CPL = |eval_before - eval_after|
```

Where:
- `eval_before` = Engine evaluation of position before the move (in centipawns, cp)
- `eval_after` = Engine evaluation of position after the move
- 1 pawn = 100 centipawns
- CPL = 0: Perfect move
- CPL = 5-50: Good move, minor inaccuracy
- CPL = 50-200: Mistake (worse alternative exists)
- CPL > 200: Blunder (major tactical loss)

### 2.2 ACPL: Average Centipawn Loss

**Definition**: ACPL aggregates CPL across all moves in a game to measure overall accuracy.

**Formula**:
```
ACPL = Σ(CPL_i) / n_moves
```

Where `n_moves` = total moves in game

**Why It Works**:
- **Correlation with Elo**: Research shows ACPL correlates >0.98 with player rating
- **Quantifiable**: Exact numerical measure of move quality
- **Comparable**: Can compare accuracy across games, openings, phases
- **Engine-Based**: Uses engine analysis as ground truth

**Research Context**:
- [Expected Human Performance Behavior in Chess Using Centipawn Loss Analysis](https://link.springer.com/chapter/10.1007/978-3-031-35979-8_19)
- Shows that human ACPL follows predictable patterns by rating
- Intermediate players (1200-1600 Elo) have consistent error profiles

### 2.3 Implementation in Chess Analyzer

```python
def calculate_centipawn_loss(eval_before: float, eval_after: float) -> float:
    """Calculate CPL for a single move."""
    return abs(eval_before - eval_after)

def get_acpl(positions: List[Dict]) -> float:
    """Calculate ACPL for a game."""
    cpls = [calculate_centipawn_loss(pos['eval_before'], pos['eval_after']) 
            for pos in positions]
    return sum(cpls) / len(cpls)
```

**Advantages**:
- Simple, mathematically sound
- Engine-independent (works with any chess engine)
- Fast to compute
- Easy to interpret

**Limitations**:
- Doesn't capture positional nuance (two moves with same CPL may be different)
- Engine dependent (evaluation accuracy varies by depth)
- Doesn't account for psychological factors (time pressure, tournament stakes)

---

## 3. Unsupervised Learning: K-Means Clustering

### 3.1 Why Clustering?

**Problem**: Identifying individual mistakes is useful, but doesn't show patterns.

**Solution**: Cluster similar mistake positions to find **thematic weaknesses**.

Example:
- **Cluster 1**: "Weak king safety" (10 positions)
- **Cluster 2**: "Bad endgame technique" (8 positions)
- **Cluster 3**: "Tactical oversights" (15 positions)

This reveals **what types of positions** the player struggles in, not just that they struggled.

### 3.2 K-Means Algorithm Explained

**Overview**: K-Means partitions data points into K clusters by minimizing within-cluster variance.

**Algorithm**:

```
1. Initialize K random cluster centers
2. REPEAT:
   a. Assign each point to nearest center (Euclidean distance)
   b. Recalculate center as mean of cluster points
   c. If no point changes cluster → STOP
3. Result: K clusters of similar positions
```

**Mathematical Foundation**:

Objective function to minimize:
```
J = Σ_i Σ_j ||x_j - μ_i||²
where:
- x_j = position j
- μ_i = center of cluster i
- ||...||² = Euclidean distance squared
```

### 3.3 Feature Engineering for Chess

Before clustering, extract numerical features from positions:

```python
features = [
    material_balance,      # white material - black material
    piece_activity,        # number of legal moves (0-100)
    king_safety,          # distance from board center (0-100)
]
```

**Why these features?**
- **Material Balance**: Fundamental evaluation - having more pieces matters
- **Piece Activity**: More moves available = more options = less desperate position
- **King Safety**: King exposed to center = more vulnerable

**Standardization** (critical!):
```python
scaler = StandardScaler()
features_scaled = scaler.fit_transform(features)
```

Without scaling, features with larger ranges dominate distance calculation.

### 3.4 Determining Optimal K (Elbow Method)

**Problem**: How many clusters should we find?

**Solution**: Elbow method - plot variance explained vs K.

```python
inertias = []
for k in range(2, 7):
    kmeans = KMeans(n_clusters=k)
    kmeans.fit(features)
    inertias.append(kmeans.inertia_)  # Sum of squared distances

# Plot: K on x-axis, inertia on y-axis
# Find "elbow" where adding more K doesn't help much
```

**Intuition**: 
- K=1: One cluster, high inertia (all points together)
- K=n: Each point is own cluster, zero inertia
- Elbow: Sweet spot where adding clusters stops reducing inertia significantly

**For Chess Analyzer**: Typical K=4-6 weakness themes

### 3.5 Research Context

- [Machine Learning to Study Patterns in Chess Games](https://www.researchgate.net/publication/379334134_Machine_Learning_to_Study_Patterns_in_Chess_Games)
- [Clustering: Chess Openings Classifier](https://towardsdatascience.com/clustering-chess-openings-classifier-part-i-6299fbc9c291)

**Why K-Means?**
- Scalable (O(n) per iteration)
- Interpretable (cluster centers are real positions)
- Fast (converges in few iterations)
- Works well for weakness patterns

### 3.6 Implementation

```python
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Standardize
scaler = StandardScaler()
features_scaled = scaler.fit_transform(features)

# Cluster
kmeans = KMeans(n_clusters=4, random_state=42)
clusters = kmeans.fit_predict(features_scaled)

# Each mistake position now has a cluster label (0, 1, 2, 3)
# Cluster 0 = one weakness theme, Cluster 1 = another, etc.
```

**Advantages**:
- Automatic pattern discovery
- No labeled data needed
- Finds hidden structure in mistakes

**Limitations**:
- Assumes spherical clusters (not always true)
- Requires choosing K
- Sensitive to feature scaling
- May not handle outliers well

---

## 4. Feature Engineering

### 4.1 Position Representation

**Challenge**: Convert a chess position (FEN string) to numerical features for ML.

**Approach 1: Simple Features**

Extract domain-specific metrics:
- **Material balance**: Pawn=1, Knight=3, Bishop=3, Rook=5, Queen=9
- **Piece activity**: Count legal moves available
- **King safety**: King distance from center
- **Pawn structure**: Isolated/doubled pawns
- **Space advantage**: Controlled squares

**Approach 2: Board Encoding**

Convert position to matrix/vector:

```
FEN: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"

Convert to 8×8 matrix:
row 0: [-4, -2, -3, -9, -5, -3, -2, -4]  # Black pieces
row 1: [-1, -1, -1, -1, -1, -1, -1, -1]  # Black pawns
rows 2-5: [0, 0, 0, 0, 0, 0, 0, 0]       # Empty
row 6: [1, 1, 1, 1, 1, 1, 1, 1]          # White pawns
row 7: [4, 2, 3, 9, 5, 3, 2, 4]          # White pieces

Flatten to vector: [-4, -2, -3, ... (64 values)]
```

**Approach 3: Embeddings** (Future - Phase 2)

Learn position embeddings from data:
```
FEN → Encode → Neural Network → Low-dim Vector
                              (e.g., 16 dimensions)
```

Inspired by word2vec in NLP - positions with similar semantic meaning cluster together.

### 4.2 Why Feature Engineering Matters

Different feature sets reveal different patterns:

**Set A**: [Material, Activity, King Safety]
- Reveals: "Weak in certain position types"

**Set B**: [Opening, Rating Opponent, Time Control]
- Reveals: "Struggles against stronger players in classical"

**Set C**: [Phase, Move Number, Game Result]
- Reveals: "Blunders more in endgames"

**Chess Analyzer uses Set A** for foundational pattern detection.

### 4.3 Research Context

- [Chess2vec: Learning Vector Representations for Chess](https://arxiv.org/abs/2011.01014)
- [GitHub: chesspos - Embedding based chess position search](https://github.com/patrickfrank1/chesspos)

---

## 5. Player Behavior Modeling: Move Prediction

### 5.1 Problem Statement

**What**: Predict moves a player would make (not what the engine would play)

**Why**: Players have individual styles. Detecting deviations reveals unusual mistakes.

**Example**:
- Engine best move: Nf3 (score: +0.4)
- Player typically plays: Nc3 (score: +0.2)
- But player played: Nh3 (score: -0.8)

This is an **unusual mistake** - different from player's typical pattern.

### 5.2 Maia Chess: Learning Individual Behavior

**Landmark Research**: [Learning Models of Individual Behavior in Chess](https://www.cs.toronto.edu/~ashton/pubs/maia-individual-kdd2022.pdf)

**Key Insight**: Chess style is like a fingerprint - unique to each player.

**Maia-2 Model**:
- Unified neural network for all skill levels
- Fine-tune on individual player's games (just 20 games needed!)
- Predicts moves human would make at given rating
- Achieves 65% accuracy on out-of-distribution players

**Why It Works**:
- **Intermediate players predictable**: Intermediate players (1200-1600 Elo) have consistent patterns
- **Experts creative**: Grandmasters play more variably
- **Style fingerprinting**: 86% of 10-game sets matched to correct player when fine-tuned

### 5.3 Implementation Approach for Chess Analyzer

Simplified version suitable for MVP:

```python
# Training data
positions = [
    {'fen': position_fen_1, 'move': 'e2e4'},
    {'fen': position_fen_2, 'move': 'c2c4'},
    ...
]

# Neural network
model = Sequential([
    Dense(128, activation='relu', input_shape=(64,)),  # Encode FEN
    Dense(128, activation='relu'),
    Dense(num_legal_moves, activation='softmax')       # Probability per move
])

# Train on player's games
model.fit(X_train, y_train, epochs=10)

# Use: predict probable move in new position
predicted_move_distribution = model.predict(new_fen)
```

**What This Reveals**:
- "In position X, this player always moves rook to e1"
- "This move is unusual for this player" (suggests special circumstances)
- "Player's style is: aggressive queenside play"

### 5.4 Research References

- [Maia Chess: Learning Models of Individual Behavior](https://www.cs.toronto.edu/~ashton/pubs/maia-individual-kdd2022.pdf)
- [Aligning Superhuman AI with Human Behavior: Chess as a Model System](https://www.cs.toronto.edu/~ashton/pubs/maia-kdd2020.pdf)
- [Maia-2: A Unified Model for Human-AI Alignment](https://arxiv.org/html/2409.20553v1)

---

## 6. Anomaly Detection & Pattern Recognition

### 6.1 Repeated Mistakes

**Goal**: Find mistakes that happen over and over in similar positions.

**Approach 1: Isolation Forest**

Anomaly detection algorithm that identifies outliers:

```python
from sklearn.ensemble import IsolationForest

# Feature vectors for all mistakes
mistake_features = [[pos1_features], [pos2_features], ...]

# Fit model
iso_forest = IsolationForest(contamination=0.1)  # 10% are anomalies
outlier_labels = iso_forest.fit_predict(mistake_features)
# Output: -1 (anomaly), 1 (normal)
```

**How It Works**:
- Anomaly = requires many splits to isolate from tree
- Normal = few splits to isolate from tree
- Unsupervised (no labels needed)

**Application**:
- `label = 1`: Mistake fits player's typical pattern
- `label = -1`: Unusual mistake (different from player's style)

### 6.2 Repetition Detection

```python
# Find positions that appear multiple times with same mistake
for position in all_positions:
    similar_positions = find_similar(position, threshold=0.95)
    if len(similar_positions) >= 3:
        print(f"Repeated mistake in {len(similar_positions)} games")
        print(f"Position: {position.fen}")
        print(f"Move: {position.move} loses {position.eval_loss}cp")
```

**Why It Matters**:
- Shows systematic weakness: "Always play weak move in this setup"
- Actionable: "Study this specific line"
- Learning opportunity: "If I fix this, rating will jump"

### 6.3 Research References

- [Classification of Chess Games: Anomaly Detection](https://cornerstone.lib.mnsu.edu/etds/1119/)
- [Detecting Chess Cheating Using ML](https://www.ijceronline.com/papers/Vol15_issue2/15022837.pdf)

---

## 7. Position Similarity: Embeddings

### 7.1 Problem

**How similar are two chess positions?**

Example:
- Position A: Rook endgame, isolated pawns, weak king
- Position B: Similar rook endgame, same weakness type

Human recognizes similarity; algorithms need numbers.

### 7.2 FEN-Based Encoding

Simplest approach: Convert FEN to vector.

```python
def fen_to_vector(fen: str):
    """Convert FEN to 64-element vector."""
    piece_values = {'p': 1, 'n': 2, 'b': 3, 'r': 4, 'q': 5, 'k': 6}
    vector = []
    
    for char in fen.split()[0]:  # Board part only
        if char == '/':
            continue
        if char.isdigit():
            vector.extend([0] * int(char))
        else:
            value = piece_values.get(char.lower(), 0)
            if char.isupper():
                value *= -1  # White negative
            vector.append(value)
    
    return np.array(vector)

# Similarity
embedding_a = fen_to_vector(fen_a)
embedding_b = fen_to_vector(fen_b)
similarity = cosine_similarity(embedding_a, embedding_b)  # 0-1
```

### 7.3 Learned Embeddings (Advanced)

Neural network learns better embeddings:

```python
# Siamese network
embedding_a = encode_position(fen_a)  # NN → 16D vector
embedding_b = encode_position(fen_b)  # NN → 16D vector

# Loss: Similar positions → embeddings close, different → far
loss = triplet_loss(anchor, positive, negative)

# Result: Embeddings capture semantic similarity
```

**Why Learned Embeddings?**
- Capture chess concepts (not just piece positions)
- Similar weakness types cluster in embedding space
- Enables "find positions like this" queries

### 7.4 Use Cases

```python
# Find 5 past positions most similar to recent blunder
blunder_embedding = encode(recent_mistake_fen)
similarities = [cosine(blunder_embedding, encode(pos)) 
                for pos in past_positions]
top_5 = argsort(similarities)[-5:]

print("You've made similar mistakes in:")
for pos_idx in top_5:
    print(f"  Game {pos_idx}, move {positions[pos_idx].move_number}")
    print(f"  You played: {positions[pos_idx].move}")
    print(f"  Engine wanted: {positions[pos_idx].best_move}")
```

### 7.5 Research References

- [Chess2vec: Learning Vector Representations for Chess](https://arxiv.org/abs/2011.01014)
- [Word2Vec: Distributed Representations](https://arxiv.org/abs/1301.3781) (inspiration)

---

## 8. Classification: Game Outcome Prediction

### 8.1 Problem

**Predict game outcome** (win/loss/draw) from position features.

**Why?** Identifies which weaknesses actually lose games.

### 8.2 Classifier Algorithms

Research shows multiple classifiers work:

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier

# Training data
features = [[material, activity, king_safety, ...], ...]
outcomes = ['win', 'loss', 'draw', ...]

# Different classifiers
lr = LogisticRegression().fit(features, outcomes)
rf = RandomForestClassifier().fit(features, outcomes)
knn = KNeighborsClassifier().fit(features, outcomes)

# Histogram Gradient Boosting best: 83% accuracy
hgb = HistGradientBoostingClassifier()
hgb.fit(features, outcomes)
accuracy = hgb.score(X_test, y_test)  # ~83%
```

### 8.3 Research Reference

- [Machine Learning Approaches for Classifying Chess Game Outcomes](https://www.mdpi.com/2079-9282/15/1/1)

Study compared 4 classifiers on chess game classification:
- Multinomial Logistic Regression: 80%
- Random Forest: 81%
- KNN: 79%
- **Histogram Gradient Boosting: 83%** ← Best

---

## 9. Practical Implementation Pipeline

### 9.1 Full Analysis Pipeline

```
1. FETCH GAMES
   chess.com API → PGN files

2. PARSE POSITIONS
   PGN Parser → Extract moves, FENs

3. EVALUATE POSITIONS
   Stockfish → Evaluation scores

4. CALCULATE CPL
   eval_before vs eval_after → Centipawn loss

5. FEATURE EXTRACTION
   FEN → material, activity, king_safety

6. MISTAKE DETECTION
   CPL > 50 → Flag as mistake

7. CLUSTERING
   K-Means on mistake positions → Weakness themes

8. PATTERN ANALYSIS
   Group by cluster → Generate labels

9. SIMILARITY MATCHING
   Position embeddings → Find similar positions

10. GENERATE RECOMMENDATIONS
    Most impactful mistakes → Study plan
```

### 9.2 Scalability Considerations

| Step | Complexity | Dataset Size |
|------|-----------|--------------|
| Game Fetch | O(n games) | 50-200 games |
| PGN Parse | O(n × m) | 50-500 moves/game |
| Evaluation | O(n × m) | Heavy - Stockfish |
| Feature Extract | O(n × m) | Fast - vectorized |
| Clustering | O(n) | K-Means is efficient |
| Pattern Analysis | O(k) | k clusters |

**Bottleneck**: Stockfish evaluation (50-200 games × 30-50 moves × 1-2 sec/position)

**Solution Phase 2**: 
- Batch evaluation
- Lower depth (faster, less accurate)
- Caching results

---

## 10. Advantages & Limitations

### 10.1 What Works Well

| Technique | Why It Works | Use Case |
|-----------|------------|----------|
| **CPL** | Correlated with strength | Identifying worst moves |
| **K-Means** | Unsupervised, interpretable | Finding weakness themes |
| **Feature Extraction** | Domain knowledge encoded | Combining metrics |
| **Similarity Matching** | Finds patterns | "You've done this before" |
| **Anomaly Detection** | Finds unusual behavior | Detects systematic issues |

### 10.2 Limitations

| Technique | Limitation | Workaround |
|-----------|-----------|-----------|
| **CPL** | Engine dependent | Use consistent depth |
| **K-Means** | Spherical clusters | Try other algorithms (DBSCAN, Hierarchical) |
| **Features** | Limited scope | Add more features (phase, time control, etc.) |
| **Similarity** | Simple encoding | Use learned embeddings (Phase 2) |
| **Prediction** | Limited data | Start with 20+ games |

---

## 11. Extensions & Future Work (Phase 2+)

### 11.1 Advanced Techniques

**Move Prediction (Maia-Inspired)**
- Fine-tune transformer model on player's games
- Detect unusual move choices
- Identify playing style

**Deep Learning**
- CNN for position representation
- LSTM for game progression analysis
- Attention mechanisms for move importance

**Causal Analysis**
- What mistakes lead to losses?
- Which weaknesses hurt rating most?
- Opportunity cost of blunders

### 11.2 Data Augmentation

**Synthetic Positions**
- Generate similar positions via perturbation
- Increase training data without fetching

**Transfer Learning**
- Train on large chess databases first
- Fine-tune on individual player

---

## 12. Summary & Recommendations

### 12.1 For This Project (Phase 1)

**Best Techniques** (implemented):
1. ✅ **Centipawn Loss** - Simple, effective, well-understood
2. ✅ **K-Means Clustering** - Finds weakness themes automatically
3. ✅ **Feature Engineering** - Captures key position aspects
4. ✅ **Similarity Matching** - Links similar mistakes

**Why These?**
- Mathematically sound
- Computationally efficient
- Interpretable results
- Actionable insights

### 12.2 For Phase 2+

**Recommended Additions**:
1. **Move Prediction** (Maia-inspired) - Understand playing style
2. **Anomaly Detection** (Isolation Forest) - Find unusual blunders
3. **Position Embeddings** - Better similarity matching
4. **Time Series Analysis** - Improvement tracking

---

## 13. References

### Academic Papers

1. [Machine Learning Approaches for Classifying Chess Game Outcomes](https://www.mdpi.com/2079-9282/15/1/1)
2. [Learning Models of Individual Behavior in Chess](https://www.cs.toronto.edu/~ashton/pubs/maia-individual-kdd2022.pdf)
3. [Aligning Superhuman AI with Human Behavior: Chess as a Model System](https://www.cs.toronto.edu/~ashton/pubs/maia-kdd2020.pdf)
4. [Maia-2: A Unified Model for Human-AI Alignment in Chess](https://arxiv.org/html/2409.20553v1)
5. [Chess2vec: Learning Vector Representations for Chess](https://arxiv.org/abs/2011.01014)
6. [Expected Human Performance Behavior in Chess Using Centipawn Loss Analysis](https://link.springer.com/chapter/10.1007/978-3-031-35979-8_19)
7. [Classification of Chess Games: An Exploration of Classifiers for Anomaly Detection in Chess](https://cornerstone.lib.mnsu.edu/etds/1119/)
8. [Detecting Chess Cheating Thanks To ML & ANN Technology](https://www.ijceronline.com/papers/Vol15_issue2/15022837.pdf)

### Books & Resources

- Stockfish Documentation: https://stockfishchess.org/
- scikit-learn Clustering: https://scikit-learn.org/stable/modules/clustering.html
- python-chess Documentation: https://python-chess.readthedocs.io/

### Datasets

- Lichess Database: https://database.lichess.org/
- Chess.com Games API: https://www.chess.com/news/view/published-data-api

---

## 14. Conclusion

Machine learning for chess weakness detection is **practical and effective**:

1. **Centipawn Loss** quantifies move quality objectively
2. **K-Means Clustering** discovers weakness themes automatically
3. **Feature Engineering** captures position characteristics
4. **Similarity Matching** links repeated mistakes
5. **Player Behavior Models** understand individual styles

These techniques, combined with chess domain knowledge, create a powerful system for helping players identify and fix specific weaknesses.

The Chess Analyzer implements these principles in a production-ready, full-stack application that demonstrates both ML fundamentals and practical software engineering.

---

**Document Version**: 1.0  
**Created**: April 12, 2026  
**Status**: Complete for Phase 1
