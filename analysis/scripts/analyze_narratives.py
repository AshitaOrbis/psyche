#!/usr/bin/env python3
"""Quantitative personality analysis of Opus-generated first-person narratives.

Runs Empath lexical analysis and LLM inference (Claude Opus 4.6 via `claude -p`)
on Ryan's first-person narratives, then compares against the original corpus
analysis to test whether narrative generation preserves personality signal.

Six analysis levels:
  v2-full     - Full v2 ryan_first_person.md (33K words)
  v2-arc1     - v2 chapters 1-13 only (27K words, no Fiona overlap)
  v2-arc2     - v2 chapters 14-18 only (8.8K words, overlaps with Fiona)
  fiona       - Full fiona ryan_first_person.md (24K words)
  combined    - Both full Ryan files (57K words)
  arc1-fiona  - v2 ch 1-13 + fiona full (51K words, overlap removed)

Uses `claude -p` CLI (Claude Max plan) for LLM inference rather than the
Anthropic SDK, since we don't maintain an API key.

Usage:
  cd psyche/analysis
  uv run python scripts/analyze_narratives.py --all
  uv run python scripts/analyze_narratives.py --level v2-full
  uv run python scripts/analyze_narratives.py --level v2-arc2 --skip-llm
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Add the analysis package to path
ANALYSIS_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ANALYSIS_ROOT))

from psyche_analysis.corpus.types import TextSample
from psyche_analysis.methods.empath_analysis import (
    EMPATH_TO_BIG_FIVE,
    EmpathResult,
    analyze_empath,
)

from rich.console import Console
from rich.table import Table

console = Console()

# --- Paths ---
WORKSPACE = Path(__file__).parent.parent.parent.parent  # claudeworkspace/
NARRATIVES = WORKSPACE / "research" / "voice-clone" / "narratives" / "output"
PROFILES = WORKSPACE / "psyche" / "profiles" / "analysis"

V2_RYAN_FULL = NARRATIVES / "v2" / "ryan_first_person.md"
FIONA_RYAN_FULL = NARRATIVES / "fiona" / "ryan_first_person.md"
V2_CHAPTERS_DIR = NARRATIVES / "v2" / "chapters" / "ryan"
FIONA_CHAPTERS_DIR = NARRATIVES / "fiona" / "chapters" / "ryan"

ORIGINAL_EMPATH = PROFILES / "empath.json"
ORIGINAL_LLM = PROFILES / "llm-claude.json"

# Citation marker pattern: {FN:hexhash}
CITATION_RE = re.compile(r"\{FN:[a-f0-9]+\}")

LEVELS = ["v2-full", "v2-arc1", "v2-arc2", "fiona", "combined", "arc1-fiona"]

# Import prompts for LLM inference
sys.path.insert(0, str(ANALYSIS_ROOT / "prompts"))
from personality_inference import (  # noqa: E402
    SYSTEM_PROMPT,
    BIG_FIVE_ASSESSMENT_PROMPT,
    VALUES_ASSESSMENT_PROMPT,
)


# --- Claude CLI LLM inference (uses `claude -p` via Max plan) ---

def _call_claude(prompt: str, system: str, model: str = "opus") -> str:
    """Call Claude via `claude -p` CLI, returning the raw text response.

    Must unset CLAUDECODE env var to avoid nested-session error.
    """
    # Build the full prompt with system context inline (claude -p has --system-prompt)
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(prompt)
        prompt_file = f.name

    try:
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
    finally:
        os.unlink(prompt_file)


def _extract_json(text: str) -> dict:
    """Extract JSON object from Claude's response, handling markdown code blocks and trailing text."""
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find the outermost JSON object by brace matching
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


