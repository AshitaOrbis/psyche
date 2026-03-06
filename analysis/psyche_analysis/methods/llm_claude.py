"""LLM personality inference using Claude (Anthropic SDK).

Assessment-optimized prompting following Peters & Matz (2024).
Anti-sycophancy measures: blind inference without self-report data.
"""

from __future__ import annotations

import json
from pathlib import Path

from anthropic import Anthropic
from pydantic import BaseModel
from rich.console import Console

from ..corpus.types import TextSample

# Import prompts
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "prompts"))
from personality_inference import (  # noqa: E402
    SYSTEM_PROMPT,
    BIG_FIVE_ASSESSMENT_PROMPT,
    VALUES_ASSESSMENT_PROMPT,
)

console = Console()


class TraitScore(BaseModel):
    score: float
    confidence: str
    evidence: list[str] = []
    reasoning: str = ""


class BigFiveResult(BaseModel):
    domains: dict[str, TraitScore]
    facets: dict[str, TraitScore] = {}
    overall_confidence: str = "medium"
    caveats: list[str] = []
    word_count_analyzed: int = 0


class ValuesResult(BaseModel):
    values: dict[str, TraitScore]
    top_3_values: list[str] = []
    bottom_3_values: list[str] = []
    overall_confidence: str = "medium"


class LLMAnalysisResult(BaseModel):
    method: str = "llm-claude"
    big_five: BigFiveResult | None = None
    values: ValuesResult | None = None
    model_used: str = ""
    total_tokens: int = 0


def segment_samples(
    samples: list[TextSample],
    max_words_per_segment: int = 2000,
) -> list[TextSample]:
    """Split long samples into ~2K-word segments to prevent truncation.

    Short samples pass through unchanged. Long samples are split at word
    boundaries into segments of approximately max_words_per_segment words.
    """
    result: list[TextSample] = []
    for s in samples:
        words = s.text.split()
        if len(words) <= max_words_per_segment:
            result.append(s)
            continue

        for i in range(0, len(words), max_words_per_segment):
            seg_text = " ".join(words[i : i + max_words_per_segment])
            seg_num = i // max_words_per_segment + 1
            result.append(
                TextSample(
                    id=f"{s.id}_seg{seg_num:02d}",
                    source=s.source,
                    author=s.author,
                    timestamp=s.timestamp,
                    text=seg_text,
                )
            )
    return result


def prepare_text_chunks(
    samples: list[TextSample],
    max_words_per_chunk: int = 8000,
    max_chunks: int = 10,
) -> list[str]:
    """Prepare text samples into chunks for LLM analysis.

    Chunks are assembled to maximize diversity across sources.
    Samples are pre-segmented to avoid truncation of long documents.
    """
    # Pre-segment long samples instead of truncating
    segmented = segment_samples(samples)

    # Group by source
    by_source: dict[str, list[TextSample]] = {}
    for s in segmented:
        by_source.setdefault(s.source, []).append(s)

    # Sort each source by word count descending (prefer substantive samples)
    for source_samples in by_source.values():
        source_samples.sort(key=lambda s: s.word_count, reverse=True)

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_words = 0

    # Round-robin across sources
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


def analyze_big_five(
    samples: list[TextSample],
    model: str = "claude-sonnet-4-5-20250514",
) -> tuple[BigFiveResult, int]:
    """Run Big Five personality inference on text samples."""
    client = Anthropic()
    chunks = prepare_text_chunks(samples)

    all_results: list[dict] = []
    total_tokens = 0

    for i, chunk in enumerate(chunks):
        console.print(f"  Analyzing chunk {i + 1}/{len(chunks)} ({len(chunk.split())} words)...")

        prompt = BIG_FIVE_ASSESSMENT_PROMPT.format(text_samples=chunk)

        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        total_tokens += response.usage.input_tokens + response.usage.output_tokens

        # Parse JSON response
        text = response.content[0].text
        # Extract JSON from potential markdown code block
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        try:
            result = json.loads(text)
            all_results.append(result)
        except json.JSONDecodeError as e:
            console.print(f"  [red]Failed to parse chunk {i + 1}: {e}[/red]")

    if not all_results:
        raise ValueError("No valid results from any chunk")

    # Merge results by averaging scores across chunks
    merged = _merge_big_five_results(all_results)
    merged.word_count_analyzed = sum(len(c.split()) for c in chunks)

    return merged, total_tokens


