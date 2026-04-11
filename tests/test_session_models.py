from learning_tool.core.session.models import QuestionAttempt, SessionRecord


def test_question_attempt_fields() -> None:
    attempt = QuestionAttempt(
        session_id="s1",
        question_text="What is X?",
        answer_text="It is Y.",
        score=8,
        timestamp="2026-03-21T10:00:00",
    )
    assert attempt.session_id == "s1"
    assert attempt.question_text == "What is X?"
    assert attempt.answer_text == "It is Y."
    assert attempt.score == 8
    assert attempt.timestamp == "2026-03-21T10:00:00"


def test_question_attempt_score_can_be_none() -> None:
    attempt = QuestionAttempt(
        session_id="s1",
        question_text="What is X?",
        answer_text="It is Y.",
        score=None,
        timestamp="2026-04-11T10:00:00",
    )
    assert attempt.score is None


def test_session_record_fields() -> None:
    attempt = QuestionAttempt(
        session_id="s1",
        question_text="What is X?",
        answer_text="It is Y.",
        score=8,
        timestamp="2026-03-21T10:00:00",
    )
    record = SessionRecord(
        session_id="s1",
        context="my-context",
        started_at="2026-03-21T09:00:00",
        attempts=[attempt],
    )
    assert record.session_id == "s1"
    assert record.context == "my-context"
    assert record.started_at == "2026-03-21T09:00:00"
    assert len(record.attempts) == 1
    assert record.attempts[0] is attempt
