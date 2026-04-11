from collections.abc import Generator
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from learning_tool.api.main import app
from learning_tool.core.ingestion.store import ContextStore


def make_api_client(store_dir: Path) -> Generator[TestClient]:
    """Yield a TestClient with heavy dependencies mocked and store wired to store_dir."""
    with ExitStack() as stack:
        stack.enter_context(patch("learning_tool.api.main.create_stores"))
        stack.enter_context(patch("learning_tool.api.main.AsyncAnthropic"))
        stack.enter_context(patch("learning_tool.api.main.genai"))
        stack.enter_context(patch("learning_tool.api.deps.SessionStore"))
        stack.enter_context(patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}))
        c = stack.enter_context(TestClient(app))
        c.app.state.store_dir = store_dir  # type: ignore[attr-defined]
        c.app.state.context_store = ContextStore(store_dir)  # type: ignore[attr-defined]
        yield c
