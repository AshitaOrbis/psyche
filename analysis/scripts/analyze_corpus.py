#!/usr/bin/env python3
"""Multi-level corpus personality analysis across all data sources.

Runs Empath lexical analysis and LLM inference (Claude Opus via `claude -p`)
on the full expanded corpus (1.47M words, 5 sources) with 13 analysis levels:
per-source, temporal eras, communication medium, and full corpus.

Uses `claude -p` CLI (Claude Max plan) for LLM inference.

Usage:
  cd psyche/analysis
  uv run python scripts/analyze_corpus.py --all
  uv run python scripts/analyze_corpus.py --level academic
  uv run python scripts/analyze_corpus.py --levels sms messenger chatgpt
  uv run python scripts/analyze_corpus.py --level full --skip-llm
  uv run python scripts/analyze_corpus.py --compare-only
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Add the analysis package to path
ANALYSIS_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ANALYSIS_ROOT))

from psyche_analysis.corpus.types import TextSample
from psyche_analysis.corpus.manager import load_samples, _code_ratio
from psyche_analysis.methods.empath_analysis import EmpathResult, analyze_empath, compute_norms, CategoryNorms
from psyche_analysis.methods.llm_claude import segment_samples

from rich.console import Console
from rich.table import Table

console = Console()

# --- Paths ---
PROJECT_ROOT = ANALYSIS_ROOT.parent  # psyche/
DATA_DIR = PROJECT_ROOT / "data"
INGESTED_DIR = DATA_DIR / "ingested"
PROFILES = PROJECT_ROOT / "profiles" / "analysis"
CORPUS_OUTPUT = PROFILES / "corpus"

# Import prompts for LLM inference
sys.path.insert(0, str(ANALYSIS_ROOT / "prompts"))
from personality_inference import (  # noqa: E402
    SYSTEM_PROMPT,
    BIG_FIVE_ASSESSMENT_PROMPT,
    VALUES_ASSESSMENT_PROMPT,
)


# --- Medium Map (configurable) ---

MEDIUM_MAP_PATH = ANALYSIS_ROOT / "medium-map.json"

DEFAULT_MEDIUM_MAP: dict[str, list[str]] = {
    "formal": ["academic"],
    "messaging": ["sms", "messenger"],
    "ai": ["chatgpt", "claude_ai"],
}


def _load_medium_map() -> dict[str, list[str]]:
    """Load medium map from JSON config, falling back to defaults."""
    if MEDIUM_MAP_PATH.exists():
        return json.loads(MEDIUM_MAP_PATH.read_text()) or DEFAULT_MEDIUM_MAP
    return DEFAULT_MEDIUM_MAP


# --- Dynamic Factor Discovery ---

def discover_factors(ingested_dir: Path) -> dict[str, dict]:
    """Examine ingested corpus data and generate analysis level configs.

    Discovers:
    - Per-source: one level per ingested source file
    - Temporal: date range bins from sample timestamps
    - Medium: groups sources into medium categories
    - Full: always includes a full-corpus level
    """
    # Find available sources
    sources: list[str] = []
    source_dates: dict[str, tuple[datetime | None, datetime | None]] = {}

    for jsonl in sorted(ingested_dir.glob("*.jsonl")):
        source = jsonl.stem
        if source == "all":
            continue
        sources.append(source)

        # Scan for date ranges
        earliest: datetime | None = None
        latest: datetime | None = None
        with open(jsonl, "rb") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    ts_str = data.get("timestamp")
                    if ts_str:
                        ts = datetime.fromisoformat(ts_str)
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                        if earliest is None or ts < earliest:
                            earliest = ts
                        if latest is None or ts > latest:
                            latest = ts
                except (json.JSONDecodeError, ValueError):
                    continue
        source_dates[source] = (earliest, latest)

    if not sources:
        console.print("[red]No ingested sources found![/red]")
        return {}

    console.print(f"[bold]Discovered {len(sources)} sources: {', '.join(sources)}[/bold]")
    for src, (e, l) in source_dates.items():
        e_str = e.strftime("%Y-%m") if e else "?"
        l_str = l.strftime("%Y-%m") if l else "?"
        console.print(f"  {src}: {e_str} to {l_str}")

    levels: dict[str, dict] = {}

    # Full corpus level
    levels["full"] = {
        "sources": sources,
        "date_range": None,
        "description": f"Complete corpus, all {len(sources)} sources",
        "max_chunks": 15,
    }

    # Per-source levels
    for source in sources:
        e, l = source_dates[source]
        date_desc = ""
        if e and l:
            date_desc = f" ({e.strftime('%Y')}-{l.strftime('%Y')})"
        levels[source] = {
            "sources": [source],
            "date_range": None,
            "description": f"{source.replace('_', ' ').title()}{date_desc}",
        }

    # Temporal eras: find natural boundaries based on source availability
    all_dates: list[datetime] = []
    for src, (e, l) in source_dates.items():
        if e:
            all_dates.append(e)
        if l:
            all_dates.append(l)

    if all_dates:
        global_earliest = min(all_dates)
        global_latest = max(all_dates)
        span_years = (global_latest - global_earliest).days / 365.25

        if span_years > 10:
            bin_size = 5
        elif span_years > 5:
            bin_size = 3
        else:
            bin_size = 2

        year = global_earliest.year
        end_year = global_latest.year + 1

        while year < end_year:
            era_end = min(year + bin_size, end_year)
            era_start_dt = datetime(year, 1, 1, tzinfo=timezone.utc)
            era_end_dt = datetime(era_end, 1, 1, tzinfo=timezone.utc)

            # Find which sources have data in this range
            era_sources = []
            for src, (e, l) in source_dates.items():
                if e is None or l is None:
                    continue
                if e < era_end_dt and l >= era_start_dt:
                    era_sources.append(src)

            if era_sources:
                era_key = f"era-{year}-{era_end}"
                levels[era_key] = {
                    "sources": era_sources,
                    "date_range": (era_start_dt, era_end_dt),
                    "description": f"{year}-{era_end} ({', '.join(era_sources)})",
                }

            year = era_end

    # Medium levels
    medium_map = _load_medium_map()
    for medium_name, medium_sources in medium_map.items():
        available = [s for s in medium_sources if s in sources]
        if available:
            levels[f"medium-{medium_name}"] = {
                "sources": available,
                "date_range": None,
                "description": f"{medium_name.title()} communication ({', '.join(available)})",
            }

    console.print(f"[bold]Generated {len(levels)} analysis levels[/bold]")
    return levels


# --- Analysis Level Definitions (fallback) ---

ANALYSIS_LEVELS: dict[str, dict] = {
    "full": {
        "sources": ["academic", "sms", "messenger", "chatgpt", "claude_ai"],
        "date_range": None,
        "description": "Complete corpus, all sources",
        "max_chunks": 15,
    },
    "academic": {
        "sources": ["academic"],
        "date_range": None,
        "description": "Formal reflective writing",
    },
    "sms": {
        "sources": ["sms"],
        "date_range": None,
        "description": "Casual text messaging (2015-2026)",
    },
    "messenger": {
        "sources": ["messenger"],
        "date_range": None,
        "description": "FB Messenger (2008-2019)",
    },
    "chatgpt": {
        "sources": ["chatgpt"],
        "date_range": None,
        "description": "AI conversations (2024-2026)",
    },
    "claude_ai": {
        "sources": ["claude_ai"],
        "date_range": None,
        "description": "AI conversations (2025-2026)",
    },
    "era-2008-2015": {
        "sources": ["messenger", "sms"],
        "date_range": (datetime(2008, 1, 1, tzinfo=timezone.utc),
                       datetime(2016, 1, 1, tzinfo=timezone.utc)),
        "description": "Early digital, mostly Messenger",
    },
    "era-2015-2019": {
        "sources": ["messenger", "sms"],
        "date_range": (datetime(2016, 1, 1, tzinfo=timezone.utc),
                       datetime(2020, 1, 1, tzinfo=timezone.utc)),
        "description": "Overlap period, SMS + Messenger",
    },
    "era-2019-2024": {
        "sources": ["sms", "academic"],
        "date_range": (datetime(2020, 1, 1, tzinfo=timezone.utc),
                       datetime(2024, 5, 1, tzinfo=timezone.utc)),
        "description": "Pre-AI, primary SMS era",
    },
    "era-2024-2026": {
        "sources": ["sms", "chatgpt", "claude_ai", "academic"],
        "date_range": (datetime(2024, 5, 1, tzinfo=timezone.utc),
                       datetime(2027, 1, 1, tzinfo=timezone.utc)),
        "description": "AI conversation era",
    },
    "medium-formal": {
        "sources": ["academic"],
        "date_range": None,
        "description": "Formal/reflective writing only",
    },
    "medium-messaging": {
        "sources": ["sms", "messenger"],
        "date_range": None,
        "description": "Casual messaging combined",
    },
    "medium-ai": {
        "sources": ["chatgpt", "claude_ai"],
        "date_range": None,
        "description": "AI platform conversations",
    },
}

ALL_LEVELS = list(ANALYSIS_LEVELS.keys())


# --- Claude CLI LLM inference ---

def _call_claude(prompt: str, system: str, model: str = "opus") -> str:
    """Call Claude via `claude -p` CLI, returning the raw text response."""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    result = subprocess.run(
        [
            "claude", "-p",
            "--model", model,
            "--output-format", "text",
            "--system-prompt", system,
        ],
        input=prompt,
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude -p failed: {result.stderr}")
    return result.stdout.strip()


def _extract_json(text: str) -> dict:
    """Extract JSON object from Claude's response."""
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Brace-matching fallback
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in response")

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])

    raise ValueError(f"Could not find complete JSON object in response (length: {len(text)})")


