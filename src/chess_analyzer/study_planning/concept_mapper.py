"""Concept mapper for mapping chess weaknesses to learning concepts."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ConceptMapper:
    """Map chess weaknesses to theory concepts, openings, and position types."""

    def __init__(self):
        """Initialize concept taxonomies."""
        # Theory concepts - what chess principles are violated
        self.theory_concepts = {
            "weak_squares": {
                "description": "Squares that opponent can exploit",
                "indicators": ["isolated", "backward", "hole"]
            },
            "piece_coordination": {
                "description": "Pieces not working together",
                "indicators": ["uncoordinated", "passive"]
            },
            "pawn_structure": {
                "description": "Weak pawn formation",
                "indicators": ["damaged", "weak_pawns"]
            },
            "king_safety": {
                "description": "Exposed king position",
                "indicators": ["exposed", "uncastled"]
            },
            "tempo": {
                "description": "Time advantage loss",
                "indicators": ["slow", "wasteful_moves"]
            },
            "material_balance": {
                "description": "Piece value imbalance",
                "indicators": ["material_loss"]
            },
            "tactics": {
                "description": "Tactical motifs (pins, forks, etc)",
                "indicators": ["tactical", "blunder", "hanging"]
            },
            "strategy": {
                "description": "Strategic positioning",
                "indicators": ["positional", "maneuvering"]
            }
        }

        # Opening concepts
        self.opening_concepts = {
            "sicilian_defense": "1.e4 c5",
            "ruy_lopez": "1.e4 e5 2.Nf3 Nc6 3.Bb5",
            "french_defense": "1.e4 e6",
            "caro_kann": "1.e4 c6",
            "italian_game": "1.e4 e5 2.Nf3 Nc6 3.Bc4",
            "english_opening": "1.c4",
            "queens_gambit": "1.d4 d5 2.c4",
            "other": "Other openings"
        }

        # Position type concepts
        self.position_concepts = {
            "opening": {"moves": (1, 12), "description": "Opening phase"},
            "middlegame": {"moves": (13, 35), "description": "Middlegame phase"},
            "endgame": {"moves": (36, 200), "description": "Endgame phase"},
            "rook_endgame": {"description": "Rook endgame"},
            "opposite_bishops": {"description": "Opposite colored bishops"},
            "passed_pawns": {"description": "Passed pawn positions"},
            "pawn_endgame": {"description": "Pawn-only endgame"}
        }

    def map_weakness(self, pattern: Any) -> list[dict]:
        """
        Map a chess weakness pattern to relevant learning concepts.

        Maps a pattern object to theory concepts, opening concepts, and position type
        concepts based on the pattern's attributes. Validates required attributes and
        gracefully handles missing data.

        Expected Pattern Interface:
            - type (str, required): Pattern type - "tactical", "positional", or "opening"
            - opening (str, optional): Opening name (e.g., "sicilian_defense")
            - avg_cpl (float, optional): Average centipawn loss (0-300+)
            - endgame_type (str, optional): Specific endgame type (e.g., "rook_endgame")

        Heuristic for Phase Detection:
            Uses endgame_type first (most reliable indicator). Falls back to avg_cpl:
            - avg_cpl < 150: Simpler position (endgame)
            - avg_cpl >= 150: Complex position (middlegame)
            Lower CPL indicates player made fewer significant errors = simpler position.

        Args:
            pattern (Any): Pattern object with optional attributes listed above

        Returns:
            List[Dict]: Concept dicts with structure:
                [{"type": "theory|opening|position_type", "name": "concept_name"}]
                Duplicates removed, order preserved.

        Example:
            >>> mapper = ConceptMapper()
            >>> pattern = Mock(type="tactical", opening="sicilian_defense", avg_cpl=250)
            >>> concepts = mapper.map_weakness(pattern)
            >>> # Returns: [
            >>> #   {"type": "theory", "name": "tactics"},
            >>> #   {"type": "opening", "name": "sicilian_defense"},
            >>> #   {"type": "position_type", "name": "middlegame"}
            >>> # ]
        """
        concepts = []

        # Validate pattern has required attributes
        if not hasattr(pattern, 'type'):
            logger.warning("Pattern missing required 'type' attribute")
            return []

        # 1. Map theory concepts based on pattern type
        if pattern.type == "tactical":
            concepts.append({"type": "theory", "name": "tactics"})
        elif pattern.type == "positional":
            concepts.append({"type": "theory", "name": "strategy"})
            concepts.append({"type": "theory", "name": "pawn_structure"})
        elif pattern.type == "opening":
            concepts.append({"type": "theory", "name": "tempo"})
        else:
            logger.warning(f"Unknown pattern type: {pattern.type}")

        # 2. Map opening concepts
        if hasattr(pattern, 'opening') and pattern.opening:
            opening_name = pattern.opening.lower().replace(" ", "_")
            if opening_name in self.opening_concepts:
                concepts.append({"type": "opening", "name": opening_name})
            else:
                logger.warning(f"Unknown opening encountered: {opening_name}")
                concepts.append({"type": "opening", "name": "other"})
        elif hasattr(pattern, 'opening'):
            logger.warning("Pattern has 'opening' attribute but it is None or empty")

        # 3. Map position type concepts based on endgame_type first (most reliable)
        # Then use CPL heuristic as fallback
        endgame_mapped = False
        if hasattr(pattern, 'endgame_type') and pattern.endgame_type:
            endgame_name = pattern.endgame_type.lower().replace(" ", "_")
            if endgame_name in self.position_concepts:
                concepts.append({"type": "position_type", "name": endgame_name})
                endgame_mapped = True
            else:
                logger.warning(f"Unknown endgame_type: {pattern.endgame_type}")

        # Use CPL as fallback if no specific endgame type was found
        if not endgame_mapped and hasattr(pattern, 'avg_cpl'):
            if pattern.avg_cpl is not None:
                # Heuristic: avg_cpl < 150 indicates simpler position (endgame)
                # Lower CPL = fewer significant errors = simpler position
                if pattern.avg_cpl < 150:
                    concepts.append({"type": "position_type", "name": "endgame"})
                else:
                    concepts.append({"type": "position_type", "name": "middlegame"})
            else:
                logger.warning("Pattern has 'avg_cpl' attribute but it is None")
        elif not endgame_mapped:
            logger.warning("Pattern missing 'avg_cpl' attribute for position type detection")

        # Remove duplicates while preserving order
        seen = set()
        unique_concepts = []
        for concept in concepts:
            key = (concept['type'], concept['name'])
            if key not in seen:
                seen.add(key)
                unique_concepts.append(concept)

        return unique_concepts
