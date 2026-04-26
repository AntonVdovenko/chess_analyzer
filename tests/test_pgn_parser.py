from src.chess_analyzer.pgn_parser import PGNParser


def test_parse_pgn_returns_moves():
    """Test that parse_pgn extracts moves from PGN."""
    parser = PGNParser()
    pgn_string = """[Event "Casual Game"]
[Site "https://www.chess.com"]
[White "Player1"]
[Black "Player2"]

1. f3 e5 2. g4 Qh4# 0-1"""

    result = parser.parse_pgn(pgn_string)

    assert 'moves' in result
    assert len(result['moves']) > 0
    assert all('move' in m for m in result['moves'])
    assert all('fen' in m for m in result['moves'])


def test_parse_pgn_extracts_metadata():
    """Test that parse_pgn extracts game metadata."""
    parser = PGNParser()
    pgn_string = """[Event "Casual Game"]
[White "Player1"]
[Black "Player2"]
[Result "0-1"]

1. e4 c5 0-1"""

    result = parser.parse_pgn(pgn_string)

    assert result['white'] == "Player1"
    assert result['black'] == "Player2"
    assert result['result'] == "0-1"
