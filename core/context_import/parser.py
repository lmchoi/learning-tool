import re
from dataclasses import dataclass


@dataclass
class ImportedContext:
    goal: str
    questions: list[tuple[str, list[str]]]

    @property
    def focus_areas(self) -> list[str]:
        return [fa for fa, _ in self.questions]


def parse_import(text: str) -> ImportedContext:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return ImportedContext(
        goal=_extract_goal(text),
        questions=_extract_questions(text),
    )


def _extract_goal(text: str) -> str:
    match = re.search(r"^## Goal[ \t]*\n(.*?)(?=\n## |\Z)", text, re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError("Missing '## Goal' section")
    goal = match.group(1).strip()
    if not goal:
        raise ValueError("'## Goal' section is empty")
    return goal


def _extract_questions(text: str) -> list[tuple[str, list[str]]]:
    section_match = re.search(
        r"^## Questions[ \t]*\n(.*?)(?=\n## |\Z)", text, re.MULTILINE | re.DOTALL
    )
    if not section_match:
        raise ValueError("Missing '## Questions' section")

    section_text = section_match.group(1)
    area_blocks = re.split(r"^### ", section_text, flags=re.MULTILINE)

    result = []
    for block in area_blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        focus_area = lines[0].strip()
        area_questions = [
            line[1:].strip()
            for line in lines[1:]
            if line.strip().startswith("-") and line[1:].strip()
        ]
        if focus_area and area_questions:
            result.append((focus_area, area_questions))

    if not result:
        raise ValueError("No focus areas with questions found in '## Questions' section")

    return result
