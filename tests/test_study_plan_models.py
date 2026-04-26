"""Tests for StudyPlan, ConceptMap, and StudySession ORM models."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.chess_analyzer.database.models import (
    ConceptMap,
    Pattern,
    StudyPlan,
    StudySession,
)


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Create tables selectively, skipping Embedding which uses PostgreSQL ARRAY
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
def sample_pattern(test_db):
    """Create a sample Pattern for testing foreign key relationships."""
    pattern = Pattern(
        pattern_name="Weak King Safety",
        weakness_type="tactical",
        frequency=5,
        game_ids=[1, 2, 3],
        position_features={"pattern": "exposed_king"},
        average_eval_loss=25.5,
        player_username="testplayer",
    )
    test_db.add(pattern)
    test_db.commit()
    test_db.refresh(pattern)
    return pattern


class TestStudyPlanModel:
    """Test cases for StudyPlan model."""

    def test_study_plan_creation(self, test_db, sample_pattern):
        """Test creating a StudyPlan with all required fields."""
        study_plan = StudyPlan(
            user_id="user123",
            weakness_id=sample_pattern.id,
            priority_score=8.5,
            status="active",
        )
        test_db.add(study_plan)
        test_db.commit()
        test_db.refresh(study_plan)

        assert study_plan.id is not None
        assert isinstance(study_plan.id, uuid.UUID)
        assert study_plan.user_id == "user123"
        assert study_plan.weakness_id == sample_pattern.id
        assert study_plan.priority_score == 8.5
        assert study_plan.status == "active"
        assert study_plan.marked_studied_at is None
        assert study_plan.created_at is not None
        assert study_plan.updated_at is not None

    def test_study_plan_marked_studied_at(self, test_db, sample_pattern):
        """Test updating marked_studied_at field."""
        study_plan = StudyPlan(
            user_id="user123",
            weakness_id=sample_pattern.id,
            priority_score=8.5,
            status="active",
        )
        test_db.add(study_plan)
        test_db.commit()

        assert study_plan.marked_studied_at is None

        # Mark as studied
        study_plan.marked_studied_at = datetime.now(UTC)
        test_db.commit()
        test_db.refresh(study_plan)

        assert study_plan.marked_studied_at is not None
        assert isinstance(study_plan.marked_studied_at, datetime)

    def test_study_plan_weakness_relationship(self, test_db, sample_pattern):
        """Test StudyPlan relationship to Pattern (weakness)."""
        study_plan = StudyPlan(
            user_id="user123",
            weakness_id=sample_pattern.id,
            priority_score=8.5,
            status="active",
        )
        test_db.add(study_plan)
        test_db.commit()
        test_db.refresh(study_plan)

        assert study_plan.weakness is not None
        assert study_plan.weakness.id == sample_pattern.id
        assert study_plan.weakness.pattern_name == "Weak King Safety"

    def test_study_plan_study_sessions_relationship(self, test_db, sample_pattern):
        """Test StudyPlan relationship to StudySession (one-to-many)."""
        study_plan = StudyPlan(
            user_id="user123",
            weakness_id=sample_pattern.id,
            priority_score=8.5,
            status="active",
        )
        test_db.add(study_plan)
        test_db.commit()
        test_db.refresh(study_plan)

        # Create study sessions
        session1 = StudySession(
            study_plan_id=study_plan.id,
            games_reviewed=[1, 2],
            engine_analysis_count=5,
        )
        session2 = StudySession(
            study_plan_id=study_plan.id,
            games_reviewed=[3, 4],
            engine_analysis_count=3,
        )
        test_db.add(session1)
        test_db.add(session2)
        test_db.commit()

        test_db.refresh(study_plan)
        assert len(study_plan.study_sessions) == 2
        assert session1 in study_plan.study_sessions
        assert session2 in study_plan.study_sessions

    def test_study_plan_user_id_index(self, test_db, sample_pattern):
        """Test that user_id field is indexed."""
        study_plan = StudyPlan(
            user_id="user123",
            weakness_id=sample_pattern.id,
            priority_score=8.5,
            status="active",
        )
        test_db.add(study_plan)
        test_db.commit()

        # Query by user_id to verify index
        result = test_db.query(StudyPlan).filter(StudyPlan.user_id == "user123").first()
        assert result is not None
        assert result.user_id == "user123"

    def test_study_plan_status_index(self, test_db, sample_pattern):
        """Test that status field is indexed."""
        study_plan = StudyPlan(
            user_id="user123",
            weakness_id=sample_pattern.id,
            priority_score=8.5,
            status="completed",
        )
        test_db.add(study_plan)
        test_db.commit()

        # Query by status to verify index
        result = test_db.query(StudyPlan).filter(StudyPlan.status == "completed").first()
        assert result is not None
        assert result.status == "completed"

    def test_study_plan_priority_index(self, test_db, sample_pattern):
        """Test that priority_score field is indexed."""
        study_plan = StudyPlan(
            user_id="user123",
            weakness_id=sample_pattern.id,
            priority_score=9.5,
            status="active",
        )
        test_db.add(study_plan)
        test_db.commit()

        # Query by priority_score to verify index
        result = test_db.query(StudyPlan).filter(StudyPlan.priority_score > 9.0).first()
        assert result is not None
        assert result.priority_score == 9.5


class TestConceptMapModel:
    """Test cases for ConceptMap model."""

    def test_concept_map_creation(self, test_db, sample_pattern):
        """Test creating a ConceptMap with all required fields."""
        concept_map = ConceptMap(
            weakness_id=sample_pattern.id,
            concept_type="tactic",
            concept_name="Pin",
        )
        test_db.add(concept_map)
        test_db.commit()
        test_db.refresh(concept_map)

        assert concept_map.id is not None
        assert isinstance(concept_map.id, uuid.UUID)
        assert concept_map.weakness_id == sample_pattern.id
        assert concept_map.concept_type == "tactic"
        assert concept_map.concept_name == "Pin"
        assert concept_map.created_at is not None

    def test_concept_map_weakness_foreign_key(self, test_db, sample_pattern):
        """Test ConceptMap foreign key to Pattern."""
        concept_map = ConceptMap(
            weakness_id=sample_pattern.id,
            concept_type="tactic",
            concept_name="Pin",
        )
        test_db.add(concept_map)
        test_db.commit()
        test_db.refresh(concept_map)

        result = test_db.query(ConceptMap).filter(
            ConceptMap.weakness_id == sample_pattern.id
        ).first()
        assert result is not None
        assert result.weakness_id == sample_pattern.id

    def test_concept_map_weakness_id_index(self, test_db, sample_pattern):
        """Test that weakness_id field is indexed."""
        concept_map = ConceptMap(
            weakness_id=sample_pattern.id,
            concept_type="tactic",
            concept_name="Pin",
        )
        test_db.add(concept_map)
        test_db.commit()

        # Query by weakness_id to verify index
        result = test_db.query(ConceptMap).filter(
            ConceptMap.weakness_id == sample_pattern.id
        ).first()
        assert result is not None

    def test_concept_map_concept_index(self, test_db, sample_pattern):
        """Test that concept_name field is indexed."""
        concept_map = ConceptMap(
            weakness_id=sample_pattern.id,
            concept_type="tactic",
            concept_name="Fork",
        )
        test_db.add(concept_map)
        test_db.commit()

        # Query by concept_name to verify index
        result = test_db.query(ConceptMap).filter(
            ConceptMap.concept_name == "Fork"
        ).first()
        assert result is not None
        assert result.concept_name == "Fork"

    def test_multiple_concepts_for_same_weakness(self, test_db, sample_pattern):
        """Test multiple ConceptMap entries for the same weakness."""
        concept1 = ConceptMap(
            weakness_id=sample_pattern.id,
            concept_type="tactic",
            concept_name="Pin",
        )
        concept2 = ConceptMap(
            weakness_id=sample_pattern.id,
            concept_type="strategy",
            concept_name="Centralization",
        )
        test_db.add(concept1)
        test_db.add(concept2)
        test_db.commit()

        results = test_db.query(ConceptMap).filter(
            ConceptMap.weakness_id == sample_pattern.id
        ).all()
        assert len(results) == 2


class TestStudySessionModel:
    """Test cases for StudySession model."""

    def test_study_session_creation(self, test_db, sample_pattern):
        """Test creating a StudySession with all required fields."""
        study_plan = StudyPlan(
            user_id="user123",
            weakness_id=sample_pattern.id,
            priority_score=8.5,
            status="active",
        )
        test_db.add(study_plan)
        test_db.commit()
        test_db.refresh(study_plan)

        study_session = StudySession(
            study_plan_id=study_plan.id,
            games_reviewed=[1, 2, 3],
            engine_analysis_count=10,
        )
        test_db.add(study_session)
        test_db.commit()
        test_db.refresh(study_session)

        assert study_session.id is not None
        assert isinstance(study_session.id, uuid.UUID)
        assert study_session.study_plan_id == study_plan.id
        assert study_session.games_reviewed == [1, 2, 3]
        assert study_session.engine_analysis_count == 10
        assert study_session.completed_at is None
        assert study_session.created_at is not None

    def test_study_session_completed_at(self, test_db, sample_pattern):
        """Test updating completed_at field."""
        study_plan = StudyPlan(
            user_id="user123",
            weakness_id=sample_pattern.id,
            priority_score=8.5,
            status="active",
        )
        test_db.add(study_plan)
        test_db.commit()
        test_db.refresh(study_plan)

        study_session = StudySession(
            study_plan_id=study_plan.id,
            games_reviewed=[1, 2],
            engine_analysis_count=5,
        )
        test_db.add(study_session)
        test_db.commit()

        assert study_session.completed_at is None

        # Mark as completed
        study_session.completed_at = datetime.now(UTC)
        test_db.commit()
        test_db.refresh(study_session)

        assert study_session.completed_at is not None
        assert isinstance(study_session.completed_at, datetime)

    def test_study_session_study_plan_relationship(self, test_db, sample_pattern):
        """Test StudySession relationship to StudyPlan (many-to-one)."""
        study_plan = StudyPlan(
            user_id="user123",
            weakness_id=sample_pattern.id,
            priority_score=8.5,
            status="active",
        )
        test_db.add(study_plan)
        test_db.commit()
        test_db.refresh(study_plan)

        study_session = StudySession(
            study_plan_id=study_plan.id,
            games_reviewed=[1, 2],
            engine_analysis_count=5,
        )
        test_db.add(study_session)
        test_db.commit()
        test_db.refresh(study_session)

        assert study_session.study_plan is not None
        assert study_session.study_plan.id == study_plan.id
        assert study_session.study_plan.user_id == "user123"

    def test_study_session_study_plan_id_index(self, test_db, sample_pattern):
        """Test that study_plan_id field is indexed."""
        study_plan = StudyPlan(
            user_id="user123",
            weakness_id=sample_pattern.id,
            priority_score=8.5,
            status="active",
        )
        test_db.add(study_plan)
        test_db.commit()
        test_db.refresh(study_plan)

        study_session = StudySession(
            study_plan_id=study_plan.id,
            games_reviewed=[1, 2],
            engine_analysis_count=5,
        )
        test_db.add(study_session)
        test_db.commit()

        # Query by study_plan_id to verify index
        result = test_db.query(StudySession).filter(
            StudySession.study_plan_id == study_plan.id
        ).first()
        assert result is not None
        assert result.study_plan_id == study_plan.id

    def test_empty_games_reviewed(self, test_db, sample_pattern):
        """Test StudySession with empty games_reviewed list."""
        study_plan = StudyPlan(
            user_id="user123",
            weakness_id=sample_pattern.id,
            priority_score=8.5,
            status="active",
        )
        test_db.add(study_plan)
        test_db.commit()
        test_db.refresh(study_plan)

        study_session = StudySession(
            study_plan_id=study_plan.id,
            games_reviewed=[],
            engine_analysis_count=0,
        )
        test_db.add(study_session)
        test_db.commit()
        test_db.refresh(study_session)

        assert study_session.games_reviewed == []
        assert study_session.engine_analysis_count == 0
