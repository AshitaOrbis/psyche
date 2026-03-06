# Psyche — Psychometric Persona Profiling Framework

Open-source framework for constructing reliable personality profiles by triangulating validated psychometric instruments with LLM-based text analysis.

## Stack

| Component | Technology |
|-----------|-----------|
| Web App | React 19, TypeScript, Vite 6, Zustand, Recharts |
| Analysis | Python 3.12, Anthropic SDK, Empath, HuggingFace (optional) |
| Package Mgr | pnpm (web), uv (analysis) |
| Testing | Vitest (web), pytest (analysis) |

## Commands

```bash
# Web app
cd web && pnpm dev          # Dev server
cd web && pnpm test         # Run tests
cd web && pnpm typecheck    # Type check

# Analysis
cd analysis && uv run psyche ingest all     # Ingest corpus
cd analysis && uv run psyche analyze all    # Run analysis
cd analysis && uv run psyche synthesize     # Merge into profile
cd analysis && uv run psyche report         # Generate narrative
```

## Architecture

### Web App (web/)
- **Instrument Engine**: Config-driven instrument definitions with generic scoring
- **Test Runner**: Single-item display, keyboard shortcuts (1-7 for Likert, T/F for binary), progress tracking
- **State**: Zustand with localStorage persistence; full JSON export/import
- **Registry**: Central instrument registry with scoring functions

### Analysis Pipeline (analysis/)
- **Corpus Parsers**: ChatGPT, Claude.ai, SMS, academic writing, Facebook
- **Methods**: LLM inference (Claude + GPT), HuggingFace, Empath, GPV values
- **Synthesis**: Weighted merge, confidence intervals, narrative generation

### Profile Schema (v2)
- Structured JSON with scores from all methods
- Confidence intervals per trait
- Extended battery: attachment, emotion regulation, empathy, self-monitoring, LOC, grit, RIASEC, BPNS, HEXACO
- Persona model: structured behavioral patterns for AI agent simulation
- Human-readable narrative report (2000-4000 words)
- Behavioral CLAUDE.md snippet (~400-600 words, if-then patterns not trait labels)

## Key Design Decisions

- **Instruments are config, not code**: Each instrument is a data definition + scoring function registered at import time
- **Scoring is generic**: `scoreLikert()` handles reverse scoring, normalization for any Likert instrument; `scoreBinary()` for True/False instruments
- **Privacy first**: `profiles/` and `data/raw/` are gitignored; no corpus data leaves the machine except via explicit LLM API calls
- **Methods are independent**: Each analysis method produces scores independently; synthesis merges them with reliability weighting

## Instrument Battery

### Phase 1 (7 instruments, ~225 items)

| # | Instrument | Items | Measures |
|---|-----------|-------|----------|
| 1 | IPIP-NEO-120 | 120 | Big Five + 30 facets |
| 2 | CRT-7 | 7 | Analytical thinking |
| 3 | NCS-18 | 18 | Need for Cognition |
| 4 | Rosenberg | 10 | Self-esteem |
| 5 | SD3 | 27 | Dark Triad |
| 6 | PHQ-9 + GAD-7 | 16 | Depression/anxiety |
| 7 | Conversational Interview | 10-15 | Values, self-concept |

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

## Research Audit Trail

Analysis results feed a working paper (`shared/content/research/convergent-personality-assessment.md`). Maintain a clean audit trail:

### Archive Convention

**NEVER overwrite or delete analysis results.** Before re-running any analysis:

1. Archive current results to `profiles/analysis/archive/YYYY-MM-DD-{reason}/`
2. Write a `MANIFEST.md` in the archive directory documenting:
   - Date and reason for archival
   - What changed (bug fix, parameter change, new data)
   - Impact assessment (which scores changed, by how much)
   - Files included
3. Cross-reference related archives (e.g., a narrative fix archive should reference the original corpus archive if the same bug applied)

### Result Provenance

Every analysis output JSON should be self-documenting. At minimum, the output must record:
- Model used (full model ID or CLI shortname)
- Words analyzed (after all sampling/chunking, not total corpus size)
- Total corpus words (so the sampling ratio is visible)
- Number of samples / chunks
- Timestamp of analysis run
- Any truncation or sampling that occurred

### Data Integrity Issue — RESOLVED (2026-03-04)

The truncation bug in `prepare_text_chunks()` has been fixed. The pipeline now segments long samples into ~2,000-word units at word boundaries (preserving all content) and uses source-stratified round-robin chunking. The expanded corpus analysis (5 sources, 1.47M words, 13 analysis levels) is complete. See `profiles/analysis/archive/2026-03-03-pre-chunking-fix/MANIFEST.md` for the pre-fix archive and `BACKLOG.md` for the full resolution summary. Research paper updated to v2 with corrected scores.

## Corpus Sources

| Source | Format | Location | Words |
|--------|--------|----------|-------|
| SMS | JSONL | data/raw/sms -> symlink | 401K |
| Facebook Messenger | JSONL | data/raw/facebook -> symlink | 413K |
| ChatGPT | JSON tree | data/raw/chatgpt -> symlink | 333K |
| Claude.ai | JSON array | data/raw/claude-ai -> symlink | 167K |
| Academic Writing | Markdown | data/raw/academic -> symlink | 151K |

Total: ~1.47M words across 5 sources, ~62K samples. Analysis output: `profiles/analysis/corpus/`.
