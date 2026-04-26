from src.chess_analyzer.feature_extractor import FeatureExtractor


def test_extract_material_balance():
    """Test material count extraction."""
    extractor = FeatureExtractor()
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    material = extractor.extract_material_balance(fen)
    assert material == 0.0


def test_extract_material_balance_endgame():
    """Test material count in endgame."""
    extractor = FeatureExtractor()
    fen = "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1"
    material = extractor.extract_material_balance(fen)
    assert material > 0


def test_extract_all_features():
    """Test that extract_all_features returns expected fields."""
    extractor = FeatureExtractor()
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    features = extractor.extract_all_features(fen)

    assert 'material_balance' in features
    assert 'piece_activity' in features
    assert 'king_safety' in features
    assert isinstance(features['material_balance'], (int, float))
