import sqlite3
from pathlib import Path

from learning_tool.core.models import BankQuestion

_SCHEMA = """
CREATE TABLE IF NOT EXISTS bank_questions (
    id         TEXT PRIMARY KEY,
    focus_area TEXT NOT NULL,
    question   TEXT NOT NULL
);
"""


class QuestionBankStore:
    def __init__(self, base_dir: Path, context: str) -> None:
        ctx_dir = base_dir / context
        ctx_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = ctx_dir / "bank.db"
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(_SCHEMA)

    def add(self, questions: list[BankQuestion]) -> int:
        """Insert questions, ignoring duplicates. Returns the number of new rows added."""
        with sqlite3.connect(self._db_path) as conn:
            before: int = conn.execute("SELECT COUNT(*) FROM bank_questions").fetchone()[0]
            conn.executemany(
                "INSERT OR IGNORE INTO bank_questions (id, focus_area, question) VALUES (?, ?, ?)",
                [(q.id, q.focus_area, q.question) for q in questions],
            )
            after: int = conn.execute("SELECT COUNT(*) FROM bank_questions").fetchone()[0]
            return after - before

    def list(self) -> list[BankQuestion]:
        """Return all questions in insertion order."""
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT id, focus_area, question FROM bank_questions ORDER BY rowid"
            ).fetchall()
            return [BankQuestion(id=row[0], focus_area=row[1], question=row[2]) for row in rows]

    def get_random(self, focus_area: str | None = None) -> BankQuestion | None:
        """Return a random question from the bank, or None if the bank is empty.

        If focus_area is provided, restrict to questions with that focus area.
        """
        sql = "SELECT id, focus_area, question FROM bank_questions"
        params: tuple[str, ...] = ()
        if focus_area is not None:
            sql += " WHERE focus_area = ?"
            params = (focus_area,)
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(sql + " ORDER BY RANDOM() LIMIT 1", params).fetchone()
        if row is None:
            return None
        return BankQuestion(id=row[0], focus_area=row[1], question=row[2])