def _prepare_text_chunks(
    samples: list[TextSample],
    max_words_per_chunk: int = 8000,
    max_chunks: int = 5,
) -> list[str]:
    """Prepare text samples into chunks for LLM analysis.

    Replicates the logic from llm_claude.py but without SDK dependency.
    """
    by_source: dict[str, list[TextSample]] = {}
    for s in samples:
        by_source.setdefault(s.source, []).append(s)

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

            text = sample.text
            words = text.split()
            if len(words) > 2000:
                text = " ".join(words[:2000]) + " [truncated]"

            sample_words = len(text.split())

            if current_words + sample_words > max_words_per_chunk and current_chunk:
                chunks.append("\n\n---\n\n".join(current_chunk))
                current_chunk = []
                current_words = 0
                if len(chunks) >= max_chunks:
                    break

            header = f"[Source: {sample.source}]"
            current_chunk.append(f"{header}\n{text}")
            current_words += sample_words
            added = True

        if not added:
            break

    if current_chunk:
        chunks.append("\n\n---\n\n".join(current_chunk))

    return chunks[:max_chunks]


def analyze_big_five_cli(
    samples: list[TextSample],
    model: str = "opus",
) -> dict:
    """Run Big Five personality inference via claude -p CLI."""
    chunks = _prepare_text_chunks(samples)
    all_results: list[dict] = []

    for i, chunk in enumerate(chunks):
        console.print(f"  Analyzing chunk {i + 1}/{len(chunks)} ({len(chunk.split())} words)...")
        prompt = BIG_FIVE_ASSESSMENT_PROMPT.format(text_samples=chunk)

        response = _call_claude(prompt, SYSTEM_PROMPT, model=model)

        try:
            result = _extract_json(response)
            all_results.append(result)
        except (json.JSONDecodeError, IndexError) as e:
            console.print(f"  [red]Failed to parse chunk {i + 1}: {e}[/red]")
            # Save raw response for debugging
            debug_path = PROFILES / f"_debug_chunk_{i + 1}.txt"
            debug_path.write_text(response)
            console.print(f"  [dim]Raw response saved to {debug_path}[/dim]")

    if not all_results:
        raise ValueError("No valid results from any chunk")

    return _merge_big_five_results(all_results, chunks)


def analyze_values_cli(
    samples: list[TextSample],
    model: str = "opus",
) -> dict:
    """Run Schwartz Values inference via claude -p CLI."""
    chunks = _prepare_text_chunks(samples, max_chunks=3)
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


def run_llm_analysis(
    samples: list[TextSample],
    model: str = "opus",
) -> dict:
    """Run complete LLM personality analysis via claude -p CLI."""
    console.print(f"[bold]Running Claude LLM analysis ({len(samples)} samples, model={model})...[/bold]")

    big_five = analyze_big_five_cli(samples, model)
    values = analyze_values_cli(samples, model)

    return {
        "method": "llm-claude",
        "model_used": f"claude-{model}-via-claude-cli",
        "big_five": big_five,
        "values": values,
    }


def strip_citations(text: str) -> str:
    """Remove {FN:hash} citation markers from narrative text."""
    cleaned = CITATION_RE.sub("", text)
    # Warn about remaining curly braces that might be malformed citations
    remaining = re.findall(r"\{[^}]*\}", cleaned)
    if remaining:
        examples = remaining[:3]
        console.print(f"  [yellow]Warning: {len(remaining)} remaining curly-brace patterns "
                      f"(e.g. {examples})[/yellow]")
    return cleaned


def load_file(path: Path, source: str) -> TextSample:
    """Load a narrative file as a single TextSample."""
    text = strip_citations(path.read_text())
    return TextSample(
        id=path.stem,
        source=source,
        author="Ryan",
        text=text,
    )


def load_file_segmented(
    path: Path, source: str, segment_words: int = 2000
) -> list[TextSample]:
    """Load a narrative file and split into segments.

    Full narrative files (20-33K words) would be truncated to 2K by the
    chunking algorithm if loaded as a single TextSample. Splitting into
    segments gives the chunker multiple samples to work with, matching
    the behavior of chapter-based levels.
    """
    text = strip_citations(path.read_text())
    words = text.split()
    if len(words) <= segment_words:
        return [TextSample(id=path.stem, source=source, author="Ryan", text=text)]

    segments: list[TextSample] = []
    for i in range(0, len(words), segment_words):
        segment_text = " ".join(words[i : i + segment_words])
        segments.append(
            TextSample(
                id=f"{path.stem}_seg{i // segment_words + 1:02d}",
                source=source,
                author="Ryan",
                text=segment_text,
            )
        )
    return segments


