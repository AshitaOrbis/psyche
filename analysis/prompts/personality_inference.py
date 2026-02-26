"""Assessment-optimized prompt templates for LLM personality inference.

Based on Peters & Matz (2024): assessment-optimized prompting achieves r=.443
with self-report vs r=.117 for generic prompting.
"""

SYSTEM_PROMPT = """You are a personality assessment psychologist conducting a structured evaluation.

You will analyze text samples written by a person and assess their personality traits.

CRITICAL RULES:
1. Base ALL assessments ONLY on evidence in the provided text. Quote specific passages.
2. Do NOT assume traits from occupation, demographics, or stereotypes.
3. If evidence is insufficient for a trait, say so explicitly and give lower confidence.
4. Distinguish between what someone TALKS ABOUT vs what they ARE. Discussing anger doesn't mean high Neuroticism.
5. Look for behavioral patterns, not single instances.
6. Consider the CONTEXT of writing (academic, casual, technical) when interpreting tone.
7. Be especially careful with Agreeableness — it's hardest to infer from text (r~.22).
"""

BIG_FIVE_ASSESSMENT_PROMPT = """Analyze the following text samples written by ONE person and assess their Big Five personality traits.

For each domain, provide:
1. A score from 1-100 (50 = population average)
2. Confidence level: high (strong evidence), medium, or low (sparse evidence)
3. 2-3 specific quotes that support your assessment
4. Brief reasoning

The five domains are:
- Neuroticism (N): anxiety, anger, depression, self-consciousness, impulsiveness, vulnerability
- Extraversion (E): warmth, gregariousness, assertiveness, activity, excitement-seeking, positive emotions
- Openness (O): fantasy, aesthetics, feelings, actions, ideas, values
- Agreeableness (A): trust, straightforwardness, altruism, compliance, modesty, tender-mindedness
- Conscientiousness (C): competence, order, dutifulness, achievement striving, self-discipline, deliberation

Also assess the 6 facets within each domain if sufficient evidence exists.

TEXT SAMPLES:
---
{text_samples}
---

Respond in this exact JSON format:
{{
  "domains": {{
    "N": {{
      "score": <1-100>,
      "confidence": "<high|medium|low>",
      "evidence": ["<quote1>", "<quote2>"],
      "reasoning": "<brief explanation>"
    }},
    "E": {{ ... }},
    "O": {{ ... }},
    "A": {{ ... }},
    "C": {{ ... }}
  }},
  "facets": {{
    "N1_anxiety": {{ "score": <1-100>, "confidence": "<high|medium|low>" }},
    "N2_anger": {{ ... }},
    ...
  }},
  "overall_confidence": "<high|medium|low>",
  "caveats": ["<any important caveats about the assessment>"],
  "word_count_analyzed": <number>
}}
"""

VALUES_ASSESSMENT_PROMPT = """Analyze the following text samples and assess this person's core values using the Schwartz Values framework.

The 10 basic values (in motivational circle order):
1. Self-Direction: independent thought, creativity, freedom
2. Stimulation: excitement, novelty, challenge
3. Hedonism: pleasure, sensuous gratification
4. Achievement: personal success, competence
5. Power: social status, dominance, control
6. Security: safety, stability, harmony
7. Conformity: restraint, obedience to expectations
8. Tradition: respect for customs, acceptance of traditions
9. Benevolence: welfare of close others, helpfulness
10. Universalism: understanding, tolerance, protecting all people and nature

TEXT SAMPLES:
---
{text_samples}
---

Respond in this exact JSON format:
{{
  "values": {{
    "self_direction": {{ "score": <1-100>, "confidence": "<high|medium|low>", "evidence": ["<quote>"] }},
    "stimulation": {{ ... }},
    "hedonism": {{ ... }},
    "achievement": {{ ... }},
    "power": {{ ... }},
    "security": {{ ... }},
    "conformity": {{ ... }},
    "tradition": {{ ... }},
    "benevolence": {{ ... }},
    "universalism": {{ ... }}
  }},
  "top_3_values": ["<value1>", "<value2>", "<value3>"],
  "bottom_3_values": ["<value1>", "<value2>", "<value3>"],
  "overall_confidence": "<high|medium|low>"
}}
"""
