import importlib
import types

import pytest


def reload_constants() -> types.ModuleType:
    import learning_tool.core.llm.constants as m

    importlib.reload(m)
    return m


def test_question_generation_model_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUESTION_GENERATION_MODEL", raising=False)
    m = reload_constants()
    assert m.QUESTION_GENERATION_MODEL == "claude-haiku-4-5"


def test_question_generation_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUESTION_GENERATION_MODEL", "claude-opus-4-6")
    m = reload_constants()
    assert m.QUESTION_GENERATION_MODEL == "claude-opus-4-6"


def test_answer_evaluation_model_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANSWER_EVALUATION_MODEL", raising=False)
    m = reload_constants()
    assert m.ANSWER_EVALUATION_MODEL == "claude-haiku-4-5"


def test_answer_evaluation_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANSWER_EVALUATION_MODEL", "claude-sonnet-4-6")
    m = reload_constants()
    assert m.ANSWER_EVALUATION_MODEL == "claude-sonnet-4-6"
