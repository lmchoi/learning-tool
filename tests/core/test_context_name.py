import pytest

from learning_tool.core.context_name import validate_context_name


@pytest.mark.parametrize(
    "name",
    [
        "abcd",
        "python-asyncio",
        "my-context",
        "a1b2",
        "context-123",
        "a" * 100,  # max length
    ],
)
def test_valid_names(name: str) -> None:
    validate_context_name(name)  # should not raise


@pytest.mark.parametrize(
    "name",
    [
        "abc",  # too short (3 chars)
        "ab",  # too short (2 chars)
        "a",  # too short (1 char)
        "",  # empty
    ],
)
def test_too_short(name: str) -> None:
    with pytest.raises(ValueError, match="at least 4"):
        validate_context_name(name)


def test_too_long() -> None:
    with pytest.raises(ValueError, match="at most 100"):
        validate_context_name("a" * 101)


@pytest.mark.parametrize(
    "name",
    [
        "My-Context",  # uppercase
        "my context",  # space
        "my_context",  # underscore
        "my.context",  # dot
        "-mycontext",  # leading hyphen
        "mycontext-",  # trailing hyphen
    ],
)
def test_invalid_characters(name: str) -> None:
    with pytest.raises(ValueError, match="lowercase letters"):
        validate_context_name(name)


@pytest.mark.parametrize(
    "name",
    [
        "../etc",
        "../../etc/passwd",
        "../secret",
        "..",
        ".",
    ],
)
def test_path_traversal_rejected(name: str) -> None:
    with pytest.raises(ValueError):
        validate_context_name(name)
