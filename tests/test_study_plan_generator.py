"""Tests for StudyPlanGenerator class."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.chess_analyzer.database.models import (
    ConceptMap,
    Pattern,
    StudyPlan,
)
from src.chess_analyzer.study_planning.study_plan_generator import StudyPlanGenerator


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    with engine.begin() as conn:
        # Create Pattern table first
        conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_name VARCHAR(200),
                weakness_type VARCHAR(50),
                frequency INTEGER,
                game_ids JSON,
                position_features JSON,
                average_eval_loss FLOAT,
                player_username VARCHAR(100),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create StudyPlan table
        conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS study_plans (
                id CHAR(36) PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                weakness_id INTEGER NOT NULL,
                priority_score FLOAT NOT NULL,
                status VARCHAR(50) NOT NULL,
                marked_studied_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (weakness_id) REFERENCES patterns(id)
            )
        """)

        # Create ConceptMap table
        conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS concept_maps (
                id CHAR(36) PRIMARY KEY,
                weakness_id INTEGER NOT NULL,
                concept_type VARCHAR(100) NOT NULL,
                concept_name VARCHAR(255) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (weakness_id) REFERENCES patterns(id)
            )
        """)

        # Create StudySession table
        conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS study_sessions (
                id CHAR(36) PRIMARY KEY,
                study_plan_id CHAR(36) NOT NULL,
                games_reviewed JSON DEFAULT '[]',
                engine_analysis_count INTEGER NOT NULL,
                completed_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (study_plan_id) REFERENCES study_plans(id)
            )
        """)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_patterns(test_db):
    """Create multiple patterns with varying frequencies."""
    patterns = [
        Pattern(
            pattern_name="Weak King Safety",
            weakness_type="tactical",
            frequency=10,
            game_ids=[1, 2, 3],
            position_features={"pattern": "exposed_king"},
            average_eval_loss=25.5,
            player_username="testplayer",
        ),
        Pattern(
            pattern_name="Poor Pawn Structure",
            weakness_type="positional",
            frequency=5,
            game_ids=[4, 5],
            position_features={"pattern": "damaged_pawns"},
            average_eval_loss=15.0,
            player_username="testplayer",
        ),
        Pattern(
            pattern_name="Tactical Blunders",
            weakness_type="tactical",
            frequency=8,
            game_ids=[6, 7, 8],
            position_features={"pattern": "missed_tactics"},
            average_eval_loss=50.0,
            player_username="testplayer",
        ),
    ]
    for pattern in patterns:
        test_db.add(pattern)
    test_db.commit()

    # Refresh to get IDs
    for pattern in patterns:
        test_db.refresh(pattern)

    return patterns


class TestStudyPlanGeneratorInit:
    """Test StudyPlanGenerator initialization."""

    def test_study_plan_generator_init(self, test_db):
        """Test StudyPlanGenerator initializes with db_session and ConceptMapper."""
        generator = StudyPlanGenerator(test_db)

        assert generator.db_session is test_db
        assert hasattr(generator, "concept_mapper")
        assert generator.concept_mapper is not None


class TestCalculatePriorityScores:
    """Test _calculate_priority_scores static method."""

    def test_calculate_priority_scores_basic(self, sample_patterns):
        """Test calculating priority scores from patterns."""
        scores = StudyPlanGenerator._calculate_priority_scores(sample_patterns)

        assert len(scores) == len(sample_patterns)
        assert all(0 <= score <= 10 for score in scores)

    def test_calculate_priority_scores_normalization(self, sample_patterns):
        """Test that highest frequency pattern gets highest score."""
        scores = StudyPlanGenerator._calculate_priority_scores(sample_patterns)

        # First pattern has frequency 10 (highest)
        # Second pattern has frequency 5
        # Third pattern has frequency 8
        assert scores[0] > scores[1]
        assert scores[0] > scores[2]

    def test_calculate_priority_scores_scale_to_1(self, sample_patterns):
        """Test that max score is 1.0."""
        scores = StudyPlanGenerator._calculate_priority_scores(sample_patterns)

        max_score = max(scores)
        assert max_score == 1.0

    def test_calculate_priority_scores_empty_list(self):
        """Test handling empty patterns list."""
        scores = StudyPlanGenerator._calculate_priority_scores([])
        assert scores == []

    def test_calculate_priority_scores_single_pattern(self):
        """Test with single pattern."""
        pattern = Pattern(
            pattern_name="Test",
            weakness_type="tactical",
            frequency=5,
            game_ids=[1],
            position_features={},
            average_eval_loss=10.0,
            player_username="test",
        )
        scores = StudyPlanGenerator._calculate_priority_scores([pattern])

        assert len(scores) == 1
        assert scores[0] == 1.0  # Single pattern gets max score (normalized to 0-1)


