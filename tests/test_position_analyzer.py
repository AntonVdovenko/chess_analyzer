"""Tests for Stockfish position analyzer."""

from unittest.mock import Mock, patch

import chess
import chess.engine
import pytest

from chess_analyzer.position_analyzer import PositionAnalyzer


@pytest.fixture
def analyzer_with_mock_engine():
    """Create analyzer with mocked engine."""
    with patch("chess_analyzer.position_analyzer.chess.engine.SimpleEngine.popen_uci"):
        analyzer = PositionAnalyzer(stockfish_path="/mock/stockfish")
        analyzer.engine = Mock()
        yield analyzer


def test_calculate_centipawn_loss(analyzer_with_mock_engine):
    """Test centipawn loss calculation."""
    analyzer = analyzer_with_mock_engine
    loss = analyzer.calculate_centipawn_loss(eval_before=0.3, eval_after=-0.8)
    assert loss == pytest.approx(110.0)


def test_calculate_centipawn_loss_zero(analyzer_with_mock_engine):
    """Test that perfect move has zero loss."""
    analyzer = analyzer_with_mock_engine
    loss = analyzer.calculate_centipawn_loss(eval_before=0.5, eval_after=0.5)
    assert loss == 0.0


def test_calculate_centipawn_loss_ignores_improvements(analyzer_with_mock_engine):
    """Test that improving moves have no centipawn loss."""
    analyzer = analyzer_with_mock_engine
    loss = analyzer.calculate_centipawn_loss(eval_before=0.0, eval_after=1.5)
    assert loss == 0.0


def test_analyze_position_returns_best_move(analyzer_with_mock_engine):
    """Test that analyze_position returns engine's best move."""
    analyzer = analyzer_with_mock_engine
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    # Mock the engine response
    mock_move = Mock()
    mock_move.uci.return_value = "e2e4"
    mock_score = Mock()
    mock_score.is_mate.return_value = False
    mock_score.cp = 50

    analyzer.engine.analyse.return_value = {
        "pv": [mock_move],
        "score": mock_score,
        "depth": 20,
    }

    result = analyzer.analyze_position(fen, depth=10)

    assert "best_move" in result
    assert "evaluation" in result
    assert isinstance(result["best_move"], str) or result["best_move"] is None
    assert isinstance(result["evaluation"], float)
    assert result["best_move"] == "e2e4"
    assert result["evaluation"] == 0.5


def test_analyze_position_uses_requested_evaluation_perspective(analyzer_with_mock_engine):
    """Test that PovScore values are converted from the requested side's perspective."""
    analyzer = analyzer_with_mock_engine
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    analyzer.engine.analyse.return_value = {
        "pv": [],
        "score": chess.engine.PovScore(chess.engine.Cp(50), chess.BLACK),
        "depth": 20,
    }

    white_result = analyzer.analyze_position(fen, depth=10, perspective="white")
    black_result = analyzer.analyze_position(fen, depth=10, perspective="black")

    assert white_result["evaluation"] == -0.5
    assert black_result["evaluation"] == 0.5


def test_get_acpl(analyzer_with_mock_engine):
    """Test ACPL calculation."""
    analyzer = analyzer_with_mock_engine
    positions = [
        {"eval_before": 0.0, "eval_after": 0.0},
        {"eval_before": 0.5, "eval_after": 0.2},
        {"eval_before": 1.0, "eval_after": 0.0},
    ]
    acpl = analyzer.get_acpl(positions)
    expected_acpl = (0.0 + 30.0 + 100.0) / 3
    assert acpl == pytest.approx(expected_acpl, rel=0.01)


def test_get_acpl_empty(analyzer_with_mock_engine):
    """Test ACPL calculation with empty positions."""
    analyzer = analyzer_with_mock_engine
    positions = []
    acpl = analyzer.get_acpl(positions)
    assert acpl == 0.0


def test_evaluation_to_float_centipawns(analyzer_with_mock_engine):
    """Test conversion of centipawns to pawns."""
    analyzer = analyzer_with_mock_engine
    mock_score = Mock()
    mock_score.is_mate.return_value = False
    mock_score.cp = 150

    result = analyzer._evaluation_to_float(mock_score)
    assert result == 1.5


def test_evaluation_to_float_mate(analyzer_with_mock_engine):
    """Test conversion of mate score."""
    analyzer = analyzer_with_mock_engine
    mock_score = Mock()
    mock_score.is_mate.return_value = True
    mock_score.mate.return_value = 3

    result = analyzer._evaluation_to_float(mock_score)
    assert result == 10000.0


def test_evaluation_to_float_mate_against(analyzer_with_mock_engine):
    """Test conversion of mate against score."""
    analyzer = analyzer_with_mock_engine
    mock_score = Mock()
    mock_score.is_mate.return_value = True
    mock_score.mate.return_value = -2

    result = analyzer._evaluation_to_float(mock_score)
    assert result == -10000.0


def test_evaluation_to_float_none(analyzer_with_mock_engine):
    """Test conversion of None score."""
    analyzer = analyzer_with_mock_engine
    result = analyzer._evaluation_to_float(None)
    assert result == 0.0


def test_close(analyzer_with_mock_engine):
    """Test engine close."""
    analyzer = analyzer_with_mock_engine
    analyzer.close()
    analyzer.engine.quit.assert_called_once()


def test_context_manager(analyzer_with_mock_engine):
    """Test context manager usage."""
    analyzer = analyzer_with_mock_engine
    with analyzer:
        pass
    analyzer.engine.quit.assert_called_once()
