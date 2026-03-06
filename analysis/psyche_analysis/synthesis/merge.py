"""Merge scores from multiple methods into unified profile."""

from __future__ import annotations

import json
import math
from pathlib import Path

from rich.console import Console

from .profile import (
    PsycheProfile,
    BigFiveProfile,
    ValuesProfile,
    MergedTrait,
    TraitEstimate,
    AnalysisMetadata,
    FacetScore,
)

console = Console()

# Method reliability weights (based on literature)
# Empath excluded: measures language register, not personality traits.
# Empath data is used for comparative corpus characterization only.
METHOD_WEIGHTS = {
    "self-report": 0.35,  # Psychometric instruments
    "interview": 0.20,    # Semi-structured interview (Peters & Matz assessment condition)
    "llm-claude": 0.20,   # Assessment-optimized prompting (r~.44)
    "llm-gpt": 0.10,      # Cross-validation
    "huggingface": 0.07,   # Fine-tuned models
}

DOMAIN_NAMES = {
    "N": "Neuroticism",
    "E": "Extraversion",
    "O": "Openness",
    "A": "Agreeableness",
    "C": "Conscientiousness",
}

_FACET_NAMES = {
    "N1": "Anxiety", "N2": "Anger", "N3": "Depression",
    "N4": "Self-Consciousness", "N5": "Immoderation", "N6": "Vulnerability",
    "E1": "Friendliness", "E2": "Gregariousness", "E3": "Assertiveness",
    "E4": "Activity Level", "E5": "Excitement-Seeking", "E6": "Cheerfulness",
    "O1": "Imagination", "O2": "Artistic Interests", "O3": "Emotionality",
    "O4": "Adventurousness", "O5": "Intellect", "O6": "Liberalism",
    "A1": "Trust", "A2": "Morality", "A3": "Altruism",
    "A4": "Cooperation", "A5": "Modesty", "A6": "Sympathy",
    "C1": "Self-Efficacy", "C2": "Orderliness", "C3": "Dutifulness",
    "C4": "Achievement-Striving", "C5": "Self-Discipline", "C6": "Cautiousness",
}