def analyze_values(
    samples: list[TextSample],
    model: str = "claude-sonnet-4-5-20250514",
) -> tuple[ValuesResult, int]:
    """Run Schwartz Values inference on text samples."""
    client = Anthropic()
    chunks = prepare_text_chunks(samples, max_chunks=3)

    # Use the most diverse chunk
    chunk = chunks[0] if chunks else ""
    prompt = VALUES_ASSESSMENT_PROMPT.format(text_samples=chunk)

    console.print(f"  Analyzing values ({len(chunk.split())} words)...")

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    total_tokens = response.usage.input_tokens + response.usage.output_tokens

    text = response.content[0].text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    result = json.loads(text)

    values = {}
    for k, v in result.get("values", {}).items():
        values[k] = TraitScore(**v) if isinstance(v, dict) else TraitScore(score=50, confidence="low")

    return ValuesResult(
        values=values,
        top_3_values=result.get("top_3_values", []),
        bottom_3_values=result.get("bottom_3_values", []),
        overall_confidence=result.get("overall_confidence", "medium"),
    ), total_tokens


def run_full_analysis(
    samples: list[TextSample],
    model: str = "claude-sonnet-4-5-20250514",
    output_dir: Path | None = None,
) -> LLMAnalysisResult:
    """Run complete LLM personality analysis."""
    console.print(f"[bold]Running Claude LLM analysis ({len(samples)} samples, {model})...[/bold]")

    big_five, tokens_bf = analyze_big_five(samples, model)
    values, tokens_v = analyze_values(samples, model)

    result = LLMAnalysisResult(
        method="llm-claude",
        big_five=big_five,
        values=values,
        model_used=model,
        total_tokens=tokens_bf + tokens_v,
    )

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / "llm-claude.json"
        out_path.write_text(result.model_dump_json(indent=2))
        console.print(f"  Saved to {out_path}")

    console.print(f"  Total tokens: {result.total_tokens:,}")
    return result


def _merge_big_five_results(results: list[dict]) -> BigFiveResult:
    """Merge multiple chunk results by averaging scores."""
    domain_scores: dict[str, list[float]] = {}
    domain_evidence: dict[str, list[str]] = {}
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

        domains[key] = TraitScore(
            score=round(avg_score, 1),
            confidence=conf,
            evidence=evidence,
        )

    facets = {}
    for key in facet_scores:
        scores = facet_scores[key]
        avg_score = sum(scores) / len(scores)
        conf = _merge_confidence(facet_confidence.get(key, ["medium"]))
        facets[key] = TraitScore(
            score=round(avg_score, 1),
            confidence=conf,
        )

    # Overall confidence is the lowest domain confidence
    conf_order = {"low": 0, "medium": 1, "high": 2}
    overall = min(
        (d.confidence for d in domains.values()),
        key=lambda c: conf_order.get(c, 1),
        default="medium",
    )

    return BigFiveResult(
        domains=domains,
        facets=facets,
        overall_confidence=overall,
        caveats=list(dict.fromkeys(all_caveats)),
    )


def _merge_confidence(confidences: list[str]) -> str:
    """Merge confidence ratings from multiple chunks."""
    counts = {"low": 0, "medium": 0, "high": 0}
    for c in confidences:
        counts[c] = counts.get(c, 0) + 1
    # Return the mode
    return max(counts, key=lambda k: counts[k])
