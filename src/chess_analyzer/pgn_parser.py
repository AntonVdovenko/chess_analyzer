from io import StringIO

import chess.pgn


class PGNParser:
    """Parse PGN files and extract positions."""

    def parse_pgn(self, pgn_string: str) -> dict:
        """Parse a PGN string and extract moves and positions."""
        game = chess.pgn.read_game(StringIO(pgn_string))

        if game is None:
            raise ValueError("Invalid PGN")

        headers = game.headers
        moves_with_positions = []
        board = game.board()
        for move_number, move in enumerate(game.mainline_moves(), start=1):
            fen_before = board.fen()
            eval_before = None

            san_move = board.san(move)
            board.push(move)

            fen_after = board.fen()
            eval_after = None

            moves_with_positions.append(
                {
                    "move_number": move_number,
                    "uci_move": move.uci(),
                    "san_move": san_move,
                    "move": san_move,  # For test compatibility
                    "fen": fen_after,  # For test compatibility
                    "fen_before": fen_before,
                    "fen_after": fen_after,
                    "eval_before": eval_before,
                    "eval_after": eval_after,
                }
            )

        return {
            "white": headers.get("White", "Unknown"),
            "black": headers.get("Black", "Unknown"),
            "event": headers.get("Event", "Unknown"),
            "date": headers.get("Date", "Unknown"),
            "result": headers.get("Result", "*"),
            "time_control": headers.get("TimeControl", "Unknown"),
            "white_elo": int(headers.get("WhiteElo", 0))
            if headers.get("WhiteElo", "").isdigit()
            else None,
            "black_elo": int(headers.get("BlackElo", 0))
            if headers.get("BlackElo", "").isdigit()
            else None,
            "moves": moves_with_positions,
        }
