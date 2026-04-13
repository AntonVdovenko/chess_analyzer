"""Tests for ConceptMapper class."""

import pytest
from src.chess_analyzer.study_planning.concept_mapper import ConceptMapper
from unittest.mock import Mock


def test_concept_mapper_init():
    """Test ConceptMapper initializes with concept taxonomies."""
    mapper = ConceptMapper()
    assert hasattr(mapper, 'theory_concepts')
    assert hasattr(mapper, 'opening_concepts')
    assert hasattr(mapper, 'position_concepts')
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
    theory_concepts = [c for c in concepts if c['type'] == 'theory']
    assert len(theory_concepts) > 0
    # Should include opening
    opening_concepts = [c for c in concepts if c['type'] == 'opening']
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
    assert any(c['type'] == 'theory' for c in concepts)


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
    position_concepts = [c for c in concepts if c['type'] == 'position_type']
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
    concept_keys = [(c['type'], c['name']) for c in concepts]
    assert len(concept_keys) == len(set(concept_keys)), "Duplicate concepts found"
