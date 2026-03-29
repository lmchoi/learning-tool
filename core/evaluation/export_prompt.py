from pathlib import Path

from core.models import ContextMetadata, UserProfile
from core.session.models import QuestionAttempt

_TEMPLATE = (Path(__file__).parent / "export_evaluation_prompt.md").read_text()


def build_export_prompt(
    attempts: list[QuestionAttempt],
    profile: UserProfile,
    metadata: ContextMetadata | None = None,
) -> str:
    goal_section = ""
    focus_section = ""
    if metadata is not None:
        goal_section = f"\n\n<goal>\n{metadata.goal}\n</goal>"
        if metadata.focus_areas:
            focus_items = "\n".join(f"- {area}" for area in metadata.focus_areas)
            focus_section = f"\n\n<focus_areas>\n{focus_items}\n</focus_areas>"

    qa_parts = []
    for attempt in attempts:
        qid = attempt.question_id or "unknown"
        qa_parts.append(
            f'<question id="{qid}">\n{attempt.question_text}\n</question>\n'
            f"<answer>\n{attempt.answer_text}\n</answer>"
        )
    questions_and_answers = "\n\n".join(qa_parts)

    return _TEMPLATE.format_map(
        {
            "experience_level": profile.experience_level,
            "goal_section": goal_section,
            "focus_section": focus_section,
            "questions_and_answers": questions_and_answers,
        }
    )
