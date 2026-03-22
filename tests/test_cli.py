from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from cli.main import app
from core.ingestion.embedder import FakeEmbedder
from core.ingestion.store import ChunkStore, ContextStore
from core.models import ContextMetadata

runner = CliRunner()

_FAKE_METADATA = ContextMetadata(
    goal="Preparing for a biology exam.",
    focus_areas=["cell biology", "genetics"],
)


@pytest.fixture()
def source_dir(tmp_path: Path) -> Path:
    source = tmp_path / "docs"
    source.mkdir()
    (source / "doc.md").write_text("Some content.")
    return source


def test_init_warns_and_exits_when_context_exists(tmp_path: Path) -> None:
    source = tmp_path / "docs"
    source.mkdir()
    (source / "doc.md").write_text("Some content.")
    store_dir = tmp_path / "store"
    ctx_store = ContextStore(store_dir)
    ctx_store.save_context(
        "my-context",
        ContextMetadata(
            goal="Preparing for an interview.",
            focus_areas=["LLM evaluation", "Python async"],
        ),
    )

    result = runner.invoke(
        app,
        ["init", "--source", str(source), "--context", "my-context", "--store-dir", str(store_dir)],
    )

    assert result.exit_code == 1
    assert "my-context" in result.output
    assert "LLM evaluation" in result.output
    assert "Python async" in result.output
    assert "--force" in result.output


def test_init_force_reingest_overwrites_existing_context(tmp_path: Path) -> None:
    source = tmp_path / "docs"
    source.mkdir()
    (source / "doc.md").write_text("Updated content.")
    store_dir = tmp_path / "store"
    ctx_store = ContextStore(store_dir)
    ctx_store.save_context(
        "my-context",
        ContextMetadata(goal="Old goal.", focus_areas=["old area"]),
    )

    with patch("cli.main.SentenceTransformerEmbedder", return_value=FakeEmbedder(dim=8)):
        result = runner.invoke(
            app,
            [
                "init",
                "--source",
                str(source),
                "--context",
                "my-context",
                "--store-dir",
                str(store_dir),
                "--force",
            ],
        )

    assert result.exit_code == 0
    assert "already exists" not in result.output
    store = ChunkStore(store_dir)
    chunks, _ = store.load("my-context")
    assert any("Updated content" in c for c in chunks)


def test_init_force_reingest_updates_context_yaml(tmp_path: Path) -> None:
    source = tmp_path / "docs"
    source.mkdir()
    (source / "doc.md").write_text("Some content.")
    (source / "GOAL.md").write_text("I want to prepare for my biology exam.")
    store_dir = tmp_path / "store"
    ctx_store = ContextStore(store_dir)
    ctx_store.save_context(
        "my-context",
        ContextMetadata(goal="Old goal.", focus_areas=["old area"]),
    )

    with (
        patch("cli.main.SentenceTransformerEmbedder", return_value=FakeEmbedder(dim=8)),
        patch("cli.main.extract_context", new=AsyncMock(return_value=_FAKE_METADATA)),
    ):
        result = runner.invoke(
            app,
            [
                "init",
                "--source",
                str(source),
                "--context",
                "my-context",
                "--store-dir",
                str(store_dir),
                "--force",
            ],
        )

    assert result.exit_code == 0
    loaded = ContextStore(store_dir).load_context("my-context")
    assert loaded is not None
    assert loaded.goal == _FAKE_METADATA.goal
    assert loaded.focus_areas == _FAKE_METADATA.focus_areas


def test_init_ingests_supported_files(tmp_path: Path) -> None:
    source = tmp_path / "docs"
    source.mkdir()
    (source / "a.md").write_text("First paragraph.\n\nSecond paragraph.")
    (source / "b.txt").write_text("Another paragraph.")
    (source / "GOAL.md").write_text("This is the goal.")
    store_dir = tmp_path / "store"

    with (
        patch("cli.main.SentenceTransformerEmbedder", return_value=FakeEmbedder(dim=8)),
        patch("cli.main.extract_context", new=AsyncMock(return_value=_FAKE_METADATA)),
    ):
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


def test_init_extracts_and_saves_context_yaml(source_dir: Path, tmp_path: Path) -> None:
    (source_dir / "GOAL.md").write_text("I want to prepare for my biology exam.")
    store_dir = tmp_path / "store"

    with (
        patch("cli.main.SentenceTransformerEmbedder", return_value=FakeEmbedder(dim=8)),
        patch("cli.main.extract_context", new=AsyncMock(return_value=_FAKE_METADATA)),
    ):
        result = runner.invoke(
            app,
            [
                "init",
                "--source",
                str(source_dir),
                "--context",
                "test",
                "--store-dir",
                str(store_dir),
            ],
        )

    assert result.exit_code == 0
    loaded = ContextStore(store_dir).load_context("test")
    assert loaded is not None
    assert loaded.goal == _FAKE_METADATA.goal
    assert loaded.focus_areas == _FAKE_METADATA.focus_areas


def test_init_prints_goal_and_focus_areas(source_dir: Path, tmp_path: Path) -> None:
    (source_dir / "GOAL.md").write_text("I want to prepare for my biology exam.")
    store_dir = tmp_path / "store"

    with (
        patch("cli.main.SentenceTransformerEmbedder", return_value=FakeEmbedder(dim=8)),
        patch("cli.main.extract_context", new=AsyncMock(return_value=_FAKE_METADATA)),
    ):
        result = runner.invoke(
            app,
            [
                "init",
                "--source",
                str(source_dir),
                "--context",
                "test",
                "--store-dir",
                str(store_dir),
            ],
        )

    assert result.exit_code == 0
    assert "Goal: Preparing for a biology exam." in result.output
    assert "- cell biology" in result.output
    assert "- genetics" in result.output
    assert str(store_dir / "test" / "context.yaml") in result.output


def test_init_skips_context_extraction_when_no_goal_md(source_dir: Path, tmp_path: Path) -> None:
    store_dir = tmp_path / "store"

    with (
        patch("cli.main.SentenceTransformerEmbedder", return_value=FakeEmbedder(dim=8)),
        patch("cli.main.extract_context", new=AsyncMock()) as mock_extract,
    ):
        result = runner.invoke(
            app,
            [
                "init",
                "--source",
                str(source_dir),
                "--context",
                "test",
                "--store-dir",
                str(store_dir),
            ],
        )

    assert result.exit_code == 0
    mock_extract.assert_not_called()
    assert "skipping context extraction" in result.output


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
