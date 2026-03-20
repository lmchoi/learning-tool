from pydantic import BaseModel, Field


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
