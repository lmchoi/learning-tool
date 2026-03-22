from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from cli.main import app
from core.models import BankQuestion
from core.question.loader import load_questions
from core.question.store import QuestionBankStore

runner = CliRunner()


# --- BankQuestion model ---


def test_bank_question_id_is_deterministic() -> None:
    q1 = BankQuestion.from_parts("Prompt Engineering", "How do you iterate on a prompt?")
    q2 = BankQuestion.from_parts("Prompt Engineering", "How do you iterate on a prompt?")
    assert q1.id == q2.id


def test_bank_question_id_differs_for_different_inputs() -> None:
    q1 = BankQuestion.from_parts("Area A", "Question one")
    q2 = BankQuestion.from_parts("Area B", "Question one")
    assert q1.id != q2.id


def test_bank_question_id_is_12_chars() -> None:
    q = BankQuestion.from_parts("focus", "question")
    assert len(q.id) == 12


# --- YAML loader ---


def test_load_questions_parses_yaml(tmp_path: Path) -> None:
    f = tmp_path / "questions.yaml"
    f.write_text(
        yaml.dump(
            [
                {"focus_area": "Agent Development", "question": "Describe the core loop."},
                {"focus_area": "Prompt Engineering", "question": "How do you improve a prompt?"},
            ]
        )
    )
    questions = load_questions(f)
    assert len(questions) == 2
    assert questions[0].focus_area == "Agent Development"
    assert questions[1].question == "How do you improve a prompt?"


def test_load_questions_assigns_deterministic_ids(tmp_path: Path) -> None:
    f = tmp_path / "questions.yaml"
    f.write_text(yaml.dump([{"focus_area": "X", "question": "Q"}]))
    [q] = load_questions(f)
    assert q.id == BankQuestion.make_id("X", "Q")


def test_load_questions_raises_on_non_list(tmp_path: Path) -> None:
    f = tmp_path / "bad.yaml"
    f.write_text("key: value\n")
    with pytest.raises(ValueError, match="Expected a YAML list"):
        load_questions(f)


def test_load_questions_raises_on_missing_key(tmp_path: Path) -> None:
    f = tmp_path / "bad.yaml"
    f.write_text(yaml.dump([{"focus_area": "X"}]))
    with pytest.raises(ValueError, match="missing"):
        load_questions(f)


# --- QuestionBankStore ---


def test_store_add_and_list(tmp_path: Path) -> None:
    store = QuestionBankStore(tmp_path, "ctx")
    questions = [
        BankQuestion.from_parts("A", "Q1"),
        BankQuestion.from_parts("B", "Q2"),
    ]
    added = store.add(questions)
    assert added == 2
    listed = store.list()
    assert len(listed) == 2
    assert {q.focus_area for q in listed} == {"A", "B"}


def test_store_add_is_idempotent(tmp_path: Path) -> None:
    store = QuestionBankStore(tmp_path, "ctx")
    questions = [BankQuestion.from_parts("A", "Q1")]
    store.add(questions)
    added_again = store.add(questions)
    assert added_again == 0
    assert len(store.list()) == 1


def test_store_uses_separate_db_per_context(tmp_path: Path) -> None:
    s1 = QuestionBankStore(tmp_path, "ctx1")
    s2 = QuestionBankStore(tmp_path, "ctx2")
    s1.add([BankQuestion.from_parts("A", "Q")])
    assert len(s2.list()) == 0


# --- CLI command ---


def _write_questions_yaml(path: Path) -> None:
    path.write_text(
        yaml.dump(
            [
                {"focus_area": "Agent Development", "question": "Describe the core loop."},
                {"focus_area": "Prompt Engineering", "question": "How do you improve a prompt?"},
            ]
        )
    )


def test_load_questions_cmd_loads_questions(tmp_path: Path) -> None:
    f = tmp_path / "questions.yaml"
    _write_questions_yaml(f)
    result = runner.invoke(
        app,
        [
            "load-questions-cmd",
            "--context",
            "myctx",
            "--file",
            str(f),
            "--store-dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "2 new question(s)" in result.output
    bank = QuestionBankStore(tmp_path, "myctx")
    assert len(bank.list()) == 2


def test_load_questions_cmd_is_idempotent(tmp_path: Path) -> None:
    f = tmp_path / "questions.yaml"
    _write_questions_yaml(f)
    args = [
        "load-questions-cmd",
        "--context",
        "myctx",
        "--file",
        str(f),
        "--store-dir",
        str(tmp_path),
    ]
    runner.invoke(app, args)
    result = runner.invoke(app, args)
    assert result.exit_code == 0
    assert "0 new question(s)" in result.output
    assert len(QuestionBankStore(tmp_path, "myctx").list()) == 2


def test_load_questions_cmd_fails_for_invalid_yaml_structure(tmp_path: Path) -> None:
    f = tmp_path / "bad.yaml"
    f.write_text(yaml.dump([{"focus_area": "X"}]))  # missing 'questions' key
    result = runner.invoke(
        app,
        [
            "load-questions-cmd",
            "--context",
            "myctx",
            "--file",
            str(f),
            "--store-dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1


def test_load_questions_cmd_fails_for_missing_file(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "load-questions-cmd",
            "--context",
            "myctx",
            "--file",
            str(tmp_path / "nonexistent.yaml"),
            "--store-dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1
