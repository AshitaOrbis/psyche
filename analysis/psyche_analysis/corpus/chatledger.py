"""ChatLedger enrichment reader: extracts behavioral patterns from enriched SMS chunks.

Reads from a ChatLedger SQLite database containing enriched SMS data with emotional tone,
relationship dynamics, and commitment tracking. The database path is configured via the
--chatledger-db CLI argument or PSYCHE_CHATLEDGER_DB environment variable.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


def read_chatledger_patterns(db_path: Path) -> dict[str, Any]:
    """Read enriched SMS chunks from ChatLedger SQLite and extract behavioral patterns.

    Returns a dict suitable for passing to persona.generate_persona_model().
    """
    if not db_path.exists():
        return {}

    patterns: dict[str, Any] = {
        "communication_style": {},
        "conflict_examples": [],
        "decision_examples": [],
        "emotional_patterns": {},
    }

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        # Discover schema - look for enrichment tables
        tables = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]

        # Try to find enriched chunks
        enrichment_table = None
        for t in tables:
            if "enrich" in t.lower() or "chunk" in t.lower():
                enrichment_table = t
                break

        if not enrichment_table:
            conn.close()
            return patterns

        # Read enriched data
        rows = conn.execute(f"SELECT * FROM {enrichment_table}").fetchall()
        columns = [desc[0] for desc in conn.execute(f"SELECT * FROM {enrichment_table} LIMIT 1").description]

        # Extract communication style metrics
        message_lengths: list[int] = []
        emotional_tones: list[str] = []

        for row in rows:
            row_dict = dict(zip(columns, row))

            # Extract enrichment JSON if present
            enrichment = None
            for col in ("enrichment", "enrichment_json", "metadata", "analysis"):
                if col in row_dict and row_dict[col]:
                    try:
                        enrichment = json.loads(row_dict[col]) if isinstance(row_dict[col], str) else row_dict[col]
                        break
                    except (json.JSONDecodeError, TypeError):
                        continue

            if not enrichment:
                continue

            # Extract emotional tone
            tone = enrichment.get("emotional_tone") or enrichment.get("tone")
            if tone:
                emotional_tones.append(str(tone))

            # Extract message length
            text = row_dict.get("text") or row_dict.get("content") or row_dict.get("message")
            if text:
                message_lengths.append(len(str(text)))

            # Extract conflict/decision examples from enrichment
            if enrichment.get("relationship_dynamics"):
                dynamics = enrichment["relationship_dynamics"]
                if isinstance(dynamics, dict) and dynamics.get("conflict"):
                    patterns["conflict_examples"].append({
                        "trigger": dynamics["conflict"].get("trigger", ""),
                        "response": dynamics["conflict"].get("response", ""),
                        "resolution": dynamics["conflict"].get("resolution", ""),
                    })

            if enrichment.get("commitment_tracking"):
                commit = enrichment["commitment_tracking"]
                if isinstance(commit, dict) and commit.get("decision"):
                    patterns["decision_examples"].append({
                        "situation": commit["decision"].get("context", ""),
                        "process": commit["decision"].get("process", ""),
                        "outcome": commit["decision"].get("result", ""),
                    })

        # Aggregate communication metrics
        if message_lengths:
            patterns["communication_style"]["avg_message_length"] = sum(message_lengths) / len(message_lengths)
            patterns["communication_style"]["total_messages"] = len(message_lengths)

        if emotional_tones:
            from collections import Counter
            tone_counts = Counter(emotional_tones)
            patterns["emotional_patterns"]["dominant_tone"] = tone_counts.most_common(1)[0][0]
            patterns["emotional_patterns"]["tone_distribution"] = dict(tone_counts)

        conn.close()

    except sqlite3.Error:
        pass

    return patterns
