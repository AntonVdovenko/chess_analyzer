"""Advanced analysis orchestration for phase 2 ML features."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from src.chess_analyzer.database.models import (
    Anomaly,
    Embedding,
    Game,
    MovePrediction,
    Position,
)
from src.chess_analyzer.ml_models.anomaly_detector import AnomalyDetector
from src.chess_analyzer.ml_models.embeddings import PositionEmbedder
from src.chess_analyzer.ml_models.move_predictor import MovePredictor

logger = logging.getLogger(__name__)


class AdvancedAnalysisPipeline:
    """Run all advanced analyses for already-analyzed player positions."""

    def __init__(self, session: Session):
        """Initialize ML components with a database session."""
        self.session = session
        self.move_predictor = MovePredictor(min_position_frequency=5)
        self.anomaly_detector = AnomalyDetector(contamination=0.1)
        self.embedder = PositionEmbedder(n_components=16)

    def analyze_player(self, username: str) -> dict[str, Any]:
        """Run all advanced analyses for a player."""
        games = self.session.query(Game).filter(Game.username == username).all()
        if not games:
            return {
                "username": username,
                "status": "error",
                "message": "No games found",
            }

        game_ids = [game.id for game in games]
        positions = self.session.query(Position).filter(Position.game_id.in_(game_ids)).all()
        if not positions:
            return {
                "username": username,
                "status": "error",
                "message": "No positions found",
            }

        logger.info("Analyzing %s games for %s", len(games), username)

        try:
            self.move_predictor.fit(games)
            self.anomaly_detector.fit(positions)
            self.embedder.fit(positions)
        except Exception as exc:
            logger.error("Advanced model fitting failed: %s", exc)
            self.session.rollback()
            return {
                "username": username,
                "status": "error",
                "message": f"Advanced analysis failed: {exc}",
            }

        self._clear_existing_results(game_ids, [position.id for position in positions])

        move_predictions: list[MovePrediction] = []
        anomalies: list[Anomaly] = []
        embeddings: list[Embedding] = []

        for position in positions:
            try:
                if position.player_move:
                    probability = self.move_predictor.predict(
                        position.fen,
                        position.player_move,
                    )
                    if probability < 0.2:
                        move_predictions.append(
                            MovePrediction(
                                game_id=position.game_id,
                                position_fen=position.fen,
                                actual_move=position.player_move,
                                predicted_move=position.engine_best_move,
                                probability_score=probability,
                                is_unusual=True,
                            )
                        )

                anomaly_score = self.anomaly_detector.predict(position)
                if anomaly_score >= 0.7:
                    anomalies.append(
                        Anomaly(
                            game_id=position.game_id,
                            position_fen=position.fen,
                            anomaly_score=anomaly_score,
                            centipawn_loss=position.evaluation_loss or 0.0,
                            reason=self._categorize_anomaly_reason(
                                position.evaluation_loss or 0.0,
                            ),
                        )
                    )

                embeddings.append(
                    Embedding(
                        position_id=position.id,
                        embedding_vector=self.embedder.embed(position).tolist(),
                        embedding_cluster=None,
                    )
                )
            except Exception as exc:
                logger.warning("Failed to score position %s: %s", position.id, exc)

        self.session.add_all(move_predictions)
        self.session.add_all(anomalies)
        self.session.add_all(embeddings)
        self.session.commit()

        logger.info(
            "Analysis complete: %s predictions, %s anomalies, %s embeddings",
            len(move_predictions),
            len(anomalies),
            len(embeddings),
        )

        return {
            "username": username,
            "status": "completed",
            "unusual_moves_found": len(move_predictions),
            "anomalies_found": len(anomalies),
            "embeddings_created": len(embeddings),
        }

    def _clear_existing_results(
        self,
        game_ids: list[int],
        position_ids: list[int],
    ) -> None:
        """Delete prior advanced-analysis artifacts for the same games."""
        if game_ids:
            self.session.query(MovePrediction).filter(
                MovePrediction.game_id.in_(game_ids)
            ).delete(synchronize_session=False)
            self.session.query(Anomaly).filter(
                Anomaly.game_id.in_(game_ids)
            ).delete(synchronize_session=False)
        if position_ids:
            self.session.query(Embedding).filter(
                Embedding.position_id.in_(position_ids)
            ).delete(synchronize_session=False)
        self.session.flush()

    @staticmethod
    def _categorize_anomaly_reason(centipawn_loss: float) -> str:
        """Build a human-readable anomaly label."""
        if centipawn_loss >= 300:
            return "rare blunder"
        if centipawn_loss >= 150:
            return "unusual tactic miss"
        return "unusual move"
