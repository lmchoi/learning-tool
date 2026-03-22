from dataclasses import dataclass
from typing import Annotated

from pydantic import BaseModel, Field


@dataclass
class UserProfile:
    experience_level: str


class ContextMetadata(BaseModel):
    goal: str
    focus_areas: list[str]


class Question(BaseModel):
    text: str


class EvaluationResult(BaseModel):
    score: Annotated[int, Field(ge=0, le=10)]
    strengths: list[str]
    gaps: list[str]
    missing_points: list[str]
    suggested_addition: str | None
    follow_up_question: str
