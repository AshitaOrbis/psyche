"""Parser for ChatGPT conversations.json export."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import orjson

from .types import TextSample


def parse_chatgpt(path: Path) -> list[TextSample]:
    """Parse ChatGPT conversations.json into TextSamples.

    Format: list of conversations, each with a 'mapping' dict of nodes.
    Each node has a 'message' with 'author.role' and 'content.parts'.
    """
    data = orjson.loads(path.read_bytes())
    samples: list[TextSample] = []

    for conv in data:
        conv_title = conv.get("title", "untitled")
        mapping = conv.get("mapping", {})

        for node in mapping.values():
            msg = node.get("message")
            if not msg:
                continue

            role = msg.get("author", {}).get("role")
            if role != "user":
                continue

            content = msg.get("content", {})
            if not isinstance(content, dict):
                continue

            parts = content.get("parts", [])
            text_parts = [p for p in parts if isinstance(p, str) and p.strip()]
            if not text_parts:
                continue

            text = "\n".join(text_parts)
            if len(text.split()) < 5:
                continue

            create_time = msg.get("create_time")
            ts = (
                datetime.fromtimestamp(create_time, tz=timezone.utc)
                if create_time
                else None
            )

            msg_id = msg.get("id", hashlib.sha256(text[:200].encode()).hexdigest()[:16])

            samples.append(
                TextSample(
                    id=f"chatgpt-{msg_id}",
                    source="chatgpt",
                    author="self",
                    timestamp=ts,
                    text=text,
                )
            )

    return samples
