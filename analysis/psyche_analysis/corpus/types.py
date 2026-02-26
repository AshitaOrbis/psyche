"""Unified text sample type for all corpus sources."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TextSample(BaseModel):
    """A single text sample from any source."""

    id: str
    source: str  # chatgpt, claude_ai, sms, academic, facebook
    author: str  # "self" for user's own text, name for others
    timestamp: datetime | None = None
    text: str
    word_count: int = 0

    def model_post_init(self, _context: object) -> None:
        if self.word_count == 0:
            self.word_count = len(self.text.split())


class CorpusStats(BaseModel):
    """Summary statistics for a corpus."""

    total_samples: int = 0
    total_words: int = 0
    by_source: dict[str, SourceStats] = {}


class SourceStats(BaseModel):
    """Statistics for a single source."""

    samples: int = 0
    words: int = 0
    self_words: int = 0  # words authored by the user
    other_words: int = 0
    earliest: datetime | None = None
    latest: datetime | None = None
