import asyncio
from pathlib import Path

import typer
from anthropic import AsyncAnthropic

from core.evaluation.evaluate import evaluate_answer
from core.evaluation.prompt import build_evaluation_prompt
from core.ingestion.embedder import SentenceTransformerEmbedder
from core.ingestion.ingest import ingest
from core.ingestion.store import ChunkStore
from core.models import UserProfile
from core.question.generate import generate_question
from core.question.prompt import build_question_prompt
from core.rag.retriever import Retriever

app = typer.Typer()

DEFAULT_STORE = Path("contexts/store")


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


if __name__ == "__main__":
    app()
