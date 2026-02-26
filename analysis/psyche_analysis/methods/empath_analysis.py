"""Empath linguistic analysis for personality inference.

Maps Empath's 200+ lexical categories to Big Five personality traits.
Empath is an MIT-licensed LIWC alternative.
"""

from __future__ import annotations

from pathlib import Path

from empath import Empath
from pydantic import BaseModel
from rich.console import Console

from ..corpus.types import TextSample

console = Console()
lexicon = Empath()

# Empirically-derived mapping from Empath categories to Big Five domains.
# Based on LIWC-personality correlations from Yarkoni (2010) and
# Empath-LIWC validation from Fast et al. (2016).
EMPATH_TO_BIG_FIVE: dict[str, dict[str, float]] = {
    "N": {
        # Positive = more neurotic
        "negative_emotion": 0.3,
        "sadness": 0.2,
        "fear": 0.2,
        "nervousness": 0.25,
        "suffering": 0.15,
        "pain": 0.1,
        "anger": 0.15,
        "shame": 0.15,
        # Negative = less neurotic
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
        # Introversion indicators
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
        "travel": 0.1,
        "adventure": 0.15,
        "curiosity": 0.2,
    },
    "A": {
        "trust": 0.2,
        "sympathy": 0.2,
        "helping": 0.2,
        "politeness": 0.15,
        "giving": 0.15,
        "friends": 0.1,
        # Disagreeableness indicators
        "aggression": -0.2,
        "dominance": -0.15,
        "anger": -0.15,
        "swearing_terms": -0.2,
    },
    "C": {
        "work": 0.2,
        "achievement": 0.2,
        "order": 0.15,
        "planning": 0.15,
        "business": 0.1,
        "science": 0.1,
        # Low conscientiousness
        "leisure": -0.1,
        "party": -0.1,
    },
}


class EmpathResult(BaseModel):
    method: str = "empath"
    categories: dict[str, float] = {}
    big_five_estimates: dict[str, float] = {}
    top_categories: list[tuple[str, float]] = []
    total_words: int = 0


def analyze_empath(
    samples: list[TextSample],
    output_dir: Path | None = None,
) -> EmpathResult:
    """Run Empath linguistic analysis on text samples."""
    console.print(f"[bold]Running Empath analysis ({len(samples)} samples)...[/bold]")

    # Concatenate all text
    full_text = "\n\n".join(s.text for s in samples)
    total_words = len(full_text.split())

    # Analyze with Empath (normalize=True gives proportions)
    categories = lexicon.analyze(full_text, normalize=True)
    if categories is None:
        categories = {}

    # Map to Big Five estimates
    big_five: dict[str, float] = {}
    for domain, mapping in EMPATH_TO_BIG_FIVE.items():
        weighted_sum = 0.0
        total_weight = 0.0
        for cat, weight in mapping.items():
            if cat in categories:
                weighted_sum += categories[cat] * weight
                total_weight += abs(weight)

        if total_weight > 0:
            # Normalize to 0-100 scale (calibrated so typical text -> ~50)
            raw = weighted_sum / total_weight
            # Scale: typical range is about -0.01 to 0.01, map to 30-70
            normalized = 50 + raw * 2000  # rough calibration
            big_five[domain] = max(0, min(100, round(normalized, 1)))
        else:
            big_five[domain] = 50.0

    # Get top categories
    sorted_cats = sorted(
        ((k, v) for k, v in categories.items() if v > 0),
        key=lambda x: x[1],
        reverse=True,
    )

    result = EmpathResult(
        categories=categories,
        big_five_estimates=big_five,
        top_categories=sorted_cats[:20],
        total_words=total_words,
    )

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / "empath.json"
        out_path.write_text(result.model_dump_json(indent=2))
        console.print(f"  Saved to {out_path}")

    console.print(f"  Analyzed {total_words:,} words across {len(categories)} categories")
    console.print(f"  Big Five estimates: {big_five}")

    return result
