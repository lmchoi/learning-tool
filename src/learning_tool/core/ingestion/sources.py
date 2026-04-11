import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf"}


def walk_source_dir(source_dir: Path) -> list[Path]:
    """Return all supported document files in source_dir, recursively."""
    found = []
    for p in sorted(source_dir.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix in _SUPPORTED_EXTENSIONS:
            logger.debug("found %s", p)
            found.append(p)
        else:
            logger.debug("skipped %s (unsupported type)", p)
    return found


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
