import os
from pathlib import Path

STORE_DIR = Path(os.environ.get("STORE_DIR", "contexts/store"))
