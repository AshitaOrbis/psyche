# Measuring Whether Personality Context Actually Works: An Experimental Design

## The Question

Does injecting a personality-derived behavioral snippet into Claude's system prompt measurably shift its responses toward the profiled person's preferences?

The claim motivating Psyche is that trait labels ("High Openness, Low Agreeableness") are functionally useless in system prompts, but behavioral snippets ("Prefers probabilistic framing over categorical claims; skip unnecessary caveats") change what the model outputs. This claim is testable.

## Background: Peters, Cerf, & Matz (2024)

Peters, Cerf, and Matz demonstrated that LLMs can predict Big Five personality traits from text corpora with meaningful accuracy:

- **Assessment-optimized prompting**: r ~ .44 correlation with self-report (structured prompt instructing the model to act as a psychometrician)
- **Generic prompting** ("analyze this text for personality"): r ~ .117
- **Blind assessment** (model doesn't know it's assessing personality): r ~ .29-.33

The key finding: structured, assessment-optimized prompts outperform generic prompts by roughly 3.8x. The framing of the task matters more than the raw capability.

Psyche uses this methodology in its LLM inference method (weight 0.25 in the final profile). But Peters, Cerf, and Matz tested the *forward* direction: text corpus -> personality prediction. The question Psyche hasn't answered is the *reverse*: personality context -> behavioral shift.

## The Reverse Design

Instead of predicting personality from text, test whether personality-informed context shifts AI behavior toward the profile.

