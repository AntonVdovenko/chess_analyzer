"""Tests for Phase 3 Study Plan REST API endpoints."""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.chess_analyzer.main import app
from src.chess_analyzer.database.models import (
    Base,
    ConceptMap,
    Game,
    Pattern,
    Position,
    StudyPlan,
    StudySession,
)
from src.chess_analyzer.database.session import get_db


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    with engine.begin() as conn:
        # Create Game table
        conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(100),
                opponent_username VARCHAR(100),
                opponent_rating INTEGER,
                time_control VARCHAR(50),
                result VARCHAR(10),
                date DATETIME,
                pgn TEXT,
                white_elo INTEGER,
                black_elo INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create Position table
        conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                move_number INTEGER,
                fen VARCHAR(200),
                player_move VARCHAR(10),
                engine_best_move VARCHAR(10),
                evaluation_loss FLOAT,
                evaluation_before FLOAT,
                evaluation_after FLOAT,
                is_opening BOOLEAN DEFAULT 0,
                is_middlegame BOOLEAN DEFAULT 0,
                is_endgame BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES games(id)
            )
        """)

        # Create Pattern table
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
def client(test_db):
    """Create FastAPI test client with test database."""
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_patterns(test_db):
    """Create sample patterns for testing."""
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
    ]
    for pattern in patterns:
        test_db.add(pattern)
    test_db.commit()

    for pattern in patterns:
        test_db.refresh(pattern)

    return patterns


@pytest.fixture
def sample_study_plans(test_db, sample_patterns):
    """Create sample study plans for testing."""
    study_plans = [
        StudyPlan(
            user_id="testplayer",
            weakness_id=sample_patterns[0].id,
            priority_score=8.5,
            status="active",
        ),
        StudyPlan(
            user_id="testplayer",
            weakness_id=sample_patterns[1].id,
            priority_score=5.0,
            status="active",
        ),
    ]
    for plan in study_plans:
        test_db.add(plan)
    test_db.commit()

    for plan in study_plans:
        test_db.refresh(plan)

    return study_plans


@pytest.fixture
def sample_concepts(test_db, sample_patterns):
    """Create sample concept maps for testing."""
    concepts = [
        ConceptMap(
            weakness_id=sample_patterns[0].id,
            concept_type="theory",
            concept_name="tactics",
        ),
        ConceptMap(
            weakness_id=sample_patterns[0].id,
            concept_type="position_type",
            concept_name="middlegame",
        ),
    ]
    for concept in concepts:
        test_db.add(concept)
    test_db.commit()

    return concepts


class TestGenerateStudyPlanEndpoint:
    """Test POST /api/study-plan/generate endpoint."""

    def test_generate_study_plan_valid_request(self, client, sample_patterns):
        """Test generating study plan with valid request."""
        response = client.post(
            "/api/study-plan/generate",
            json={"username": "testplayer", "game_limit": 100},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testplayer"
        assert data["total_weaknesses"] == 2
        assert data["study_plans_created"] == 2

    def test_generate_study_plan_with_default_game_limit(self, client, sample_patterns):
        """Test generating study plan with default game_limit."""
        response = client.post(
            "/api/study-plan/generate",
            json={"username": "testplayer"},
        )
        assert response.status_code == 200
        assert response.json()["username"] == "testplayer"

    def test_generate_study_plan_no_patterns(self, client):
        """Test generating study plan for user with no patterns."""
        response = client.post(
            "/api/study-plan/generate",
            json={"username": "noplayer"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_weaknesses"] == 0
        assert data["study_plans_created"] == 0

    def test_generate_study_plan_missing_username(self, client):
        """Test error when username is missing."""
        response = client.post(
            "/api/study-plan/generate",
            json={"game_limit": 100},
        )
        assert response.status_code == 422


class TestListStudyPlansEndpoint:
    """Test GET /api/study-plan endpoint."""

    def test_list_study_plans_for_user(self, client, sample_study_plans):
        """Test listing study plans for a user."""
        response = client.get("/api/study-plan?user_id=testplayer")
        assert response.status_code == 200
        plans = response.json()
        assert len(plans) == 2

    def test_list_study_plans_filter_by_status(self, client, test_db, sample_study_plans):
        """Test listing study plans filtered by status."""
        # Update one plan to completed
        test_db.query(StudyPlan).filter(
            StudyPlan.id == sample_study_plans[1].id
        ).update({"status": "completed"})
        test_db.commit()

        response = client.get("/api/study-plan?user_id=testplayer&status=active")
        assert response.status_code == 200
        plans = response.json()
        assert len(plans) == 1
        assert plans[0]["status"] == "active"

    def test_list_study_plans_empty(self, client):
        """Test listing study plans with no results."""
        response = client.get("/api/study-plan?user_id=nosuchuser")
        assert response.status_code == 200
        plans = response.json()
        assert len(plans) == 0

    def test_list_study_plans_with_sorting(self, client, sample_study_plans):
        """Test listing study plans with sorting."""
        response = client.get(
            "/api/study-plan?user_id=testplayer&sort_by=priority_score"
        )
        assert response.status_code == 200
        plans = response.json()
        assert len(plans) == 2


class TestMarkStudiedEndpoint:
    """Test PATCH /api/study-plan/{id}/mark-studied endpoint."""

    def test_mark_studied_success(self, client, sample_study_plans):
        """Test marking a study plan as studied."""
        plan_id = str(sample_study_plans[0].id)
        response = client.patch(f"/api/study-plan/{plan_id}/mark-studied", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == plan_id
        assert data["status"] == "completed"
        assert data["marked_studied_at"] is not None

    def test_mark_studied_not_found(self, client):
        """Test marking non-existent study plan."""
        fake_id = str(uuid.uuid4())
        response = client.patch(f"/api/study-plan/{fake_id}/mark-studied", json={})
        assert response.status_code == 404

    def test_mark_studied_twice(self, client, sample_study_plans):
        """Test marking same plan as studied twice."""
        plan_id = str(sample_study_plans[0].id)
        response1 = client.patch(f"/api/study-plan/{plan_id}/mark-studied", json={})
        assert response1.status_code == 200

        response2 = client.patch(f"/api/study-plan/{plan_id}/mark-studied", json={})
        assert response2.status_code == 200


class TestProgressEndpoint:
    """Test GET /api/study-plan/progress endpoint."""

    def test_get_study_progress(self, client, sample_study_plans):
        """Test getting study progress for a user."""
        response = client.get("/api/study-plan/progress?user_id=testplayer")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "testplayer"
        assert data["total_plans"] == 2
        assert data["active_plans"] == 2
        assert data["completed_plans"] == 0

    def test_get_study_progress_no_plans(self, client):
        """Test getting progress for user with no plans."""
        response = client.get("/api/study-plan/progress?user_id=nosuchuser")
        assert response.status_code == 200
        data = response.json()
        assert data["total_plans"] == 0

    def test_get_study_progress_completion_rate(self, client, test_db, sample_study_plans):
        """Test completion rate calculation."""
        # Mark one plan as completed
        test_db.query(StudyPlan).filter(
            StudyPlan.id == sample_study_plans[1].id
        ).update({"status": "completed", "marked_studied_at": datetime.now(timezone.utc)})
        test_db.commit()

        response = client.get("/api/study-plan/progress?user_id=testplayer")
        assert response.status_code == 200
        data = response.json()
        assert data["completed_plans"] == 1
        assert data["completion_rate"] == 50.0


class TestConceptsEndpoint:
    """Test GET /api/study-plan/concepts endpoint."""

    def test_get_concepts_for_study_plan(self, client, test_db, sample_study_plans, sample_concepts):
        """Test getting concepts for a study plan."""
        plan_id = str(sample_study_plans[0].id)
        response = client.get(f"/api/study-plan/{plan_id}/concepts")
        assert response.status_code == 200
        data = response.json()
        assert "concepts" in data
        assert len(data["concepts"]) >= 2

    def test_get_concepts_not_found(self, client):
        """Test getting concepts for non-existent plan."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/study-plan/{fake_id}/concepts")
        assert response.status_code == 404

    def test_get_concepts_structure(self, client, sample_study_plans, sample_concepts):
        """Test concept response structure."""
        plan_id = str(sample_study_plans[0].id)
        response = client.get(f"/api/study-plan/{plan_id}/concepts")
        assert response.status_code == 200
        data = response.json()
        assert "concepts" in data
        for concept in data["concepts"]:
            assert "type" in concept
            assert "name" in concept


class TestGamesEndpoint:
    """Test GET /api/study-plan/{id}/games endpoint."""

    def test_get_games_for_study_plan(self, client, test_db, sample_patterns, sample_study_plans):
        """Test getting games for a study plan."""
        plan_id = str(sample_study_plans[0].id)

        # Create sample games
        game = Game(
            username="testplayer",
            opponent_username="opponent",
            time_control="blitz",
            result="loss",
            date=datetime.now(timezone.utc),
            pgn="1. e4 e5",
        )
        test_db.add(game)
        test_db.commit()
        test_db.refresh(game)

        response = client.get(f"/api/study-plan/{plan_id}/games")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_games_not_found(self, client):
        """Test getting games for non-existent plan."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/study-plan/{fake_id}/games")
        assert response.status_code == 404

    def test_get_games_empty(self, client, sample_study_plans):
        """Test getting games when no games exist."""
        plan_id = str(sample_study_plans[0].id)
        response = client.get(f"/api/study-plan/{plan_id}/games")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
