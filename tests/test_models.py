import uuid

from core.models import Question


def test_question_auto_generates_valid_uuid() -> None:
    q = Question(text="x")
    uuid.UUID(q.question_id)  # raises ValueError if not a valid UUID


def test_question_ids_are_unique() -> None:
    q1 = Question(text="x")
    q2 = Question(text="x")
    assert q1.question_id != q2.question_id
