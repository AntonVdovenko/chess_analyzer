from unittest.mock import Mock

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


def test_move_predictor_fit_with_games():
    """Test fit learns move patterns correctly"""
    # Create mock game with positions (need at least 5 to meet min_position_frequency)
    positions = []
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    # Add 3 e2e4 moves and 2 d2d4 moves
    for _ in range(3):
        pos = Mock()
        pos.fen = fen
        pos.player_move = "e2e4"
        positions.append(pos)

    for _ in range(2):
        pos = Mock()
        pos.fen = fen
        pos.player_move = "d2d4"
        positions.append(pos)

    game = Mock()
    game.positions = positions

    predictor = MovePredictor()
    predictor.fit([game])

    # Should have learned the position (total 5 moves >= min_position_frequency)
    assert fen in predictor.move_distributions
    assert predictor.move_distributions[fen]["e2e4"] == 3
    assert predictor.move_distributions[fen]["d2d4"] == 2

    # Test prediction
    assert predictor.predict(fen, "e2e4") == 0.6
    assert predictor.predict(fen, "d2d4") == 0.4
    assert predictor.predict(fen, "a2a3") == 0.0


def test_move_predictor_unusual_moves():
    """Test unusual move detection"""
    # Create training data with many e2e4 moves and few h2h4 moves
    position_configs = []
    for i in range(9):
        pos = Mock()
        pos.fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        pos.player_move = "e2e4"
        position_configs.append(pos)

    # Add one unusual move
    position_h = Mock()
    position_h.fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    position_h.player_move = "h2h4"
    position_configs.append(position_h)

    training_game = Mock()
    training_game.positions = position_configs

    predictor = MovePredictor()
    predictor.fit([training_game])

    # Test game with the unusual move
    test_position = Mock()
    test_position.fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    test_position.player_move = "h2h4"

    test_game = Mock()
    test_game.positions = [test_position]

    unusual = predictor.get_unusual_moves(test_game, threshold=0.2)
    assert len(unusual) == 1
    assert unusual[0]["move"] == "h2h4"
    assert unusual[0]["probability"] == 0.1  # 1 out of 10 moves is h2h4
