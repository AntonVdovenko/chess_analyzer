"""Chess.com API integration for fetching player games."""

from datetime import UTC, datetime

from chessdotcom import ChessDotComClient


class ChessComFetcher:
    """Fetch games from chess.com API."""

    def __init__(self, user_agent: str | None = None):
        """Initialize the Chess.com fetcher.

        Args:
            user_agent: Optional User-Agent header for API requests.
        """
        self.client = ChessDotComClient(user_agent=user_agent or "Chess Analyzer Bot")

    def fetch_games(self, username: str, limit: int = 100) -> list[dict]:
        """Fetch games for a player from chess.com.

        Args:
            username: Chess.com username
            limit: Maximum number of games to fetch

        Returns:
            List of game dictionaries with pgn, players, result, etc.

        Raises:
            Exception: If API call fails or player not found.
        """
        games = []

        try:
            # Get list of game archives (monthly)
            archives_response = self.client.get_player_game_archives(username)
            archives = archives_response.archives

            # Fetch games starting from most recent archive
            for archive_url in reversed(archives):
                if len(games) >= limit:
                    break

                # Extract year and month from archive URL
                # Format: https://api.chess.com/pub/player/{username}/games/{year}/{month}
                parts = archive_url.rstrip("/").split("/")
                year = parts[-2]
                month = parts[-1]

                # Fetch games for this month
                games_response = self.client.get_player_games_by_month(
                    username, year=year, month=month
                )

                # Process each game
                for game in games_response.games:
                    if len(games) >= limit:
                        break

                    game_dict = self._parse_game(game, username)
                    games.append(game_dict)

            return games[:limit]

        except Exception as e:
            raise Exception(f"Error fetching games for {username}: {e}") from e

    def _parse_game(self, game, player_username: str) -> dict:
        """Parse a game object from chess.com API into standard format.

        Args:
            game: Game object from chess.com API
            player_username: Username of the player we're analyzing

        Returns:
            Dictionary with normalized game data.
        """
        # Determine which side the player was on
        white_username = game.white.username if game.white else None
        black_username = game.black.username if game.black else None

        is_white = white_username and white_username.lower() == player_username.lower()

        # Get the opponent
        opponent = black_username if is_white else white_username

        # Normalize result: white's perspective
        result = game.white.result if is_white else game.black.result
        result_normalized = self._normalize_result(result)

        return {
            "pgn": game.pgn,
            "url": game.url,
            "white": white_username,
            "black": black_username,
            "white_elo": game.white.rating if game.white else None,
            "black_elo": game.black.rating if game.black else None,
            "result": result_normalized,
            "time_control": game.time_control,
            "time_class": game.time_class or self._infer_time_class(game.time_control),
            "date": datetime.fromtimestamp(game.end_time, tz=UTC) if game.end_time else None,
            "opponent": opponent,
            "opponent_elo": (game.black.rating if is_white else game.white.rating),
        }

    @staticmethod
    def _normalize_result(result: str) -> str:
        """Normalize result to standard format.

        Args:
            result: Result from chess.com API

        Returns:
            Normalized result: 'win', 'loss', 'draw', 'timeout', 'abandoned'
        """
        result_map = {
            "win": "win",
            "loss": "loss",
            "draw": "draw",
            "checkmated": "loss",
            "timeout": "timeout",
            "abandoned": "abandoned",
            "repetition": "draw",
            "agreed": "draw",
            "resigned": "loss",
            "stalemate": "draw",
            "insufficient": "draw",
            "50move": "draw",
            "timevsinsufficient": "draw",
        }

        normalized = result_map.get(result, result)
        return normalized.lower() if normalized else "draw"

    @staticmethod
    def _infer_time_class(time_control: str) -> str:
        """Infer time class from time control string.

        Args:
            time_control: Time control string (e.g., "180+0", "300+3")

        Returns:
            Time class: 'bullet', 'blitz', 'rapid', 'classical'
        """
        if not time_control or "+" not in time_control:
            return "unknown"

        try:
            base_time = int(time_control.split("+", maxsplit=1)[0])

            if base_time < 180:
                return "bullet"
            elif base_time < 600:
                return "blitz"
            elif base_time < 1800:
                return "rapid"
            else:
                return "classical"
        except (ValueError, IndexError):
            return "unknown"
