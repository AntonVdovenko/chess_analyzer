"""Orchestrate the complete analysis pipeline."""

from __future__ import annotations

import logging
from statistics import mean
from typing import Any

import numpy as np

from src.chess_analyzer.feature_extractor import FeatureExtractor
from src.chess_analyzer.ml_models.clustering import WeaknessClustering
from src.chess_analyzer.pgn_parser import PGNParser
from src.chess_analyzer.position_analyzer import PositionAnalyzer

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """Orchestrate parsing, engine analysis, feature extraction, and clustering."""

    def __init__(self):
        """Initialize pipeline components."""
        self.pgn_parser = PGNParser()
        self.position_analyzer = PositionAnalyzer()
        self.feature_extractor = FeatureExtractor()
        self.clusterer = WeaknessClustering()

    def analyze_games(
        self,
        pgn_data: list[dict[str, Any]],
        player_perspective: str = "white",
    ) -> dict[str, Any]:
        """Analyze a list of games and extract aggregate patterns."""
        all_positions: list[dict[str, Any]] = []
        mistake_positions: list[dict[str, Any]] = []
        game_summaries: list[dict[str, Any]] = []
        acpls: list[float] = []

        for game_pgn_dict in pgn_data:
            try:
                parsed = self.pgn_parser.parse_pgn(game_pgn_dict["pgn"])
            except Exception as exc:
                logger.warning("Error parsing PGN: %s", exc)
                continue

            player_color = game_pgn_dict.get("player_color", player_perspective).lower()
            game_id = game_pgn_dict.get("game_id")
            game_positions: list[dict[str, Any]] = []

            for pos_idx, move_data in enumerate(parsed["moves"]):
                fen_before = move_data["fen_before"]
                fen_after = move_data["fen_after"]

                if not self._is_player_move(fen_before, player_color):
                    continue

                try:
                    analysis_before = self.position_analyzer.analyze_position(
                        fen_before,
                        depth=15,
                        time_limit=0.5,
                        perspective=player_color,
                    )
                    analysis_after = self.position_analyzer.analyze_position(
                        fen_after,
                        depth=15,
                        time_limit=0.5,
                        perspective=player_color,
                    )
                except Exception as exc:
                    logger.warning("Error analyzing position %s: %s", pos_idx, exc)
                    continue

                eval_before = analysis_before["evaluation"]
                eval_after = analysis_after["evaluation"]
                cpl = self.position_analyzer.calculate_centipawn_loss(
                    eval_before,
                    eval_after,
                )

                features = self.feature_extractor.extract_all_features(fen_after)
                phase = self.feature_extractor.classify_phase(
                    fen_after,
                    move_data["move_number"],
                )

                position_record = {
                    "game_id": game_id,
                    "move_number": move_data["move_number"],
                    "fen": fen_after,
                    "player_move": move_data["uci_move"],
                    "engine_best_move": analysis_before["best_move"],
                    "evaluation_loss": cpl,
                    "evaluation_before": eval_before,
                    "evaluation_after": eval_after,
                    "material_balance": features["material_balance"],
                    "piece_activity": features["piece_activity"],
                    "king_safety": features["king_safety"],
                    "is_opening": phase == "opening",
                    "is_middlegame": phase == "middlegame",
                    "is_endgame": phase == "endgame",
                }

                game_positions.append(position_record)
                all_positions.append(position_record)

                if cpl > 50:
                    mistake_positions.append(position_record)

            if not game_positions:
                continue

            game_acpl = self.position_analyzer.get_acpl(
                [
                    {
                        "eval_before": position["evaluation_before"],
                        "eval_after": position["evaluation_after"],
                    }
                    for position in game_positions
                ]
            )
            game_accuracy = self._estimate_accuracy(game_acpl)

            acpls.append(game_acpl)
            game_summaries.append(
                {
                    "game_id": game_id,
                    "player_color": player_color,
                    "positions": game_positions,
                    "acpl": game_acpl,
                    "accuracy": game_accuracy,
                }
            )

        cluster_info, pattern_candidates = self._build_patterns(mistake_positions)

        return {
            "games_analyzed": len(pgn_data),
            "total_acpl": float(mean(acpls)) if acpls else 0.0,
            "total_positions": len(all_positions),
            "mistake_positions": len(mistake_positions),
            "patterns": cluster_info,
            "games": game_summaries,
            "pattern_candidates": pattern_candidates,
        }

    def _build_patterns(
        self,
        mistake_positions: list[dict[str, Any]],
    ) -> tuple[dict[int, dict[str, Any]], list[dict[str, Any]]]:
        """Create cluster summaries and DB-ready pattern candidates."""
        if not mistake_positions:
            return {}, []

        if len(mistake_positions) < 3:
            pattern = self._create_pattern_candidate(
                "Recurring mistakes",
                mistake_positions,
            )
            return {0: {"label": pattern["name"], "size": pattern["frequency"]}}, [pattern]

        try:
            features_array = np.array(
                [
                    [
                        position["material_balance"],
                        position["piece_activity"],
                        position["king_safety"],
                    ]
                    for position in mistake_positions
                ]
            )
            optimal_k = self.clusterer.find_optimal_k(
                features_array,
                k_range=range(2, min(6, len(mistake_positions)) + 1),
            )
            if optimal_k <= 1:
                raise ValueError("Not enough positions to cluster")

            clusters = self.clusterer.cluster_positions(
                features_array,
                n_clusters=optimal_k,
            )
            cluster_info = self.clusterer.label_clusters(clusters, mistake_positions)
            pattern_candidates = [
                self._create_pattern_candidate(
                    cluster_info[cluster_id]["label"],
                    [
                        position
                        for idx, position in enumerate(mistake_positions)
                        if clusters[idx] == cluster_id
                    ],
                )
                for cluster_id in sorted(cluster_info)
            ]
            return cluster_info, pattern_candidates
        except Exception as exc:
            logger.warning("Error clustering positions: %s", exc)
            pattern = self._create_pattern_candidate(
                "Recurring mistakes",
                mistake_positions,
            )
            return {0: {"label": pattern["name"], "size": pattern["frequency"]}}, [pattern]

    def _create_pattern_candidate(
        self,
        label: str,
        positions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build a persistent pattern summary from clustered positions."""
        avg_eval_loss = float(mean(position["evaluation_loss"] for position in positions))
        avg_material = float(mean(position["material_balance"] for position in positions))
        avg_activity = float(mean(position["piece_activity"] for position in positions))
        avg_king_safety = float(mean(position["king_safety"] for position in positions))
        dominant_phase = self._dominant_phase(positions)

        return {
            "name": label,
            "weakness_type": self._infer_weakness_type(
                label,
                dominant_phase,
                avg_eval_loss,
                avg_king_safety,
            ),
            "frequency": len(positions),
            "game_ids": sorted(
                {
                    position["game_id"]
                    for position in positions
                    if position.get("game_id") is not None
                }
            ),
            "position_features": {
                "avg_material_balance": avg_material,
                "avg_piece_activity": avg_activity,
                "avg_king_safety": avg_king_safety,
                "dominant_phase": dominant_phase,
                "sample_fen": positions[0]["fen"],
            },
            "average_eval_loss": avg_eval_loss,
        }

    @staticmethod
    def _dominant_phase(positions: list[dict[str, Any]]) -> str:
        """Return the most common phase represented in a list of positions."""
        opening = sum(position["is_opening"] for position in positions)
        middlegame = sum(position["is_middlegame"] for position in positions)
        endgame = sum(position["is_endgame"] for position in positions)
        scores = {
            "opening": opening,
            "middlegame": middlegame,
            "endgame": endgame,
        }
        return max(scores, key=scores.get)

    @staticmethod
    def _infer_weakness_type(
        label: str,
        dominant_phase: str,
        average_eval_loss: float,
        average_king_safety: float,
    ) -> str:
        """Infer a weakness type compatible with the rest of the product."""
        label_lower = label.lower()
        if dominant_phase == "opening":
            return "opening"
        if "king safety" in label_lower or average_king_safety < 40 or average_eval_loss >= 150:
            return "tactical"
        return "positional"

    @staticmethod
    def _estimate_accuracy(acpl: float) -> float:
        """Estimate a percentage-style accuracy from ACPL."""
        return max(0.0, min(100.0, 100.0 - (acpl / 10.0)))

    @staticmethod
    def _is_player_move(fen_before: str, player_color: str) -> bool:
        """Check whether a FEN side-to-move matches the analyzed player."""
        active_color = fen_before.split()[1]
        if player_color == "white":
            return active_color == "w"
        return active_color == "b"

    def close(self):
        """Clean up resources."""
        try:
            self.position_analyzer.close()
            logger.info("Analysis pipeline closed successfully")
        except Exception as exc:
            logger.error("Error closing pipeline: %s", exc)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
