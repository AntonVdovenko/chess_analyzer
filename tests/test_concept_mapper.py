"""Tests for ConceptMapper class."""

from unittest.mock import Mock

from src.chess_analyzer.study_planning.concept_mapper import ConceptMapper


def test_concept_mapper_init():
    """Test ConceptMapper initializes with concept taxonomies."""
    mapper = ConceptMapper()
    assert hasattr(mapper, "theory_concepts")
    assert hasattr(mapper, "opening_concepts")
    assert hasattr(mapper, "position_concepts")
    assert len(mapper.theory_concepts) > 0
    assert len(mapper.opening_concepts) > 0
    assert len(mapper.position_concepts) > 0


def test_map_tactical_pattern():
    """Test mapping tactical weakness."""
    mapper = ConceptMapper()

    pattern = Mock()
    pattern.type = "tactical"
    pattern.opening = "sicilian_defense"
    pattern.avg_cpl = 300

    concepts = mapper.map_weakness(pattern)

    assert len(concepts) > 0
    # Should include a theory concept
    theory_concepts = [c for c in concepts if c["type"] == "theory"]
    assert len(theory_concepts) > 0
    # Should include opening
    opening_concepts = [c for c in concepts if c["type"] == "opening"]
    assert len(opening_concepts) > 0


def test_map_positional_pattern():
    """Test mapping positional weakness."""
    mapper = ConceptMapper()

    pattern = Mock()
    pattern.type = "positional"
    pattern.opening = "ruy_lopez"
    pattern.avg_cpl = 100

    concepts = mapper.map_weakness(pattern)

    assert len(concepts) > 0
    # Should have theory concept for positional
    assert any(c["type"] == "theory" for c in concepts)


def test_map_endgame_pattern():
    """Test mapping endgame weakness."""
    mapper = ConceptMapper()

    pattern = Mock()
    pattern.type = "positional"
    pattern.opening = None
    pattern.endgame_type = "rook_endgame"
    pattern.avg_cpl = 150

    concepts = mapper.map_weakness(pattern)

    # Should include position type
    position_concepts = [c for c in concepts if c["type"] == "position_type"]
    assert len(position_concepts) > 0


def test_remove_duplicates():
    """Test that duplicate concepts are removed while preserving order."""
    mapper = ConceptMapper()

    pattern = Mock()
    pattern.type = "tactical"
    pattern.opening = "sicilian_defense"
    pattern.avg_cpl = 300
    pattern.endgame_type = None

    concepts = mapper.map_weakness(pattern)

    # Convert to set to check for duplicates
    concept_keys = [(c["type"], c["name"]) for c in concepts]
    assert len(concept_keys) == len(set(concept_keys)), "Duplicate concepts found"


def test_missing_pattern_type():
    """Test handling of missing required type attribute."""
    mapper = ConceptMapper()

    pattern = Mock(spec=[])  # No attributes
    pattern.type = None  # Will fail hasattr check

    concepts = mapper.map_weakness(pattern)

    # Should return empty list when type is missing
    assert len(concepts) == 0


def test_missing_pattern_attributes():
    """Test graceful handling of missing optional attributes."""
    mapper = ConceptMapper()

    pattern = Mock(spec=["type"])  # Only has 'type' attribute
    pattern.type = "tactical"

    concepts = mapper.map_weakness(pattern)

    # Should still map theory concept despite missing optional attributes
    assert len(concepts) > 0
    theory_concepts = [c for c in concepts if c["type"] == "theory"]
    assert len(theory_concepts) > 0


def test_unknown_opening():
    """Test handling of unknown opening name."""
    mapper = ConceptMapper()

    pattern = Mock()
    pattern.type = "positional"
    pattern.opening = "unknown_opening_xyz"
    pattern.avg_cpl = 100

    concepts = mapper.map_weakness(pattern)

    # Should map to "other" for unknown opening
    opening_concepts = [c for c in concepts if c["type"] == "opening"]
    assert len(opening_concepts) == 1
    assert opening_concepts[0]["name"] == "other"


def test_edge_case_cpl_values():
    """Test boundary CPL values for phase detection."""
    mapper = ConceptMapper()

    # Test CPL at exact boundary (150)
    pattern_at_boundary = Mock()
    pattern_at_boundary.type = "positional"
    pattern_at_boundary.avg_cpl = 150
    pattern_at_boundary.endgame_type = None

    concepts = mapper.map_weakness(pattern_at_boundary)

    position_concepts = [c for c in concepts if c["type"] == "position_type"]
    assert len(position_concepts) == 1
    assert position_concepts[0]["name"] == "middlegame"  # >= 150 is middlegame


def test_cpl_boundary_below():
    """Test CPL just below boundary (149)."""
    mapper = ConceptMapper()

    pattern = Mock()
    pattern.type = "positional"
    pattern.avg_cpl = 149
    pattern.endgame_type = None

    concepts = mapper.map_weakness(pattern)

    position_concepts = [c for c in concepts if c["type"] == "position_type"]
    assert len(position_concepts) == 1
    assert position_concepts[0]["name"] == "endgame"  # < 150 is endgame


def test_none_avg_cpl():
    """Test handling of None avg_cpl value."""
    mapper = ConceptMapper()

    pattern = Mock()
    pattern.type = "positional"
    pattern.avg_cpl = None
    pattern.endgame_type = None

    concepts = mapper.map_weakness(pattern)

    # Should still map theory concepts but no position type
    theory_concepts = [c for c in concepts if c["type"] == "theory"]
    assert len(theory_concepts) > 0

    position_concepts = [c for c in concepts if c["type"] == "position_type"]
    assert len(position_concepts) == 0


def test_endgame_type_priority():
    """Test that endgame_type takes priority over CPL heuristic."""
    mapper = ConceptMapper()

    pattern = Mock()
    pattern.type = "positional"
    pattern.avg_cpl = 250  # Would indicate middlegame
    pattern.endgame_type = "rook_endgame"  # But this should take priority

    concepts = mapper.map_weakness(pattern)

    position_concepts = [c for c in concepts if c["type"] == "position_type"]
    # Should have rook_endgame, not middlegame
    assert any(c["name"] == "rook_endgame" for c in position_concepts)
    assert not any(c["name"] == "middlegame" for c in position_concepts)
