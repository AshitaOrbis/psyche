"""Psyche CLI — corpus ingestion, analysis, and profile synthesis."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="psyche", help="Psychometric corpus analysis and profiling")
console = Console()

PROJECT_ROOT = Path(__file__).parent.parent.parent
PROFILES_DIR = PROJECT_ROOT / "profiles"
DATA_DIR = PROJECT_ROOT / "data"


@app.command()
def ingest(
    source: str = typer.Argument(
        help="Source to ingest: chatgpt, claude_ai, sms, academic, facebook, all"
    ),
) -> None:
    """Ingest text corpus from a source."""
    from .corpus.manager import ingest_source, ingest_all, save_samples, compute_stats

    console.print(f"[bold]Ingesting from {source}...[/bold]")

    if source == "all":
        samples = ingest_all()
    else:
        samples = ingest_source(source)

    console.print(f"  Parsed {len(samples)} samples ({sum(s.word_count for s in samples):,} words)")

    # Save raw ingested samples
    out_path = DATA_DIR / "ingested" / f"{source}.jsonl"
    save_samples(samples, out_path)
    console.print(f"  Saved to {out_path}")

    # Show stats
    st = compute_stats(samples)
    _print_stats(st)


@app.command()
def stats() -> None:
    """Show corpus statistics for all ingested sources."""
    from .corpus.manager import load_samples, compute_stats

    ingested_dir = DATA_DIR / "ingested"
    if not ingested_dir.exists():
        console.print("[yellow]No ingested data. Run 'psyche ingest all' first.[/yellow]")
        return

    all_samples = []
    for jsonl in sorted(ingested_dir.glob("*.jsonl")):
        all_samples.extend(load_samples(jsonl))

    st = compute_stats(all_samples)
    _print_stats(st)


@app.command()
def sample(
    target_words: int = typer.Option(50_000, help="Target word count for sample"),
    seed: int = typer.Option(42, help="Random seed for reproducibility"),
) -> None:
    """Create a diversity-sampled corpus subset for analysis."""
    from .corpus.manager import load_samples, sample_corpus, save_samples, compute_stats

    ingested_dir = DATA_DIR / "ingested"
    if not ingested_dir.exists():
        console.print("[yellow]No ingested data. Run 'psyche ingest all' first.[/yellow]")
        return

    all_samples = []
    for jsonl in sorted(ingested_dir.glob("*.jsonl")):
        all_samples.extend(load_samples(jsonl))

    # Filter to self-authored only for sampling
    self_samples = [s for s in all_samples if s.author == "self"]
    console.print(f"Total self-authored samples: {len(self_samples)} ({sum(s.word_count for s in self_samples):,} words)")

    sampled = sample_corpus(self_samples, target_words=target_words, seed=seed)
    console.print(f"Sampled: {len(sampled)} samples ({sum(s.word_count for s in sampled):,} words)")

    out_path = DATA_DIR / "sampled" / "corpus.jsonl"
    save_samples(sampled, out_path)
    console.print(f"Saved to {out_path}")

    st = compute_stats(sampled)
    _print_stats(st)


@app.command()
def analyze(
    method: str = typer.Argument(
        help="Analysis method: llm-claude, empath, all"
    ),
    model: str = typer.Option("claude-sonnet-4-5-20250514", help="LLM model to use"),
    max_samples: int = typer.Option(500, help="Max samples for LLM analysis"),
) -> None:
    """Run personality inference on sampled corpus."""
    from .corpus.manager import load_samples

    sampled_path = DATA_DIR / "sampled" / "corpus.jsonl"
    if not sampled_path.exists():
        console.print("[yellow]No sampled corpus. Run 'psyche sample' first.[/yellow]")
        return

    samples = load_samples(sampled_path)
    # For LLM, limit samples to keep API costs reasonable
    llm_samples = samples[:max_samples] if len(samples) > max_samples else samples

    output_dir = PROFILES_DIR / "analysis"

    if method in ("llm-claude", "all"):
        from .methods.llm_claude import run_full_analysis
        run_full_analysis(llm_samples, model=model, output_dir=output_dir)

    if method in ("empath", "all"):
        from .methods.empath_analysis import analyze_empath
        analyze_empath(samples, output_dir=output_dir)


@app.command()
def synthesize(
    self_report: Path | None = typer.Option(None, help="Path to web app export JSON"),
    chatledger_db: Path | None = typer.Option(
        None, "--chatledger-db",
        help="Path to ChatLedger SQLite database (or set PSYCHE_CHATLEDGER_DB env var)",
        envvar="PSYCHE_CHATLEDGER_DB",
    ),
) -> None:
    """Merge all analysis sources into a unified profile."""
    from .synthesis.merge import merge_profile
    from .synthesis.narrative import generate_narrative_report, generate_claude_md_snippet

    analysis_dir = PROFILES_DIR / "analysis"
    if not analysis_dir.exists():
        console.print("[yellow]No analysis results. Run 'psyche analyze all' first.[/yellow]")
        return

    console.print("[bold]Synthesizing profile...[/bold]")
    profile = merge_profile(analysis_dir, self_report)

    # Populate corpus metadata from sampled data
    from .corpus.manager import load_samples, compute_stats
    sampled_path = DATA_DIR / "sampled" / "corpus.jsonl"
    if sampled_path.exists():
        sampled = load_samples(sampled_path)
        st = compute_stats(sampled)
        profile.metadata.corpus_word_count = st.total_words
        profile.metadata.corpus_sources = list(st.by_source.keys())

    # Generate persona model
    from .synthesis.persona import generate_persona_model
    interview_path = analysis_dir / "interview.json"
    interview_transcript = None
    if interview_path.exists():
        import json
        interview_data = json.loads(interview_path.read_text())
        interview_transcript = interview_data.get("transcript", "")

    # Also check for standalone transcript file
    if not interview_transcript:
        transcript_path = PROFILES_DIR / "interview" / "transcript.md"
        if transcript_path.exists():
            interview_transcript = transcript_path.read_text()
            console.print(f"  Interview transcript loaded from {transcript_path}")

    # Try ChatLedger integration
    chatledger_patterns = None
    if chatledger_db:
        for db_name in ("enriched.db", "chatledger.db", "sms.db"):
            db_path = chatledger_db / db_name if chatledger_db.is_dir() else chatledger_db
            if db_path.exists():
                from .corpus.chatledger import read_chatledger_patterns
                chatledger_patterns = read_chatledger_patterns(db_path)
                if chatledger_patterns:
                    console.print(f"  ChatLedger data loaded from {db_path}")
                break

    profile.persona = generate_persona_model(
        profile,
        interview_transcript=interview_transcript,
        chatledger_patterns=chatledger_patterns,
    )

    # Generate outputs
    profile.narrative = generate_narrative_report(
        profile,
        interview_transcript=interview_transcript,
    )
    profile.claude_md_snippet = generate_claude_md_snippet(profile)

    # Save profile
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    profile_path = PROFILES_DIR / "profile.json"
    profile_path.write_text(profile.model_dump_json(indent=2))
    console.print(f"  Profile saved to {profile_path}")

    # Save narrative
    narrative_path = PROFILES_DIR / "report.md"
    narrative_path.write_text(profile.narrative)
    console.print(f"  Narrative saved to {narrative_path}")

    # Save CLAUDE.md snippet
    snippet_path = PROFILES_DIR / "claude-context.md"
    snippet_path.write_text(profile.claude_md_snippet)
    console.print(f"  CLAUDE.md snippet saved to {snippet_path}")

    # Print summary
    console.print("\n[bold]Big Five Summary:[/bold]")
    for key, name in [("O", "Openness"), ("C", "Conscientiousness"), ("E", "Extraversion"), ("A", "Agreeableness"), ("N", "Neuroticism")]:
        t = profile.big_five.domains.get(key)
        if t:
            console.print(f"  {name}: {t.final_score:.0f}/100 ({t.confidence}, CI: {t.ci_lower:.0f}-{t.ci_upper:.0f})")

    # Extended battery summary
    ext_scores = []
    if profile.attachment.anxiety is not None:
        ext_scores.append(f"Attachment Anxiety: {profile.attachment.anxiety:.0f}")
    if profile.attachment.avoidance is not None:
        ext_scores.append(f"Attachment Avoidance: {profile.attachment.avoidance:.0f}")
    if profile.hexaco.honesty_humility is not None:
        ext_scores.append(f"Honesty-Humility: {profile.hexaco.honesty_humility:.0f}")
    if profile.grit.perseverance is not None:
        ext_scores.append(f"Grit Perseverance: {profile.grit.perseverance:.0f}")
    if ext_scores:
        console.print("\n[bold]Extended Battery (selected):[/bold]")
        for s in ext_scores:
            console.print(f"  {s}/100")

    # Persona model summary
    if profile.persona.communication.directness:
        console.print("\n[bold]Persona Model:[/bold]")
        console.print(f"  Communication: {profile.persona.communication.directness}")
        if profile.persona.interpersonal.empathy_mode:
            console.print(f"  Empathy: {profile.persona.interpersonal.empathy_mode}")
        if profile.persona.conflict_response.under_criticism:
            console.print(f"  Under criticism: {profile.persona.conflict_response.under_criticism}")

    if profile.metadata.methods_used:
        console.print(f"\n  Methods: {', '.join(profile.metadata.methods_used)}")


@app.command()
def report() -> None:
    """Display the generated narrative report."""
    narrative_path = PROFILES_DIR / "report.md"
    if not narrative_path.exists():
        console.print("[yellow]No report. Run 'psyche synthesize' first.[/yellow]")
        return
    console.print(narrative_path.read_text())


def _print_stats(st: object) -> None:
    """Print corpus stats as a rich table."""
    from .corpus.types import CorpusStats

    if not isinstance(st, CorpusStats):
        return

    table = Table(title="Corpus Statistics")
    table.add_column("Source", style="bold")
    table.add_column("Samples", justify="right")
    table.add_column("Words", justify="right")
    table.add_column("Self Words", justify="right")
    table.add_column("Date Range")

    for source, ss in sorted(st.by_source.items()):
        date_range = ""
        if ss.earliest and ss.latest:
            date_range = f"{ss.earliest.strftime('%Y-%m')}-{ss.latest.strftime('%Y-%m')}"
        elif ss.earliest:
            date_range = ss.earliest.strftime("%Y-%m")

        table.add_row(
            source,
            f"{ss.samples:,}",
            f"{ss.words:,}",
            f"{ss.self_words:,}",
            date_range,
        )

    table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{st.total_samples:,}[/bold]",
        f"[bold]{st.total_words:,}[/bold]",
        "",
        "",
    )

    console.print(table)


if __name__ == "__main__":
    app()
