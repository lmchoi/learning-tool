from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from cli.main import app
from core.models import EvaluationResult, Question

runner = CliRunner()


def _fake_retriever(chunks: list[str]) -> MagicMock:
    retriever = MagicMock()
    retriever.retrieve.return_value = [(chunk, 0.9) for chunk in chunks]
    return retriever


def _evaluation(*, score: int = 7, follow_up: str = "") -> EvaluationResult:
    return EvaluationResult(
        score=score,
        strengths=["Good point."],
        gaps=[],
        missing_points=[],
        suggested_addition=None,
        follow_up_question=follow_up,
    )


def test_practice_fails_fast_for_unknown_context(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["practice", "no-such-context", "some query", "--store-dir", str(tmp_path)]
    )
    assert result.exit_code == 1
    assert "no-such-context" in result.output


@patch("cli.main.SentenceTransformerEmbedder")
@patch("cli.main.Retriever")
@patch("cli.main.evaluate_answer", new_callable=AsyncMock)
@patch("cli.main.generate_question", new_callable=AsyncMock)
def test_practice_prints_score_and_stops_when_declined(
    mock_generate: AsyncMock,
    mock_evaluate: AsyncMock,
    mock_retriever_cls: MagicMock,
    mock_embedder_cls: MagicMock,
    tmp_path: Path,
) -> None:
    (tmp_path / "test-context").mkdir()
    mock_generate.return_value = Question(text="What is the role?")
    mock_evaluate.return_value = _evaluation(score=7)
    mock_retriever_cls.return_value = _fake_retriever(["some chunk"])

    result = runner.invoke(
        app,
        ["practice", "test-context", "responsibilities", "--store-dir", str(tmp_path)],
        input="my answer\nn\n",
    )

    assert "Score: 7/10" in result.output
    assert "Good point." in result.output


@patch("cli.main.SentenceTransformerEmbedder")
@patch("cli.main.Retriever")
@patch("cli.main.evaluate_answer", new_callable=AsyncMock)
@patch("cli.main.generate_question", new_callable=AsyncMock)
def test_practice_auto_follows_up_without_prompting(
    mock_generate: AsyncMock,
    mock_evaluate: AsyncMock,
    mock_retriever_cls: MagicMock,
    mock_embedder_cls: MagicMock,
    tmp_path: Path,
) -> None:
    (tmp_path / "test-context").mkdir()
    mock_generate.return_value = Question(text="What is the role?")
    mock_evaluate.side_effect = [
        _evaluation(score=5, follow_up="What does FDE stand for?"),
        _evaluation(score=8),
    ]
    mock_retriever_cls.return_value = _fake_retriever(["some chunk"])

    result = runner.invoke(
        app,
        ["practice", "test-context", "responsibilities", "--store-dir", str(tmp_path)],
        input="first answer\nsecond answer\nn\n",
    )

    assert "What does FDE stand for?" in result.output
    assert "Score: 5/10" in result.output
    assert "Score: 8/10" in result.output
    assert mock_evaluate.call_count == 2
