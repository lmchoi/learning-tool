import asyncio
import logging
from pathlib import Path

import typer
from anthropic import AsyncAnthropic

from learning_tool.core.evaluation.evaluate import evaluate_answer
from learning_tool.core.evaluation.prompt import build_evaluation_prompt
from learning_tool.core.ingestion.context import extract_context
from learning_tool.core.ingestion.ingest import ingest
from learning_tool.core.ingestion.sources import walk_source_dir
from learning_tool.core.models import ContextMetadata, EvaluationResult, UserProfile
from learning_tool.core.question.generate import generate_question
from learning_tool.core.question.loader import load_questions
from learning_tool.core.question.prompt import build_question_prompt
from learning_tool.core.question.store import QuestionBankStore
from learning_tool.core.rag.retriever import Retriever
from learning_tool.core.session.store import SessionStore
from learning_tool.core.settings import LOG_LEVEL
from learning_tool.core.settings import STORE_DIR as DEFAULT_STORE
from learning_tool.core.stores import Stores, create_stores

logger = logging.getLogger(__name__)

app = typer.Typer()


@app.callback()
def main(
    ctx: typer.Context,
    store_dir: Path = typer.Option(
        DEFAULT_STORE, help="Path to the store directory", envvar="STORE_DIR"
    ),
) -> None:
    """Learning Tool CLI."""
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    ctx.obj = create_stores(store_dir)


@app.command()
def init(
    ctx: typer.Context,
    source: Path = typer.Option(..., help="Directory of source documents"),
    context: str = typer.Option(..., help="Context name"),
    force: bool = typer.Option(False, "--force", help="Wipe and reingest even if context exists"),
) -> None:
    """Ingest all documents in a source directory into a context."""
    stores: Stores = ctx.obj
    if not source.exists() or not source.is_dir():
        typer.echo(f"Error: source directory not found: {source}", err=True)
        raise typer.Exit(code=1)
    if not force:
        existing = stores.context_store.load_context(context)
        if existing:
            typer.echo(f"Context '{context}' already exists. Focus areas:")
            for area in existing.focus_areas:
                typer.echo(f"  - {area}")
            typer.echo("Run with --force to reingest and overwrite.")
            raise typer.Exit(code=1)
    all_paths = walk_source_dir(source)
    paths = [p for p in all_paths if p.name != "GOAL.md"]
    skipped = len(all_paths) - len(paths)
    if skipped:
        logger.debug("excluded %d GOAL.md file(s) from ingestion", skipped)
    if not paths:
        typer.echo(f"Error: no supported files found in {source}", err=True)
        raise typer.Exit(code=1)

    ingest(context=context, paths=paths, embedder=stores.embedder, store=stores.chunk_store)
    typer.echo(f"Ingested {len(paths)} file(s) into context '{context}'")

    goal_file = source / "GOAL.md"
    if goal_file.exists():
        goal_text = goal_file.read_text()

        async def _extract() -> None:
            async with AsyncAnthropic() as client:
                metadata = await extract_context(goal_text, client)
            stores.context_store.save_context(context, metadata)
            context_yaml_path = stores.store_dir / context / "context.yaml"
            typer.echo(f"\nContext '{context}' ready.\n")
            typer.echo(f"Goal: {metadata.goal}")
            if metadata.focus_areas:
                typer.echo("Focus areas:")
                for area in metadata.focus_areas:
                    typer.echo(f"  - {area}")
            typer.echo(f"\nTo adjust, edit: {context_yaml_path}")

        asyncio.run(_extract())
    else:
        typer.echo("No GOAL.md found — skipping context extraction")


@app.command()
def ingest_context(
    ctx: typer.Context,
    context: str = typer.Argument(..., help="Context name to ingest into"),
    files: list[Path] = typer.Argument(..., help="Paths to files to ingest"),
) -> None:
    """Chunk, embed, and store documents for a context."""
    stores: Stores = ctx.obj
    missing = [f for f in files if not f.exists()]
    if missing:
        typer.echo(f"Error: file(s) not found: {', '.join(str(f) for f in missing)}", err=True)
        raise typer.Exit(code=1)
    ingest(context=context, paths=files, embedder=stores.embedder, store=stores.chunk_store)
    typer.echo(f"Ingested {len(files)} file(s) into context '{context}'")


@app.command()
def load_questions_cmd(
    ctx: typer.Context,
    context: str = typer.Option(..., help="Context name"),
    file: Path = typer.Option(..., help="Path to YAML question file"),
) -> None:
    """Load questions from a YAML file into the question bank."""
    stores: Stores = ctx.obj
    if not file.exists():
        typer.echo(f"Error: file not found: {file}", err=True)
        raise typer.Exit(code=1)
    try:
        questions = load_questions(file)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    # Context-scoped stores are created on demand using the shared store_dir
    bank = QuestionBankStore(stores.store_dir, context)
    added = bank.add(questions)
    typer.echo(f"Loaded {added} new question(s) into '{context}' ({len(questions)} in file).")


def setup_context_resources(
    context: str,
    query: str,
    experience_level: str,
    k: int,
    stores: Stores,
) -> tuple[Retriever, UserProfile, ContextMetadata | None, list[str]]:
    """Validate context, load profile/metadata, and retrieve chunks."""
    ctx_dir = stores.store_dir / context
    if not ctx_dir.exists():
        typer.echo(f"Error: context '{context}' not found. Run 'make ingest' first.", err=True)
        raise typer.Exit(code=1)

    metadata = stores.context_store.load_context(context)
    profile = UserProfile(experience_level=experience_level)
    chunks = [chunk for chunk, _ in stores.retriever.retrieve(context, query, k)]
    return stores.retriever, profile, metadata, chunks


