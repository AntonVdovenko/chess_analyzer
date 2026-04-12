from typing import List, Dict, Optional
from src.chess_analyzer.database.models import Game, Position
import hashlib


class MovePredictor:
    """Learn player's move patterns and detect unusual moves"""

    def __init__(self, min_position_frequency: int = 5):
        """
        Args:
            min_position_frequency: Only learn patterns from positions seen 5+ times
        """
        self.min_position_frequency = min_position_frequency
        self.move_distributions = {}  # {position_hash: {move: count}}

    def fit(self, games: List[Game]) -> None:
        """Learn move patterns from player's games"""
        if not games:
            return

        # Extract positions and moves
        for game in games:
            if not hasattr(game, 'positions') or not game.positions:
                continue

            for position in game.positions:
                if not hasattr(position, 'fen') or not hasattr(position, 'player_move'):
                    continue

                # Create position hash (using FEN as key)
                pos_key = position.fen

                if pos_key not in self.move_distributions:
                    self.move_distributions[pos_key] = {}

                if position.player_move:
                    move = position.player_move
                    if move not in self.move_distributions[pos_key]:
                        self.move_distributions[pos_key][move] = 0
                    self.move_distributions[pos_key][move] += 1

    def predict(self, position_fen: str, move: str) -> float:
        """
        Return probability of this move in this position (0-1)

        Args:
            position_fen: FEN string of position
            move: Move in algebraic notation

        Returns:
            Probability 0-1, or 0.0 if position not seen during training
        """
        if position_fen not in self.move_distributions:
            return 0.0

        moves_dict = self.move_distributions[position_fen]
        if not moves_dict:
            return 0.0

        total = sum(moves_dict.values())
        move_count = moves_dict.get(move, 0)

        if total == 0:
            return 0.0

        return float(move_count) / float(total)

    def get_unusual_moves(self, game: Game, threshold: float = 0.2) -> List[Dict]:
        """
        Get moves with probability < threshold

        Args:
            game: Game object with positions
            threshold: Probability threshold (default 0.2)

        Returns:
            List of dicts with move_number, move, probability, expected_moves
        """
        unusual = []

        if not hasattr(game, 'positions') or not game.positions:
            return unusual

        for i, position in enumerate(game.positions):
            if not hasattr(position, 'player_move') or not position.player_move:
                continue

            prob = self.predict(position.fen, position.player_move)

            if prob < threshold:
                # Get expected moves (most common in this position)
                if position.fen in self.move_distributions:
                    moves_dict = self.move_distributions[position.fen]
                    expected_moves = sorted(
                        moves_dict.keys(),
                        key=lambda m: moves_dict[m],
                        reverse=True
                    )[:3]  # Top 3 expected moves
                else:
                    expected_moves = []

                unusual.append({
                    "move_number": i + 1,
                    "move": position.player_move,
                    "probability": prob,
                    "expected_moves": expected_moves
                })

        return unusual
