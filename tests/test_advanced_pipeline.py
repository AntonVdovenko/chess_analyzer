from unittest.mock import Mock

from chess_analyzer.advanced_analysis_pipeline import AdvancedAnalysisPipeline


def test_advanced_pipeline_init():
    """Test AdvancedAnalysisPipeline initializes correctly"""
    mock_session = Mock()
    pipeline = AdvancedAnalysisPipeline(mock_session)

    assert pipeline.session is mock_session
    assert pipeline.move_predictor is not None
    assert pipeline.anomaly_detector is not None
    assert pipeline.embedder is not None


def test_advanced_pipeline_analyze_empty_games():
    """Test analyze_player with no games"""
    mock_session = Mock()
    mock_session.query.return_value.filter.return_value.all.return_value = []

    pipeline = AdvancedAnalysisPipeline(mock_session)
    result = pipeline.analyze_player("nonexistent_user")

    assert result["status"] == "error"
    assert "No games found" in result["message"]
