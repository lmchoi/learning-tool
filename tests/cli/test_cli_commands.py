from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from learning_tool.cli.main import app
from learning_tool.core.ingestion.embedder import FakeEmbedder
from learning_tool.core.models import EvaluationResult, Question
from learning_tool.core.stores import create_stores

runner = CliRunner()


def test_ingest_context_command(tmp_path: Path) -> None:
    source_file = tmp_path / "test.md"
    source_file.write_text("Test content.")
    store_dir = tmp_path / "store"

    # We need to mock create_stores to use FakeEmbedder to avoid heavy sentence-transformers
    with patch("learning_tool.cli.main.create_stores") as mock_create_stores:
        mock_create_stores.return_value = create_stores(store_dir, embedder=FakeEmbedder(dim=8))

        result = runner.invoke(
            app,
            ["--store-dir", str(store_dir), "ingest-context", "myctx", str(source_file)],
        )

    assert result.exit_code == 0
    assert "Ingested 1 file(s)" in result.output


def test_ingest_context_command_missing_files(tmp_path: Path) -> None:
    store_dir = tmp_path / "store"
    with patch("learning_tool.cli.main.create_stores") as mock_create_stores:
        mock_create_stores.return_value = create_stores(store_dir, embedder=FakeEmbedder(dim=8))
        result = runner.invoke(
            app,
            ["--store-dir", str(store_dir), "ingest-context", "myctx", "nonexistent.md"],
        )
    assert result.exit_code == 1
    assert "Error: file(s) not found" in result.output


@patch("learning_tool.cli.main.create_stores")
def test_question_prompt_command(mock_create_stores: AsyncMock, tmp_path: Path) -> None:
    store_dir = tmp_path / "store"
    (store_dir / "myctx").mkdir(parents=True)

    stores = create_stores(store_dir, embedder=FakeEmbedder(dim=8))
    mock_create_stores.return_value = stores

    with (
        patch.object(stores.context_store, "load_context"),
        patch.object(stores.retriever, "retrieve", return_value=[("chunk", 0.9)]),
        patch("learning_tool.cli.main.build_question_prompt", return_value="Mock Prompt"),
    ):
        result = runner.invoke(
            app,
            ["--store-dir", str(store_dir), "question-prompt", "myctx", "query"],
        )

    assert result.exit_code == 0
    assert "Mock Prompt" in result.output


@patch("learning_tool.cli.main.create_stores")
@patch("learning_tool.cli.main.generate_question", new_callable=AsyncMock)
def test_question_command(
    mock_generate: AsyncMock, mock_create_stores: MagicMock, tmp_path: Path
) -> None:
    store_dir = tmp_path / "store"
    (store_dir / "myctx").mkdir(parents=True)

    stores = create_stores(store_dir, embedder=FakeEmbedder(dim=8))
    mock_create_stores.return_value = stores

    mock_generate.return_value = Question(text="Generated Question")

    with (
        patch.object(stores.context_store, "load_context"),
        patch.object(stores.retriever, "retrieve", return_value=[("chunk", 0.9)]),
    ):
        result = runner.invoke(
            app,
            ["--store-dir", str(store_dir), "question", "myctx", "query"],
        )

    assert result.exit_code == 0
    assert "Generated Question" in result.output


@patch("learning_tool.cli.main.create_stores")
@patch("learning_tool.cli.main.evaluate_answer", new_callable=AsyncMock)
def test_evaluate_command(
    mock_evaluate: AsyncMock, mock_create_stores: MagicMock, tmp_path: Path
) -> None:
    store_dir = tmp_path / "store"
    (store_dir / "myctx").mkdir(parents=True)

    stores = create_stores(store_dir, embedder=FakeEmbedder(dim=8))
    mock_create_stores.return_value = stores

    mock_evaluate.return_value = EvaluationResult(
        score=9,
        strengths=["Good"],
        gaps=[],
        missing_points=[],
        suggested_addition=None,
        follow_up_question="",
    )

    with (
        patch.object(stores.context_store, "load_context"),
        patch.object(stores.retriever, "retrieve", return_value=[("chunk", 0.9)]),
    ):
        result = runner.invoke(
            app,
            ["--store-dir", str(store_dir), "evaluate", "myctx", "query", "Q", "A"],
        )

    assert result.exit_code == 0
    assert "Score: 9/10" in result.output