class TestCategorizeByPriority:
    """Test _categorize_by_priority static method."""

    def test_categorize_by_priority_high(self):
        """Test categorizing high priority scores."""
        category = StudyPlanGenerator._categorize_by_priority(0.85)
        assert category == "high"

    def test_categorize_by_priority_medium(self):
        """Test categorizing medium priority scores."""
        category = StudyPlanGenerator._categorize_by_priority(0.5)
        assert category == "medium"

    def test_categorize_by_priority_low(self):
        """Test categorizing low priority scores."""
        category = StudyPlanGenerator._categorize_by_priority(0.2)
        assert category == "low"

    def test_categorize_by_priority_boundary_high(self):
        """Test boundary between high and medium (0.7)."""
        category = StudyPlanGenerator._categorize_by_priority(0.7)
        assert category == "high"

    def test_categorize_by_priority_boundary_medium(self):
        """Test boundary between medium and low (0.35)."""
        category = StudyPlanGenerator._categorize_by_priority(0.35)
        assert category == "medium"


class TestGenerateStudyPlan:
    """Test generate_study_plan main method."""

    def test_generate_study_plan_creates_records(self, test_db, sample_patterns):
        """Test that generate_study_plan creates StudyPlan records."""
        generator = StudyPlanGenerator(test_db)
        result = generator.generate_study_plan("testplayer", game_limit=100)

        # Verify result contains expected fields
        assert result["username"] == "testplayer"
        assert result["total_weaknesses"] == len(sample_patterns)
        assert result["study_plans_created"] == len(sample_patterns)
        assert "priority_distribution" in result

        # Verify StudyPlan records were created
        study_plans = test_db.query(StudyPlan).filter(StudyPlan.user_id == "testplayer").all()
        assert len(study_plans) == len(sample_patterns)

    def test_generate_study_plan_priority_scores(self, test_db, sample_patterns):
        """Test that priority scores are assigned correctly."""
        generator = StudyPlanGenerator(test_db)
        generator.generate_study_plan("testplayer", game_limit=100)

        study_plans = test_db.query(StudyPlan).filter(StudyPlan.user_id == "testplayer").all()

        # Verify all study plans have priority scores in range [0, 10]
        for sp in study_plans:
            assert 0 <= sp.priority_score <= 10

    def test_generate_study_plan_creates_concept_maps(self, test_db, sample_patterns):
        """Test that ConceptMap records are created."""
        generator = StudyPlanGenerator(test_db)
        generator.generate_study_plan("testplayer", game_limit=100)

        concept_maps = test_db.query(ConceptMap).all()
        # Should have at least one concept map per pattern
        assert len(concept_maps) >= len(sample_patterns)

    def test_generate_study_plan_status_active(self, test_db, sample_patterns):
        """Test that all study plans are created with active status."""
        generator = StudyPlanGenerator(test_db)
        generator.generate_study_plan("testplayer", game_limit=100)

        study_plans = test_db.query(StudyPlan).filter(StudyPlan.user_id == "testplayer").all()

        for sp in study_plans:
            assert sp.status == "active"

    def test_generate_study_plan_with_different_users(self, test_db, sample_patterns):
        """Test generating study plans for different users."""
        generator = StudyPlanGenerator(test_db)

        # Add patterns for second user
        pattern2 = Pattern(
            pattern_name="Opening Mistakes",
            weakness_type="opening",
            frequency=3,
            game_ids=[9],
            position_features={},
            average_eval_loss=20.0,
            player_username="otherplayer",
        )
        test_db.add(pattern2)
        test_db.commit()

        # Generate for first user
        result1 = generator.generate_study_plan("testplayer", game_limit=100)
        # Generate for second user
        result2 = generator.generate_study_plan("otherplayer", game_limit=100)

        # Verify isolation
        assert result1["username"] == "testplayer"
        assert result2["username"] == "otherplayer"

        plans1 = test_db.query(StudyPlan).filter(StudyPlan.user_id == "testplayer").all()
        plans2 = test_db.query(StudyPlan).filter(StudyPlan.user_id == "otherplayer").all()

        assert len(plans1) == len(sample_patterns)
        assert len(plans2) == 1

    def test_generate_study_plan_no_patterns(self, test_db):
        """Test generating study plan when user has no patterns."""
        generator = StudyPlanGenerator(test_db)
        result = generator.generate_study_plan("noplayer", game_limit=100)

        assert result["username"] == "noplayer"
        assert result["total_weaknesses"] == 0
        assert result["study_plans_created"] == 0

    def test_generate_study_plan_priority_distribution(self, test_db, sample_patterns):
        """Test that priority_distribution is properly calculated."""
        generator = StudyPlanGenerator(test_db)
        result = generator.generate_study_plan("testplayer", game_limit=100)

        distribution = result["priority_distribution"]
        assert "high" in distribution or "medium" in distribution or "low" in distribution
        assert isinstance(distribution, dict)

    def test_generate_study_plan_with_patterns_with_mock_concept_mapper(
        self, test_db, sample_patterns
    ):
        """Test generate_study_plan with mocked concept mapper to verify it's called."""

        generator = StudyPlanGenerator(test_db)

        # Mock the concept_mapper.map_weakness to track calls
        original_map_weakness = generator.concept_mapper.map_weakness
        call_count = [0]

        def mock_map_weakness(pattern):
            call_count[0] += 1
            return original_map_weakness(pattern)

        generator.concept_mapper.map_weakness = mock_map_weakness

        generator.generate_study_plan("testplayer", game_limit=100)

        # Verify concept mapper was called for each pattern
        assert call_count[0] == len(sample_patterns)
