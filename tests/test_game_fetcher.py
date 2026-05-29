"""Tests for the Chess.com game fetcher."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import call, patch

import pytest

from chess_analyzer.game_fetcher import ChessComFetcher


def make_player(username: str, rating: int, result: str) -> SimpleNamespace:
    """Build a minimal player object matching the chess.com client shape."""
    return SimpleNamespace(username=username, rating=rating, result=result)


def make_game(
    *,
    white_username: str,
    white_rating: int,
    white_result: str,
    black_username: str,
    black_rating: int,
    black_result: str,
    url: str,
    time_control: str = "180+2",
    time_class: str | None = None,
    end_time: int = 1704067200,
    pgn: str = '[Event "Live Chess"]\n1. e4 e5 1-0',
) -> SimpleNamespace:
    """Build a minimal game object matching the chess.com client shape."""
    return SimpleNamespace(
        white=make_player(white_username, white_rating, white_result),
        black=make_player(black_username, black_rating, black_result),
        pgn=pgn,
        url=url,
        time_control=time_control,
        time_class=time_class,
        end_time=end_time,
    )


@pytest.fixture
def mock_chessdotcom_client():
    """Patch the chess.com client so tests never touch the network."""
    with patch("chess_analyzer.game_fetcher.ChessDotComClient") as client_cls:
        yield client_cls.return_value


def test_fetch_games_returns_parsed_fields_without_network(mock_chessdotcom_client):
    """fetch_games should return normalized dictionaries from stubbed responses."""
    mock_chessdotcom_client.get_player_game_archives.return_value = SimpleNamespace(
        archives=["https://api.chess.com/pub/player/hikaru/games/2024/01"]
    )
    mock_chessdotcom_client.get_player_games_by_month.return_value = SimpleNamespace(
        games=[
            make_game(
                white_username="hikaru",
                white_rating=3200,
                white_result="repetition",
                black_username="opponent",
                black_rating=2800,
                black_result="repetition",
                url="https://www.chess.com/game/live/1",
            )
        ]
    )

    games = ChessComFetcher().fetch_games("hikaru", limit=5)

    assert isinstance(games, list)
    assert len(games) == 1

    game = games[0]
    assert game["pgn"].startswith('[Event "Live Chess"]')
    assert game["url"] == "https://www.chess.com/game/live/1"
    assert game["white"] == "hikaru"
    assert game["black"] == "opponent"
    assert game["white_elo"] == 3200
    assert game["black_elo"] == 2800
    assert game["result"] == "draw"
    assert game["time_control"] == "180+2"
    assert game["time_class"] == "blitz"
    assert game["date"] == datetime.fromtimestamp(1704067200, tz=UTC)
    assert game["opponent"] == "opponent"
    assert game["opponent_elo"] == 2800


def test_fetch_games_uses_player_perspective_when_user_is_black(mock_chessdotcom_client):
    """Parsed fields should be calculated from the requested player's side."""
    mock_chessdotcom_client.get_player_game_archives.return_value = SimpleNamespace(
        archives=["https://api.chess.com/pub/player/hikaru/games/2024/02"]
    )
    mock_chessdotcom_client.get_player_games_by_month.return_value = SimpleNamespace(
        games=[
            make_game(
                white_username="opponent",
                white_rating=2750,
                white_result="checkmated",
                black_username="hikaru",
                black_rating=3190,
                black_result="win",
                url="https://www.chess.com/game/live/2",
                time_control="60+0",
                time_class="bullet",
            )
        ]
    )

    games = ChessComFetcher().fetch_games("hikaru", limit=1)

    assert len(games) == 1
    game = games[0]
    assert game["white"] == "opponent"
    assert game["black"] == "hikaru"
    assert game["result"] == "win"
    assert game["time_class"] == "bullet"
    assert game["opponent"] == "opponent"
    assert game["opponent_elo"] == 2750


def test_fetch_games_respects_limit_across_archives(mock_chessdotcom_client):
    """The fetcher should read newest archives first and stop at the requested limit."""
    mock_chessdotcom_client.get_player_game_archives.return_value = SimpleNamespace(
        archives=[
            "https://api.chess.com/pub/player/hikaru/games/2024/01",
            "https://api.chess.com/pub/player/hikaru/games/2024/02",
        ]
    )
    mock_chessdotcom_client.get_player_games_by_month.side_effect = [
        SimpleNamespace(
            games=[
                make_game(
                    white_username="hikaru",
                    white_rating=3200,
                    white_result="win",
                    black_username="recent-opponent",
                    black_rating=2700,
                    black_result="checkmated",
                    url="https://www.chess.com/game/live/recent",
                    end_time=1706745600,
                )
            ]
        ),
        SimpleNamespace(
            games=[
                make_game(
                    white_username="hikaru",
                    white_rating=3200,
                    white_result="win",
                    black_username="older-opponent-1",
                    black_rating=2650,
                    black_result="checkmated",
                    url="https://www.chess.com/game/live/older-1",
                    end_time=1704067200,
                ),
                make_game(
                    white_username="hikaru",
                    white_rating=3200,
                    white_result="win",
                    black_username="older-opponent-2",
                    black_rating=2600,
                    black_result="checkmated",
                    url="https://www.chess.com/game/live/older-2",
                    end_time=1704067100,
                ),
            ]
        ),
    ]

    games = ChessComFetcher().fetch_games("hikaru", limit=2)

    assert len(games) == 2
    assert [game["url"] for game in games] == [
        "https://www.chess.com/game/live/recent",
        "https://www.chess.com/game/live/older-1",
    ]
    mock_chessdotcom_client.get_player_games_by_month.assert_has_calls(
        [
            call("hikaru", year="2024", month="02"),
            call("hikaru", year="2024", month="01"),
        ]
    )
    assert mock_chessdotcom_client.get_player_games_by_month.call_count == 2


def test_fetch_games_wraps_client_errors(mock_chessdotcom_client):
    """Client failures should be surfaced with the fetcher's contextual message."""
    mock_chessdotcom_client.get_player_game_archives.side_effect = RuntimeError("offline")

    with pytest.raises(Exception, match="Error fetching games for hikaru: offline"):
        ChessComFetcher().fetch_games("hikaru", limit=1)
