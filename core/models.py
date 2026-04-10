import hashlib
import uuid
from dataclasses import dataclass
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


@dataclass
class UserProfile:
    experience_level: str


class ContextMetadata(BaseModel):
    goal: Annotated[str, Field(min_length=1)]
    focus_areas: list[str]
    archived: bool = False


class Question(BaseModel):
    text: str
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class EvaluationResult(BaseModel):
    score: Annotated[int, Field(ge=0, le=10)]
    strengths: list[str]
    gaps: list[str]
    missing_points: list[str]
    suggested_addition: str | None
    follow_up_question: str

    @field_validator("strengths", "gaps", "missing_points", mode="before")
    @classmethod
    def coerce_str_to_list(cls, v: object) -> object:
        if isinstance(v, str):
            # Empty string means "nothing here" — treat as empty list so the
            # template doesn't render a single empty <li>.
            return [v] if v else []
        return v


@dataclass
class BankQuestion:
    id: str
    focus_area: str
    question: str

    @staticmethod
    def make_id(focus_area: str, question: str) -> str:
        return hashlib.sha256(f"{focus_area}\n{question}".encode()).hexdigest()[:12]

    @classmethod
    def from_parts(cls, focus_area: str, question: str) -> "BankQuestion":
        return cls(id=cls.make_id(focus_area, question), focus_area=focus_area, question=question)
