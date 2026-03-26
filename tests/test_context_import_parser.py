import pytest

from core.context_import.parser import ImportedContext, parse_import

_VALID = """\
## Goal
Learn the basics of machine learning.

## Questions

### Supervised Learning
- What is a training set?
- What is overfitting?

### Neural Networks
- What is a layer in a neural network?
- How does backpropagation work?
"""


def test_parse_import_returns_imported_context() -> None:
    result = parse_import(_VALID)
    assert isinstance(result, ImportedContext)


def test_parse_import_extracts_goal() -> None:
    result = parse_import(_VALID)
    assert result.goal == "Learn the basics of machine learning."


def test_parse_import_extracts_focus_areas() -> None:
    result = parse_import(_VALID)
    assert result.focus_areas == ["Supervised Learning", "Neural Networks"]


def test_parse_import_extracts_questions() -> None:
    result = parse_import(_VALID)
    assert result.questions[0] == (
        "Supervised Learning",
        ["What is a training set?", "What is overfitting?"],
    )
    assert result.questions[1] == (
        "Neural Networks",
        ["What is a layer in a neural network?", "How does backpropagation work?"],
    )


def test_parse_import_strips_whitespace_from_goal() -> None:
    text = "## Goal\n  Padded goal.  \n\n## Questions\n\n### Area\n- Q?\n"
    result = parse_import(text)
    assert result.goal == "Padded goal."


def test_parse_import_raises_on_missing_goal_section() -> None:
    text = "## Questions\n\n### Area\n- Q?\n"
    with pytest.raises(ValueError, match="Goal"):
        parse_import(text)


def test_parse_import_raises_on_empty_goal() -> None:
    text = "## Goal\n\n## Questions\n\n### Area\n- Q?\n"
    with pytest.raises(ValueError, match="empty"):
        parse_import(text)


def test_parse_import_raises_on_missing_questions_section() -> None:
    text = "## Goal\nLearn something.\n"
    with pytest.raises(ValueError, match="Questions"):
        parse_import(text)


def test_parse_import_raises_when_no_focus_areas_found() -> None:
    text = "## Goal\nLearn something.\n\n## Questions\n"
    with pytest.raises(ValueError, match="No focus areas"):
        parse_import(text)


def test_parse_import_ignores_bullets_without_text() -> None:
    text = "## Goal\nGoal.\n\n## Questions\n\n### Area\n- Valid question?\n-\n- \n"
    result = parse_import(text)
    assert result.questions[0][1] == ["Valid question?"]


def test_parse_import_strips_whitespace_from_questions() -> None:
    text = "## Goal\nGoal.\n\n## Questions\n\n### Area\n-  Padded question?  \n"
    result = parse_import(text)
    assert result.questions[0][1] == ["Padded question?"]


def test_parse_import_handles_crlf_line_endings() -> None:
    text = "## Goal\r\nLearn something.\r\n\r\n## Questions\r\n\r\n### Area\r\n- Q?\r\n"
    result = parse_import(text)
    assert result.goal == "Learn something."
    assert result.focus_areas == ["Area"]