# --- Text chunking (fixed: no truncation) ---

def prepare_text_chunks(
    samples: list[TextSample],
    max_words_per_chunk: int = 8000,
    max_chunks: int = 10,
) -> list[str]:
    """Prepare text samples into chunks for LLM analysis.

    Pre-segments long samples instead of truncating them.
    Round-robins across sources for diversity.
    """
    # Pre-segment long samples
    segmented = segment_samples(samples)

    # Group by source
    by_source: dict[str, list[TextSample]] = {}
    for s in segmented:
        by_source.setdefault(s.source, []).append(s)

    # Sort each source by word count descending
    for source_samples in by_source.values():
        source_samples.sort(key=lambda s: s.word_count, reverse=True)

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_words = 0

    source_lists = list(by_source.values())
    indices = [0] * len(source_lists)

    while len(chunks) < max_chunks:
        added = False
        for i, sl in enumerate(source_lists):
            if indices[i] >= len(sl):
                continue
            sample = sl[indices[i]]
            indices[i] += 1

            sample_words = sample.word_count

            if current_words + sample_words > max_words_per_chunk and current_chunk:
                chunks.append("\n\n---\n\n".join(current_chunk))
                current_chunk = []
                current_words = 0
                if len(chunks) >= max_chunks:
                    break

            header = f"[Source: {sample.source}"
            if sample.timestamp:
                header += f", Date: {sample.timestamp.strftime('%Y-%m')}"
            header += "]"

            current_chunk.append(f"{header}\n{sample.text}")
            current_words += sample_words
            added = True

        if not added:
            break

    if current_chunk:
        chunks.append("\n\n---\n\n".join(current_chunk))

    return chunks[:max_chunks]


