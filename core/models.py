from dataclasses import dataclass


@dataclass
class UserProfile:
    experience_level: str


@dataclass
class Question:
    text: str