def merge_profile(
    analysis_dir: Path,
    self_report_path: Path | None = None,
) -> PsycheProfile:
    """Merge all available analysis results into a unified profile.

    Reads from:
    - analysis_dir/llm-claude.json
    - analysis_dir/empath.json
    - self_report_path (exported from web app)
    """
    profile = PsycheProfile()
    methods_used: list[str] = []

    # Load LLM-Claude results
    llm_path = analysis_dir / "llm-claude.json"
    llm_data = None
    if llm_path.exists():
        llm_data = json.loads(llm_path.read_text())
        methods_used.append("llm-claude")
        profile.metadata.llm_tokens_used += llm_data.get("total_tokens", 0)

    # Load interview results
    interview_path = analysis_dir / "interview.json"
    interview_data = None
    if interview_path.exists():
        interview_data = json.loads(interview_path.read_text())
        methods_used.append("interview")

    # Empath is excluded from profile synthesis — it measures language
    # register (what you write about), not personality traits (who you are).
    # Empath data is used only for comparative corpus characterization.

    # Load self-report results
    self_report = None
    if self_report_path and self_report_path.exists():
        self_report = json.loads(self_report_path.read_text())
        methods_used.append("self-report")

    # Merge Big Five
    for domain_key in DOMAIN_NAMES:
        estimates: list[TraitEstimate] = []

        # LLM-Claude estimate
        if llm_data and llm_data.get("big_five"):
            domain_data = llm_data["big_five"].get("domains", {}).get(domain_key)
            if domain_data:
                estimates.append(TraitEstimate(
                    score=domain_data["score"],
                    confidence=domain_data.get("confidence", "medium"),
                    method="llm-claude",
                    evidence=domain_data.get("evidence", []),
                ))

        # Interview estimate
        if interview_data and interview_data.get("big_five"):
            domain_data = interview_data["big_five"].get("domains", {}).get(domain_key)
            if domain_data:
                estimates.append(TraitEstimate(
                    score=domain_data["score"],
                    confidence=domain_data.get("confidence", "medium"),
                    method="interview",
                    evidence=domain_data.get("evidence", []),
                ))

        # Self-report estimate (average NEO-120 and NEO-300 if both available)
        if self_report:
            results = self_report.get("results", {})
            sr_scores: list[float] = []

            for instrument_id in ("ipip-neo-120", "ipip-neo-300"):
                inst = results.get(instrument_id)
                if inst:
                    for s in inst.get("scores", []):
                        if s.get("scaleId") == domain_key:
                            sr_scores.append(s["normalized"])

            if sr_scores:
                avg_score = sum(sr_scores) / len(sr_scores)
                estimates.append(TraitEstimate(
                    score=avg_score,
                    confidence="high",
                    method="self-report",
                ))

        profile.big_five.domains[domain_key] = _merge_estimates(estimates)

    # Extract facet-level scores from NEO-120 and NEO-300
    if self_report:
        results = self_report.get("results", {})
        neo120_facets: dict[str, float] = {}
        neo300_facets: dict[str, float] = {}

        for inst_id, facet_dict in [("ipip-neo-120", neo120_facets), ("ipip-neo-300", neo300_facets)]:
            inst = results.get(inst_id)
            if inst:
                for s in inst.get("scores", []):
                    sid = s.get("scaleId", "")
                    if sid not in DOMAIN_NAMES:  # skip domain-level scores
                        facet_dict[sid] = s["normalized"]

        all_facet_ids = sorted(set(neo120_facets) | set(neo300_facets))
        for fid in all_facet_ids:
            v120 = neo120_facets.get(fid)
            v300 = neo300_facets.get(fid)
            vals = [v for v in (v120, v300) if v is not None]
            avg = sum(vals) / len(vals) if vals else None
            domain = fid[0] if fid and fid[0] in DOMAIN_NAMES else ""
            profile.big_five.facet_scores.append(FacetScore(
                facet_id=fid,
                name=_FACET_NAMES.get(fid, fid),
                domain=domain,
                neo120=v120,
                neo300=v300,
                average=round(avg, 1) if avg is not None else None,
            ))

    # Merge Values (from LLM + interview)
    all_value_keys: set[str] = set()
    value_sources: list[tuple[dict, str]] = []
    if llm_data and llm_data.get("values"):
        vals = llm_data["values"].get("values", {})
        all_value_keys.update(vals.keys())
        value_sources.append((vals, "llm-claude"))
    if interview_data and interview_data.get("values"):
        vals = interview_data["values"].get("values", {})
        all_value_keys.update(vals.keys())
        value_sources.append((vals, "interview"))

    for value_key in all_value_keys:
        value_estimates: list[TraitEstimate] = []
        for vals_dict, method_name in value_sources:
            vd = vals_dict.get(value_key)
            if isinstance(vd, dict):
                value_estimates.append(TraitEstimate(
                    score=vd.get("score", 50),
                    confidence=vd.get("confidence", "medium"),
                    method=method_name,
                    evidence=vd.get("evidence", []),
                ))
        if value_estimates:
            profile.values.values[value_key] = _merge_estimates(value_estimates)

    # Determine top/bottom values from merged scores
    sorted_values = sorted(
        profile.values.values.items(),
        key=lambda x: x[1].final_score,
        reverse=True,
    )
    profile.values.top_3 = [k for k, _ in sorted_values[:3]]
    profile.values.bottom_3 = [k for k, _ in sorted_values[-3:]]

    # Import self-report scores for all instruments
    if self_report:
        results = self_report.get("results", {})

        # CRT
        crt = results.get("crt-7")
        if crt:
            for s in crt.get("scores", []):
                if s.get("scaleId") == "crt-analytic":
                    profile.cognitive.crt_score = s["raw"]

        # NCS
        ncs = results.get("ncs-18")
        if ncs:
            for s in ncs.get("scores", []):
                if s.get("scaleId") == "ncs":
                    profile.cognitive.need_for_cognition = s["normalized"]

        # Rosenberg
        rses = results.get("rosenberg")
        if rses:
            for s in rses.get("scores", []):
                if s.get("scaleId") == "self-esteem":
                    profile.cognitive.self_esteem = s["normalized"]

        # SD3
        sd3 = results.get("sd3")
        if sd3:
            for s in sd3.get("scores", []):
                if s.get("scaleId") == "mach":
                    profile.dark_triad.machiavellianism = s["normalized"]
                elif s.get("scaleId") == "narc":
                    profile.dark_triad.narcissism = s["normalized"]
                elif s.get("scaleId") == "psych":
                    profile.dark_triad.psychopathy = s["normalized"]

        # PHQ-9 / GAD-7
        phq_gad = results.get("phq9-gad7")
        if phq_gad:
            for s in phq_gad.get("scores", []):
                if s.get("scaleId") == "phq9":
                    profile.clinical.phq9 = s["raw"]
                    profile.clinical.phq9_severity = _phq9_severity(s["raw"])
                elif s.get("scaleId") == "gad7":
                    profile.clinical.gad7 = s["raw"]
                    profile.clinical.gad7_severity = _gad7_severity(s["raw"])

        # ─── Phase 3: Extended Battery ───────────────────────

        # ECR-R (Attachment)
        ecr = results.get("ecr-r")
        if ecr:
            for s in ecr.get("scores", []):
                if s.get("scaleId") == "anxiety":
                    profile.attachment.anxiety = s["normalized"]
                elif s.get("scaleId") == "avoidance":
                    profile.attachment.avoidance = s["normalized"]

        # ERQ (Emotion Regulation)
        erq = results.get("erq-10")
        if erq:
            for s in erq.get("scores", []):
                if s.get("scaleId") == "reappraisal":
                    profile.emotion_reg.reappraisal = s["normalized"]
                elif s.get("scaleId") == "suppression":
                    profile.emotion_reg.suppression = s["normalized"]

        # IRI (Empathy)
        iri = results.get("iri-28")
        if iri:
            for s in iri.get("scores", []):
                if s.get("scaleId") == "fantasy":
                    profile.empathy.fantasy = s["normalized"]
                elif s.get("scaleId") == "perspective_taking":
                    profile.empathy.perspective_taking = s["normalized"]
                elif s.get("scaleId") == "empathic_concern":
                    profile.empathy.empathic_concern = s["normalized"]
                elif s.get("scaleId") == "personal_distress":
                    profile.empathy.personal_distress = s["normalized"]

        # Self-Monitoring
        sm = results.get("self-monitoring-18")
        if sm:
            for s in sm.get("scores", []):
                if s.get("scaleId") == "self-monitoring":
                    profile.social.self_monitoring = s["normalized"]

        # LOC IE-4
        loc = results.get("loc-ie4")
        if loc:
            for s in loc.get("scores", []):
                if s.get("scaleId") == "internal":
                    profile.social.loc_internal = s["normalized"]
                elif s.get("scaleId") == "external":
                    profile.social.loc_external = s["normalized"]

        # Grit-S
        grit = results.get("grit-s")
        if grit:
            for s in grit.get("scores", []):
                if s.get("scaleId") == "perseverance":
                    profile.grit.perseverance = s["normalized"]
                elif s.get("scaleId") == "interest_consistency":
                    profile.grit.interest_consistency = s["normalized"]

        # RIASEC
        riasec = results.get("riasec-48")
        if riasec:
            scale_map = {
                "realistic": "realistic",
                "investigative": "investigative",
                "artistic": "artistic",
                "social": "social",
                "enterprising": "enterprising",
                "conventional": "conventional",
            }
            for s in riasec.get("scores", []):
                field = scale_map.get(s.get("scaleId", ""))
                if field:
                    setattr(profile.vocational, field, s["normalized"])

        # BPNS
        bpns = results.get("bpns-9")
        if bpns:
            for s in bpns.get("scores", []):
                if s.get("scaleId") == "autonomy":
                    profile.needs.autonomy = s["normalized"]
                elif s.get("scaleId") == "competence":
                    profile.needs.competence = s["normalized"]
                elif s.get("scaleId") == "relatedness":
                    profile.needs.relatedness = s["normalized"]

        # HEXACO-60
        hexaco = results.get("hexaco-60")
        if hexaco:
            hexaco_map = {
                "hh": "honesty_humility",
                "em": "emotionality",
                "ex": "extraversion",
                "ag": "agreeableness",
                "co": "conscientiousness",
                "op": "openness",
            }
            for s in hexaco.get("scores", []):
                field = hexaco_map.get(s.get("scaleId", ""))
                if field:
                    setattr(profile.hexaco, field, s["normalized"])

    profile.metadata.methods_used = methods_used
    return profile


