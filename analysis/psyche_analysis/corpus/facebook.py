"""Parser for Facebook narrative reports (Markdown + JSON)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .types import TextSample


def parse_facebook(directory: Path) -> list[TextSample]:
    """Parse Facebook narrative reports into TextSamples.

    Format: Markdown narrative files + JSON source data.
    """
    samples: list[TextSample] = []

    for md_file in sorted(directory.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        if not content or len(content.split()) < 20:
            continue

        file_id = hashlib.sha256(md_file.name.encode()).hexdigest()[:12]

        samples.append(
            TextSample(
                id=f"facebook-{file_id}",
                source="facebook",
                author="self",
                timestamp=None,
                text=content,
            )
        )

    return samples
