"""Study plan generator for creating personalized study plans from weakness patterns."""

import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from src.chess_analyzer.database.models import ConceptMap, Pattern, StudyPlan
from src.chess_analyzer.study_planning.concept_mapper import ConceptMapper

logger = logging.getLogger(__name__)


class PatternAdapter:
    """Adapter to convert Pattern ORM model to ConceptMapper interface."""

    def __init__(self, pattern: Pattern):
        """Initialize adapter with a Pattern ORM model.

        Args:
            pattern: Pattern ORM model
        """
        self.pattern = pattern

    @property
    def type(self) -> str:
        """Get pattern type from weakness_type."""
        return self.pattern.weakness_type

    @property
    def opening(self) -> str:
        """Get opening name (from features if available)."""
        if self.pattern.position_features and isinstance(
            self.pattern.position_features, dict
        ):
            return self.pattern.position_features.get("opening")
        return None

    @property
    def avg_cpl(self) -> float:
        """Get average centipawn loss."""
        return self.pattern.average_eval_loss

    @property
    def endgame_type(self) -> str:
        """Get endgame type (from features if available)."""
        if self.pattern.position_features and isinstance(
            self.pattern.position_features, dict
        ):
            return self.pattern.position_features.get("endgame_type")
        return None


class StudyPlanGenerator:
    """Generate study plans from weakness patterns with frequency-based prioritization."""

    def __init__(self, db_session: Session):
        """Initialize StudyPlanGenerator with database session and ConceptMapper.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db_session = db_session
        self.concept_mapper = ConceptMapper()

    def generate_study_plan(
        self, username: str, game_limit: int = 100
    ) -> Dict[str, Any]:
        """Generate a personalized study plan for a player.

        Retrieves all weakness patterns for a player, calculates priority scores
        based on frequency, creates StudyPlan and ConceptMap records in the database.

        Args:
            username: Chess.com username
            game_limit: Maximum games to consider (for future filtering)

        Returns:
            Dict with structure:
            {
                "username": str,
                "total_weaknesses": int,
                "study_plans_created": int,
                "priority_distribution": {
                    "high": int,
                    "medium": int,
                    "low": int
                }
            }
        """
        # Get all patterns for this user
        patterns = (
            self.db_session.query(Pattern)
            .filter(Pattern.player_username == username)
            .all()
        )

        if not patterns:
            return {
                "username": username,
                "total_weaknesses": 0,
                "study_plans_created": 0,
                "priority_distribution": {"high": 0, "medium": 0, "low": 0},
            }

        # Calculate priority scores
        priority_scores = self._calculate_priority_scores(patterns)

        # Track distribution
        distribution = {"high": 0, "medium": 0, "low": 0}
        study_plans_created = 0

        # Create StudyPlan and ConceptMap records for each pattern
        for pattern, score in zip(patterns, priority_scores):
            # Categorize by priority
            category = self._categorize_by_priority(score)
            distribution[category] += 1

            # Create StudyPlan record
            study_plan = StudyPlan(
                user_id=username,
                weakness_id=pattern.id,
                priority_score=score,
                status="active",
            )
            self.db_session.add(study_plan)

            # Map concepts for this pattern using adapter
            adapter = PatternAdapter(pattern)
            concepts = self.concept_mapper.map_weakness(adapter)

            # Create ConceptMap records
            for concept in concepts:
                concept_map = ConceptMap(
                    weakness_id=pattern.id,
                    concept_type=concept["type"],
                    concept_name=concept["name"],
                )
                self.db_session.add(concept_map)

            study_plans_created += 1

        # Batch commit all changes at once
        self.db_session.commit()

        return {
            "username": username,
            "total_weaknesses": len(patterns),
            "study_plans_created": study_plans_created,
            "priority_distribution": distribution,
        }

    @staticmethod
    def _calculate_priority_scores(patterns: List[Pattern]) -> List[float]:
        """Calculate priority scores for patterns based on frequency.

        Normalizes pattern frequencies to a 0-1 scale, with the highest
        frequency pattern receiving a score of 1.0.

        Args:
            patterns: List of Pattern objects

        Returns:
            List of priority scores (0-1) corresponding to patterns
        """
        if not patterns:
            return []

        # Find max frequency
        frequencies = [p.frequency for p in patterns]
        max_frequency = max(frequencies)

        if max_frequency == 0:
            # Handle edge case of all zero frequencies
            return [0.0] * len(patterns)

        # Normalize to 0-1 scale
        scores = [freq / max_frequency for freq in frequencies]
        return scores

    @staticmethod
    def _categorize_by_priority(score: float) -> str:
        """Categorize a priority score into high, medium, or low.

        Args:
            score: Priority score (0-1)

        Returns:
            Category string: "high", "medium", or "low"
        """
        if score >= 0.7:
            return "high"
        elif score >= 0.35:
            return "medium"
        else:
            return "low"