def load_chapters(directory: Path, source: str, start: int = 1, end: int = 99) -> list[TextSample]:
    """Load chapter files from a directory, filtering by chapter number."""
    samples = []
    for path in sorted(directory.glob("chapter_*.md")):
        num = int(path.stem.split("_")[1])
        if start <= num <= end:
            samples.append(load_file(path, source))
    return samples


def get_samples_for_level(level: str) -> list[TextSample]:
    """Return the appropriate TextSample list for an analysis level."""
    if level == "v2-full":
        return load_file_segmented(V2_RYAN_FULL, "narrative-v2")
    elif level == "v2-arc1":
        return load_chapters(V2_CHAPTERS_DIR, "narrative-v2-arc1", start=1, end=13)
    elif level == "v2-arc2":
        return load_chapters(V2_CHAPTERS_DIR, "narrative-v2-arc2", start=14, end=18)
    elif level == "fiona":
        return load_file_segmented(FIONA_RYAN_FULL, "narrative-fiona")
    elif level == "combined":
        samples = load_file_segmented(V2_RYAN_FULL, "narrative-v2")
        samples.extend(load_file_segmented(FIONA_RYAN_FULL, "narrative-fiona"))
        return samples
    elif level == "arc1-fiona":
        samples = load_chapters(V2_CHAPTERS_DIR, "narrative-v2-arc1", start=1, end=13)
        samples.extend(load_file_segmented(FIONA_RYAN_FULL, "narrative-fiona"))
        return samples
    else:
        raise ValueError(f"Unknown level: {level}")


def output_suffix(level: str) -> str:
    """Return the filename suffix for a given level."""
    return f"-{level}" if level != "combined" else ""


def load_original_results() -> tuple[dict, dict]:
    """Load original empath and LLM analysis results."""
    empath = json.loads(ORIGINAL_EMPATH.read_text())
    llm = json.loads(ORIGINAL_LLM.read_text())
    return empath, llm


def evaluate_empath_methodology(
    original: dict,
    narrative_results: dict[str, EmpathResult],
) -> dict:
    """Evaluate why Empath produces compressed Big Five scores.

    Returns a structured evaluation with root cause analysis.
    """
    from empath import Empath
    lexicon = Empath()

    # 1. Check which mapped categories actually exist in Empath
    all_empath_cats = set(lexicon.analyze("test", normalize=True).keys())
    missing_cats = {}
    valid_cats = {}
    for domain, mapping in EMPATH_TO_BIG_FIVE.items():
        for cat in mapping:
            if cat not in all_empath_cats:
                missing_cats.setdefault(domain, []).append(cat)
            else:
                valid_cats.setdefault(domain, []).append(cat)

    # 2. Compute raw score ranges before calibration
    original_big_five = original.get("big_five_estimates", {})
    original_cats = original.get("categories", {})

    # Compute the weighted sums (pre-calibration) for original
    raw_scores_original = {}
    for domain, mapping in EMPATH_TO_BIG_FIVE.items():
        weighted_sum = 0.0
        total_weight = 0.0
        for cat, weight in mapping.items():
            if cat in original_cats:
                weighted_sum += original_cats[cat] * weight
                total_weight += abs(weight)
        if total_weight > 0:
            raw_scores_original[domain] = weighted_sum / total_weight

    # 3. Check if categories differentiate between original and narratives
    cat_comparison = {}
    # Use the combined narrative result if available, else first available
    narr_key = next(
        (k for k in ["combined", "v2-full", "fiona"] if k in narrative_results),
        None,
    )
    if narr_key:
        narr_cats = narrative_results[narr_key].categories
        # Compare top 20 categories from each
        orig_top = sorted(
            ((k, v) for k, v in original_cats.items() if v > 0),
            key=lambda x: x[1], reverse=True,
        )[:20]
        narr_top = sorted(
            ((k, v) for k, v in narr_cats.items() if v > 0),
            key=lambda x: x[1], reverse=True,
        )[:20]
        cat_comparison = {
            "original_top_20": [(k, round(v, 6)) for k, v in orig_top],
            "narrative_top_20": [(k, round(v, 6)) for k, v in narr_top],
            "overlap_count": len(set(k for k, _ in orig_top) & set(k for k, _ in narr_top)),
        }

    # 4. Compute the actual range of raw scores to determine compression source
    raw_range = max(raw_scores_original.values()) - min(raw_scores_original.values()) if raw_scores_original else 0
    calibrated_range = max(original_big_five.values()) - min(original_big_five.values()) if original_big_five else 0

    # 5. Determine verdict
    if raw_range < 0.001:
        verdict = "fundamental_limitation"
        explanation = (
            "Raw weighted category scores show minimal differentiation across domains "
            f"(range: {raw_range:.6f}). The Empath lexical categories, when mapped to Big Five "
            "domains, produce near-identical aggregate scores regardless of domain. This suggests "
            "lexical frequency counting at corpus level lacks sensitivity for personality "
            "differentiation — it measures genre/topic distribution rather than personality."
        )
    elif calibrated_range < 10 and raw_range > 0.002:
        verdict = "calibration_issue"
        explanation = (
            f"Raw scores differentiate (range: {raw_range:.6f}) but calibration formula "
            f"compresses to {calibrated_range:.1f}-point range. The `50 + raw * 2000` scaling "
            "does not adequately amplify the small raw differences."
        )
    elif raw_range > 0.001:
        verdict = "mapping_issue"
        explanation = (
            f"Some raw differentiation exists (range: {raw_range:.6f}) but the mapping from "
            "~200 Empath categories to 5 domains via weighted averaging dilutes distinct signals. "
            "Opposing category weights cancel out, producing regression to the mean."
        )
    else:
        verdict = "indeterminate"
        explanation = "Unable to isolate a single root cause."

    evaluation = {
        "verdict": verdict,
        "explanation": explanation,
        "missing_empath_categories": missing_cats,
        "valid_category_counts": {d: len(cs) for d, cs in valid_cats.items()},
        "raw_score_range": round(raw_range, 6),
        "calibrated_score_range": round(calibrated_range, 1),
        "raw_scores_pre_calibration": {k: round(v, 6) for k, v in raw_scores_original.items()},
        "original_big_five": original_big_five,
        "category_comparison": cat_comparison,
    }

    return evaluation


