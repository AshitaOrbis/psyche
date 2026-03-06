# Psyche Analysis Backlog

Deferred improvements and future experiments.

## ~~Critical: Re-Run Original Corpus LLM Analysis~~ COMPLETED

**Status**: COMPLETED — 2026-03-04
**Archive**: `profiles/analysis/archive/2026-03-03-pre-chunking-fix/`

### Resolution

Fixed three compounding bugs (per-sample truncation, max_samples limit, chunk budget). Expanded corpus from 3 to 5 sources (311K → 1.47M words) by adding SMS old-phone data and Facebook Messenger conversations. Ran full 13-level analysis (per-source, per-era, per-medium, full corpus).

**Key results:**

| Dimension | Old | New | Delta |
|-----------|-----|-----|-------|
| N | 62 | 51.1 | -10.9 |
| E | 18 | 28.3 | +10.3 |
| O | 92 | 88.6 | -3.4 |
| A | 32 | 36.4 | +4.4 |
| C | 38 | 61.4 | **+23.4** |

C shift (+23.4) was the truncation bug's primary casualty — academic papers (high C signal) were truncated to 2K words. The analysis also produced 13 levels of per-source, temporal, and per-medium comparisons. Research paper updated to v2 with all corrected scores, new Sections 3.8-3.9, and Appendix A.

**Output files**: `profiles/analysis/corpus/{level}-llm-claude.json`, `{level}-empath.json`, `comparison-summary.json`

### Cascading Effects (all addressed in paper v2)

- Table 4 merged scores recalculated
- Table 7 / S6 deltas recalculated (tighter range: 7.2-11.6 vs old 10.2-15.0)
- Self-enhancement analysis rewritten (C and N enhancement were partially artifact)
- Signal preservation pattern clarified (preserved O/E, amplified N, genre-inflated A, bracketed C)
- Differential personality experiment baseline updated in this BACKLOG

---

## Future Experiments

### Differential Personality Across Narrative Perspectives

**Status**: High priority — initial results make this experiment essential
**Estimated cost**: ~$3-5 (8 files x Opus LLM inference)
**Priority**: HIGH — the quantitative results from the Ryan PoV analysis are suggestive but inconclusive, and this experiment is the critical disambiguation step

### Motivation from Initial Results

The Ryan PoV narrative analysis (Section 3.7 of the research paper) produced a pattern of extreme trait preservation (O, E) with moderate trait mean-regression (A, C, N). However, the results cannot distinguish between two explanations:

1. **Signal preservation**: Narrative generation genuinely encodes personality signal, with extreme traits surviving transformation better than moderate ones
2. **Model-invariant output**: Opus produces similar personality profiles regardless of input, and the observed pattern reflects LLM inference biases rather than preserved signal

The differential experiment directly tests this: if interlocutor PoV files produce the SAME Big Five profile as Ryan PoV files, explanation #2 is supported and the "convergence" finding in the paper is substantially weakened.

### Input Files

Run the same LLM inference + Empath pipeline on ALL perspective files from the voice-clone narratives:

| File | Expected Personality | Reference Scores |
|------|---------------------|-----------------|
| `v2/ryan_first_person.md` | Ryan's personality (v2) | Already done: N=48-76, E=26-28, O=88 |
| `fiona/ryan_first_person.md` | Ryan's personality (v3) | Already done: N=82, E=28, O=83 |
| `v2/stephanie_first_person.md` | Interlocutor A's personality | Should differ from Ryan if signal preserved |
| `fiona/fiona_first_person.md` | Interlocutor B's personality | Should differ from Ryan if signal preserved |
| `v2/third_person_account.md` | Opus's authorial voice / blended | May reveal Opus's "default" personality |
| `fiona/third_person_account.md` | Opus's authorial voice / blended | Should correlate with v2 third-person |
| `v2/dual_pov_relationship.md` | Blended (both perspectives) | Should approximate average of pure PoVs |
| `fiona/dual_pov_relationship.md` | Blended (both perspectives) | Should approximate average of pure PoVs |

### Hypotheses

1. Interlocutor PoV files should produce DIFFERENT Big Five scores than Ryan PoV files (different person -> different personality)
2. Third-person files should produce a blended signal (between Ryan and interlocutor, plus Opus's authorial tendencies)
3. Dual PoV should correlate with an average of the two pure PoV personalities
4. **Critical confound test**: If ALL perspectives produce the SAME personality -> Opus has a fixed "voice" regardless of intended perspective -> the convergent assessment paper's findings are substantially weakened

### Decision Matrix

| Outcome | Paper Impact | Action |
|---------|-------------|--------|
| Interlocutors differ from Ryan | Strengthens signal preservation claim | Add as Section 3.8, upgrade "suggestive" to "supported" |
| All perspectives same profile | Serious confound | Reframe Section 3.7 as methodological limitation, downgrade claims |
| Third-person = Opus default, PoVs differ | Mixed — signal preservation for PoV, but Opus leaks its personality into omniscient narration | Nuanced discussion in Section 4 |
| Partial differentiation | Most likely outcome | Quantify degree of differentiation, discuss implications |

### Implementation

Extend `analyze_narratives.py` with additional levels for each perspective file. The infrastructure already supports arbitrary file/source combinations via the `LEVEL_CONFIGS` dict.

### Quantitative Baseline from Initial Results

For reference, the Ryan PoV analysis produced these scores:

| Level | N | E | O | A | C | Words | Mean Δ |
|-------|---|---|---|---|---|-------|--------|
| Original corpus (corrected) | 51.1 | 28.3 | 88.6 | 36.4 | 61.4 | 101,005 | — |
| v2 (full) | 78 | 27 | 89 | 52 | 54 | 32,927 | 10.3 |
| v2-early | 76 | 26 | 88 | 49 | 47 | 24,998 | 11.0 |
| v3 | 75 | 25 | 91 | 56 | 69 | 23,876 | 11.4 |
| v2+v3 | 75 | 26 | 88 | 50 | 58 | 40,055 | 8.8 |

The interlocutor PoV scores need to differ by *more* than the within-Ryan variance (~8-11 mean Δ against the corrected baseline) to support differentiation. A critical finding would be if ALL perspective files produce essentially the same profile (within ~5 points per dimension), which would indicate model-invariant output rather than genuine personality encoding.

---

## Potential Improvements

### Empath Calibration Overhaul

The current `50 + raw * 2000` calibration produces a 5.8-point spread across all Big Five domains (effectively no differentiation). Root cause analysis in `empath-evaluation.json` identifies this as primarily a calibration issue compounded by missing categories in the mapping.

Options:
- Empirical recalibration against known personality benchmarks
- Replace linear scaling with percentile mapping
- Accept Empath as a negative finding (methodological limitation) and document it

### LLM Inference Model Comparison

Run the same narrative analysis with multiple models (Sonnet, Opus, GPT-5) to test model-robustness of personality inference. The current implementation already supports `--model` parameter changes.