def _merge_estimates(estimates: list[TraitEstimate]) -> MergedTrait:
    """Merge multiple method estimates into a single score with CI."""
    if not estimates:
        return MergedTrait(final_score=50.0, confidence="low")

    if len(estimates) == 1:
        e = estimates[0]
        ci_half = 15 if e.confidence == "high" else 25 if e.confidence == "medium" else 35
        return MergedTrait(
            final_score=e.score,
            ci_lower=max(0, e.score - ci_half),
            ci_upper=min(100, e.score + ci_half),
            confidence=e.confidence,
            estimates=estimates,
        )

    # Weighted average
    total_weight = 0.0
    weighted_sum = 0.0
    for e in estimates:
        w = METHOD_WEIGHTS.get(e.method, 0.1)
        # Adjust weight by confidence
        conf_mult = {"high": 1.0, "medium": 0.7, "low": 0.4}.get(e.confidence, 0.5)
        effective_w = w * conf_mult
        weighted_sum += e.score * effective_w
        total_weight += effective_w

    final = weighted_sum / total_weight if total_weight > 0 else 50.0

    # Compute divergence (SD across estimates)
    scores = [e.score for e in estimates]
    mean = sum(scores) / len(scores)
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    divergence = math.sqrt(variance)

    # CI based on divergence and number of methods
    ci_half = max(5, divergence * 1.5) if len(estimates) >= 2 else 20

    # Overall confidence
    if divergence > 20:
        conf = "low"
    elif divergence > 10 or any(e.confidence == "low" for e in estimates):
        conf = "medium"
    else:
        conf = "high"

    return MergedTrait(
        final_score=round(final, 1),
        ci_lower=max(0, round(final - ci_half, 1)),
        ci_upper=min(100, round(final + ci_half, 1)),
        confidence=conf,
        estimates=estimates,
        divergence=round(divergence, 1),
    )


def _phq9_severity(score: float) -> str:
    if score < 5: return "none"
    if score < 10: return "mild"
    if score < 15: return "moderate"
    if score < 20: return "moderately severe"
    return "severe"


def _gad7_severity(score: float) -> str:
    if score < 5: return "none"
    if score < 10: return "mild"
    if score < 15: return "moderate"
    return "severe"
