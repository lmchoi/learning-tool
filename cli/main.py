import asyncio
from pathlib import Path

import typer
from anthropic import AsyncAnthropic

from core.evaluation.evaluate import evaluate_answer
from core.evaluation.prompt import build_evaluation_prompt
from core.ingestion.context import extract_context
from core.ingestion.embedder import SentenceTransformerEmbedder
from core.ingestion.ingest import ingest
from core.ingestion.sources import walk_source_dir
from core.ingestion.store import ChunkStore, ContextStore
from core.models import UserProfile
from core.question.generate import generate_question
from core.question.prompt import build_question_prompt
from core.rag.retriever import Retriever
from core.session.store import SessionStore
from core.settings import STORE_DIR as DEFAULT_STORE

app = typer.Typer()


@app.command()
def init(
    source: Path = typer.Option(..., help="Directory of source documents"),
    context: str = typer.Option(..., help="Context name"),
    store_dir: Path = typer.Option(DEFAULT_STORE, help="Path to the chunk store"),
) -> None:
    """Ingest all documents in a source directory into a context."""
    if not source.exists() or not source.is_dir():
        typer.echo(f"Error: source directory not found: {source}", err=True)
        raise typer.Exit(code=1)
    paths = [p for p in walk_source_dir(source) if p.name != "GOAL.md"]
    if not paths:
        typer.echo(f"Error: no supported files found in {source}", err=True)
        raise typer.Exit(code=1)
    store = ChunkStore(store_dir)
    embedder = SentenceTransformerEmbedder()
    ingest(context=context, paths=paths, embedder=embedder, store=store)
    typer.echo(f"Ingested {len(paths)} file(s) into context '{context}'")

    goal_file = source / "GOAL.md"
    if goal_file.exists():
        goal_text = goal_file.read_text()

        async def _extract() -> None:
            async with AsyncAnthropic() as client:
                metadata = await extract_context(goal_text, client)
            ContextStore(store_dir).save_context(context, metadata)
            typer.echo(f"Extracted goal: {metadata.goal}")

        asyncio.run(_extract())
    else:
        typer.echo("No GOAL.md found — skipping context extraction")


@app.command()
def ingest_context(
    context: str = typer.Argument(..., help="Context name to ingest into"),
    files: list[Path] = typer.Argument(..., help="Paths to files to ingest"),
    store_dir: Path = typer.Option(DEFAULT_STORE, help="Path to the chunk store"),
) -> None:
    """Chunk, embed, and store documents for a context."""
    missing = [f for f in files if not f.exists()]
    if missing:
        typer.echo(f"Error: file(s) not found: {', '.join(str(f) for f in missing)}", err=True)
        raise typer.Exit(code=1)
    store = ChunkStore(store_dir)
    embedder = SentenceTransformerEmbedder()
    ingest(context=context, paths=files, embedder=embedder, store=store)
    typer.echo(f"Ingested {len(files)} file(s) into context '{context}'")


def _build_prompt(
    context: str,
    query: str,
    experience_level: str,
    k: int,
    store_dir: Path,
) -> str:
    ctx_dir = store_dir / context
    if not ctx_dir.exists():
        typer.echo(f"Error: context '{context}' not found. Run 'make ingest' first.", err=True)
        raise typer.Exit(code=1)
    store = ChunkStore(store_dir)
    embedder = SentenceTransformerEmbedder()
    retriever = Retriever(store=store, embedder=embedder)
    profile = UserProfile(experience_level=experience_level)
    chunks = [chunk for chunk, _ in retriever.retrieve(context, query, k)]
    return build_question_prompt(chunks, profile)


@app.command()
def question_prompt(
    context: str = typer.Argument(..., help="Context name (must be ingested)"),
    query: str = typer.Argument(..., help="Query to retrieve relevant chunks"),
    experience_level: str = typer.Option("intermediate", help="Learner experience level"),
    k: int = typer.Option(5, help="Number of chunks to retrieve"),
    store_dir: Path = typer.Option(DEFAULT_STORE, help="Path to the chunk store"),
) -> None:
    """Print the question prompt that would be sent to Claude."""
    print(_build_prompt(context, query, experience_level, k, store_dir))


