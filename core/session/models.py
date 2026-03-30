from dataclasses import dataclass


@dataclass
class QuestionAttempt:
    session_id: str
    question_text: str
    answer_text: str
    score: int
    timestamp: str
    question_id: str | None = None
    result_json: str | None = None
    attempt_id: int | None = None
    focus_area: str | None = None


@dataclass
class SessionRecord:
    session_id: str
    context: str
    started_at: str
    attempts: list[QuestionAttempt]
