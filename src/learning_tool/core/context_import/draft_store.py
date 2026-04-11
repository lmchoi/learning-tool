import json
import time
import uuid
from pathlib import Path

from .parser import ImportedContext


class DraftStore:
    def __init__(self, store_dir: Path, ttl_hours: int = 24):
        self.drafts_dir = store_dir / "drafts"
        self.drafts_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_hours * 3600

    def save(self, context_name: str, imported: ImportedContext) -> str:
        draft_id = str(uuid.uuid4())
        file_path = self.drafts_dir / f"{draft_id}.json"

        data = {
            "context_name": context_name,
            "created_at": time.time(),
            "goal": imported.goal,
            "questions": imported.questions,
        }

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

        return draft_id

    def load(self, context_name: str, draft_id: str) -> ImportedContext | None:
        # Basic validation to prevent path traversal
        if not draft_id or not all(c.isalnum() or c == "-" for c in draft_id):
            return None

        file_path = self.drafts_dir / f"{draft_id}.json"
        if not file_path.exists():
            return None

        with open(file_path) as f:
            data = json.load(f)

        # Validate context name match
        if data.get("context_name") != context_name:
            return None

        # Expire old drafts
        if time.time() - data.get("created_at", 0) > self.ttl_seconds:
            file_path.unlink(missing_ok=True)
            return None

        # JSON loads tuples as lists, convert back to tuple for ImportedContext
        questions = [(item[0], item[1]) for item in data["questions"]]
        return ImportedContext(goal=data["goal"], questions=questions)
