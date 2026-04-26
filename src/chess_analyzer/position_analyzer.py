"""Analyze chess positions using Stockfish engine."""

import logging

import chess
import chess.engine

from src.chess_analyzer.config import settings

logger = logging.getLogger(__name__)


class PositionAnalyzer:
    """Analyze chess positions using Stockfish engine."""

    def __init__(self, stockfish_path: str | None = None):
        """Initialize the position analyzer with Stockfish engine.

        Args:
            stockfish_path: Path to Stockfish executable. If None, uses settings.STOCKFISH_PATH.

        Raises:
            FileNotFoundError: If Stockfish executable not found.
            RuntimeError: If engine fails to initialize.
        """
        path = stockfish_path or settings.STOCKFISH_PATH
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(path)
            logger.info(f"Stockfish engine initialized at {path}")
        except Exception as e:
            logger.error(f"Failed to initialize Stockfish engine: {e}")
            raise RuntimeError(f"Failed to initialize Stockfish engine at {path}") from e

    def calculate_centipawn_loss(self, eval_before: float, eval_after: float) -> float:
        """Calculate centipawn loss for a move.

        Centipawn loss is the absolute difference between the evaluation before
        and after a move, measured in centipawns (hundredths of a pawn).

        Args:
            eval_before: Evaluation before the move (in pawns).
            eval_after: Evaluation after the move (in pawns).

        Returns:
            Absolute centipawn loss as a float.
        """
        return abs(eval_before - eval_after) * 100.0

    def analyze_position(
        self, fen: str, depth: int | None = None, time_limit: float = 1.0
    ) -> dict:
        """Analyze a position using Stockfish.

        Args:
            fen: FEN string representing the position.
            depth: Analysis depth (optional, uses time_limit if not set).
            time_limit: Time limit in seconds for analysis (default 1.0).

        Returns:
            Dictionary with keys:
                - best_move: UCI string of best move, or None
                - evaluation: Evaluation in pawns as float
                - depth: Depth reached by engine
        """
        try:
            board = chess.Board(fen)
        except ValueError as e:
            logger.error(f"Invalid FEN: {fen}")
            raise ValueError(f"Invalid FEN string: {fen}") from e

        try:
            limit = chess.engine.Limit(depth=depth, time=time_limit)
            info = self.engine.analyse(board, limit)

            best_move = info.get("pv")
            best_move_uci = best_move[0].uci() if best_move else None
            evaluation = self._evaluation_to_float(info.get("score"))

            return {
                "best_move": best_move_uci,
                "evaluation": evaluation,
                "depth": info.get("depth"),
            }
        except Exception as e:
            logger.error(f"Error analyzing position: {e}")
            raise

    def _evaluation_to_float(self, score: chess.engine.Score | None) -> float:
        """Convert Stockfish evaluation to float (pawns).

        Args:
            score: Stockfish Score object or PovScore object.

        Returns:
            Evaluation as float in pawns. Mate scores are converted to +/- 10000.
        """
        if score is None:
            return 0.0

        # Handle PovScore by converting to Score object
        if isinstance(score, chess.engine.PovScore):
            score = score.relative

        if score.is_mate():
            mate_in_n = score.mate()
            return 10000.0 if mate_in_n > 0 else -10000.0

        # Convert centipawns to pawns
        return float(score.cp) / 100.0

    def get_acpl(self, positions: list[dict]) -> float:
        """Calculate ACPL (Average Centipawn Loss) for a game.

        ACPL is the average absolute difference between evaluation before
        and after each move in a game.

        Args:
            positions: List of dicts with 'eval_before' and 'eval_after' keys.

        Returns:
            Average centipawn loss as float.
        """
        if not positions:
            return 0.0

        cpls = [
            self.calculate_centipawn_loss(pos["eval_before"], pos["eval_after"])
            for pos in positions
        ]
        return sum(cpls) / len(cpls)

    def close(self):
        """Close the Stockfish engine."""
        try:
            self.engine.quit()
            logger.info("Stockfish engine closed")
        except Exception as e:
            logger.error(f"Error closing engine: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
