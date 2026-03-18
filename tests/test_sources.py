from pathlib import Path

import pytest

from core.ingestion.sources import load_sources


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
