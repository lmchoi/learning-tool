from pathlib import Path

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def test_question_prompt_fails_fast_for_unknown_context(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["question-prompt", "no-such-context", "some query", "--store-dir", str(tmp_path)]
    )
    assert result.exit_code == 1
    assert "no-such-context" in result.output


def test_question_fails_fast_for_unknown_context(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["question", "no-such-context", "some query", "--store-dir", str(tmp_path)]
    )
    assert result.exit_code == 1
    assert "no-such-context" in result.output
