# ADR 015 — Context name validation rules

## Status
Accepted

## Context

The admin UI collects a context name from the user before redirecting to the setup
flow. The name becomes a directory on disk and appears in URLs — both constrain what
characters are valid. Without validation, a user could enter a name that breaks the
URL structure (spaces, special characters) or escapes the storage directory (path
traversal).

The tool previously assumed the context name was already valid — it was entered
directly in the URL bar. The admin creation form is the first place where raw user
input is collected and used as a context identifier.

## Decision

Context names must match the slug convention:

```
^[a-z0-9]+(-[a-z0-9]+)*$
```

- Lowercase letters (`a–z`), digits (`0–9`), and hyphens (`-`) only
- Must start and end with a letter or digit (no leading or trailing hyphens)
- Consecutive hyphens are not allowed (`my--context` is rejected)
- Minimum length: 4 characters
- Maximum length: 100 characters

The validator lives in `core/context_name.py` and raises `ValueError` on failure.
The route calls it and returns the form with the error message — no transformation
is applied.

## Slug convention

Lowercase-with-hyphens is the standard slug format used by GitHub repository names,
npm packages, and Python package names (with hyphens). It is URL-safe, readable, and
safe as a filesystem directory name.

## Length bounds

**Maximum: 100 characters** — matches the GitHub repository name limit. There is no
technical reason to be stricter; this bound is familiar and leaves headroom for
descriptive names.

**Minimum: 4 characters** — a 1–3 character name would be either a single letter, an
initialism, or too abbreviated to be meaningful. A minimum of 4 encourages names that
communicate intent (e.g. `rust`, `sql-joins`, `python-asyncio`). Single-letter or
two-character context names would be confusing to navigate and search.

## No transformation

Invalid input is rejected with an error message — the user must supply a valid slug.
Automatic transformation (e.g. lowercasing, replacing spaces with hyphens) was
considered and deferred:

- Transformation hides the canonical form from the user; they see `My Context`
  in the input but `my-context` in the URL. The mismatch is confusing.
- Live slug preview (showing the transformed result as the user types) would make
  transformation usable, but preview and transformation should land together rather
  than one without the other.
- Rejecting invalid input is simpler and more predictable.

## Future multi-user note

Context names are currently per-installation — there is one namespace and all
contexts live under `STORE_DIR`. If the tool becomes multi-user, each user would
likely have their own namespace, and the context name would be scoped to the user.
The slug convention remains appropriate; only the storage layout and URL structure
would change.

## Revisit if

- Live slug preview is added — at that point, automatic transformation becomes viable
  and the no-transformation decision should be reconsidered.
- Multi-user support is introduced — the validator may need to accept a user scope
  parameter, or a separate per-user uniqueness check may be required.
