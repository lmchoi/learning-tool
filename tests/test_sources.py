from pathlib import Path

import pytest

from core.ingestion.sources import load_sources, walk_source_dir


def test_walk_source_dir_finds_supported_types(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text("markdown")
    (tmp_path / "notes.txt").write_text("text")
    (tmp_path / "report.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "script.py").write_text("python")

    paths = walk_source_dir(tmp_path)
    names = {p.name for p in paths}
    assert names == {"doc.md", "notes.txt", "report.pdf"}


def test_walk_source_dir_includes_goal_md(tmp_path: Path) -> None:
    # walk_source_dir is domain-agnostic; GOAL.md exclusion is the caller's responsibility
    (tmp_path / "GOAL.md").write_text("goal")
    (tmp_path / "doc.md").write_text("content")

    paths = walk_source_dir(tmp_path)
    names = {p.name for p in paths}
    assert "GOAL.md" in names
    assert "doc.md" in names


def test_walk_source_dir_recurses_subdirectories(tmp_path: Path) -> None:
    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "nested.md").write_text("nested")

    paths = walk_source_dir(tmp_path)
    assert any(p.name == "nested.md" for p in paths)


def test_walk_source_dir_empty_directory(tmp_path: Path) -> None:
    assert walk_source_dir(tmp_path) == []


def test_load_local_files(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("Content A.")
    (tmp_path / "b.md").write_text("Content B.")

    sources_file = tmp_path / "sources.yaml"
    sources_file.write_text(f"local_files:\n  - {tmp_path}/a.md\n  - {tmp_path}/b.md\n")

    paths = load_sources(sources_file)
    assert len(paths) == 2
    assert all(p.exists() for p in paths)


def test_load_sources_missing_file_raises(tmp_path: Path) -> None:
    sources_file = tmp_path / "sources.yaml"
    sources_file.write_text(f"local_files:\n  - {tmp_path}/missing.md\n")

    with pytest.raises(FileNotFoundError):
        load_sources(sources_file)


def test_load_sources_missing_yaml_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_sources(tmp_path / "nonexistent.yaml")


def test_empty_sources_returns_empty_list(tmp_path: Path) -> None:
    sources_file = tmp_path / "sources.yaml"
    sources_file.write_text("local_files: []\n")

    paths = load_sources(sources_file)
    assert paths == []
