# Psyche

Open-source framework for constructing reliable personality profiles by triangulating validated psychometric instruments with LLM-based text analysis.

## Quick Start

### Web App (Psychometric Instruments)

```bash
cd web
pnpm install
pnpm dev        # http://localhost:5173
```

Complete the instrument battery (17 instruments across two phases), then export your results as JSON for profile synthesis.

### Analysis Pipeline (Text Corpus)

```bash
cd analysis
uv sync

# Ingest text corpus (symlink your data into data/raw/ first)
uv run psyche ingest all

# Create diversity-sampled subset
uv run psyche sample

# Run analysis
uv run psyche analyze empath           # Local, no API cost
uv run psyche analyze llm-claude       # Requires ANTHROPIC_API_KEY (pip install psyche-analysis[llm])

# Merge into unified profile
uv run psyche synthesize --self-report path/to/export.json

# View report
uv run psyche report
```

## Architecture

### Web App (`web/`)
- **React 19 + TypeScript + Vite 6** with Zustand state management
- Config-driven instrument definitions with generic scoring engine
- Single-item display with keyboard shortcuts (1-7 for Likert, T/F for binary, arrow keys for navigation)
- localStorage persistence with full JSON export/import

### Analysis Pipeline (`analysis/`)
- **Corpus parsers**: ChatGPT, Claude.ai, SMS, academic writing, Facebook
- **Quality filters**: AI-generated content detection, authorship verification, gibberish filtering
- **LLM inference**: Assessment-optimized prompting (Peters & Matz 2024, r~.44)
- **Empath analysis**: 200+ lexical categories mapped to Big Five
- **Profile synthesis**: Weighted merge with confidence intervals
- **Persona model**: Facet-level behavioral patterns for AI context generation

### Outputs
- **Profile JSON**: Structured data for all traits, methods, and confidence intervals
- **Narrative Report**: Human-readable markdown report (2000-4000 words)
- **CLAUDE.md Snippet**: ~500 word behavioral context for AI assistants (if-then patterns, not trait labels)

## Instrument Battery

### Phase 1 (7 instruments, ~225 items)

| # | Instrument | Items | Measures |
|---|-----------|-------|----------|
| 1 | IPIP-NEO-120 | 120 | Big Five + 30 facets |
| 2 | CRT-7 | 7 | Analytical thinking |
| 3 | NCS-18 | 18 | Need for Cognition |
| 4 | Rosenberg | 10 | Self-esteem |
| 5 | SD3 | 27 | Dark Triad |
| 6 | PHQ-9 + GAD-7 | 16 | Depression/anxiety screening |
| 7 | Conversational Interview | 10-15 | Values, self-concept, behavioral examples |

### Phase 2 (10 instruments, ~561 additional items)

| # | Instrument | Items | Format | Measures |
|---|-----------|-------|--------|----------|
| 8 | IPIP-NEO-300 | 300 | 5-pt Likert | Big Five + 30 facets (10 items/facet) |
| 9 | HEXACO-60 | 60 | 5-pt Likert | 6 factors inc. Honesty-Humility |
| 10 | ECR-R | 36 | 7-pt Likert | Attachment: Anxiety + Avoidance |
| 11 | ERQ-10 | 10 | 7-pt Likert | Emotion regulation: Reappraisal + Suppression |
| 12 | IRI-28 | 28 | 5-pt Likert | Empathy: 4 dimensions |
| 13 | Self-Monitoring-18 | 18 | True/False | Social flexibility vs consistency |
| 14 | LOC IE-4 | 4 | 5-pt Likert | Internal/External locus of control |
| 15 | Grit-S | 8 | 5-pt Likert | Perseverance + Interest consistency |
| 16 | RIASEC-48 | 48 | 5-pt Likert | Vocational interests (6 types) |
| 17 | BPNS-9 | 9 | 7-pt Likert | Basic needs: Autonomy, Competence, Relatedness |

## Methodology

The framework triangulates four independent evidence sources:

| Method | Expected Accuracy | Weight | Notes |
|--------|-------------------|--------|-------|
| Psychometric self-report | Alpha ~.85+ | 0.40 | 17 validated instruments |
| LLM inference (Claude) | r~.44 | 0.25 | Assessment-optimized prompting (Peters & Matz 2024) |
| Empath linguistic analysis | LIWC-validated | 0.10 | 200+ lexical categories |
| Conversational interview | Qualitative | 0.25 | Semi-structured 10-question protocol |

Confidence intervals reflect cross-method agreement. When methods diverge significantly (SD > 15), the trait is flagged as context-dependent.

### Persona Model

The synthesis generates a 10-dimension persona model mapping psychometric scores to behavioral predictions:

1. **Communication** — directness, depth preference, rationale needs, audience adaptation
2. **Decision-making** — attribution style, risk orientation, deliberation process
3. **Conflict response** — behavior under criticism, regulation strategy, feedback preference
4. **Motivation** — primary needs, persistence patterns, interest consistency
5. **Epistemic style** — analytical tendency, uncertainty tolerance, source preferences
6. **Interpersonal** — trust threshold, empathy mode, ethical stance
7. **Stress response** — crisis mode, recovery strategy, coping mechanisms
8. **Relationships** — attachment style, initiation/maintenance patterns
9. **Flow states** — triggers, phenomenology, barriers
10. **Self-concept** — identity model, competence gap, comparative orientation

The persona model generates behavioral CLAUDE.md snippets — if-then patterns that tell an AI assistant how to behave differently, not trait labels that describe the person.

### ChatLedger Integration (Optional)

If you have a [ChatLedger](https://github.com/AshitaOrbis/chatledger) database with enriched SMS data, pass it to the synthesizer for additional behavioral evidence:

```bash
uv run psyche synthesize --self-report export.json --chatledger-db /path/to/chatledger/
# Or via environment variable:
export PSYCHE_CHATLEDGER_DB=/path/to/chatledger/
uv run psyche synthesize --self-report export.json
```

## Validation

See [docs/VALIDATION-DESIGN.md](docs/VALIDATION-DESIGN.md) for the experimental design to test whether personality-derived context actually shifts AI behavior toward the profiled person's preferences.

## Privacy

- `profiles/`, `data/raw/`, `data/ingested/`, `data/sampled/` are gitignored
- `web/public/seed-data.json` and `web/public/profile.json` are gitignored (see `.example.json` files for schema)
- No corpus data leaves the machine except via explicit LLM API calls
- Self-report data is stored in localStorage (browser-only)

## License

MIT
