import uuid

import pytest
from pydantic import ValidationError

from learning_tool.core.models import ContextMetadata, EvaluationResult, Question


def test_question_auto_generates_valid_uuid() -> None:
    q = Question(text="x")
    uuid.UUID(q.question_id)  # raises ValueError if not a valid UUID


def test_question_ids_are_unique() -> None:
    q1 = Question(text="x")
    q2 = Question(text="x")
    assert q1.question_id != q2.question_id


def test_context_metadata_rejects_empty_goal() -> None:
    with pytest.raises(ValidationError):
        ContextMetadata(goal="", focus_areas=[])


def test_evaluation_result_coerces_string_strengths_to_list() -> None:
    result = EvaluationResult(
        score=7,
        strengths="Good structure.",  # type: ignore[arg-type]
        gaps=[],
        missing_points=[],
        suggested_addition=None,
        follow_up_question="What else?",
    )
    assert result.strengths == ["Good structure."]


def test_evaluation_result_coerces_string_gaps_to_list() -> None:
    result = EvaluationResult(
        score=5,
        strengths=[],
        gaps="Missed key detail.",  # type: ignore[arg-type]
        missing_points=[],
        suggested_addition=None,
        follow_up_question="Can you elaborate?",
    )
    assert result.gaps == ["Missed key detail."]


def test_evaluation_result_coerces_string_missing_points_to_list() -> None:
    result = EvaluationResult(
        score=4,
        strengths=[],
        gaps=[],
        missing_points="Definition omitted.",  # type: ignore[arg-type]
        suggested_addition=None,
        follow_up_question="What did you miss?",
    )
    assert result.missing_points == ["Definition omitted."]


def test_evaluation_result_coerces_empty_string_to_empty_list() -> None:
    result = EvaluationResult(
        score=6,
        strengths="",  # type: ignore[arg-type]
        gaps="",  # type: ignore[arg-type]
        missing_points="",  # type: ignore[arg-type]
        suggested_addition=None,
        follow_up_question="Anything else?",
    )
    assert result.strengths == []
    assert result.gaps == []
    assert result.missing_points == []
