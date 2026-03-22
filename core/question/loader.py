from pathlib import Path

import yaml

from core.models import BankQuestion


def load_questions(path: Path) -> list[BankQuestion]:
    """Parse a YAML file of focus_area/question entries into BankQuestion records."""
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, list):
        raise ValueError(f"Expected a YAML list, got {type(raw).__name__}")
    questions = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"Entry {i} is not a mapping")
        if "focus_area" not in entry or "question" not in entry:
            raise ValueError(f"Entry {i} missing 'focus_area' or 'question' key")
        questions.append(BankQuestion.from_parts(str(entry["focus_area"]), str(entry["question"])))
    return questions
