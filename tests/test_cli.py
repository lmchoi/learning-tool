from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from cli.main import app
from core.ingestion.embedder import FakeEmbedder
from core.ingestion.store import ChunkStore

runner = CliRunner()


def test_init_ingests_supported_files(tmp_path: Path) -> None:
    source = tmp_path / "docs"
    source.mkdir()
    (source / "a.md").write_text("First paragraph.\n\nSecond paragraph.")
    (source / "b.txt").write_text("Another paragraph.")
    (source / "GOAL.md").write_text("This is the goal.")
    store_dir = tmp_path / "store"

    with patch("cli.main.SentenceTransformerEmbedder", return_value=FakeEmbedder(dim=8)):
        result = runner.invoke(
            app,
            ["init", "--source", str(source), "--context", "test", "--store-dir", str(store_dir)],
        )

    assert result.exit_code == 0
    assert "2" in result.output  # GOAL.md excluded by init → 2 files (a.md, b.txt)
    store = ChunkStore(store_dir)
    chunks, embeddings = store.load("test")
    assert len(chunks) > 0
    assert embeddings.shape[0] == len(chunks)


def test_init_excludes_goal_md(tmp_path: Path) -> None:
    source = tmp_path / "docs"
    source.mkdir()
    (source / "GOAL.md").write_text("goal description")
    store_dir = tmp_path / "store"

    # Only GOAL.md present — should fail as no supported files remain
    result = runner.invoke(
        app,
        ["init", "--source", str(source), "--context", "test", "--store-dir", str(store_dir)],
    )
    assert result.exit_code == 1


def test_init_fails_for_missing_source_dir(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "init",
            "--source",
            str(tmp_path / "nonexistent"),
            "--context",
            "test",
            "--store-dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1


def test_init_fails_when_no_supported_files(tmp_path: Path) -> None:
    source = tmp_path / "docs"
    source.mkdir()
    (source / "notes.py").write_text("not supported")

    result = runner.invoke(
        app,
        ["init", "--source", str(source), "--context", "test", "--store-dir", str(tmp_path)],
    )
    assert result.exit_code == 1


@pytest.mark.parametrize("context", ["my-context"])
def test_init_wipes_and_rebuilds(tmp_path: Path, context: str) -> None:
    source = tmp_path / "docs"
    source.mkdir()
    (source / "doc.md").write_text("Only paragraph.")
    store_dir = tmp_path / "store"

    with patch("cli.main.SentenceTransformerEmbedder", return_value=FakeEmbedder(dim=8)):
        runner.invoke(
            app,
            ["init", "--source", str(source), "--context", context, "--store-dir", str(store_dir)],
        )
        runner.invoke(
            app,
            ["init", "--source", str(source), "--context", context, "--store-dir", str(store_dir)],
        )

    store = ChunkStore(store_dir)
    chunks, _ = store.load(context)
    assert len(chunks) == 1  # not doubled


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
