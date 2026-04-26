"""Utilities for extracting numeric features from chess positions."""

import chess


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

        for piece_type, piece_value in piece_values.items():
            white_count = len(board.pieces(piece_type, chess.WHITE))
            black_count = len(board.pieces(piece_type, chess.BLACK))
            white_material += white_count * piece_value
            black_material += black_count * piece_value

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

        white_king_file = chess.square_file(white_king_pos)
        white_king_rank = chess.square_rank(white_king_pos)

        center_distance = abs(white_king_file - 3.5) + abs(white_king_rank - 3.5)
        safety_score = 100.0 - (center_distance * 10.0)

        return max(0.0, min(100.0, safety_score))

    def classify_phase(self, fen: str, move_number: int) -> str:
        """Classify a position into opening, middlegame, or endgame."""
        board = chess.Board(fen)
        major_minor_count = sum(
            len(board.pieces(piece_type, chess.WHITE))
            + len(board.pieces(piece_type, chess.BLACK))
            for piece_type in (
                chess.KNIGHT,
                chess.BISHOP,
                chess.ROOK,
                chess.QUEEN,
            )
        )
        queens_remaining = (
            len(board.pieces(chess.QUEEN, chess.WHITE))
            + len(board.pieces(chess.QUEEN, chess.BLACK))
        )

        if move_number <= 20:
            return "opening"
        if queens_remaining == 0 and major_minor_count <= 6:
            return "endgame"
        if major_minor_count <= 4:
            return "endgame"
        return "middlegame"

    def extract_all_features(self, fen: str) -> dict[str, float]:
        """Extract all relevant features from a position."""
        return {
            "material_balance": self.extract_material_balance(fen),
            "piece_activity": self.extract_piece_activity(fen),
            "king_safety": self.extract_king_safety(fen),
        }