def print_comparison_table(
    original_llm: dict,
    original_empath: dict,
    narrative_llm_results: dict[str, dict],
    narrative_empath_results: dict[str, EmpathResult],
):
    """Print a comparison table of all analysis levels vs original."""
    domains = ["N", "E", "O", "A", "C"]

    # LLM comparison
    console.print("\n[bold cyan]═══ LLM Big Five Comparison ═══[/bold cyan]")
    table = Table(title="LLM Inference: Original Corpus vs Narratives")
    table.add_column("Level", style="bold")
    for d in domains:
        table.add_column(d, justify="right")
    table.add_column("Words", justify="right")

    # Original row
    orig_scores = {d: original_llm["big_five"]["domains"][d]["score"] for d in domains}
    table.add_row(
        "Original (corpus)",
        *[str(orig_scores[d]) for d in domains],
        f"{original_llm['big_five'].get('word_count_analyzed', '?'):,}",
        style="green",
    )

    for level in LEVELS:
        if level not in narrative_llm_results:
            continue
        result = narrative_llm_results[level]
        bf = result.get("big_five", {})
        if not bf:
            continue
        scores = {d: bf["domains"].get(d, {}).get("score", "?") for d in domains}
        words = bf.get("word_count_analyzed", "?")
        words_str = f"{words:,}" if isinstance(words, int) else str(words)
        table.add_row(level, *[str(scores[d]) for d in domains], words_str)

    console.print(table)

    # Delta table
    console.print("\n[bold cyan]═══ LLM Delta from Original ═══[/bold cyan]")
    delta_table = Table(title="Score Differences (Narrative - Original)")
    delta_table.add_column("Level", style="bold")
    for d in domains:
        delta_table.add_column(f"Δ{d}", justify="right")
    delta_table.add_column("Mean |Δ|", justify="right")

    for level in LEVELS:
        if level not in narrative_llm_results:
            continue
        result = narrative_llm_results[level]
        bf = result.get("big_five", {})
        if not bf:
            continue
        deltas = {}
        for d in domains:
            narr_score = bf["domains"].get(d, {}).get("score")
            if narr_score is not None:
                deltas[d] = narr_score - orig_scores[d]

        if deltas:
            mean_abs = sum(abs(v) for v in deltas.values()) / len(deltas)
            style = "green" if mean_abs < 10 else ("yellow" if mean_abs < 20 else "red")
            delta_table.add_row(
                level,
                *[f"{deltas.get(d, '?'):+.0f}" if isinstance(deltas.get(d), (int, float)) else "?" for d in domains],
                f"{mean_abs:.1f}",
                style=style,
            )

    console.print(delta_table)

    # Empath comparison
    console.print("\n[bold cyan]═══ Empath Big Five Comparison ═══[/bold cyan]")
    empath_table = Table(title="Empath Estimates: Original Corpus vs Narratives")
    empath_table.add_column("Level", style="bold")
    for d in domains:
        empath_table.add_column(d, justify="right")
    empath_table.add_column("Words", justify="right")

    orig_empath_scores = original_empath.get("big_five_estimates", {})
    empath_table.add_row(
        "Original (corpus)",
        *[str(orig_empath_scores.get(d, "?")) for d in domains],
        f"{original_empath.get('total_words', '?'):,}",
        style="green",
    )

    for level in LEVELS:
        if level not in narrative_empath_results:
            continue
        result = narrative_empath_results[level]
        empath_table.add_row(
            level,
            *[str(result.big_five_estimates.get(d, "?")) for d in domains],
            f"{result.total_words:,}",
        )

    console.print(empath_table)


