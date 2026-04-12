import pytest
import numpy as np
from unittest.mock import Mock
from src.chess_analyzer.ml_models.anomaly_detector import AnomalyDetector


def test_anomaly_detector_init():
    """Test AnomalyDetector initializes correctly"""
    detector = AnomalyDetector(contamination=0.1)
    assert detector.contamination == 0.1
    assert detector.model is not None
    assert detector.scaler is not None
    assert detector.is_fitted is False


def test_anomaly_detector_fit_predict():
    """Test fit and predict methods"""
    # Create mock positions
    positions = []
    for i in range(20):
        pos = Mock()
        pos.fen = f"fen_string_{i}"
        pos.evaluation_loss = 50.0 + (i * 2)  # Increasing evaluation loss
        pos.evaluation_before = -1.0
        pos.evaluation_after = -0.5
        positions.append(pos)

    detector = AnomalyDetector(contamination=0.1)
    detector.fit(positions)

    assert detector.is_fitted is True

    # Test prediction on normal position
    normal_pos = Mock()
    normal_pos.fen = "normal_fen"
    normal_pos.evaluation_loss = 60.0
    normal_pos.evaluation_before = -1.0
    normal_pos.evaluation_after = -0.5

    score = detector.predict(normal_pos)
    assert 0.0 <= score <= 1.0


def test_anomaly_detector_empty_positions():
    """Test with empty positions"""
    detector = AnomalyDetector()
    detector.fit([])
    assert detector.is_fitted is True

    pos = Mock()
    pos.fen = "test_fen"
    pos.evaluation_loss = 100.0
    pos.evaluation_before = -1.0
    pos.evaluation_after = -0.5

    score = detector.predict(pos)
    assert score == 0.0


def test_anomaly_detector_get_anomalies():
    """Test anomaly detection with threshold"""
    # Create positions with varying evaluation loss
    positions = []
    for i in range(15):
        pos = Mock()
        pos.fen = f"fen_{i}"
        pos.evaluation_loss = 100.0 if i < 12 else 400.0  # Last 3 are high loss
        pos.evaluation_before = -1.0
        pos.evaluation_after = -0.5
        positions.append(pos)

    detector = AnomalyDetector(contamination=0.2)
    detector.fit(positions)

    # Get anomalies
    anomalies = detector.get_anomalies(positions, threshold=0.5)

    # Should detect some anomalies (at least some of the high-loss positions)
    assert len(anomalies) > 0
    assert all('anomaly_score' in a for a in anomalies)
    assert all('centipawn_loss' in a for a in anomalies)
    assert all('reason' in a for a in anomalies)
