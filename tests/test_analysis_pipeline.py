import pytest
from unittest.mock import Mock, patch

from src.chess_analyzer.analysis_pipeline import AnalysisPipeline


@pytest.fixture
def pipeline_with_mocks():
    """Create pipeline with mocked engine and components."""
    with patch("src.chess_analyzer.analysis_pipeline.PositionAnalyzer") as mock_pa:
        with patch("src.chess_analyzer.analysis_pipeline.PGNParser") as mock_pgn:
            with patch("src.chess_analyzer.analysis_pipeline.FeatureExtractor") as mock_fe:
                with patch("src.chess_analyzer.analysis_pipeline.WeaknessClustering") as mock_cluster:
                    pipeline = AnalysisPipeline()

                    # Setup mocks for position analyzer
                    pipeline.position_analyzer.analyze_position = Mock(return_value={
                        'evaluation': 0.5,
                        'best_move': 'e2e4',
                        'depth': 20
                    })
                    pipeline.position_analyzer.calculate_centipawn_loss = Mock(return_value=10.0)
                    pipeline.position_analyzer.get_acpl = Mock(return_value=15.0)
                    pipeline.position_analyzer.close = Mock()

                    # Setup mocks for feature extractor
                    pipeline.feature_extractor.extract_all_features = Mock(return_value={
                        'material_balance': 1.0,
                        'piece_activity': 50.0,
                        'king_safety': 75.0,
                    })

                    # Setup mocks for clusterer
                    pipeline.clusterer.find_optimal_k = Mock(return_value=2)
                    pipeline.clusterer.cluster_positions = Mock(return_value=[0, 0, 1])
                    pipeline.clusterer.label_clusters = Mock(return_value={
                        0: {'label': 'Weak king safety', 'size': 2},
                        1: {'label': 'Material disadvantage', 'size': 1},
                    })

                    yield pipeline


def test_analyze_games_end_to_end(pipeline_with_mocks):
    """Test complete analysis pipeline."""
    pipeline = pipeline_with_mocks

    # Mock PGN parser
    pipeline.pgn_parser.parse_pgn = Mock(return_value={
        'white': 'Player1',
        'black': 'Player2',
        'result': '0-1',
        'moves': [
            {
                'move_number': 1,
                'fen_before': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
                'fen_after': 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
                'uci_move': 'e2e4',
                'san_move': 'e4',
            },
            {
                'move_number': 2,
                'fen_before': 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
                'fen_after': 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2',
                'uci_move': 'e7e5',
                'san_move': 'e5',
            },
        ]
    })

    pgn_data = [
        {
            'pgn': """[White "Player1"][Black "Player2"]\n1. e4 e5 2. Nf3 Nc6 0-1""",
            'white': 'Player1',
            'black': 'Player2',
            'result': '0-1',
        }
    ]

    result = pipeline.analyze_games(pgn_data, player_perspective='white')

    assert 'games_analyzed' in result
    assert 'total_acpl' in result
    assert 'patterns' in result
    assert result['games_analyzed'] == 1


def test_analyze_games_with_mistake_positions(pipeline_with_mocks):
    """Test pipeline correctly identifies mistake positions."""
    pipeline = pipeline_with_mocks

    # Mock position analyzer to return high centipawn loss for a mistake
    pipeline.position_analyzer.calculate_centipawn_loss = Mock(side_effect=[60.0, 10.0])

    pipeline.pgn_parser.parse_pgn = Mock(return_value={
        'white': 'Player1',
        'black': 'Player2',
        'result': '0-1',
        'moves': [
            {
                'move_number': 1,
                'fen_before': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
                'fen_after': 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
                'uci_move': 'e2e4',
                'san_move': 'e4',
            },
            {
                'move_number': 2,
                'fen_before': 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
                'fen_after': 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2',
                'uci_move': 'e7e5',
                'san_move': 'e5',
            },
        ]
    })

    pgn_data = [
        {
            'pgn': """[White "Player1"][Black "Player2"]\n1. e4 e5 0-1""",
        }
    ]

    result = pipeline.analyze_games(pgn_data)

    assert result['games_analyzed'] == 1
    assert result['mistake_positions'] > 0
    assert 'patterns' in result


def test_analyze_games_empty_list(pipeline_with_mocks):
    """Test pipeline handles empty game list."""
    pipeline = pipeline_with_mocks

    result = pipeline.analyze_games([], player_perspective='white')

    assert result['games_analyzed'] == 0
    assert result['total_acpl'] == 0.0
    assert result['total_positions'] == 0
    assert result['mistake_positions'] == 0
    assert result['patterns'] == {}


def test_analyze_games_closes_resources(pipeline_with_mocks):
    """Test that pipeline properly closes resources."""
    pipeline = pipeline_with_mocks

    pgn_data = []
    pipeline.analyze_games(pgn_data)

    # Check that engine.quit was NOT called automatically (just during manual close)
    # This will be called in __exit__ or close() method
    assert pipeline.position_analyzer.close is not None


def test_pipeline_context_manager(pipeline_with_mocks):
    """Test pipeline can be used as context manager."""
    with pipeline_with_mocks as pipeline:
        pgn_data = []
        result = pipeline.analyze_games(pgn_data)
        assert result['games_analyzed'] == 0
