"""Corpus manager: ingestion, statistics, and sampling."""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import orjson

from .types import CorpusStats, SourceStats, TextSample
from .chatgpt import parse_chatgpt
from .claude_ai import parse_claude_ai
from .sms import parse_sms
from .academic import parse_academic
from .voice_clone import parse_voice_clone


# Default data directory (relative to project root)
DEFAULT_DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "raw"


def ingest_source(source: str, data_dir: Path = DEFAULT_DATA_DIR) -> list[TextSample]:
    """Ingest a single source."""
    match source:
        case "chatgpt":
            path = data_dir / "chatgpt" / "conversations.json"
            return parse_chatgpt(path) if path.exists() else []
        case "claude_ai":
            path = data_dir / "claude-ai" / "conversations.json"
            return parse_claude_ai(path) if path.exists() else []
        case "sms":
            # Combined: old_phone (2015-2019) + sms_full (2019-2026)
            # Dedup overlap: old_phone messages before 2019-10-06 only
            samples: list[TextSample] = []
            old_phone = data_dir / "sms_old_phone.jsonl"
            if old_phone.exists():
                cutoff = datetime(2019, 10, 6, tzinfo=timezone.utc)
                samples.extend(parse_voice_clone(old_phone, "sms", before=cutoff))
            sms_full = data_dir / "sms_full.jsonl"
            if sms_full.exists():
                samples.extend(parse_voice_clone(sms_full, "sms"))
            return samples
        case "messenger":
            path = data_dir / "messenger.jsonl"
            return parse_voice_clone(path, "messenger") if path.exists() else []
        case "academic":
            path = data_dir / "academic"
            return parse_academic(path) if path.is_dir() else []
        case _:
            raise ValueError(f"Unknown source: {source}")


ALL_SOURCES = ["chatgpt", "claude_ai", "sms", "messenger", "academic"]


def ingest_all(data_dir: Path = DEFAULT_DATA_DIR) -> list[TextSample]:
    """Ingest all sources."""
    samples: list[TextSample] = []
    for source in ALL_SOURCES:
        samples.extend(ingest_source(source, data_dir))
    return samples


def compute_stats(samples: list[TextSample]) -> CorpusStats:
    """Compute corpus statistics."""
    stats = CorpusStats()
    by_source: dict[str, SourceStats] = defaultdict(SourceStats)

    for s in samples:
        stats.total_samples += 1
        stats.total_words += s.word_count

        src = by_source[s.source]
        src.samples += 1
        src.words += s.word_count

        if s.author == "self":
            src.self_words += s.word_count
        else:
            src.other_words += s.word_count

        if s.timestamp:
            if src.earliest is None or s.timestamp < src.earliest:
                src.earliest = s.timestamp
            if src.latest is None or s.timestamp > src.latest:
                src.latest = s.timestamp

    stats.by_source = dict(by_source)
    return stats


def sample_corpus(
    samples: list[TextSample],
    target_words: int = 50_000,
    seed: int = 42,
) -> list[TextSample]:
    """Diversity-sample corpus to target word count.

    Strategy:
    - Include ALL academic writing and Facebook (high signal, low volume)
    - Include ALL SMS from self (personal, authentic)
    - Diversity-sample AI conversation turns to fill remaining budget
      (stratified by source, preferring longer messages)
    """
    rng = random.Random(seed)

    # Priority 1: All high-signal sources
    priority_sources = {"academic", "facebook"}
    priority = [s for s in samples if s.source in priority_sources]
    priority_self_sms = [s for s in samples if s.source == "sms" and s.author == "self"]

    selected = priority + priority_self_sms
    used_words = sum(s.word_count for s in selected)

    # Priority 2: AI conversations (diversity-sampled)
    ai_samples = [
        s for s in samples
        if s.source in ("chatgpt", "claude_ai") and s.author == "self"
    ]

    # Filter debugging noise: skip very short messages and code-heavy messages
    ai_filtered = [
        s for s in ai_samples
        if s.word_count >= 10 and _code_ratio(s.text) < 0.5
    ]

    # Sort by word count descending (prefer substantive messages)
    ai_filtered.sort(key=lambda s: s.word_count, reverse=True)

    remaining_budget = target_words - used_words
    if remaining_budget > 0 and ai_filtered:
        # Stratify by source
        by_source: dict[str, list[TextSample]] = defaultdict(list)
        for s in ai_filtered:
            by_source[s.source].append(s)

        # Round-robin sample from each source
        source_lists = list(by_source.values())
        rng.shuffle(source_lists)
        idx = [0] * len(source_lists)

        while remaining_budget > 0:
            added = False
            for i, sl in enumerate(source_lists):
                if idx[i] >= len(sl):
                    continue
                sample = sl[idx[i]]
                if sample.word_count <= remaining_budget:
                    selected.append(sample)
                    remaining_budget -= sample.word_count
                    added = True
                idx[i] += 1
            if not added:
                break

    return selected


def _code_ratio(text: str) -> float:
    """Estimate ratio of code-like content in text."""
    lines = text.split("\n")
    if not lines:
        return 0.0
    code_indicators = sum(
        1 for line in lines
        if any(
            marker in line
            for marker in ["```", "import ", "def ", "class ", "function ", "const ", "let ", "var ", "=>", "//", "/*"]
        )
    )
    return code_indicators / len(lines)


def save_samples(samples: list[TextSample], path: Path) -> None:
    """Save samples to JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        for s in samples:
            f.write(orjson.dumps(s.model_dump(mode="json")) + b"\n")


def load_samples(path: Path) -> list[TextSample]:
    """Load samples from JSONL."""
    samples: list[TextSample] = []
    with open(path, "rb") as f:
        for line in f:
            if line.strip():
                samples.append(TextSample.model_validate_json(line))
    return samples
