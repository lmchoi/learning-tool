from pydantic import BaseModel, Field

from learning_tool.core.models import EvaluationResult


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
    evaluation: EvaluationResult
    score: int
    focus_area: str | None = None


class FocusAreaRequest(BaseModel):
    name: str
    questions: list[str]


class DraftRequest(BaseModel):
    goal: str
    focus_areas: list[FocusAreaRequest]


class DraftResponse(BaseModel):
    draft_id: str
    review_url: str