# --- LLM analysis functions ---

def analyze_big_five_cli(
    samples: list[TextSample],
    max_chunks: int = 10,
    model: str = "opus",
) -> dict:
    """Run Big Five personality inference via claude -p CLI."""
    chunks = prepare_text_chunks(samples, max_chunks=max_chunks)
    all_results: list[dict] = []

    for i, chunk in enumerate(chunks):
        console.print(f"  Analyzing chunk {i + 1}/{len(chunks)} ({len(chunk.split())} words)...")
        prompt = BIG_FIVE_ASSESSMENT_PROMPT.format(text_samples=chunk)

        try:
            response = _call_claude(prompt, SYSTEM_PROMPT, model=model)
            result = _extract_json(response)
            all_results.append(result)
        except Exception as e:
            console.print(f"  [red]Failed chunk {i + 1}: {e}[/red]")

    if not all_results:
        raise ValueError("No valid results from any chunk")

    return _merge_big_five_results(all_results, chunks)


def analyze_values_cli(
    samples: list[TextSample],
    model: str = "opus",
) -> dict:
    """Run Schwartz Values inference via claude -p CLI."""
    chunks = prepare_text_chunks(samples, max_chunks=3)
    chunk = chunks[0] if chunks else ""

    console.print(f"  Analyzing values ({len(chunk.split())} words)...")
    prompt = VALUES_ASSESSMENT_PROMPT.format(text_samples=chunk)

    response = _call_claude(prompt, SYSTEM_PROMPT, model=model)
    result = _extract_json(response)

    return {
        "values": result.get("values", {}),
        "top_3_values": result.get("top_3_values", []),
        "bottom_3_values": result.get("bottom_3_values", []),
        "overall_confidence": result.get("overall_confidence", "medium"),
    }


