"""Tests for Phase 3 Study Plan API schemas."""

import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from src.chess_analyzer.api.schemas import (
    ConceptListResponse,
    MarkStudiedRequest,
    MarkStudiedResponse,
    StudyGameDetailResponse,
    StudyPlanGenerateRequest,
    StudyPlanGenerateResponse,
    StudyPlanResponse,
    StudyProgressResponse,
)


class TestStudyPlanGenerateRequest:
    """Test StudyPlanGenerateRequest schema."""

    def test_study_plan_generate_request_valid(self):
        """Test creating valid StudyPlanGenerateRequest."""
        request = StudyPlanGenerateRequest(
            username="testplayer",
            game_limit=100,
        )
        assert request.username == "testplayer"
        assert request.game_limit == 100

    def test_study_plan_generate_request_with_default_game_limit(self):
        """Test StudyPlanGenerateRequest with default game_limit."""
        request = StudyPlanGenerateRequest(username="testplayer")
        assert request.username == "testplayer"
        assert request.game_limit == 100

    def test_study_plan_generate_request_missing_username(self):
        """Test StudyPlanGenerateRequest raises error when username missing."""
        with pytest.raises(ValidationError):
            StudyPlanGenerateRequest(game_limit=100)

    def test_study_plan_generate_request_negative_game_limit(self):
        """Test StudyPlanGenerateRequest validates game_limit >= 1."""
        with pytest.raises(ValidationError):
            StudyPlanGenerateRequest(username="test", game_limit=0)


class TestStudyPlanGenerateResponse:
    """Test StudyPlanGenerateResponse schema."""

    def test_study_plan_generate_response_valid(self):
        """Test creating valid StudyPlanGenerateResponse."""
        response = StudyPlanGenerateResponse(
            username="testplayer",
            total_weaknesses=5,
            study_plans_created=5,
            priority_distribution={"high": 2, "medium": 2, "low": 1},
        )
        assert response.username == "testplayer"
        assert response.total_weaknesses == 5
        assert response.study_plans_created == 5
        assert response.priority_distribution == {"high": 2, "medium": 2, "low": 1}

    def test_study_plan_generate_response_zero_weaknesses(self):
        """Test StudyPlanGenerateResponse with zero weaknesses."""
        response = StudyPlanGenerateResponse(
            username="noplayer",
            total_weaknesses=0,
            study_plans_created=0,
            priority_distribution={"high": 0, "medium": 0, "low": 0},
        )
        assert response.total_weaknesses == 0
        assert response.study_plans_created == 0


class TestStudyPlanResponse:
    """Test StudyPlanResponse schema."""

    def test_study_plan_response_valid(self):
        """Test creating valid StudyPlanResponse."""
        plan_id = str(uuid.uuid4())
        response = StudyPlanResponse(
            id=plan_id,
            user_id="user123",
            weakness_id=1,
            priority_score=8.5,
            status="active",
            concept_count=3,
            created_at=datetime.now(),
        )
        assert response.id == plan_id
        assert response.user_id == "user123"
        assert response.weakness_id == 1
        assert response.priority_score == 8.5
        assert response.status == "active"
        assert response.concept_count == 3

    def test_study_plan_response_all_statuses(self):
        """Test StudyPlanResponse with different statuses."""
        plan_id = str(uuid.uuid4())
        for status in ["active", "completed", "paused"]:
            response = StudyPlanResponse(
                id=plan_id,
                user_id="user123",
                weakness_id=1,
                priority_score=5.0,
                status=status,
                concept_count=2,
                created_at=datetime.now(),
            )
            assert response.status == status

    def test_study_plan_response_priority_score_range(self):
        """Test StudyPlanResponse with priority scores in valid range."""
        plan_id = str(uuid.uuid4())
        response = StudyPlanResponse(
            id=plan_id,
            user_id="user123",
            weakness_id=1,
            priority_score=10.0,
            status="active",
            concept_count=1,
            created_at=datetime.now(),
        )
        assert 0 <= response.priority_score <= 10


class TestMarkStudiedRequest:
    """Test MarkStudiedRequest schema."""

    def test_mark_studied_request_valid(self):
        """Test creating valid MarkStudiedRequest."""
        request = MarkStudiedRequest()
        # Should create empty request for mark studied
        assert request is not None

    def test_mark_studied_request_empty(self):
        """Test MarkStudiedRequest is empty body."""
        request = MarkStudiedRequest()
        # No required fields
        assert hasattr(request, "__dict__")


