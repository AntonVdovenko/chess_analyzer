import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


class WeaknessClustering:
    """Cluster positions into weakness themes using K-Means."""

    def cluster_positions(self, features: np.ndarray, n_clusters: int = 4) -> list[int]:
        """Cluster positions using K-Means."""
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(features_scaled)

        return clusters.tolist()

    def find_optimal_k(self, features: np.ndarray, k_range: range = range(2, 7)) -> int:
        """Find optimal number of clusters using elbow method."""
        candidate_ks = [k for k in k_range if 1 < k <= len(features)]
        if not candidate_ks:
            return 1
        if len(candidate_ks) <= 2:
            return candidate_ks[0]

        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)

        inertias = []

        for k in candidate_ks:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(features_scaled)
            inertias.append(kmeans.inertia_)

        diffs = np.diff(inertias)
        if len(diffs) < 2:
            return candidate_ks[0]

        elbow_idx = np.argmin(np.diff(diffs)) + 1

        optimal_k = candidate_ks[elbow_idx]
        return optimal_k

    def label_clusters(
        self,
        clusters: list[int],
        position_features: list[dict],
    ) -> dict[int, dict]:
        """Generate human-readable labels for clusters."""
        cluster_info = {}

        for cluster_id in set(clusters):
            cluster_positions = [
                position_features[i] for i, c in enumerate(clusters) if c == cluster_id
            ]

            avg_material = np.mean([p.get("material_balance", 0) for p in cluster_positions])
            avg_king_safety = np.mean([p.get("king_safety", 50) for p in cluster_positions])

            label = self._generate_label(avg_material, avg_king_safety)

            cluster_info[cluster_id] = {
                "label": label,
                "size": len(cluster_positions),
                "avg_material": float(avg_material),
                "avg_king_safety": float(avg_king_safety),
            }

        return cluster_info

    def _generate_label(self, avg_material: float, avg_king_safety: float) -> str:
        """Generate human-readable label for a cluster."""
        if avg_king_safety < 40:
            return "Weak king safety"
        if avg_material < -2:
            return "Material disadvantage"
        if avg_material > 2:
            return "Material advantage"
        return "Tactical positions"
