"""Concept mapper for mapping chess weaknesses to learning concepts."""

from typing import List, Dict


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

    def map_weakness(self, pattern) -> List[Dict]:
        """
        Map a pattern to chess concepts.

        Args:
            pattern: Pattern object with type, opening, features

        Returns:
            List of concept dicts: [{"type": "theory|opening|position_type", "name": "..."}]
        """
        concepts = []

        # 1. Map theory concepts based on pattern type
        if hasattr(pattern, 'type'):
            if pattern.type == "tactical":
                concepts.append({"type": "theory", "name": "tactics"})
            elif pattern.type == "positional":
                concepts.append({"type": "theory", "name": "strategy"})
                concepts.append({"type": "theory", "name": "pawn_structure"})
            elif pattern.type == "opening":
                concepts.append({"type": "theory", "name": "tempo"})

        # 2. Map opening concepts
        if hasattr(pattern, 'opening') and pattern.opening:
            opening_name = pattern.opening.lower().replace(" ", "_")
            if opening_name in self.opening_concepts:
                concepts.append({"type": "opening", "name": opening_name})
            else:
                concepts.append({"type": "opening", "name": "other"})

        # 3. Map position type concepts
        if hasattr(pattern, 'avg_cpl'):
            # Use CPL as indicator of endgame (high CPL = important phase)
            if pattern.avg_cpl > 200:
                concepts.append({"type": "position_type", "name": "middlegame"})
            else:
                concepts.append({"type": "position_type", "name": "endgame"})

        # Check for specific endgame types
        if hasattr(pattern, 'endgame_type') and pattern.endgame_type:
            endgame_name = pattern.endgame_type.lower().replace(" ", "_")
            if endgame_name in self.position_concepts:
                concepts.append({"type": "position_type", "name": endgame_name})

        # Remove duplicates while preserving order
        seen = set()
        unique_concepts = []
        for concept in concepts:
            key = (concept['type'], concept['name'])
            if key not in seen:
                seen.add(key)
                unique_concepts.append(concept)

        return unique_concepts
