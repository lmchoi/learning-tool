from dataclasses import dataclass

from pydantic import BaseModel


@dataclass
class UserProfile:
    experience_level: str


class Question(BaseModel):
    text: str