- **Independent variable**: System prompt condition (what the model knows about the user's personality)
- **Dependent variable**: Response quality as rated by the profiled person
- **Core hypothesis**: Behavioral snippets outperform trait labels; full persona model may not improve meaningfully over snippets (diminishing returns on context length)

## Experimental Protocol

### Stimuli

30 diverse prompts spanning six categories (5 per category):

1. **Advice requests** — career decisions, relationship dilemmas, practical problems
2. **Emotional support** — processing difficult events, grief, frustration
3. **Technical help** — debugging, system design, tool selection
4. **Creative collaboration** — brainstorming, writing feedback, ideation
5. **Disagreement scenarios** — the model must push back or deliver unwelcome analysis
6. **Ambiguous situations** — prompts with no clear "right answer" where personality determines preference

### Conditions (within-subject, randomized)

| Condition | Description | Context Length |
|-----------|-------------|----------------|
| A: Baseline | No personality context | 0 words |
| B: Trait labels | "High Openness (85/100), Low Agreeableness (32/100), ..." | ~50 words |
| C: Behavioral snippet | If-then patterns from CLAUDE.md generation (~500 words) | ~500 words |
| D: Full persona model | Structured JSON persona with all 10 dimensions + examples | ~2000 words |

Each prompt is presented to the model under all four conditions. The subject rates all four responses without knowing which condition produced which.

### Rating Dimensions

For each response, the subject rates on a 5-point Likert scale:

1. **Appropriateness** — "This response fits how I'd want to be spoken to"
2. **Anticipation** — "This response anticipated my needs or preferences"
3. **Naturalness** — "This feels like talking to someone who knows me"
4. **Usefulness** — "This response was more useful than a generic one would be"

### Blinding

- Subject does not know which condition produced which response
- Responses are presented in randomized order within each prompt
- Condition labels are not shown until after all ratings are complete
- Order of prompts is randomized across rating sessions

### Analysis

- **Primary**: Repeated-measures ANOVA across conditions (A, B, C, D) for each rating dimension
- **Pairwise comparisons**: Cohen's d for each pair (A vs B, A vs C, A vs D, B vs C, B vs D, C vs D)
- **Per-dimension breakdown**: Which aspects of response quality are most affected by personality context?
- **Per-category breakdown**: Does personality context matter more for emotional support than technical help?

## Power Analysis

This is a single-subject design (N=1 profiled person, multiple prompts as observations).

- 30 prompts x 4 conditions = 120 rated responses
- At alpha = .05, power = .80: can detect medium effects (d = 0.5) with 30 observations per condition
- For small effects (d = 0.3): increase to 50 prompts (200 rated responses)
- Non-parametric alternatives (Friedman test) available if normality assumptions are violated

The single-subject design is appropriate here because the question is "does *this specific* personality profile improve responses for *this specific* person" — not "does personality context improve responses in general." Generalization requires multi-subject replication (see Extensions).

## Implementation Plan (Future Work)

### Rating Web App

Build a simple web application:

1. **Prompt display**: Shows one prompt at a time
2. **Response presentation**: Shows 4 responses in randomized order (condition hidden)
3. **Rating interface**: 4 Likert scales per response (Appropriateness, Anticipation, Naturalness, Usefulness)
4. **Progress tracking**: Which prompts have been rated, session state persistence
5. **Data collection**: Timestamps, response order, ratings stored in structured JSON

### API Integration

- Pre-generate all 120 responses (30 prompts x 4 conditions) before rating begins
- Use identical model version and temperature (0.7) across all conditions
- Store full request/response pairs for reproducibility

### Analysis Pipeline

- Auto-generate analysis report with:
  - Condition means and standard deviations per dimension
  - ANOVA results (F-statistic, p-value, eta-squared)
  - Pairwise effect sizes with 95% confidence intervals
  - Visualization: condition x dimension interaction plots
- Raw data export for external analysis

## Extensions

### Multi-Subject Replication

Recruit 5-10 additional participants who:
1. Complete the full instrument battery (17 instruments)
2. Provide a text corpus for LLM inference
3. Generate their own behavioral snippet and persona model
4. Rate responses to the same 30 prompts under all 4 conditions

This tests whether the personality-context benefit generalizes across personality types, or whether it works better for certain profiles (e.g., those with extreme trait scores may benefit more from context).

### Cross-Model Comparison

Run the same protocol with:
- Claude (Sonnet, Opus)
- GPT-4/5
- Gemini

Does the behavioral snippet transfer across models, or is it model-specific? If model-specific, the CLAUDE.md snippet format may need model-aware variants.

### Longitudinal Stability

Retest the same subject after 6 months:
- Do ratings remain stable? (personality stability)
- Does a re-administered battery produce similar profiles? (measurement reliability)
- Do model updates change the effectiveness of the same snippet? (model sensitivity)

### Adversarial Condition

Add a fifth condition (E): intentionally *mismatched* profile.

- Take a profile with inverted trait scores
- Generate a behavioral snippet from the inverted profile
- Test whether a wrong profile is *worse* than no profile

If E < A (mismatched worse than baseline): the model is genuinely using personality context, not just performing "attentiveness theater."
If E ~ A: the model may be ignoring the personality context and just responding better to any additional system prompt content (a confound).

## What Would "Success" Look Like

| Finding | Interpretation |
|---------|----------------|
| C > B (behavioral snippet > trait labels) | Validates that *how* you describe personality matters more than *that* you describe it |
| D ~ C (full persona ~ snippet) | Validates conciseness — 500 words is sufficient, 2000 adds noise |
| Any condition > A (anything > baseline) | Validates personality context generally |
| B ~ A (trait labels ~ baseline) | Confirms the motivating claim: trait labels are useless in system prompts |
| C or D > A with d > 0.5 | Practically meaningful effect — worth the effort of profiling |
| E < A (mismatched < baseline) | Confirms genuine personality-context utilization, not placebo |

The ideal outcome: B ~ A, C >> B, D ~ C. This would mean trait labels add nothing, behavioral snippets add substantially, and more context doesn't help beyond the snippet. That's the cleanest validation of Psyche's design philosophy.

## Limitations

- Single-subject designs have limited generalizability
- Self-ratings of AI response quality are inherently subjective
- The profiled person may rate "appropriateness" based on expectations shaped by the profiling process itself (demand characteristics)
- Condition D (full persona) has a confound: more context = more tokens = potentially different model behavior independent of personality content
- Rating fatigue across 120 responses may reduce discrimination in later sessions

Mitigation: split rating across multiple sessions (e.g., 10 prompts per session, 3 sessions), randomize prompt order across sessions, include attention checks.
