from pathlib import Path

from core.models import ContextMetadata, UserProfile

_TEMPLATE = (Path(__file__).parent / "evaluation_prompt.md").read_text()


def build_evaluation_prompt(
    question: str,
    answer: str,
    chunks: list[str],
    profile: UserProfile,
    metadata: ContextMetadata | None = None,
) -> str:
    material = "\n\n".join(f"- {chunk}" for chunk in chunks)
    goal_section = ""
    focus_section = ""
    if metadata is not None:
        goal_section = f"\n\n<goal>\n{metadata.goal}\n</goal>"
        focus_items = "\n".join(f"- {area}" for area in metadata.focus_areas)
        focus_section = f"\n\n<focus_areas>\n{focus_items}\n</focus_areas>"
    return _TEMPLATE.format_map(
        {
            "experience_level": profile.experience_level,
            "goal_section": goal_section,
            "focus_section": focus_section,
            "material": material,
            "question": question,
            "answer": answer,
        }
    )
