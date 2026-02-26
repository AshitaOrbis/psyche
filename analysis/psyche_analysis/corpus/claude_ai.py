"""Parser for Claude.ai conversations.json export."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import orjson

from .types import TextSample


def parse_claude_ai(path: Path) -> list[TextSample]:
    """Parse Claude.ai conversations.json into TextSamples.

    Format: list of conversations with 'chat_messages' array.
    Each message has 'sender' (human/assistant), 'text', and 'content' array.
    """
    data = orjson.loads(path.read_bytes())
    samples: list[TextSample] = []

    for conv in data:
        messages = conv.get("chat_messages", [])

        for msg in messages:
            if msg.get("sender") != "human":
                continue

            # Try 'text' field first, then 'content' array
            text = msg.get("text", "")
            if not text:
                content_blocks = msg.get("content", [])
                text_parts = []
                for block in content_blocks:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        text_parts.append(block)
                text = "\n".join(text_parts)

            if not text or len(text.split()) < 5:
                continue

            created_at = msg.get("created_at")
            ts = datetime.fromisoformat(created_at) if created_at else None

            msg_id = msg.get("uuid", hashlib.sha256(text[:200].encode()).hexdigest()[:16])

            samples.append(
                TextSample(
                    id=f"claude-ai-{msg_id}",
                    source="claude_ai",
                    author="self",
                    timestamp=ts,
                    text=text,
                )
            )

    return samples
