import re

_SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_MIN_LEN = 4
_MAX_LEN = 100


def validate_context_name(name: str) -> None:
    """Validate a context name against the slug convention.

    Rules:
    - Between 4 and 100 characters (inclusive)
    - Matches ``^[a-z0-9]+(-[a-z0-9]+)*$`` — lowercase letters and digits, with
      single hyphens as separators; must start and end with a letter or digit;
      consecutive hyphens are not allowed

    Raises ``ValueError`` with a human-readable message on failure.
    No transformation is applied — the caller must supply a valid slug.
    """
    if len(name) < _MIN_LEN:
        raise ValueError(f"Context name must be at least {_MIN_LEN} characters; got {len(name)!r}.")
    if len(name) > _MAX_LEN:
        raise ValueError(f"Context name must be at most {_MAX_LEN} characters; got {len(name)!r}.")
    if not _SLUG_RE.match(name):
        raise ValueError(
            "Context name must contain only lowercase letters, digits, and hyphens, "
            "and must start and end with a letter or digit."
        )