def print_empath_evaluation(evaluation: dict):
    """Print the Empath methodology evaluation."""
    console.print("\n[bold cyan]═══ Empath Methodology Evaluation ═══[/bold cyan]")

    # Verdict
    verdict = evaluation["verdict"]
    color = {"fundamental_limitation": "red", "calibration_issue": "yellow",
             "mapping_issue": "yellow", "indeterminate": "dim"}.get(verdict, "white")
    console.print(f"\n[bold {color}]Verdict: {verdict.upper().replace('_', ' ')}[/bold {color}]")
    console.print(f"  {evaluation['explanation']}\n")

    # Missing categories
    if evaluation["missing_empath_categories"]:
        console.print("[bold]Missing Empath categories in Big Five mapping:[/bold]")
        for domain, cats in evaluation["missing_empath_categories"].items():
            console.print(f"  {domain}: {', '.join(cats)}")
        console.print()

    # Valid category counts
    console.print("[bold]Valid category counts per domain:[/bold]")
    for domain, count in evaluation["valid_category_counts"].items():
        console.print(f"  {domain}: {count} categories")

    # Raw vs calibrated ranges
    console.print(f"\n[bold]Score ranges:[/bold]")
    console.print(f"  Raw score range: {evaluation['raw_score_range']:.6f}")
    console.print(f"  Calibrated score range: {evaluation['calibrated_score_range']:.1f} points")

    # Raw pre-calibration scores
    console.print(f"\n[bold]Raw scores (pre-calibration):[/bold]")
    for domain, score in evaluation["raw_scores_pre_calibration"].items():
        console.print(f"  {domain}: {score:.6f}")

    # Category comparison
    comp = evaluation.get("category_comparison", {})
    if comp:
        console.print(f"\n[bold]Top-20 category overlap:[/bold] "
                      f"{comp.get('overlap_count', '?')}/20 shared between corpus and narrative")

        console.print("\n[bold]Original corpus top 10:[/bold]")
        for cat, val in comp.get("original_top_20", [])[:10]:
            console.print(f"  {cat:25s} {val:.6f}")

        console.print("\n[bold]Narrative top 10:[/bold]")
        for cat, val in comp.get("narrative_top_20", [])[:10]:
            console.print(f"  {cat:25s} {val:.6f}")


