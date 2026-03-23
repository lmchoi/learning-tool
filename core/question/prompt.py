from core.models import ContextMetadata, UserProfile


def build_question_prompt(
    chunks: list[str], profile: UserProfile, metadata: ContextMetadata | None = None
) -> str:
    material = "\n\n".join(f"- {chunk}" for chunk in chunks)
    goal_block = ""
    focus_block = ""
    focus_instruction = ""
    if metadata is not None:
        goal_block = f"\n\n<goal>\n{metadata.goal}\n</goal>"
        focus_items = "\n".join(f"- {area}" for area in metadata.focus_areas)
        focus_block = f"\n\n<focus_areas>\n{focus_items}\n</focus_areas>"
        focus_instruction = " Prioritise questions that are relevant to the stated focus areas."
    return f"""You are a tutor generating a practice question for a learner.

<learner>
Experience level: {profile.experience_level}
</learner>{goal_block}{focus_block}

<context>
{material}
</context>

<instructions>
Generate one specific practice question grounded in the context above.
The question must be directly answerable from the context and not from general knowledge alone.
Do not include the answer.
Return only the question as plain text. No markdown, no headers, no preamble.{focus_instruction}
</instructions>"""
