from pydantic import BaseModel, Field


class QuestionResponse(BaseModel):
    text: str
    question_id: str


class EvaluateRequest(BaseModel):
    query: str = Field(description="RAG retrieval query — used to find relevant context chunks")
    question: str
    answer: str


class EvaluationResponse(BaseModel):
    score: int
    strengths: list[str]
    gaps: list[str]
    missing_points: list[str]
    suggested_addition: str | None
    follow_up_question: str


class AttemptRequest(BaseModel):
    context: str
    session_id: str
    question_id: str
    question: str
    answer: str
    evaluation: dict[str, object]
    score: int
    focus_area: str | None = None
