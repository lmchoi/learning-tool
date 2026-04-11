from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from learning_tool.cli.main import app
from learning_tool.core.models import EvaluationResult, Question
from learning_tool.core.session.store import SessionStore
from learning_tool.core.stores import create_stores

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
        app, ["--store-dir", str(tmp_path), "practice", "no-such-context", "some query"]
    )
    assert result.exit_code == 1
    assert "no-such-context" in result.output


@patch("learning_tool.cli.main.create_stores")
@patch("learning_tool.cli.main.evaluate_answer", new_callable=AsyncMock)
@patch("learning_tool.cli.main.generate_question", new_callable=AsyncMock)
def test_practice_prints_score_and_stops_when_declined(
    mock_generate: AsyncMock,
    mock_evaluate: AsyncMock,
    mock_create_stores: MagicMock,
    tmp_path: Path,
) -> None:
    (tmp_path / "test-context").mkdir()
    mock_generate.return_value = Question(text="What is the role?")
    mock_evaluate.return_value = _evaluation(score=7)

    from learning_tool.core.ingestion.embedder import FakeEmbedder

    stores = create_stores(tmp_path, embedder=FakeEmbedder(dim=8))
    stores = stores._replace(retriever=_fake_retriever(["some chunk"]))
    mock_create_stores.return_value = stores

    result = runner.invoke(
        app,
        ["--store-dir", str(tmp_path), "practice", "test-context", "responsibilities"],
        input="my answer\nn\n",
    )

    assert "Score: 7/10" in result.output
    assert "Good point." in result.output


@patch("learning_tool.cli.main.create_stores")
@patch("learning_tool.cli.main.evaluate_answer", new_callable=AsyncMock)
@patch("learning_tool.cli.main.generate_question", new_callable=AsyncMock)
def test_practice_auto_follows_up_without_prompting(
    mock_generate: AsyncMock,
    mock_evaluate: AsyncMock,
    mock_create_stores: MagicMock,
    tmp_path: Path,
) -> None:
    (tmp_path / "test-context").mkdir()
    mock_generate.return_value = Question(text="What is the role?")
    mock_evaluate.side_effect = [
        _evaluation(score=5, follow_up="What does FDE stand for?"),
        _evaluation(score=8),
    ]

    from learning_tool.core.ingestion.embedder import FakeEmbedder

    stores = create_stores(tmp_path, embedder=FakeEmbedder(dim=8))
    stores = stores._replace(retriever=_fake_retriever(["some chunk"]))
    mock_create_stores.return_value = stores

    result = runner.invoke(
        app,
        ["--store-dir", str(tmp_path), "practice", "test-context", "responsibilities"],
        input="first answer\nsecond answer\nn\n",
    )

    assert "What does FDE stand for?" in result.output
    assert "Score: 5/10" in result.output
    assert "Score: 8/10" in result.output
    assert mock_evaluate.call_count == 2


@patch("learning_tool.cli.main.create_stores")
@patch("learning_tool.cli.main.evaluate_answer", new_callable=AsyncMock)
@patch("learning_tool.cli.main.generate_question", new_callable=AsyncMock)
def test_practice_creates_sessions_db(
    mock_generate: AsyncMock,
    mock_evaluate: AsyncMock,
    mock_create_stores: MagicMock,
    tmp_path: Path,
) -> None:
    (tmp_path / "test-context").mkdir()
    mock_generate.return_value = Question(text="What is the role?")
    mock_evaluate.return_value = _evaluation(score=8)

    from learning_tool.core.ingestion.embedder import FakeEmbedder

    stores = create_stores(tmp_path, embedder=FakeEmbedder(dim=8))
    stores = stores._replace(retriever=_fake_retriever(["some chunk"]))
    mock_create_stores.return_value = stores

    runner.invoke(
        app,
        ["--store-dir", str(tmp_path), "practice", "test-context", "responsibilities"],
        input="my answer\nn\n",
    )

    assert (tmp_path / "test-context" / "sessions.db").exists()
    store = SessionStore(tmp_path, "test-context")
    sessions = store.load_sessions()
    assert len(sessions) == 1
    assert len(sessions[0].attempts) == 1
    assert sessions[0].attempts[0].answer_text == "my answer"
    assert sessions[0].attempts[0].score == 8
