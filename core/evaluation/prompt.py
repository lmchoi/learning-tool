from core.models import UserProfile


def build_evaluation_prompt(
    question: str,
    answer: str,
    chunks: list[str],
    profile: UserProfile,
) -> str:
    material = "\n\n".join(f"- {chunk}" for chunk in chunks)
    return f"""You are a tutor evaluating a learner's answer to a practice question.

<learner>
Experience level: {profile.experience_level}
</learner>

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
