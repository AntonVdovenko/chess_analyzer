import numpy as np

from chess_analyzer.ml_models.clustering import WeaknessClustering


def test_kmeans_clustering():
    """Test K-Means clustering on mistake positions."""
    clusterer = WeaknessClustering()
    features = np.array(
        [
            [1.0, 2.0, 3.0],
            [1.1, 2.1, 3.1],
            [10.0, 20.0, 30.0],
        ]
    )
    clusters = clusterer.cluster_positions(features, n_clusters=2)

    assert len(clusters) == 3
    assert 0 in clusters
    assert 1 in clusters


def test_elbow_method():
    """Test elbow method for finding optimal K."""
    clusterer = WeaknessClustering()
    features = np.vstack(
        [
            np.random.randn(20, 2) + [0, 0],
            np.random.randn(20, 2) + [10, 10],
            np.random.randn(20, 2) + [20, 0],
        ]
    )
    optimal_k = clusterer.find_optimal_k(features, k_range=range(2, 6))
    assert 2 <= optimal_k <= 4