class TestMarkStudiedResponse:
    """Test MarkStudiedResponse schema."""

    def test_mark_studied_response_valid(self):
        """Test creating valid MarkStudiedResponse."""
        plan_id = str(uuid.uuid4())
        response = MarkStudiedResponse(
            id=plan_id,
            status="completed",
            marked_studied_at=datetime.now(),
        )
        assert response.id == plan_id
        assert response.status == "completed"
        assert response.marked_studied_at is not None

    def test_mark_studied_response_datetime(self):
        """Test MarkStudiedResponse stores datetime correctly."""
        plan_id = str(uuid.uuid4())
        now = datetime.now()
        response = MarkStudiedResponse(
            id=plan_id,
            status="completed",
            marked_studied_at=now,
        )
        assert response.marked_studied_at == now


class TestConceptListResponse:
    """Test ConceptListResponse schema."""

    def test_concept_list_response_valid(self):
        """Test creating valid ConceptListResponse."""
        response = ConceptListResponse(
            concepts=[
                {"type": "theory", "name": "tactics"},
                {"type": "opening", "name": "sicilian_defense"},
                {"type": "position_type", "name": "middlegame"},
            ]
        )
        assert len(response.concepts) == 3
        assert response.concepts[0]["name"] == "tactics"

    def test_concept_list_response_empty(self):
        """Test ConceptListResponse with empty concepts."""
        response = ConceptListResponse(concepts=[])
        assert len(response.concepts) == 0

    def test_concept_list_response_concept_structure(self):
        """Test ConceptListResponse concepts have required fields."""
        response = ConceptListResponse(
            concepts=[
                {"type": "theory", "name": "strategy"},
            ]
        )
        concept = response.concepts[0]
        assert "type" in concept
        assert "name" in concept


class TestStudyProgressResponse:
    """Test StudyProgressResponse schema."""

    def test_study_progress_response_valid(self):
        """Test creating valid StudyProgressResponse."""
        response = StudyProgressResponse(
            user_id="user123",
            total_plans=5,
            active_plans=3,
            completed_plans=2,
            completion_rate=40.0,
        )
        assert response.user_id == "user123"
        assert response.total_plans == 5
        assert response.active_plans == 3
        assert response.completed_plans == 2
        assert response.completion_rate == 40.0

    def test_study_progress_response_zero_plans(self):
        """Test StudyProgressResponse with zero plans."""
        response = StudyProgressResponse(
            user_id="user123",
            total_plans=0,
            active_plans=0,
            completed_plans=0,
            completion_rate=0.0,
        )
        assert response.total_plans == 0
        assert response.completion_rate == 0.0

    def test_study_progress_response_completion_rate(self):
        """Test StudyProgressResponse completion rate is percentage."""
        response = StudyProgressResponse(
            user_id="user123",
            total_plans=10,
            active_plans=6,
            completed_plans=4,
            completion_rate=40.0,
        )
        assert response.completion_rate == 40.0
        assert 0 <= response.completion_rate <= 100


class TestStudyGameDetailResponse:
    """Test StudyGameDetailResponse schema."""

    def test_study_game_detail_response_valid(self):
        """Test creating valid StudyGameDetailResponse."""
        response = StudyGameDetailResponse(
            game_id=1,
            study_plan_id=str(uuid.uuid4()),
            weakness_id=1,
            result="loss",
            accuracy=75.5,
            eval_loss=25.3,
            position_fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        )
        assert response.game_id == 1
        assert response.result == "loss"
        assert response.accuracy == 75.5
        assert response.eval_loss == 25.3

    def test_study_game_detail_response_all_results(self):
        """Test StudyGameDetailResponse with different results."""
        plan_id = str(uuid.uuid4())
        for result in ["win", "loss", "draw"]:
            response = StudyGameDetailResponse(
                game_id=1,
                study_plan_id=plan_id,
                weakness_id=1,
                result=result,
                accuracy=80.0,
                eval_loss=15.0,
                position_fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            )
            assert response.result == result

    def test_study_game_detail_response_accuracy_range(self):
        """Test StudyGameDetailResponse accuracy in valid range."""
        response = StudyGameDetailResponse(
            game_id=1,
            study_plan_id=str(uuid.uuid4()),
            weakness_id=1,
            result="win",
            accuracy=95.5,
            eval_loss=5.0,
            position_fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        )
        assert 0 <= response.accuracy <= 100
