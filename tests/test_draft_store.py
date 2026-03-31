import time
from pathlib import Path

from core.context_import.draft_store import DraftStore
from core.context_import.parser import ImportedContext


def test_draft_store_save_and_load(tmp_path: Path) -> None:
    store = DraftStore(tmp_path)
    imported = ImportedContext(
        goal="Learn stuff", questions=[("Area 1", ["Q1", "Q2"]), ("Area 2", ["Q3"])]
    )

    draft_id = store.save("test-ctx", imported)
    assert draft_id

    loaded = store.load("test-ctx", draft_id)
    assert loaded is not None
    assert loaded.goal == "Learn stuff"
    assert loaded.questions == [("Area 1", ["Q1", "Q2"]), ("Area 2", ["Q3"])]


def test_draft_store_load_wrong_context_returns_none(tmp_path: Path) -> None:
    store = DraftStore(tmp_path)
    imported = ImportedContext(goal="g", questions=[])
    draft_id = store.save("test-ctx", imported)

    assert store.load("other-ctx", draft_id) is None


def test_draft_store_expiration(tmp_path: Path) -> None:
    store = DraftStore(tmp_path, ttl_hours=0)  # Expire immediately
    imported = ImportedContext(goal="g", questions=[])
    draft_id = store.save("test-ctx", imported)

    time.sleep(0.01)  # Ensure some time passed
    assert store.load("test-ctx", draft_id) is None


def test_draft_store_load_missing_returns_none(tmp_path: Path) -> None:
    store = DraftStore(tmp_path)
    assert store.load("test-ctx", "non-existent") is None


def test_draft_store_load_invalid_id_returns_none(tmp_path: Path) -> None:
    store = DraftStore(tmp_path)
    # Testing that it handles basic path traversal attempts
    assert store.load("test-ctx", "../secrets") is None
    assert store.load("test-ctx", "") is None
