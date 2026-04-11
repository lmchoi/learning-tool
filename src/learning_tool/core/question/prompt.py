from pathlib import Path

from learning_tool.core.models import ContextMetadata, UserProfile

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "resources" / "prompts"
_TEMPLATE = (_PROMPTS_DIR / "question_prompt.md").read_text()


def build_question_prompt(
    chunks: list[str], profile: UserProfile, metadata: ContextMetadata | None = None
) -> str:
    material = "\n\n".join(f"- {chunk}" for chunk in chunks)
    goal_section = ""
    focus_section = ""
    focus_instruction = ""
    if metadata is not None:
        goal_section = f"\n\n<goal>\n{metadata.goal}\n</goal>"
        focus_items = "\n".join(f"- {area}" for area in metadata.focus_areas)
        focus_section = f"\n\n<focus_areas>\n{focus_items}\n</focus_areas>"
        focus_instruction = "Prioritise questions that are relevant to the stated focus areas.\n"
    return _TEMPLATE.format_map(
        {
            "experience_level": profile.experience_level,
            "goal_section": goal_section,
            "focus_section": focus_section,
            "material": material,
            "focus_instruction": focus_instruction,
        }
    )
