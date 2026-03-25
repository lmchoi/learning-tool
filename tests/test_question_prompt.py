from core.models import ContextMetadata, UserProfile
from core.question.prompt import build_question_prompt


def test_prompt_contains_goal() -> None:
    metadata = ContextMetadata(
        goal="Learn async Python", focus_areas=["asyncio", "context managers"]
    )
    prompt = build_question_prompt(
        ["Some material."], UserProfile(experience_level="beginner"), metadata
    )
    assert "Learn async Python" in prompt


def test_prompt_contains_focus_areas() -> None:
    metadata = ContextMetadata(goal="Any goal", focus_areas=["asyncio", "context managers"])
    prompt = build_question_prompt(
        ["Some material."], UserProfile(experience_level="beginner"), metadata
    )
    assert "asyncio" in prompt
    assert "context managers" in prompt


def test_prompt_focus_areas_steer_instructions() -> None:
    metadata = ContextMetadata(goal="Any goal", focus_areas=["asyncio"])
    prompt = build_question_prompt(
        ["Some material."], UserProfile(experience_level="beginner"), metadata
    )
    assert "focus" in prompt.lower() or "focus areas" in prompt.lower()


def test_prompt_contains_chunks() -> None:
    chunks = ["Photosynthesis converts light to energy.", "Chlorophyll absorbs red and blue light."]
    profile = UserProfile(experience_level="beginner")
    prompt = build_question_prompt(chunks, profile)
    assert "Photosynthesis converts light to energy." in prompt
    assert "Chlorophyll absorbs red and blue light." in prompt


def test_prompt_contains_experience_level() -> None:
    profile = UserProfile(experience_level="intermediate")
    prompt = build_question_prompt(["Some material."], profile)
    assert "intermediate" in prompt


def test_prompt_is_parameterised() -> None:
    chunks = ["Domain-specific content here."]
    profile = UserProfile(experience_level="expert")
    prompt = build_question_prompt(chunks, profile)
    # No hardcoded domain details — only what came from chunks and profile
    assert "Domain-specific content here." in prompt
    assert "expert" in prompt


def test_prompt_uses_xml_tags() -> None:
    chunks = ["Some material."]
    profile = UserProfile(experience_level="beginner")
    prompt = build_question_prompt(chunks, profile)
    assert "<learner>" in prompt
    assert "<context>" in prompt
    assert "<instructions>" in prompt


def test_chunks_are_inside_context_section() -> None:
    chunks = ["Unique chunk content."]
    profile = UserProfile(experience_level="beginner")
    prompt = build_question_prompt(chunks, profile)
    context_start = prompt.index("<context>")
    context_end = prompt.index("</context>")
    assert "Unique chunk content." in prompt[context_start:context_end]


def test_prompt_renders_from_template() -> None:
    chunks = ["Template content."]
    profile = UserProfile(experience_level="beginner")
    prompt = build_question_prompt(chunks, profile)
    assert "Template content." in prompt
    assert "{" not in prompt  # no unrendered placeholders


def test_prompt_instructs_plain_text_output() -> None:
    prompt = build_question_prompt(["Some material."], UserProfile(experience_level="beginner"))
    assert "plain text" in prompt


def test_braces_in_chunk_content_do_not_crash() -> None:
    chunks = ["Call func() with kwargs: {key: value}"]
    prompt = build_question_prompt(chunks, UserProfile(experience_level="beginner"))
    assert "{key: value}" in prompt
