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

    def extract_features(self, positions: list[Position]) -> np.ndarray:
        """
        Extract features for anomaly detection: [CPL, material_loss, king_exposure, eval_drop]

        Args:
            positions: List of Position objects

        Returns:
            Feature matrix (n_positions x 4)
        """
        features = []

        for position in positions:
            # Feature 1: Centipawn loss (evaluation_loss from database)
            cpl = getattr(position, 'evaluation_loss', 0.0) or 0.0

            # Feature 2: Evaluation drop (absolute difference between before and after)
            eval_before = getattr(position, 'evaluation_before', 0.0) or 0.0
            eval_after = getattr(position, 'evaluation_after', 0.0) or 0.0
            eval_drop = abs(eval_before - eval_after)

            # Feature 3: King exposure proxy (use evaluation_loss as a proxy)
            king_exposure = max(0.0, min(1.0, cpl / 300.0))

            # Feature 4: Raw evaluation loss magnitude
            loss_magnitude = abs(cpl)

            feature_vector = [cpl, eval_drop, king_exposure, loss_magnitude]
            features.append(feature_vector)

        if not features:
            return np.array([]).reshape(0, 4)

        return np.array(features)

    def fit(self, positions: list[Position]) -> None:
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

        # Check if scaler was fitted (it won't be if fit was called with empty positions)
        if not hasattr(self.scaler, 'mean_'):
            return 0.0

        scaled = self.scaler.transform(features)
        score = self.model.score_samples(scaled)[0]

        # Normalize: Isolation Forest returns negative scores for anomalies
        # score_samples returns values < 0 for anomalies, > 0 for normal
        # We want 0-1 where 1 = most anomalous
        normalized = (1.0 - score) / 2.0
        return float(np.clip(normalized, 0.0, 1.0))

    def get_anomalies(self, positions: list[Position], threshold: float = 0.7) -> list[dict]:
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
                cpl = getattr(position, 'evaluation_loss', 0.0) or 0.0

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
