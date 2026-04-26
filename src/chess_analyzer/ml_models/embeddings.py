"""Position embedding utilities."""

from __future__ import annotations

import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from src.chess_analyzer.feature_extractor import FeatureExtractor


class PositionEmbedder:
    """Convert positions to semantic vectors for similarity matching."""

    def __init__(self, n_components: int = 16):
        """Initialize the embedder."""
        self.n_components = n_components
        self.pca = PCA(n_components=n_components, random_state=42)
        self.scaler = StandardScaler()
        self.feature_extractor = FeatureExtractor()
        self.is_fitted = False
        self._effective_components = n_components
        self._constant_space = False

    def extract_features(self, positions: list[object]) -> np.ndarray:
        """Extract a stable numeric feature vector for each position."""
        features: list[list[float]] = []

        for position in positions:
            fen = getattr(position, "fen", None)
            derived_features = {
                "material_balance": 0.0,
                "piece_activity": 0.0,
                "king_safety": 0.5,
            }
            if fen:
                try:
                    derived_features = self.feature_extractor.extract_all_features(fen)
                except ValueError:
                    pass
            material = self._get_attr(
                position,
                "material_balance",
                derived_features["material_balance"],
            )
            activity = self._get_attr(
                position,
                "piece_activity",
                derived_features["piece_activity"],
            )
            king_safety = self._get_attr(
                position,
                "king_safety",
                derived_features["king_safety"],
            )
            evaluation_before = self._get_attr(position, "evaluation_before", 0.0)
            evaluation_after = self._get_attr(
                position,
                "evaluation",
                self._get_attr(position, "evaluation_after", 0.0),
            )
            cpl = self._get_attr(
                position,
                "centipawn_loss",
                self._get_attr(position, "evaluation_loss", 0.0),
            )

            feature_vector = [
                material,
                activity,
                king_safety,
                evaluation_before,
                evaluation_after,
                cpl,
                evaluation_after - evaluation_before,
                abs(material),
                activity * king_safety,
                cpl / max(1.0, abs(evaluation_after) * 100.0),
                king_safety**2,
                activity**2,
                max(0.0, evaluation_after),
                min(0.0, evaluation_after),
                material * activity,
                abs(material - activity),
                cpl * king_safety,
                float(self._get_flag(position, "is_opening")),
                float(self._get_flag(position, "is_middlegame")),
                float(self._get_flag(position, "is_endgame")),
            ]
            features.append(feature_vector)

        if not features:
            return np.array([]).reshape(0, 20)

        return np.array(features, dtype=float)

    def fit(self, positions: list[object]) -> None:
        """Learn an embedding space from historic positions."""
        if not positions:
            self.is_fitted = True
            return

        features = self.extract_features(positions)
        if features.size == 0:
            self.is_fitted = True
            return

        scaled = self.scaler.fit_transform(features)
        if np.allclose(scaled, scaled[0]):
            self._constant_space = True
            self._effective_components = 0
            self.is_fitted = True
            return

        self._effective_components = min(
            self.n_components,
            scaled.shape[0],
            scaled.shape[1],
        )
        self.pca = PCA(n_components=self._effective_components, random_state=42)
        self.pca.fit(scaled)
        self._constant_space = False
        self.is_fitted = True

    def embed(self, position: object) -> np.ndarray:
        """Convert a position to a fixed-width embedding vector."""
        if not self.is_fitted:
            return np.zeros(self.n_components)

        if self._constant_space:
            return np.zeros(self.n_components)

        features = self.extract_features([position])
        if features.size == 0:
            return np.zeros(self.n_components)

        scaled = self.scaler.transform(features)
        embedding = self.pca.transform(scaled)[0]
        if len(embedding) == self.n_components:
            return embedding

        padded = np.zeros(self.n_components)
        padded[: len(embedding)] = embedding
        return padded

    def find_similar(
        self,
        embedding: np.ndarray,
        all_embeddings: np.ndarray,
        k: int = 5,
    ) -> list[int]:
        """Find the indices of the k most similar embeddings."""
        if len(all_embeddings) == 0:
            return []

        similarities = np.array(
            [
                self.get_similarity_score(embedding, candidate)
                for candidate in all_embeddings
            ]
        )
        sorted_indices = np.argsort(-similarities, kind="stable")
        return sorted_indices[:k].tolist()

    def get_similarity_score(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray,
    ) -> float:
        """Get a cosine similarity score in the range [0, 1]."""
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        if norm1 == 0.0 and norm2 == 0.0:
            return 1.0
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0

        similarity = float(np.dot(embedding1, embedding2) / (norm1 * norm2))
        return float(np.clip(similarity, 0.0, 1.0))

    @staticmethod
    def _get_attr(position: object, attribute: str, default: float) -> float:
        """Read a numeric attribute from a position-like object."""
        if hasattr(position, "__dict__") and attribute in position.__dict__:
            value = position.__dict__[attribute]
        else:
            value = getattr(position, attribute, default)
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _get_flag(position: object, attribute: str) -> bool:
        """Read a boolean-like attribute from a position-like object."""
        if hasattr(position, "__dict__") and attribute in position.__dict__:
            value = position.__dict__[attribute]
        else:
            value = getattr(position, attribute, False)
        if isinstance(value, bool):
            return value
        return False
