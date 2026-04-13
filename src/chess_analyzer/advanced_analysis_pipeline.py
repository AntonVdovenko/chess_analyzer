from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from src.chess_analyzer.ml_models.move_predictor import MovePredictor
from src.chess_analyzer.ml_models.anomaly_detector import AnomalyDetector
from src.chess_analyzer.ml_models.embeddings import PositionEmbedder
from src.chess_analyzer.database.models import (
    Game, Position, MovePrediction, Anomaly, Embedding
)
import logging

logger = logging.getLogger(__name__)


class AdvancedAnalysisPipeline:
    """Orchestrate all Phase 2 ML components"""

    def __init__(self, session: Session):
        """
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.move_predictor = MovePredictor(min_position_frequency=5)
        self.anomaly_detector = AnomalyDetector(contamination=0.1)
        self.embedder = PositionEmbedder(n_components=16)

    def analyze_player(self, username: str) -> Dict:
        """Run all advanced analyses for a player"""
        games = self.session.query(Game).filter(
            Game.username == username
        ).all()

        if not games:
            return {
                "username": username,
                "status": "error",
                "message": "No games found"
            }

        logger.info(f"Analyzing {len(games)} games for {username}")

        try:
            self.move_predictor.fit(games)
            logger.info("MovePredictor fitted")
        except Exception as e:
            logger.error(f"MovePredictor fit failed: {e}")
            return {
                "username": username,
                "status": "error",
                "message": f"MovePredictor failed: {str(e)}"
            }

        positions = self.session.query(Position).filter(
            Position.game_id.in_([g.id for g in games])
        ).all()

        if not positions:
            return {
                "username": username,
                "status": "error",
                "message": "No positions found"
            }

        try:
            self.anomaly_detector.fit(positions)
            logger.info("AnomalyDetector fitted")
        except Exception as e:
            logger.error(f"AnomalyDetector fit failed: {e}")
            return {
                "username": username,
                "status": "error",
                "message": f"AnomalyDetector failed: {str(e)}"
            }

        try:
            self.embedder.fit(positions)
            logger.info("PositionEmbedder fitted")
        except Exception as e:
            logger.error(f"PositionEmbedder fit failed: {e}")
            return {
                "username": username,
                "status": "error",
                "message": f"PositionEmbedder failed: {str(e)}"
            }

        move_pred_count = 0
        anomaly_count = 0
        embedding_count = 0

        for game in games:
            for position in game.positions:
                try:
                    if hasattr(position, 'move') and position.move:
                        prob = self.move_predictor.predict(position.fen, position.move)
                        if prob < 0.2:
                            self._save_move_prediction(game.id, position, prob)
                            move_pred_count += 1

                    anom_score = self.anomaly_detector.predict(position)
                    if anom_score > 0.7:
                        self._save_anomaly(game.id, position, anom_score)
                        anomaly_count += 1

                    embedding = self.embedder.embed(position)
                    self._save_embedding(position, embedding)
                    embedding_count += 1

                except Exception as e:
                    logger.warning(f"Failed to score position: {e}")
                    continue

        logger.info(f"Analysis complete: {move_pred_count} predictions, "
                   f"{anomaly_count} anomalies, {embedding_count} embeddings")

        return {
            "username": username,
            "status": "completed",
            "unusual_moves_found": move_pred_count,
            "anomalies_found": anomaly_count,
            "embeddings_created": embedding_count
        }

    def _save_move_prediction(self, game_id: int, position: Position, probability: float) -> None:
        """Save move prediction to database"""
        try:
            prediction = MovePrediction(
                game_id=game_id,
                position_fen=position.fen,
                actual_move=getattr(position, 'move', ''),
                predicted_move=None,
                probability_score=probability,
                is_unusual=True
            )
            self.session.add(prediction)
            self.session.commit()
        except Exception as e:
            logger.warning(f"Failed to save move prediction: {e}")
            self.session.rollback()

    def _save_anomaly(self, game_id: int, position: Position, anomaly_score: float) -> None:
        """Save anomaly to database"""
        try:
            cpl = getattr(position, 'centipawn_loss', 0.0) or 0.0

            if cpl > 300:
                reason = "rare blunder"
            elif cpl > 150:
                reason = "unusual tactic miss"
            else:
                reason = "unusual move"

            anomaly = Anomaly(
                game_id=game_id,
                position_fen=position.fen,
                anomaly_score=anomaly_score,
                centipawn_loss=cpl,
                reason=reason
            )
            self.session.add(anomaly)
            self.session.commit()
        except Exception as e:
            logger.warning(f"Failed to save anomaly: {e}")
            self.session.rollback()

    def _save_embedding(self, position: Position, embedding_vector: list) -> None:
        """Save embedding to database"""
        try:
            embedding = Embedding(
                position_id=position.id,
                embedding_vector=embedding_vector.tolist(),
                embedding_cluster=None
            )
            self.session.add(embedding)
            self.session.commit()
        except Exception as e:
            logger.warning(f"Failed to save embedding: {e}")
            self.session.rollback()
