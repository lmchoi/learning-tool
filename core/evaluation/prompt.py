from core.models import ContextMetadata, UserProfile


def build_evaluation_prompt(
    question: str,
    answer: str,
    chunks: list[str],
    profile: UserProfile,
    metadata: ContextMetadata | None = None,
) -> str:
    material = "\n\n".join(f"- {chunk}" for chunk in chunks)
    goal_block = ""
    focus_block = ""
    if metadata is not None:
        goal_block = f"\n\n<goal>\n{metadata.goal}\n</goal>"
        focus_items = "\n".join(f"- {area}" for area in metadata.focus_areas)
        focus_block = f"\n\n<focus_areas>\n{focus_items}\n</focus_areas>"
    return f"""You are a tutor evaluating a learner's answer to a practice question.

<learner>
Experience level: {profile.experience_level}
</learner>{goal_block}{focus_block}

<context>
{material}
</context>

<question>
{question}
</question>

<answer>
{answer}
</answer>

<instructions>
Evaluate the answer honestly. Do not be encouraging or inflate the score.
Identify what the learner got right and what factual points they missed or got wrong.
Only flag something as a gap if it affects the correctness or meaningful completeness of the answer.
Do not penalise for not citing sources, not quoting the material, or not explaining
their reasoning — only the substance matters.
Suggest a follow-up question that probes a gap in their understanding.
</instructions>"""