def run_level(
    level: str,
    *,
    skip_llm: bool = False,
    skip_empath: bool = False,
) -> tuple[EmpathResult | None, dict | None]:
    """Run analysis for a single level. Returns (empath_result, llm_result_dict)."""
    console.print(f"\n[bold magenta]{'=' * 60}[/bold magenta]")
    console.print(f"[bold magenta]  Level: {level}[/bold magenta]")
    console.print(f"[bold magenta]{'=' * 60}[/bold magenta]")

    samples = get_samples_for_level(level)
    total_words = sum(s.word_count for s in samples)
    console.print(f"  Loaded {len(samples)} sample(s), {total_words:,} words")

    if total_words < 1000:
        console.print(f"  [yellow]Warning: only {total_words:,} words — low confidence expected[/yellow]")

    suffix = output_suffix(level)
    empath_result = None
    llm_result_dict = None

    # Empath analysis
    if not skip_empath:
        console.print(f"\n  [bold]Running Empath analysis...[/bold]")
        empath_out = PROFILES / f"narrative{suffix}-empath.json"
        empath_result = analyze_empath(samples)
        # Save with custom filename
        empath_out.parent.mkdir(parents=True, exist_ok=True)
        empath_out.write_text(empath_result.model_dump_json(indent=2))
        console.print(f"  Saved to {empath_out}")

    # LLM analysis (via claude -p CLI)
    if not skip_llm:
        console.print(f"\n  [bold]Running LLM inference via claude -p...[/bold]")
        llm_out_path = PROFILES / f"narrative{suffix}-llm-claude.json"
        llm_result_dict = run_llm_analysis(samples, model="opus")
        # Save
        llm_out_path.parent.mkdir(parents=True, exist_ok=True)
        llm_out_path.write_text(json.dumps(llm_result_dict, indent=2))
        console.print(f"  Saved to {llm_out_path}")

    return empath_result, llm_result_dict


def main():
    parser = argparse.ArgumentParser(description="Analyze narratives for personality signal")
    parser.add_argument("--all", action="store_true", help="Run all 6 analysis levels")
    parser.add_argument("--level", choices=LEVELS, help="Run a single analysis level")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM inference (Empath only)")
    parser.add_argument("--skip-empath", action="store_true", help="Skip Empath analysis (LLM only)")
    parser.add_argument("--compare-only", action="store_true",
                        help="Skip analysis, just load existing results and compare")
    args = parser.parse_args()

    if not args.all and not args.level and not args.compare_only:
        parser.print_help()
        sys.exit(1)

    # Validate paths
    for path, name in [
        (V2_RYAN_FULL, "v2 ryan_first_person.md"),
        (FIONA_RYAN_FULL, "fiona ryan_first_person.md"),
        (V2_CHAPTERS_DIR, "v2 chapters/ryan"),
        (FIONA_CHAPTERS_DIR, "fiona chapters/ryan"),
    ]:
        if not path.exists():
            console.print(f"[red]Missing: {path} ({name})[/red]")
            sys.exit(1)

    # Load original results
    original_empath, original_llm = load_original_results()

    # Determine which levels to run
    levels_to_run = LEVELS if args.all else ([args.level] if args.level else [])

    empath_results: dict[str, EmpathResult] = {}
    llm_results: dict[str, dict] = {}

    if args.compare_only:
        # Load existing results from disk
        for level in LEVELS:
            suffix = output_suffix(level)
            empath_path = PROFILES / f"narrative{suffix}-empath.json"
            llm_path = PROFILES / f"narrative{suffix}-llm-claude.json"
            if empath_path.exists():
                data = json.loads(empath_path.read_text())
                empath_results[level] = EmpathResult(**data)
            if llm_path.exists():
                llm_results[level] = json.loads(llm_path.read_text())
    else:
        # Run analysis
        for level in levels_to_run:
            empath_r, llm_r = run_level(
                level,
                skip_llm=args.skip_llm,
                skip_empath=args.skip_empath,
            )
            if empath_r:
                empath_results[level] = empath_r
            if llm_r:
                llm_results[level] = llm_r

    # Print comparison tables
    if llm_results or empath_results:
        print_comparison_table(original_llm, original_empath, llm_results, empath_results)

    # Empath methodology evaluation
    if empath_results:
        evaluation = evaluate_empath_methodology(original_empath, empath_results)
        print_empath_evaluation(evaluation)

        # Save evaluation
        eval_path = PROFILES / "empath-evaluation.json"
        eval_path.write_text(json.dumps(evaluation, indent=2))
        console.print(f"\n  Saved Empath evaluation to {eval_path}")

    console.print("\n[bold green]Done.[/bold green]")


if __name__ == "__main__":
    main()