def print_evaluation_results(evaluation: EvaluationResult) -> str:
    """Format evaluation results into a printable string."""
    parts = [f"Score: {evaluation.score}/10"]
    if evaluation.strengths:
        parts.append("\nStrengths:")
        for s in evaluation.strengths:
            parts.append(f"  - {s}")
    if evaluation.gaps:
        parts.append("\nGaps:")
        for g in evaluation.gaps:
            parts.append(f"  - {g}")
    if evaluation.missing_points:
        parts.append("\nMissing points:")
        for m in evaluation.missing_points:
            parts.append(f"  - {m}")
    if evaluation.suggested_addition:
        parts.append(f"\nSuggested addition: {evaluation.suggested_addition}")
    return "\n".join(parts)


@app.command()
def question_prompt(
    ctx: typer.Context,
    context: str = typer.Argument(..., help="Context name (must be ingested)"),
    query: str = typer.Argument(..., help="Query to retrieve relevant chunks"),
    experience_level: str = typer.Option("intermediate", help="Learner experience level"),
    k: int = typer.Option(5, help="Number of chunks to retrieve"),
) -> None:
    """Print the question prompt that would be sent to Claude."""
    stores: Stores = ctx.obj
    _, profile, metadata, chunks = setup_context_resources(
        context, query, experience_level, k, stores
    )
    print(build_question_prompt(chunks, profile, metadata))


@app.command()
def question(
    ctx: typer.Context,
    context: str = typer.Argument(..., help="Context name (must be ingested)"),
    query: str = typer.Argument(..., help="Query to retrieve relevant chunks"),
    experience_level: str = typer.Option("intermediate", help="Learner experience level"),
    k: int = typer.Option(5, help="Number of chunks to retrieve"),
) -> None:
    """Generate a practice question from retrieved chunks using Claude."""
    stores: Stores = ctx.obj
    _, profile, metadata, chunks = setup_context_resources(
        context, query, experience_level, k, stores
    )
    prompt = build_question_prompt(chunks, profile, metadata)
    result = asyncio.run(generate_question(prompt, AsyncAnthropic()))
    print(result.text)


@app.command()
def evaluate(
    ctx: typer.Context,
    context: str = typer.Argument(..., help="Context name (must be ingested)"),
    query: str = typer.Argument(..., help="Query to retrieve relevant chunks"),
    question_text: str = typer.Argument(..., help="The question that was asked"),
    answer_text: str = typer.Argument(..., help="The learner's answer to evaluate"),
    experience_level: str = typer.Option("intermediate", help="Learner experience level"),
    k: int = typer.Option(5, help="Number of chunks to retrieve"),
) -> None:
    """Evaluate a learner's answer to a question using Claude."""
    stores: Stores = ctx.obj
    _, profile, metadata, chunks = setup_context_resources(
        context, query, experience_level, k, stores
    )
    eval_prompt = build_evaluation_prompt(
        question=question_text,
        answer=answer_text,
        chunks=chunks,
        profile=profile,
        metadata=metadata,
    )
    result = asyncio.run(evaluate_answer(eval_prompt, AsyncAnthropic()))
    print(print_evaluation_results(result))
    if result.follow_up_question:
        print(f"\nFollow-up question: {result.follow_up_question}")


@app.command()
def practice(
    ctx: typer.Context,
    context: str = typer.Argument(..., help="Context name (must be ingested)"),
    query: str = typer.Argument(..., help="Topic to generate questions about"),
    experience_level: str = typer.Option("intermediate", help="Learner experience level"),
    k: int = typer.Option(5, help="Number of chunks to retrieve"),
) -> None:
    """Interactive practice loop — question, answer, evaluate, repeat."""
    stores: Stores = ctx.obj

    async def loop() -> None:
        client = AsyncAnthropic()
        _, profile, metadata, chunks = setup_context_resources(
            context, query, experience_level, k, stores
        )

        # Context-scoped stores are created on demand using the shared store_dir
        session_store = SessionStore(stores.store_dir, context)
        session_id = session_store.start_session()
        next_question: str | None = None
        while True:
            if next_question is None:
                prompt = build_question_prompt(chunks, profile, metadata)
                result = await generate_question(prompt, client)
                next_question = result.text

            print(f"\n{next_question}\n")
            answer = typer.prompt("Your answer")

            eval_prompt = build_evaluation_prompt(
                question=next_question,
                answer=answer,
                chunks=chunks,
                profile=profile,
                metadata=metadata,
            )
            evaluation = await evaluate_answer(eval_prompt, client)

            session_store.record(session_id, next_question, answer, evaluation.score)

            print(f"\n{print_evaluation_results(evaluation)}")

            if evaluation.follow_up_question:
                next_question = evaluation.follow_up_question
            elif typer.confirm("\nAnother question?", default=True):
                next_question = None
            else:
                break

    try:
        asyncio.run(loop())
    except (KeyboardInterrupt, typer.Abort):
        typer.echo("\nBye.")


if __name__ == "__main__":
    app()