def _merge_big_five_results(results: list[dict], chunks: list[str]) -> dict:
    """Merge multiple chunk results by averaging scores."""
    domain_scores: dict[str, list[float]] = {}
    domain_evidence: dict[str, list[str]] = {}
    domain_reasoning: dict[str, list[str]] = {}
    domain_confidence: dict[str, list[str]] = {}
    facet_scores: dict[str, list[float]] = {}
    facet_confidence: dict[str, list[str]] = {}
    all_caveats: list[str] = []

    for r in results:
        for domain_key, domain_data in r.get("domains", {}).items():
            if isinstance(domain_data, dict):
                score = domain_data.get("score", 50)
                domain_scores.setdefault(domain_key, []).append(score)
                domain_evidence.setdefault(domain_key, []).extend(
                    domain_data.get("evidence", [])
                )
                domain_reasoning.setdefault(domain_key, []).append(
                    domain_data.get("reasoning", "")
                )
                domain_confidence.setdefault(domain_key, []).append(
                    domain_data.get("confidence", "medium")
                )

        for facet_key, facet_data in r.get("facets", {}).items():
            if isinstance(facet_data, dict):
                facet_scores.setdefault(facet_key, []).append(
                    facet_data.get("score", 50)
                )
                facet_confidence.setdefault(facet_key, []).append(
                    facet_data.get("confidence", "medium")
                )

        all_caveats.extend(r.get("caveats", []))

    domains = {}
    for key in domain_scores:
        scores = domain_scores[key]
        avg_score = sum(scores) / len(scores)
        conf = _merge_confidence(domain_confidence.get(key, ["medium"]))
        evidence = list(dict.fromkeys(domain_evidence.get(key, [])))[:5]
        reasoning = " | ".join(filter(None, domain_reasoning.get(key, [])))

        domains[key] = {
            "score": round(avg_score, 1),
            "confidence": conf,
            "evidence": evidence,
            "reasoning": reasoning,
        }

    facets = {}
    for key in facet_scores:
        scores = facet_scores[key]
        avg_score = sum(scores) / len(scores)
        conf = _merge_confidence(facet_confidence.get(key, ["medium"]))
        facets[key] = {"score": round(avg_score, 1), "confidence": conf}

    conf_order = {"low": 0, "medium": 1, "high": 2}
    overall = min(
        (d["confidence"] for d in domains.values()),
        key=lambda c: conf_order.get(c, 1),
        default="medium",
    )

    return {
        "domains": domains,
        "facets": facets,
        "overall_confidence": overall,
        "caveats": list(dict.fromkeys(all_caveats)),
        "word_count_analyzed": sum(len(c.split()) for c in chunks),
    }


