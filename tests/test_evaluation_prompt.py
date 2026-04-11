from learning_tool.core.evaluation.prompt import build_evaluation_prompt
from learning_tool.core.models import ContextMetadata, UserProfile


def test_prompt_contains_goal() -> None:
    metadata = ContextMetadata(goal="Learn async Python", focus_areas=["asyncio"])
    prompt = build_evaluation_prompt(
        question="Q?",
        answer="A.",
        chunks=["Some context."],
        profile=UserProfile(experience_level="beginner"),
        metadata=metadata,
    )
    assert "Learn async Python" in prompt


def test_prompt_contains_focus_areas() -> None:
    metadata = ContextMetadata(goal="Any goal", focus_areas=["asyncio", "context managers"])
    prompt = build_evaluation_prompt(
        question="Q?",
        answer="A.",
        chunks=["Some context."],
        profile=UserProfile(experience_level="beginner"),
        metadata=metadata,
    )
    assert "asyncio" in prompt
    assert "context managers" in prompt


def test_prompt_contains_question() -> None:
    prompt = build_evaluation_prompt(
        question="What is the role of mitochondria?",
        answer="They produce energy.",
        chunks=["Some context."],
        profile=UserProfile(experience_level="beginner"),
    )
    assert "What is the role of mitochondria?" in prompt


def test_prompt_contains_answer() -> None:
    prompt = build_evaluation_prompt(
        question="What is X?",
        answer="X is a unique answer string.",
        chunks=["Some context."],
        profile=UserProfile(experience_level="beginner"),
    )
    assert "X is a unique answer string." in prompt


def test_prompt_contains_chunks_in_context_section() -> None:
    chunks = ["Chunk alpha.", "Chunk beta."]
    prompt = build_evaluation_prompt(
        question="Q?",
        answer="A.",
        chunks=chunks,
        profile=UserProfile(experience_level="beginner"),
    )
    context_start = prompt.index("<context>")
    context_end = prompt.index("</context>")
    context_block = prompt[context_start:context_end]
    assert "Chunk alpha." in context_block
    assert "Chunk beta." in context_block


def test_prompt_contains_experience_level() -> None:
    prompt = build_evaluation_prompt(
        question="Q?",
        answer="A.",
        chunks=["Some context."],
        profile=UserProfile(experience_level="advanced"),
    )
    assert "advanced" in prompt


def test_prompt_instructs_honesty_not_encouragement() -> None:
    prompt = build_evaluation_prompt(
        question="Q?",
        answer="A.",
        chunks=["Some context."],
        profile=UserProfile(experience_level="beginner"),
    )
    lower = prompt.lower()
    assert "honest" in lower
    assert "encouraging" in lower or "encouragement" in lower


def test_prompt_uses_xml_tags() -> None:
    prompt = build_evaluation_prompt(
        question="Q?",
        answer="A.",
        chunks=["Some context."],
        profile=UserProfile(experience_level="beginner"),
    )
    assert "<learner>" in prompt
    assert "<context>" in prompt
    assert "<question>" in prompt
    assert "<answer>" in prompt
    assert "<instructions>" in prompt


def test_prompt_renders_from_template() -> None:
    prompt = build_evaluation_prompt(
        question="What is X?",
        answer="X is Y.",
        chunks=["Some context."],
        profile=UserProfile(experience_level="beginner"),
    )
    assert "What is X?" in prompt
    assert "X is Y." in prompt
    assert "{" not in prompt  # no unrendered placeholders


def test_braces_in_content_do_not_crash() -> None:
    prompt = build_evaluation_prompt(
        question="What is {this}?",
        answer="It is {that}.",
        chunks=["Example: {key: value}"],
        profile=UserProfile(experience_level="beginner"),
    )
    assert "{this}" in prompt
    assert "{that}" in prompt
    assert "{key: value}" in prompt
