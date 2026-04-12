import chess
from typing import Dict


class FeatureExtractor:
    """Extract numerical features from chess positions."""

    def extract_material_balance(self, fen: str) -> float:
        """Extract material balance (white - black)."""
        board = chess.Board(fen)
        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 0,
        }

        white_material = 0
        black_material = 0

        for piece_type in piece_values:
            white_count = len(board.pieces(piece_type, chess.WHITE))
            black_count = len(board.pieces(piece_type, chess.BLACK))
            white_material += white_count * piece_values[piece_type]
            black_material += black_count * piece_values[piece_type]

        return float(white_material - black_material)

    def extract_piece_activity(self, fen: str) -> float:
        """Extract piece activity (number of legal moves available)."""
        board = chess.Board(fen)
        num_moves = board.legal_moves.count()
        return min(100.0, (num_moves / 60.0) * 100.0)

    def extract_king_safety(self, fen: str) -> float:
        """Extract king safety metric (0-100)."""
        board = chess.Board(fen)

        white_king_pos = board.king(chess.WHITE)
        black_king_pos = board.king(chess.BLACK)

        white_king_file = chess.square_file(white_king_pos)
        white_king_rank = chess.square_rank(white_king_pos)

        center_distance = abs(white_king_file - 3.5) + abs(white_king_rank - 3.5)
        safety_score = 100.0 - (center_distance * 10.0)

        return max(0.0, min(100.0, safety_score))

    def extract_all_features(self, fen: str) -> Dict[str, float]:
        """Extract all relevant features from a position."""
        return {
            "material_balance": self.extract_material_balance(fen),
            "piece_activity": self.extract_piece_activity(fen),
            "king_safety": self.extract_king_safety(fen),
        }
