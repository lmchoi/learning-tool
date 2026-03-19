from core.models import UserProfile


def build_question_prompt(chunks: list[str], profile: UserProfile) -> str:
    material = "\n\n".join(f"- {chunk}" for chunk in chunks)
    return f"""You are a tutor generating a practice question for a learner.

<learner>
Experience level: {profile.experience_level}
</learner>

<context>
{material}
</context>

<instructions>
Generate one specific practice question grounded in the context above.
The question must be directly answerable from the context and not from general knowledge alone.
Do not include the answer.
</instructions>"""