@app.command()
def question(
    context: str = typer.Argument(..., help="Context name (must be ingested)"),
    query: str = typer.Argument(..., help="Query to retrieve relevant chunks"),
    experience_level: str = typer.Option("intermediate", help="Learner experience level"),
    k: int = typer.Option(5, help="Number of chunks to retrieve"),
    store_dir: Path = typer.Option(DEFAULT_STORE, help="Path to the chunk store"),
) -> None:
    """Generate a practice question from retrieved chunks using Claude."""
    prompt = _build_prompt(context, query, experience_level, k, store_dir)
    result = asyncio.run(generate_question(prompt, AsyncAnthropic()))
    print(result.text)


@app.command()
def evaluate(
    context: str = typer.Argument(..., help="Context name (must be ingested)"),
    query: str = typer.Argument(..., help="Query to retrieve relevant chunks"),
    question_text: str = typer.Argument(..., help="The question that was asked"),
    answer_text: str = typer.Argument(..., help="The learner's answer to evaluate"),
    experience_level: str = typer.Option("intermediate", help="Learner experience level"),
    k: int = typer.Option(5, help="Number of chunks to retrieve"),
    store_dir: Path = typer.Option(DEFAULT_STORE, help="Path to the chunk store"),
) -> None:
    """Evaluate a learner's answer to a question using Claude."""
    store = ChunkStore(store_dir)
    embedder = SentenceTransformerEmbedder()
    retriever = Retriever(store=store, embedder=embedder)
    profile = UserProfile(experience_level=experience_level)
    chunks = [chunk for chunk, _ in retriever.retrieve(context, query, k)]
    prompt = build_evaluation_prompt(
        question=question_text,
        answer=answer_text,
        chunks=chunks,
        profile=profile,
    )
    result = asyncio.run(evaluate_answer(prompt, AsyncAnthropic()))
    print(f"Score: {result.score}/10")
    if result.strengths:
        print("\nStrengths:")
        for s in result.strengths:
            print(f"  - {s}")
    if result.gaps:
        print("\nGaps:")
        for g in result.gaps:
            print(f"  - {g}")
    if result.missing_points:
        print("\nMissing points:")
        for m in result.missing_points:
            print(f"  - {m}")
    if result.suggested_addition:
        print(f"\nSuggested addition: {result.suggested_addition}")
    if result.follow_up_question:
        print(f"\nFollow-up question: {result.follow_up_question}")


@app.command()
def practice(
    context: str = typer.Argument(..., help="Context name (must be ingested)"),
    query: str = typer.Argument(..., help="Topic to generate questions about"),
    experience_level: str = typer.Option("intermediate", help="Learner experience level"),
    k: int = typer.Option(5, help="Number of chunks to retrieve"),
    store_dir: Path = typer.Option(DEFAULT_STORE, help="Path to the chunk store"),
) -> None:
    """Interactive practice loop — question, answer, evaluate, repeat."""
    ctx_dir = store_dir / context
    if not ctx_dir.exists():
        typer.echo(f"Error: context '{context}' not found. Run 'make ingest' first.", err=True)
        raise typer.Exit(code=1)

    async def loop() -> None:
        client = AsyncAnthropic()
        profile = UserProfile(experience_level=experience_level)
        chunk_store = ChunkStore(store_dir)
        embedder = SentenceTransformerEmbedder()
        retriever = Retriever(store=chunk_store, embedder=embedder)
        # Chunks are retrieved once per topic query and reused across follow-ups,
        # since follow-up questions target gaps within the same retrieved context.
        chunks = [chunk for chunk, _ in retriever.retrieve(context, query, k)]

        session_store = SessionStore(store_dir, context)
        session_id = session_store.start_session()

        next_question: str | None = None
        while True:
            if next_question is None:
                prompt = build_question_prompt(chunks, profile)
                result = await generate_question(prompt, client)
                next_question = result.text

            print(f"\n{next_question}\n")
            answer = typer.prompt("Your answer")

            eval_prompt = build_evaluation_prompt(
                question=next_question,
                answer=answer,
                chunks=chunks,
                profile=profile,
            )
            evaluation = await evaluate_answer(eval_prompt, client)

            session_store.record(session_id, next_question, answer, evaluation.score)

            print(f"\nScore: {evaluation.score}/10")
            if evaluation.strengths:
                print("\nStrengths:")
                for s in evaluation.strengths:
                    print(f"  - {s}")
            if evaluation.gaps:
                print("\nGaps:")
                for g in evaluation.gaps:
                    print(f"  - {g}")
            if evaluation.missing_points:
                print("\nMissing points:")
                for m in evaluation.missing_points:
                    print(f"  - {m}")
            if evaluation.suggested_addition:
                print(f"\nSuggested addition: {evaluation.suggested_addition}")

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
