from pathlib import Path

import yaml

_SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf"}


def walk_source_dir(source_dir: Path) -> list[Path]:
    """Return all supported document files in source_dir, recursively."""
    return sorted(
        p for p in source_dir.rglob("*") if p.is_file() and p.suffix in _SUPPORTED_EXTENSIONS
    )


def load_sources(sources_file: Path) -> list[Path]:
    """Load and validate local file paths from a sources.yaml config."""
    if not sources_file.exists():
        raise FileNotFoundError(f"Sources file not found: {sources_file}")

    config = yaml.safe_load(sources_file.read_text())
    raw_paths: list[str] = config.get("local_files", [])
    paths = [Path(p) for p in raw_paths]

    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Source file not found: {path}")

    return paths
