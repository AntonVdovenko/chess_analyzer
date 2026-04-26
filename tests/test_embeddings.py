from unittest.mock import Mock

import numpy as np

from src.chess_analyzer.ml_models.embeddings import PositionEmbedder


def test_position_embedder_init():
    """Test PositionEmbedder initializes correctly"""
    embedder = PositionEmbedder(n_components=16)
    assert embedder.n_components == 16
    assert embedder.pca is not None
    assert embedder.scaler is not None
    assert embedder.is_fitted is False


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
    assert embedder.is_fitted is True

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

    embedding = embedder.embed(positions[0])
    all_embeddings = np.array([embedder.embed(p) for p in positions])
    similar_indices = embedder.find_similar(embedding, all_embeddings, k=5)

    assert len(similar_indices) == 5
    assert 0 in similar_indices


def test_position_embedder_similarity_score():
    """Test similarity score calculation"""
    embedder = PositionEmbedder()
    emb1 = np.array([1.0, 0.0, 0.0])
    emb2 = np.array([1.0, 0.0, 0.0])
    similarity = embedder.get_similarity_score(emb1, emb2)
    assert similarity > 0.99