def _merge_confidence(confidences: list[str]) -> str:
    """Merge confidence ratings from multiple chunks."""
    counts = {"low": 0, "medium": 0, "high": 0}
    for c in confidences:
        counts[c] = counts.get(c, 0) + 1
    return max(counts, key=lambda k: counts[k])


# --- Data loading ---

def load_ingested_samples(
    sources: list[str],
    date_range: tuple[datetime, datetime] | None = None,
    self_only: bool = True,
    filter_code: bool = False,
) -> list[TextSample]:
    """Load samples from ingested JSONL files with filtering.

    Args:
        sources: Source names to load (e.g. ["sms", "messenger"]).
        date_range: If set, only include samples within (start, end).
        self_only: If True, only include self-authored samples.
        filter_code: If True, exclude samples with >50% code content.
    """
    samples: list[TextSample] = []

    for source in sources:
        path = INGESTED_DIR / f"{source}.jsonl"
        if not path.exists():
            console.print(f"  [yellow]Warning: {path} not found, skipping[/yellow]")
            continue
        source_samples = load_samples(path)
        samples.extend(source_samples)

    # Filter to self-authored
    if self_only:
        samples = [s for s in samples if s.author == "self"]

    # Date range filter (exclude undated samples from temporal analysis)
    if date_range:
        start, end = date_range
        filtered = []
        for s in samples:
            if not s.timestamp:
                continue
            # Normalize timezone: make naive timestamps UTC-aware for comparison
            ts = s.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if start <= ts < end:
                filtered.append(s)
        samples = filtered

    # Code content filter for AI conversation sources
    if filter_code:
        samples = [s for s in samples if _code_ratio(s.text) < 0.5]

    return samples


# --- Level execution ---

def run_level(
    level: str,
    *,
    skip_llm: bool = False,
    skip_empath: bool = False,
    model: str = "opus",
    levels_dict: dict[str, dict] | None = None,
    empath_norms: CategoryNorms | None = None,
) -> tuple[dict | None, dict | None]:
    """Run analysis for a single level. Returns (empath_dict, llm_dict)."""
    source = levels_dict or ANALYSIS_LEVELS
    config = source[level]
    sources = config["sources"]
    date_range = config.get("date_range")
    max_chunks = config.get("max_chunks", 10)
    description = config["description"]

    console.print(f"\n[bold magenta]{'=' * 60}[/bold magenta]")
    console.print(f"[bold magenta]  Level: {level} — {description}[/bold magenta]")
    console.print(f"[bold magenta]{'=' * 60}[/bold magenta]")

    # Filter code for AI conversation sources
    filter_code = any(s in sources for s in ("chatgpt", "claude_ai"))

    samples = load_ingested_samples(
        sources,
        date_range=date_range,
        self_only=True,
        filter_code=filter_code,
    )

    total_words = sum(s.word_count for s in samples)
    console.print(f"  Loaded {len(samples):,} samples, {total_words:,} words")
    console.print(f"  Sources: {', '.join(sources)}")
    if date_range:
        console.print(f"  Date range: {date_range[0].strftime('%Y-%m')} to {date_range[1].strftime('%Y-%m')}")

    if not samples:
        console.print(f"  [red]No samples found for this level![/red]")
        return None, None

    if total_words < 1000:
        console.print(f"  [yellow]Warning: only {total_words:,} words — low confidence expected[/yellow]")

    empath_dict = None
    llm_dict = None

    # Empath analysis
    if not skip_empath:
        console.print(f"\n  [bold]Running Empath analysis...[/bold]")
        empath_result = analyze_empath(samples, norms=empath_norms)
        empath_dict = json.loads(empath_result.model_dump_json())
        # Add provenance
        empath_dict["provenance"] = _build_provenance(
            level, sources, date_range, samples, total_words,
            segments_created=0, chunks_to_llm=0, words_to_llm=0, model="empath",
        )
        _save_result(empath_dict, level, "empath")

    # LLM analysis
    if not skip_llm:
        console.print(f"\n  [bold]Running LLM inference via claude -p (model={model})...[/bold]")

        # Segment long samples before chunking
        segmented = segment_samples(samples)
        console.print(f"  Segmented: {len(samples):,} samples -> {len(segmented):,} segments")

        big_five = analyze_big_five_cli(segmented, max_chunks=max_chunks, model=model)
        values = analyze_values_cli(segmented, model=model)

        # Build provenance
        chunks_preview = prepare_text_chunks(segmented, max_chunks=max_chunks)
        words_to_llm = sum(len(c.split()) for c in chunks_preview)

        llm_dict = {
            "method": "llm-claude",
            "model_used": f"claude-{model}-via-claude-cli",
            "big_five": big_five,
            "values": values,
            "provenance": _build_provenance(
                level, sources, date_range, samples, total_words,
                segments_created=len(segmented),
                chunks_to_llm=len(chunks_preview),
                words_to_llm=words_to_llm,
                model=model,
            ),
        }
        _save_result(llm_dict, level, "llm-claude")

    return empath_dict, llm_dict


