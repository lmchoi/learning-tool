import os
from pathlib import Path

STORE_DIR = Path(os.environ.get("STORE_DIR", "contexts/store"))

GITHUB_TOKEN: str | None = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO: str | None = os.environ.get("GITHUB_REPO")
