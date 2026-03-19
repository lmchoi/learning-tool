from core.models import UserProfile
from core.question.prompt import build_question_prompt


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
    assert "<context>" in prompt
    assert "</context>" in prompt
    assert "<instructions>" in prompt
    assert "</instructions>" in prompt
    assert "<learner>" in prompt
    assert "</learner>" in prompt


def test_chunks_are_inside_context_tags() -> None:
    chunks = ["Unique chunk content."]
    profile = UserProfile(experience_level="beginner")
    prompt = build_question_prompt(chunks, profile)
    context_start = prompt.index("<context>")
    context_end = prompt.index("</context>")
    assert "Unique chunk content." in prompt[context_start:context_end]


def test_prompt_instructs_plain_text_output() -> None:
    prompt = build_question_prompt(["Some material."], UserProfile(experience_level="beginner"))
    assert "plain text" in prompt
