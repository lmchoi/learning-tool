from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer

from learning_tool.cli.main import print_evaluation_results, setup_context_resources
from learning_tool.core.models import ContextMetadata, EvaluationResult, UserProfile
from learning_tool.core.stores import Stores


def test_print_evaluation_results_all_fields() -> None:
    evaluation = EvaluationResult(
        score=8,
        strengths=["Strong grasp of the basics", "Good examples"],
        gaps=["Could explain the 'why' more"],
        missing_points=["Missing the final step"],
        suggested_addition="Add a summary of the benefits.",
        follow_up_question="How would you handle the edge case?",
    )
    output = print_evaluation_results(evaluation)

    assert "Score: 8/10" in output
    assert "Strengths:" in output
    assert "- Strong grasp of the basics" in output
    assert "- Good examples" in output
    assert "Gaps:" in output
    assert "- Could explain the 'why' more" in output
    assert "Missing points:" in output
    assert "- Missing the final step" in output
    assert "Suggested addition: Add a summary of the benefits." in output


def test_print_evaluation_results_minimal() -> None:
    evaluation = EvaluationResult(
        score=10,
        strengths=[],
        gaps=[],
        missing_points=[],
        suggested_addition=None,
        follow_up_question="Great job!",
    )
    output = print_evaluation_results(evaluation)

    assert output == "Score: 10/10"


def test_setup_context_resources_success(tmp_path: Path) -> None:
    context = "test-context"
    (tmp_path / context).mkdir()

    mock_stores = MagicMock(spec=Stores)
    mock_stores.store_dir = tmp_path
    mock_stores.context_store.load_context.return_value = ContextMetadata(
        goal="Test goal", focus_areas=["area1"]
    )
    mock_stores.retriever.retrieve.return_value = [("chunk1", 0.9), ("chunk2", 0.8)]

    retriever, profile, metadata, chunks = setup_context_resources(
        context=context,
        query="test query",
        experience_level="expert",
        k=2,
        stores=mock_stores,
    )

    assert retriever == mock_stores.retriever
    assert isinstance(profile, UserProfile)
    assert profile.experience_level == "expert"
    assert metadata is not None
    assert metadata.goal == "Test goal"
    assert chunks == ["chunk1", "chunk2"]
    mock_stores.retriever.retrieve.assert_called_once_with(context, "test query", 2)


def test_setup_context_resources_missing_context(tmp_path: Path) -> None:
    mock_stores = MagicMock(spec=Stores)
    mock_stores.store_dir = tmp_path

    with pytest.raises(typer.Exit) as exc:
        setup_context_resources(
            context="missing-context",
            query="test",
            experience_level="beginner",
            k=5,
            stores=mock_stores,
        )

    assert exc.value.exit_code == 1
