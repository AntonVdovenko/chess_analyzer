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
        """Extract ~20 features per position for embedding"""
        features = []

        for position in positions:
            material = getattr(position, 'material_balance', 0.0) or 0.0
            activity = getattr(position, 'piece_activity', 0.0) or 0.0
            king_safety = getattr(position, 'king_safety', 0.5) or 0.5
            evaluation = getattr(position, 'evaluation', 0.0) or 0.0
            cpl = getattr(position, 'centipawn_loss', 0.0) or 0.0

            features_vector = [
                material, activity, king_safety, evaluation, cpl,
                abs(material), activity * king_safety, evaluation * king_safety,
                cpl / max(1, abs(evaluation)), king_safety ** 2,
                activity ** 2, max(0, evaluation), min(0, evaluation),
                cpl * king_safety, material * activity, (1 - king_safety),
                activity / max(1, king_safety), abs(material - activity),
                cpl ** 2, evaluation / max(1, cpl),
            ]
            features.append(features_vector)

        if not features:
            return np.array([]).reshape(0, 20)

        return np.array(features)

    def fit(self, positions: List[Position]) -> None:
        """Learn embedding space from positions"""
        if not positions:
            self.is_fitted = True
            return

        features = self.extract_features(positions)

        if features.size == 0:
            self.is_fitted = True
            return

        scaled = self.scaler.fit_transform(features)
        self.pca.fit(scaled)
        self.is_fitted = True

    def embed(self, position: Position) -> np.ndarray:
        """Convert position to embedding vector"""
        if not self.is_fitted:
            return np.zeros(self.n_components)

        features = self.extract_features([position])

        if features.size == 0:
            return np.zeros(self.n_components)

        scaled = self.scaler.transform(features)
        embedding = self.pca.transform(scaled)[0]

        return embedding

    def find_similar(self, embedding: np.ndarray, all_embeddings: np.ndarray, k: int = 5) -> List[int]:
        """Find k most similar embeddings by cosine distance"""
        if len(all_embeddings) == 0:
            return []

        distances = cosine_distances([embedding], all_embeddings)[0]
        return np.argsort(distances)[:k].tolist()

    def get_similarity_score(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Get cosine similarity between two embeddings"""
        distance = cosine_distances([embedding1], [embedding2])[0][0]
        similarity = 1.0 - distance
        return float(np.clip(similarity, 0.0, 1.0))