def _build_provenance(
    level: str,
    sources: list[str],
    date_range: tuple[datetime, datetime] | None,
    samples: list[TextSample],
    total_words: int,
    segments_created: int,
    chunks_to_llm: int,
    words_to_llm: int,
    model: str,
) -> dict:
    """Build provenance metadata for result output."""
    return {
        "level": level,
        "sources_included": sources,
        "date_range": (
            [date_range[0].isoformat(), date_range[1].isoformat()]
            if date_range else None
        ),
        "total_corpus_samples": len(samples),
        "total_corpus_words": total_words,
        "self_samples_used": len(samples),
        "self_words_used": total_words,
        "segments_created": segments_created,
        "chunks_to_llm": chunks_to_llm,
        "words_to_llm": words_to_llm,
        "sampling_ratio": (
            f"{words_to_llm / total_words * 100:.1f}%"
            if total_words > 0 and words_to_llm > 0 else "N/A"
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
    }


def _save_result(data: dict, level: str, method: str) -> None:
    """Save analysis result to the corpus output directory."""
    CORPUS_OUTPUT.mkdir(parents=True, exist_ok=True)
    path = CORPUS_OUTPUT / f"{level}-{method}.json"
    path.write_text(json.dumps(data, indent=2, default=str))
    console.print(f"  Saved to {path}")


# --- Comparison table ---

def print_comparison_table(levels_dict: dict[str, dict] | None = None):
    """Load existing results and print a comparison table."""
    domains = ["N", "E", "O", "A", "C"]
    level_keys = list((levels_dict or ANALYSIS_LEVELS).keys())
    level_descs = levels_dict or ANALYSIS_LEVELS

    # LLM comparison
    sep = "=" * 60
    console.print(f"\n[bold cyan]{sep}[/bold cyan]")
    console.print("[bold cyan]  LLM Big Five: Per-Level Comparison[/bold cyan]")
    console.print(f"[bold cyan]{sep}[/bold cyan]")

    table = Table(title="LLM Corpus Analysis: Big Five Scores by Level")
    table.add_column("Level", style="bold", min_width=18)
    for d in domains:
        table.add_column(d, justify="right", min_width=5)
    table.add_column("Words Analyzed", justify="right", min_width=14)
    table.add_column("Corpus Words", justify="right", min_width=12)

    results_llm: dict[str, dict] = {}
    results_empath: dict[str, dict] = {}

    # Scan all result files in corpus output (dynamic discovery)
    if CORPUS_OUTPUT.exists():
        for f in CORPUS_OUTPUT.glob("*-llm-claude.json"):
            level_name = f.stem.replace("-llm-claude", "")
            results_llm[level_name] = json.loads(f.read_text())
            if level_name not in level_keys:
                level_keys.append(level_name)
        for f in CORPUS_OUTPUT.glob("*-empath.json"):
            level_name = f.stem.replace("-empath", "")
            results_empath[level_name] = json.loads(f.read_text())
            if level_name not in level_keys:
                level_keys.append(level_name)

    if not results_llm and not results_empath:
        console.print("[yellow]No results found. Run analysis first.[/yellow]")
        return

    # LLM table
    for level in level_keys:
        if level not in results_llm:
            continue
        data = results_llm[level]
        bf = data.get("big_five", {})
        prov = data.get("provenance", {})
        scores = {d: bf.get("domains", {}).get(d, {}).get("score", "?") for d in domains}
        words_analyzed = bf.get("word_count_analyzed", prov.get("words_to_llm", "?"))
        corpus_words = prov.get("total_corpus_words", "?")

        words_str = f"{words_analyzed:,}" if isinstance(words_analyzed, int) else str(words_analyzed)
        corpus_str = f"{corpus_words:,}" if isinstance(corpus_words, int) else str(corpus_words)

        table.add_row(level, *[str(scores[d]) for d in domains], words_str, corpus_str)

    if results_llm:
        console.print(table)

    # Empath lexical profile table
    if results_empath:
        console.print(f"\n[bold cyan]{sep}[/bold cyan]")
        console.print("[bold cyan]  Empath Lexical Profile: Per-Level Comparison[/bold cyan]")
        console.print(f"[bold cyan]{sep}[/bold cyan]")

        empath_table = Table(title="Empath Lexical Profile (ordinal, corpus-relative)")
        empath_table.add_column("Level", style="bold", min_width=18)
        for d in domains:
            empath_table.add_column(d, justify="center", min_width=14)
        empath_table.add_column("Total Words", justify="right", min_width=12)

        for level in level_keys:
            if level not in results_empath:
                continue
            data = results_empath[level]
            lp = data.get("lexical_profile", {})
            total_words = data.get("total_words", "?")
            words_str = f"{total_words:,}" if isinstance(total_words, int) else str(total_words)

            cells = []
            for d in domains:
                dim = lp.get(d, {})
                z = dim.get("z_score", 0)
                label = dim.get("label", "?")
                cells.append(f"{label} ({z:+.2f})")

            empath_table.add_row(level, *cells, words_str)

        console.print(empath_table)

    # Summary comparison JSON
    summary = {"levels": {}}
    for level in level_keys:
        desc = level_descs.get(level, {}).get("description", level) if isinstance(level_descs, dict) else level
        entry: dict = {"level": level, "description": desc}
        if level in results_llm:
            bf = results_llm[level].get("big_five", {})
            entry["llm_big_five"] = {
                d: bf.get("domains", {}).get(d, {}).get("score") for d in domains
            }
            prov = results_llm[level].get("provenance", {})
            entry["corpus_words"] = prov.get("total_corpus_words")
            entry["words_to_llm"] = prov.get("words_to_llm")
        if level in results_empath:
            lp = results_empath[level].get("lexical_profile", {})
            entry["empath_lexical"] = {
                d: {"z": lp.get(d, {}).get("z_score", 0), "label": lp.get(d, {}).get("label", "average")}
                for d in domains
            }
            entry["empath_words"] = results_empath[level].get("total_words")
        summary["levels"][level] = entry

    summary_path = CORPUS_OUTPUT / "comparison-summary.json"
    CORPUS_OUTPUT.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2))
    console.print(f"\n  Comparison summary saved to {summary_path}")


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description="Multi-level corpus personality analysis")
    parser.add_argument("--all", action="store_true", help="Run all 13 analysis levels")
    parser.add_argument("--level", choices=ALL_LEVELS, help="Run a single analysis level")
    parser.add_argument("--levels", nargs="+", choices=ALL_LEVELS,
                        help="Run multiple specific levels")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM inference (Empath only)")
    parser.add_argument("--skip-empath", action="store_true", help="Skip Empath analysis (LLM only)")
    parser.add_argument("--compare-only", action="store_true",
                        help="Skip analysis, load existing results and print comparison")
    parser.add_argument("--model", default="opus", help="LLM model for claude -p (default: opus)")
    parser.add_argument("--auto-discover", action="store_true",
                        help="Auto-discover analysis levels from ingested data instead of using hardcoded levels")
    args = parser.parse_args()

    if not args.all and not args.level and not args.levels and not args.compare_only:
        parser.print_help()
        sys.exit(1)

    # Comparison-only mode
    if args.compare_only:
        print_comparison_table()
        return

    # Note: --compare-only runs before auto-discover since it doesn't need ingested data

    # Validate ingested data exists
    if not INGESTED_DIR.exists():
        console.print("[red]No ingested data. Run 'cd psyche/analysis && uv run psyche ingest all' first.[/red]")
        sys.exit(1)

    # Auto-discover levels if requested
    active_levels = ANALYSIS_LEVELS
    if args.auto_discover:
        discovered = discover_factors(INGESTED_DIR)
        if discovered:
            active_levels = discovered
            console.print(f"[bold green]Using {len(active_levels)} auto-discovered levels[/bold green]")
        else:
            console.print("[yellow]Discovery found nothing, falling back to hardcoded levels[/yellow]")

    # Determine which levels to run
    all_level_keys = list(active_levels.keys())
    if args.all:
        levels_to_run = all_level_keys
    elif args.levels:
        levels_to_run = [l for l in args.levels if l in active_levels]
    elif args.level:
        levels_to_run = [args.level] if args.level in active_levels else []
    else:
        levels_to_run = []

    console.print(f"[bold]Running {len(levels_to_run)} analysis level(s)...[/bold]")
    console.print(f"  LLM: {'SKIP' if args.skip_llm else args.model}")
    console.print(f"  Empath: {'SKIP' if args.skip_empath else 'enabled'}")

    # Pre-compute Empath norms from the full corpus so per-level analysis
    # is z-scored against the same baseline (not self-normed per level)
    full_corpus_norms: CategoryNorms | None = None
    if not args.skip_empath and len(levels_to_run) > 1:
        console.print("\n[bold]Computing Empath corpus norms...[/bold]")
        all_sources = set()
        for level_key in levels_to_run:
            cfg = active_levels[level_key]
            all_sources.update(cfg["sources"])
        full_samples = load_ingested_samples(
            list(all_sources),
            self_only=True,
            filter_code=any(s in all_sources for s in ("chatgpt", "claude_ai")),
        )
        if full_samples:
            full_corpus_norms = compute_norms(full_samples)
            console.print(f"  Norms computed from {len(full_samples):,} samples, {full_corpus_norms.n_segments} segments")

    for level in levels_to_run:
        try:
            run_level(
                level,
                skip_llm=args.skip_llm,
                skip_empath=args.skip_empath,
                model=args.model,
                levels_dict=active_levels,
                empath_norms=full_corpus_norms,
            )
        except Exception as e:
            console.print(f"\n  [red]Error on level '{level}': {e}[/red]")
            import traceback
            traceback.print_exc()

    # Print comparison table at the end
    print_comparison_table(levels_dict=active_levels)

    console.print("\n[bold green]Done.[/bold green]")


if __name__ == "__main__":
    main()
