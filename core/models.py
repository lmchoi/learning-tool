from dataclasses import dataclass

from pydantic import BaseModel


@dataclass
class UserProfile:
    experience_level: str


class Question(BaseModel):
    text: str


class EvaluationResult(BaseModel):
    score: int
    strengths: list[str]
    gaps: list[str]
    missing_points: list[str]
    suggested_addition: str
    follow_up_question: str
