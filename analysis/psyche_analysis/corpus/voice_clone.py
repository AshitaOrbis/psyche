"""Parser for voice-clone JSONL files (messenger, sms_full, sms_old_phone).

Shared schema:
  {"sender": "me", "contact": "...", "timestamp": "...", "text": "...", "direction": "sent", "source": "..."}
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import orjson

from .types import TextSample


def parse_voice_clone(
    path: Path,
    source_label: str,
    min_words: int = 3,
    before: datetime | None = None,
) -> list[TextSample]:
    """Parse a voice-clone JSONL file into self-authored TextSamples.

    Args:
        path: Path to the JSONL file.
        source_label: Source label for TextSample (e.g. "sms", "messenger").
        min_words: Skip messages shorter than this.
        before: If set, only include messages with timestamp < before (for dedup).
    """
    samples: list[TextSample] = []

    with open(path, "rb") as f:
        for idx, line in enumerate(f):
            if not line.strip():
                continue

            msg = orjson.loads(line)

            # Only self-authored messages
            if msg.get("sender") != "me" and msg.get("direction") != "sent":
                continue

            text = msg.get("text", "")
            if not text or len(text.split()) < min_words:
                continue

            ts_str = msg.get("timestamp")
            ts = datetime.fromisoformat(ts_str) if ts_str else None

            # Dedup cutoff for overlapping date ranges
            if before and ts and ts >= before:
                continue

            samples.append(
                TextSample(
                    id=f"{source_label}-{idx:06d}",
                    source=source_label,
                    author="self",
                    timestamp=ts,
                    text=text,
                )
            )

    return samples
