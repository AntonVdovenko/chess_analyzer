"""Orchestrate the complete analysis pipeline."""

import logging
from typing import List, Dict

import numpy as np

from src.chess_analyzer.pgn_parser import PGNParser
from src.chess_analyzer.position_analyzer import PositionAnalyzer
from src.chess_analyzer.feature_extractor import FeatureExtractor
from src.chess_analyzer.ml_models.clustering import WeaknessClustering

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """Orchestrate the complete analysis pipeline."""

    def __init__(self):
        """Initialize pipeline components."""
        self.pgn_parser = PGNParser()
        self.position_analyzer = PositionAnalyzer()
        self.feature_extractor = FeatureExtractor()
        self.clusterer = WeaknessClustering()

    def analyze_games(self, pgn_data: List[Dict], player_perspective: str = 'white') -> Dict:
        """Analyze a list of games and extract patterns.

        Args:
            pgn_data: List of dictionaries with 'pgn' key containing PGN strings.
            player_perspective: Perspective for analysis ('white' or 'black').

        Returns:
            Dictionary with analysis results including games_analyzed, total_acpl, patterns.
        """
        all_positions = []
        mistake_positions = []
        acpls = []

        for game_pgn_dict in pgn_data:
            try:
                parsed = self.pgn_parser.parse_pgn(game_pgn_dict['pgn'])

                game_positions = []
                for pos_idx, move_data in enumerate(parsed['moves']):
                    fen = move_data['fen_before']

                    try:
                        analysis = self.position_analyzer.analyze_position(fen, depth=15, time_limit=0.5)
                        fen_after = move_data['fen_after']
                        analysis_after = self.position_analyzer.analyze_position(fen_after, depth=15, time_limit=0.5)

                        eval_before = analysis['evaluation']
                        eval_after = analysis_after['evaluation']
                        cpl = self.position_analyzer.calculate_centipawn_loss(eval_before, eval_after)

                        position_record = {
                            'move_number': move_data['move_number'],
                            'fen': fen_after,
                            'move': move_data['uci_move'],
                            'cpl': cpl,
                            'eval_before': eval_before,
                            'eval_after': eval_after,
                        }

                        features = self.feature_extractor.extract_all_features(fen_after)
                        position_record.update(features)

                        game_positions.append(position_record)
                        all_positions.append(position_record)

                        if cpl > 50:
                            mistake_positions.append(position_record)

                    except Exception as e:
                        logger.warning(f"Error analyzing position {pos_idx}: {e}")
                        continue

                if game_positions:
                    game_acpl = self.position_analyzer.get_acpl([
                        {'eval_before': p['eval_before'], 'eval_after': p['eval_after']}
                        for p in game_positions
                    ])
                    acpls.append(game_acpl)

            except Exception as e:
                logger.warning(f"Error parsing PGN: {e}")
                continue

        cluster_info = {}
        if mistake_positions and len(mistake_positions) > 2:
            try:
                features_array = np.array([
                    [p['material_balance'], p['piece_activity'], p['king_safety']]
                    for p in mistake_positions
                ])

                optimal_k = self.clusterer.find_optimal_k(
                    features_array,
                    k_range=range(2, min(6, len(mistake_positions)))
                )
                clusters = self.clusterer.cluster_positions(features_array, n_clusters=optimal_k)
                cluster_info = self.clusterer.label_clusters(clusters, mistake_positions)
            except Exception as e:
                logger.warning(f"Error clustering positions: {e}")

        return {
            'games_analyzed': len(pgn_data),
            'total_acpl': float(np.mean(acpls)) if acpls else 0.0,
            'total_positions': len(all_positions),
            'mistake_positions': len(mistake_positions),
            'patterns': cluster_info,
        }

    def close(self):
        """Clean up resources."""
        try:
            self.position_analyzer.close()
            logger.info("Analysis pipeline closed successfully")
        except Exception as e:
            logger.error(f"Error closing pipeline: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
