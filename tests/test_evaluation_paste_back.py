from core.evaluation.paste_back import parse_paste_back
from core.models import EvaluationResult


def test_parse_paste_back_well_formed() -> None:
    text = """
```json
{
  "question_id": "qid-1",
  "attempt_id": 123,
  "score": 8,
  "strengths": ["Good point"],
  "gaps": [],
  "missing_points": [],
  "suggested_addition": null,
  "follow_up_question": "Why?"
}
```
"""
    results = parse_paste_back(text)
    assert len(results) == 1
    aid, eval_res = results[0]
    assert aid == 123
    assert isinstance(eval_res, EvaluationResult)
    assert eval_res.score == 8


def test_parse_paste_back_multiple_blocks() -> None:
    text = """
```json
{ "question_id": "q1", "attempt_id": 1, "score": 10, "strengths": [], "gaps": [],
  "missing_points": [], "suggested_addition": null, "follow_up_question": "..." }
```
Some noise.
```json
{ "question_id": "q2", "attempt_id": 2, "score": 5, "strengths": [], "gaps": [],
  "missing_points": [], "suggested_addition": null, "follow_up_question": "..." }
```
"""
    results = parse_paste_back(text)
    assert len(results) == 2
    assert results[0][0] == 1
    assert results[1][0] == 2


def test_parse_paste_back_skips_malformed_json() -> None:
    text = "```json { invalid } ```"
    assert parse_paste_back(text) == []


def test_parse_paste_back_skips_missing_attempt_id() -> None:
    text = """
```json
{ "question_id": "q1", "score": 10, "strengths": [], "gaps": [], "missing_points": [],
  "suggested_addition": null, "follow_up_question": "..." }
```
"""
    assert parse_paste_back(text) == []


def test_parse_paste_back_skips_missing_required_fields() -> None:
    text = """
```json
{ "attempt_id": 1, "score": 10 }
```
"""
    assert parse_paste_back(text) == []


def test_parse_paste_back_no_code_blocks_fallback() -> None:
    text = (
        '{ "question_id": "q1", "attempt_id": 99, "score": 9, "strengths": [], "gaps": [], '
        '"missing_points": [], "suggested_addition": null, "follow_up_question": "..." }'
    )
    results = parse_paste_back(text)
    assert len(results) == 1
    assert results[0][0] == 99
