from pathlib import Path

from fastapi.templating import Jinja2Templates

from learning_tool.core.question.store import QuestionBankStore
from learning_tool.core.session.store import SessionStore
from learning_tool.resources import PROMPTS_DIR

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

_IMPORT_PROMPT: str | None = None
_IMPORT_PROMPT_PATH = PROMPTS_DIR / "context_import_prompt.md"


def get_import_prompt() -> str:
    global _IMPORT_PROMPT
    if _IMPORT_PROMPT is None:
        _IMPORT_PROMPT = _IMPORT_PROMPT_PATH.read_text()
    return _IMPORT_PROMPT


def get_session_store(
    cache: dict[str, SessionStore], store_dir: Path, context: str
) -> SessionStore:
    if context not in cache:
        cache[context] = SessionStore(store_dir, context)
    return cache[context]


def get_bank_store(
    cache: dict[str, QuestionBankStore], store_dir: Path, context: str
) -> QuestionBankStore:
    if context not in cache:
        cache[context] = QuestionBankStore(store_dir, context)
    return cache[context]
