from pathlib import Path

import yaml


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
