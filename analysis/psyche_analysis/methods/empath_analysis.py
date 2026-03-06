"""Empath lexical analysis — comparative corpus characterization.

Empath is an MIT-licensed LIWC alternative with 200+ lexical categories.
It measures *what you write about*, not *who you are*: word frequency
patterns reflect communication register (formal vs casual, social vs
analytical) rather than personality traits.

This module produces ORDINAL/COMPARATIVE output suitable for characterizing
differences between corpus segments (sources, eras, mediums). It does NOT
produce population-normed personality scores.

Methodology:
  1. Compute category frequency norms (mean/stddev) from a reference corpus
  2. Z-score each target's category frequencies against those norms
  3. Weighted composite z-score per Big-Five-aligned dimension
  4. Ordinal label derived from z-score position (high/above/average/below/low)

The z-scores are meaningful only relative to the reference corpus.
A z=+1.0 on Openness means "more intellectual/creative language than
the corpus average," not "this person is one SD above the population
mean on Openness."
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Literal

from empath import Empath
from pydantic import BaseModel
from rich.console import Console

from ..corpus.types import TextSample

console = Console()
lexicon = Empath()

# Mapping from Empath categories to Big-Five-aligned lexical dimensions.
# Signs reflect direction of Yarkoni (2010) LIWC-personality correlations;
# magnitudes are relative importance weights within each dimension.
EMPATH_TO_BIG_FIVE: dict[str, dict[str, float]] = {
    "N": {
        "negative_emotion": 0.3,
        "sadness": 0.2,
        "fear": 0.2,
        "nervousness": 0.25,
        "suffering": 0.15,
        "pain": 0.1,
        "anger": 0.15,
        "shame": 0.15,
        "cheerfulness": -0.15,
        "optimism": -0.2,
        "contentment": -0.15,
    },
    "E": {
        "positive_emotion": 0.25,
        "cheerfulness": 0.2,
        "friends": 0.2,
        "party": 0.15,
        "social_media": 0.1,
        "speaking": 0.15,
        "optimism": 0.15,
        "fun": 0.15,
        "reading": -0.1,
        "philosophy": -0.1,
    },
    "O": {
        "art": 0.2,
        "philosophy": 0.2,
        "science": 0.15,
        "reading": 0.15,
        "writing": 0.15,
        "music": 0.15,
        "internet": 0.1,
    },
    "A": {
        "trust": 0.2,
        "sympathy": 0.2,
        "politeness": 0.15,
        "giving": 0.15,
        "friends": 0.1,
        "aggression": -0.2,
        "anger": -0.15,
        "swearing_terms": -0.2,
    },
    "C": {
        "work": 0.2,
        "achievement": 0.2,
        "order": 0.15,
        "business": 0.1,
        "science": 0.1,
        "leisure": -0.1,
        "party": -0.1,
    },
}

# Categories that were always zero in the corpus — excluded to avoid
# division-by-zero in z-scoring.
_EXCLUDED_ZERO_CATS = {"travel", "adventure", "curiosity", "helping", "dominance", "planning"}

OrdinalLabel = Literal["high", "above average", "average", "below average", "low"]


def _z_to_ordinal(z: float) -> OrdinalLabel:
    """Map a z-score to an ordinal label.

    Thresholds calibrated to the observed z-score distribution across
    corpus levels (SD ~0.22), so roughly 40% of levels get a non-average
    label — enough to surface meaningful differences without noise.
    """
    if z >= 0.5:
        return "high"
    if z >= 0.15:
        return "above average"
    if z > -0.15:
        return "average"
    if z > -0.5:
        return "below average"
    return "low"


class CategoryNorms(BaseModel):
    """Per-category mean and stddev from a reference corpus."""
    means: dict[str, float] = {}
    stddevs: dict[str, float] = {}
    n_segments: int = 0


class LexicalDimension(BaseModel):
    """A single Big-Five-aligned lexical dimension score."""
    z_score: float = 0.0
    label: OrdinalLabel = "average"


class EmpathResult(BaseModel):
    method: str = "empath"
    categories: dict[str, float] = {}
    lexical_profile: dict[str, LexicalDimension] = {}
    top_categories: list[tuple[str, float]] = []
    total_words: int = 0
    norms_source: str = "self"
    n_segments: int = 0


def compute_norms(
    samples: list[TextSample],
    segment_words: int = 5000,
) -> CategoryNorms:
    """Compute per-category frequency norms by segmenting the corpus.

    Splits the corpus into segments of ~segment_words words each,
    computes Empath frequencies per segment, then returns mean/stddev
    across segments. This gives us a within-corpus baseline distribution.
    """
    segments: list[str] = []
    current: list[str] = []
    current_words = 0

    for s in samples:
        current.append(s.text)
        current_words += s.word_count
        if current_words >= segment_words:
            segments.append("\n\n".join(current))
            current = []
            current_words = 0

    if current:
        segments.append("\n\n".join(current))

    if len(segments) < 3:
        return CategoryNorms(n_segments=len(segments))

    segment_cats: list[dict[str, float]] = []
    for seg in segments:
        cats = lexicon.analyze(seg, normalize=True)
        if cats:
            segment_cats.append(cats)

    if len(segment_cats) < 3:
        return CategoryNorms(n_segments=len(segment_cats))

    all_keys = set()
    for cats in segment_cats:
        all_keys.update(cats.keys())

    means: dict[str, float] = {}
    stddevs: dict[str, float] = {}

    for key in all_keys:
        vals = [cats.get(key, 0.0) for cats in segment_cats]
        m = sum(vals) / len(vals)
        means[key] = m
        if len(vals) > 1:
            variance = sum((v - m) ** 2 for v in vals) / (len(vals) - 1)
            stddevs[key] = math.sqrt(variance)
        else:
            stddevs[key] = 0.0

    return CategoryNorms(
        means=means,
        stddevs=stddevs,
        n_segments=len(segment_cats),
    )


def _compute_lexical_profile(
    categories: dict[str, float],
    norms: CategoryNorms,
) -> dict[str, LexicalDimension]:
    """Compute ordinal lexical profile from z-scored category frequencies.

    For each Big-Five-aligned dimension:
    1. Z-score each mapped category: z_i = (freq_i - mean_i) / stddev_i
    2. Weighted sum: composite = Σ(z_i × weight_i) / Σ|weight_i|
    3. Map composite z to ordinal label
    """
    profile: dict[str, LexicalDimension] = {}

    for domain, mapping in EMPATH_TO_BIG_FIVE.items():
        weighted_z_sum = 0.0
        total_weight = 0.0

        for cat, weight in mapping.items():
            if cat in _EXCLUDED_ZERO_CATS:
                continue
            if cat not in categories or cat not in norms.means:
                continue

            freq = categories[cat]
            mean = norms.means[cat]
            sd = norms.stddevs.get(cat, 0.0)

            if sd > 0:
                z = (freq - mean) / sd
            else:
                continue

            z = max(-3.0, min(3.0, z))
            weighted_z_sum += z * weight
            total_weight += abs(weight)

        if total_weight > 0:
            composite_z = weighted_z_sum / total_weight
        else:
            composite_z = 0.0

        profile[domain] = LexicalDimension(
            z_score=round(composite_z, 2),
            label=_z_to_ordinal(composite_z),
        )

    return profile


def analyze_empath(
    samples: list[TextSample],
    output_dir: Path | None = None,
    norms: CategoryNorms | None = None,
) -> EmpathResult:
    """Run Empath lexical analysis on text samples.

    Args:
        samples: Text samples to analyze.
        output_dir: Optional directory to save results.
        norms: Pre-computed category norms from a reference corpus.
            If None, norms are computed from the input samples (self-norming).
    """
    console.print(f"[bold]Running Empath analysis ({len(samples)} samples)...[/bold]")

    full_text = "\n\n".join(s.text for s in samples)
    total_words = len(full_text.split())

    categories = lexicon.analyze(full_text, normalize=True)
    if categories is None:
        categories = {}

    norms_source = "provided"
    if norms is None:
        norms = compute_norms(samples)
        norms_source = "self"

    if norms.n_segments >= 3:
        lexical_profile = _compute_lexical_profile(categories, norms)
    else:
        lexical_profile = {d: LexicalDimension() for d in EMPATH_TO_BIG_FIVE}
        console.print("  [yellow]Insufficient segments for z-score — all dimensions average[/yellow]")

    sorted_cats = sorted(
        ((k, v) for k, v in categories.items() if v > 0),
        key=lambda x: x[1],
        reverse=True,
    )

    result = EmpathResult(
        categories=categories,
        lexical_profile=lexical_profile,
        top_categories=sorted_cats[:20],
        total_words=total_words,
        norms_source=norms_source,
        n_segments=norms.n_segments,
    )

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / "empath.json"
        out_path.write_text(result.model_dump_json(indent=2))
        console.print(f"  Saved to {out_path}")

    profile_str = "  ".join(f"{d}={lp.label}" for d, lp in lexical_profile.items())
    console.print(f"  Analyzed {total_words:,} words across {len(categories)} categories")
    console.print(f"  Lexical profile: {profile_str}")
    console.print(f"  Norms: {norms_source} ({norms.n_segments} segments)")

    return result
