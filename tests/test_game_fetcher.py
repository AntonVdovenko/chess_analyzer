"""Tests for chess.com game fetcher."""

from src.chess_analyzer.game_fetcher import ChessComFetcher


def test_fetch_games_returns_list():
    """Test that fetch_games returns a list of games."""
    fetcher = ChessComFetcher()
    games = fetcher.fetch_games("hikaru", limit=5)

    assert isinstance(games, list)
    assert len(games) > 0
    assert all("pgn" in game for game in games)
    assert all("date" in game for game in games)


def test_fetch_games_parsing():
    """Test that games have expected fields."""
    fetcher = ChessComFetcher()
    games = fetcher.fetch_games("hikaru", limit=1)

    game = games[0]
    assert "pgn" in game
    assert "white" in game
    assert "black" in game
    assert "result" in game
    assert "time_control" in game


def test_fetch_games_with_valid_player():
    """Test fetch_games with a known player."""
    fetcher = ChessComFetcher()
    games = fetcher.fetch_games("hikaru", limit=3)

    assert isinstance(games, list)
    assert len(games) <= 3
    if len(games) > 0:
        game = games[0]
        assert isinstance(game["pgn"], str)
        assert isinstance(game["white"], str)
        assert isinstance(game["black"], str)
        assert game["result"] in ["win", "loss", "draw", "timeout", "abandoned"]
        assert game["time_class"] in ["blitz", "rapid", "classical", "bullet", "unknown"]


def test_fetch_games_respects_limit():
    """Test that limit parameter is respected."""
    fetcher = ChessComFetcher()
    games = fetcher.fetch_games("hikaru", limit=2)

    assert len(games) <= 2
