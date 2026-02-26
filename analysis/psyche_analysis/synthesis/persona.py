"""Persona model generator: maps psychometric scores to behavioral predictions."""

from __future__ import annotations

import re

from .profile import (
    PsycheProfile,
    PersonaModel,
    CommunicationStyle,
    DecisionStyle,
    ConflictStyle,
    MotivationStyle,
    EpistemicStyle,
    InterpersonalStyle,
    StressResponse,
    RelationshipPatterns,
    FlowStates,
    SelfConcept,
    DecisionExample,
    ConflictExample,
)


def generate_persona_model(
    profile: PsycheProfile,
    interview_transcript: str | None = None,
    chatledger_patterns: dict | None = None,
) -> PersonaModel:
    """Generate a structured persona model from profile scores and qualitative data.

    Uses facet-level NEO data where available (more precise than domain scores),
    cross-validates with HEXACO convergent factors, and extracts behavioral
    examples from interview transcript.
    """
    persona = PersonaModel()
    persona.communication = _build_communication(profile)
    persona.decision_making = _build_decision(profile)
    persona.conflict_response = _build_conflict(profile)
    persona.motivation = _build_motivation(profile)
    persona.epistemic_style = _build_epistemic(profile)
    persona.interpersonal = _build_interpersonal(profile)
    persona.stress_response = _build_stress_response(profile)
    persona.relationships = _build_relationships(profile)
    persona.flow_states = _build_flow_states(profile)
    persona.self_concept = _build_self_concept(profile)

    # Extract characteristic phrases and behavioral examples from interview
    if interview_transcript:
        persona.characteristic_phrases = _extract_phrases(interview_transcript)
        persona.decision_examples = _extract_decision_examples(interview_transcript)
        persona.conflict_examples = _extract_conflict_examples(interview_transcript)

    # Integrate ChatLedger observed patterns
    if chatledger_patterns:
        _integrate_chatledger(persona, chatledger_patterns)

    return persona


# ─── Helper: get facet score ─────────────────────────────────────

def _facet(profile: PsycheProfile, facet_id: str) -> float | None:
    """Get the best available facet score (prefer NEO-300 > average > NEO-120)."""
    for fs in profile.big_five.facet_scores:
        if fs.facet_id == facet_id:
            if fs.neo300 is not None:
                return fs.neo300
            if fs.average is not None:
                return fs.average
            return fs.neo120
    return None


# ─── Communication ───────────────────────────────────────────────

def _build_communication(p: PsycheProfile) -> CommunicationStyle:
    style = CommunicationStyle()
    d = p.big_five.domains

    # Directness: use facet-level A1 (Trust) and A4 (Cooperation) if available,
    # plus cross-validate with HEXACO-A and text analysis estimates
    a = d.get("A")
    a1_trust = _facet(p, "A1")
    a4_coop = _facet(p, "A4")

    # Check if text analysis gave substantially lower Agreeableness than self-report
    # (common pattern: self-report inflates cooperation, text reveals directness)
    text_a_lower = False
    if a:
        for est in a.estimates:
            if est.method in ("llm-claude", "interview") and est.score < 40:
                text_a_lower = True
                break

    if text_a_lower or (p.hexaco.agreeableness is not None and p.hexaco.agreeableness < 40):
        # Text analysis and/or HEXACO show directness that self-report misses
        style.directness = "Very direct in natural communication; self-report overstates agreeableness"
    elif a and a.final_score < 35:
        style.directness = "Very direct; values bluntness over tact"
    elif a and a.final_score < 45:
        style.directness = "Direct but not aggressive; prefers clarity"
    elif a and a.final_score >= 65:
        style.directness = "Diplomatic; frames things constructively"
    else:
        style.directness = "Balanced directness"

    # Depth from Openness (especially O5 Intellect) + NCS
    o = d.get("O")
    o5_intellect = _facet(p, "O5")
    ncs = p.cognitive.need_for_cognition

    if (o5_intellect and o5_intellect >= 80) or (o and o.final_score >= 60 and ncs and ncs >= 60):
        style.depth_preference = "Prefers depth and nuance; comfortable with long, detailed responses"
    elif o and o.final_score < 40:
        style.depth_preference = "Prefers concise, practical responses"
    else:
        style.depth_preference = "Moderate depth preference"

    # Rationale: NCS is the primary driver, not Conscientiousness domain score
    # (C domain can be low while C3 Dutifulness is very high)
    c3_dutifulness = _facet(p, "C3")
    if ncs and ncs >= 60:
        style.rationale_need = "Needs to understand WHY, not just WHAT; rejects instructions without reasoning"
    elif c3_dutifulness and c3_dutifulness >= 70 and ncs and ncs >= 50:
        style.rationale_need = "Values rationale; follows rules when the reasoning is clear"
    else:
        style.rationale_need = "Moderate need for rationale"

    # Audience adaptation from Self-Monitoring
    if p.social.self_monitoring is not None:
        if p.social.self_monitoring < 35:
            style.audience_adaptation = "Cross-situationally consistent; does not modulate style for audience"
        elif p.social.self_monitoring >= 65:
            style.audience_adaptation = "High social adaptability; naturally mirrors conversational register"
        else:
            style.audience_adaptation = "Moderate audience adaptation"

    # Analogy domains from RIASEC
    riasec = {
        "investigative": p.vocational.investigative,
        "artistic": p.vocational.artistic,
        "social": p.vocational.social,
        "enterprising": p.vocational.enterprising,
        "realistic": p.vocational.realistic,
        "conventional": p.vocational.conventional,
    }
    top = sorted(
        [(k, v) for k, v in riasec.items() if v is not None and v >= 50],
        key=lambda x: x[1],
        reverse=True,
    )[:3]
    style.analogy_domains = [k for k, _ in top]

    return style


# ─── Decision-Making ─────────────────────────────────────────────

def _build_decision(p: PsycheProfile) -> DecisionStyle:
    style = DecisionStyle()

    # Attribution from LOC
    if p.social.loc_internal is not None and p.social.loc_external is not None:
        if p.social.loc_internal > p.social.loc_external + 15:
            style.attribution_style = "Strong internal locus; attributes outcomes to own actions and choices"
        elif p.social.loc_external > p.social.loc_internal + 15:
            style.attribution_style = "External locus; highly aware of environmental constraints and luck"
        else:
            style.attribution_style = "Balanced attribution; recognizes both personal agency and external factors"

    # Risk orientation: use facet-level data (N4 Self-Consciousness, C6 Cautiousness)
    n4_selfconscious = _facet(p, "N4")
    c6_cautious = _facet(p, "C6")
    n = p.big_five.domains.get("N")

    if n4_selfconscious and n4_selfconscious >= 65 and c6_cautious and c6_cautious >= 60:
        style.risk_orientation = "Risk-averse in social/reputational domains; cautious deliberation before action"
    elif n and n.final_score >= 55:
        style.risk_orientation = "Risk-averse; potential failure weighs more than potential gain"
    elif n and n.final_score < 35:
        style.risk_orientation = "Risk-tolerant; comfortable with uncertainty and calculated gambles"
    else:
        style.risk_orientation = "Moderate risk tolerance"

    # Deliberation from Openness + Extraversion + how they use AI
    o = p.big_five.domains.get("O")
    e = p.big_five.domains.get("E")
    if o and o.final_score >= 55 and e and e.final_score < 40:
        style.deliberation_style = (
            "Extended internal deliberation; uses conversation (especially AI-mediated) "
            "to externalize and resolve gut instinct rather than thinking out loud socially"
        )
    elif o and o.final_score >= 55 and e and e.final_score >= 55:
        style.deliberation_style = "Thinks out loud; uses conversation as a deliberation tool"
    else:
        style.deliberation_style = "Balanced deliberation"

    # Loss aversion from N4 Self-Consciousness + Attachment Anxiety
    if n4_selfconscious and n4_selfconscious >= 60:
        if p.attachment.anxiety is not None and p.attachment.anxiety >= 50:
            style.loss_aversion = (
                "High loss aversion, especially in relational/reputational domains; "
                "avoidance of failure is a stronger motivator than pursuit of success"
            )
        else:
            style.loss_aversion = "Moderate loss aversion, concentrated in social evaluation"
    elif n and n.final_score >= 50 and p.attachment.anxiety is not None and p.attachment.anxiety >= 50:
        style.loss_aversion = "Moderate loss aversion"

    return style


# ─── Conflict ────────────────────────────────────────────────────

def _build_conflict(p: PsycheProfile) -> ConflictStyle:
    style = ConflictStyle()

    # Under criticism: combine attachment dimensions + ERQ
    # Low avoidance = wants engagement, but high anxiety = fears rejection
    # High suppression = processes internally first regardless of avoidance
    if p.emotion_reg.suppression is not None and p.emotion_reg.suppression >= 70:
        if p.attachment.anxiety is not None and p.attachment.anxiety >= 50:
            style.under_criticism = (
                "Suppresses immediate emotional response; processes internally before engaging. "
                "Wants resolution (low avoidance) but fears it will go badly (high anxiety). "
                "Silence is processing, not withdrawal or acceptance."
            )
        else:
            style.under_criticism = "Suppresses initial reaction; processes internally before responding"
    elif p.attachment.avoidance is not None and p.attachment.avoidance >= 55:
        style.under_criticism = "Withdraws to process internally; needs space before re-engaging"
    elif p.attachment.avoidance is not None and p.attachment.avoidance < 35:
        if p.attachment.anxiety is not None and p.attachment.anxiety >= 50:
            style.under_criticism = (
                "Wants to engage immediately but may freeze first; "
                "fear of rejection creates hesitation despite desire for resolution"
            )
        else:
            style.under_criticism = "Engages directly with criticism; seeks immediate resolution"
    else:
        style.under_criticism = "Moderate processing time before responding to criticism"

    # Regulation strategy from ERQ
    if p.emotion_reg.reappraisal is not None and p.emotion_reg.suppression is not None:
        if p.emotion_reg.reappraisal >= 80 and p.emotion_reg.suppression >= 70:
            style.regulation_strategy = (
                "Dual-deployment: reframes the meaning of events (reappraisal) first, "
                "then suppresses remaining emotional expression when reframing is insufficient. "
                "Both strategies at near-ceiling intensity."
            )
        elif p.emotion_reg.reappraisal > p.emotion_reg.suppression + 15:
            style.regulation_strategy = "Primarily cognitive reappraisal; reframes situations rather than suppressing emotions"
        elif p.emotion_reg.suppression > p.emotion_reg.reappraisal + 15:
            style.regulation_strategy = "Primarily suppression; keeps emotions private rather than reframing"
        else:
            style.regulation_strategy = "Uses both reappraisal and suppression flexibly"

    # Manipulation tolerance from HEXACO H-H
    if p.hexaco.honesty_humility is not None:
        if p.hexaco.honesty_humility >= 70:
            style.manipulation_tolerance = "Very low tolerance for manipulation, deception, or social games"
        elif p.hexaco.honesty_humility >= 50:
            style.manipulation_tolerance = "Low tolerance for manipulation; values authenticity"
        else:
            style.manipulation_tolerance = "Pragmatic about social tactics; can engage in strategic self-presentation"

    # Feedback preference from Agreeableness facets (A1 Trust, A4 Cooperation)
    # + Self-Consciousness (N4) which affects how criticism is received
    a = p.big_five.domains.get("A")
    n4 = _facet(p, "N4")
    if a and a.final_score < 40:
        style.feedback_preference = "Wants blunt, unvarnished feedback; finds diplomatic hedging patronizing"
    elif n4 and n4 >= 65:
        style.feedback_preference = (
            "Wants direct feedback but is acutely sensitive to condescension; "
            "factual critique is fine, patronizing delivery is not"
        )
    elif a and a.final_score >= 65:
        style.feedback_preference = "Prefers constructive framing; harsh criticism can be demotivating"
    else:
        style.feedback_preference = "Direct feedback is fine but delivery matters"

    return style


# ─── Motivation ──────────────────────────────────────────────────

def _build_motivation(p: PsycheProfile) -> MotivationStyle:
    style = MotivationStyle()

    # Primary needs from BPNS
    needs_scores = {
        "autonomy": p.needs.autonomy,
        "competence": p.needs.competence,
        "relatedness": p.needs.relatedness,
    }
    satisfied = sorted(
        [(k, v) for k, v in needs_scores.items() if v is not None],
        key=lambda x: x[1],
        reverse=True,
    )
    style.primary_needs = [k for k, _ in satisfied]

    # Persistence from Grit — use Achievement-Striving (C4) and Self-Discipline (C5) as cross-validation
    c4 = _facet(p, "C4")
    if p.grit.perseverance is not None:
        if p.grit.perseverance >= 70:
            style.persistence_pattern = "Extremely persistent; rarely gives up once committed"
        elif p.grit.perseverance >= 40:
            style.persistence_pattern = "Moderately persistent within active engagements; can push through difficulty"
        else:
            style.persistence_pattern = "Selective persistence; disengages if effort-reward ratio drops"

    if p.grit.interest_consistency is not None:
        if p.grit.interest_consistency >= 65:
            style.interest_consistency = "Sustained focus on the same goals over long periods"
        elif p.grit.interest_consistency >= 30:
            style.interest_consistency = "Generally consistent interests with occasional pivots"
        elif p.grit.interest_consistency < 10:
            style.interest_consistency = (
                "Maximally fluid interests; cycles through domains rapidly (~8-month periods). "
                "Sustained engagement requires the field to move fast enough to stay ahead of the learning curve. "
                "Exceptions: embodied practice, transcendent commitments, fast-moving fields."
            )
        else:
            style.interest_consistency = "Interest cycles rapidly; needs novelty to maintain engagement"

    # Domain preferences from RIASEC
    riasec = {
        "Realistic": p.vocational.realistic,
        "Investigative": p.vocational.investigative,
        "Artistic": p.vocational.artistic,
        "Social": p.vocational.social,
        "Enterprising": p.vocational.enterprising,
        "Conventional": p.vocational.conventional,
    }
    top = sorted(
        [(k, v) for k, v in riasec.items() if v is not None],
        key=lambda x: x[1],
        reverse=True,
    )[:3]
    style.domain_preferences = [k for k, _ in top]

    return style


# ─── Epistemic Style ─────────────────────────────────────────────

def _build_epistemic(p: PsycheProfile) -> EpistemicStyle:
    style = EpistemicStyle()

    # Analytical tendency from CRT + NCS
    crt = p.cognitive.crt_score
    ncs = p.cognitive.need_for_cognition
    if crt is not None and crt >= 6 and ncs is not None and ncs >= 65:
        style.analytical_tendency = "Highly analytical; enjoys effortful thinking and resists intuitive shortcuts"
    elif crt is not None and crt >= 5:
        style.analytical_tendency = "Strong analytical capacity; balances analysis with intuition"
    else:
        style.analytical_tendency = "Moderate analytical tendency"

    # Uncertainty tolerance: use O5 (Intellect) + O6 (Liberalism) + N facets
    o = p.big_five.domains.get("O")
    n = p.big_five.domains.get("N")
    o5_intellect = _facet(p, "O5")

    if o5_intellect and o5_intellect >= 80:
        style.uncertainty_tolerance = (
            "High tolerance for genuine unknowns; comfortable saying 'I don't know'. "
            "Very low tolerance for confident-sounding guesses or premature closure."
        )
    elif o and o.final_score >= 60 and n and n.final_score < 50:
        style.uncertainty_tolerance = "High tolerance for ambiguity; comfortable with open questions"
    elif n and n.final_score >= 60:
        style.uncertainty_tolerance = "Moderate uncertainty tolerance; prefers to resolve ambiguity"
    else:
        style.uncertainty_tolerance = "Average uncertainty tolerance"

    # Source preference
    if ncs and ncs >= 60:
        style.source_preference = "Reads primary sources; skeptical of secondhand summaries on important topics"
    else:
        style.source_preference = "Relies on curated summaries; goes to primary sources when stakes are high"

    # Framework building from Openness + O5 Intellect
    if o5_intellect and o5_intellect >= 80:
        style.framework_building = (
            "Rapidly builds vast conceptual frameworks; maps new information onto existing mental models. "
            "Can get confused by simple things outside existing frameworks, but frameworks cover most domains."
        )
    elif o and o.final_score >= 65:
        style.framework_building = "Rapidly builds conceptual frameworks; maps new information onto existing mental models"
    else:
        style.framework_building = "Incremental knowledge building; prefers concrete examples over abstract frameworks"

    return style


# ─── Interpersonal ───────────────────────────────────────────────

def _build_interpersonal(p: PsycheProfile) -> InterpersonalStyle:
    style = InterpersonalStyle()

    # Trust threshold: combine BOTH attachment dimensions
    # Low avoidance + high anxiety = wants closeness but fears rejection (NOT "trusting")
    if p.attachment.anxiety is not None and p.attachment.avoidance is not None:
        anx = p.attachment.anxiety
        avoid = p.attachment.avoidance
        if avoid >= 55:
            style.trust_threshold = "High trust threshold; shares selectively and expects trust to be earned over time"
        elif avoid < 35 and anx >= 55:
            style.trust_threshold = (
                "Wants closeness intensely but monitors relational signals vigilantly; "
                "the desire for trust is strong but fear of rejection creates guardedness. "
                "Trust is given but with anxiety about whether it will be reciprocated."
            )
        elif avoid < 35 and anx < 40:
            style.trust_threshold = "Relatively trusting; comfortable with intimacy and openness"
        else:
            style.trust_threshold = "Moderate trust threshold"
    elif p.attachment.avoidance is not None:
        if p.attachment.avoidance >= 55:
            style.trust_threshold = "High trust threshold; shares selectively"
        elif p.attachment.avoidance < 35:
            style.trust_threshold = "Relatively trusting; willing to be open"
        else:
            style.trust_threshold = "Moderate trust threshold"

    # Empathy mode from IRI
    ec = p.empathy.empathic_concern
    pt = p.empathy.perspective_taking
    fan = p.empathy.fantasy
    pd = p.empathy.personal_distress
    if ec is not None and pt is not None:
        if pt >= 60 and ec <= 55 and (pd is None or pd < 45):
            style.empathy_mode = (
                "Affective contagion empathy: absorbs emotional atmospheres and interpersonal tensions "
                "viscerally. Perspective-taking is high-capacity but counterproductive — simulating others' "
                "reasoning produces alienation (they appear irrational from the inside) rather than "
                "understanding. Falls back on accepting others' self-reports at face value."
            )
        elif ec >= 60 and pt < 45:
            style.empathy_mode = (
                "Affective/somatic empathy: feels others' moods and interpersonal tensions viscerally "
                "but struggles to cognitively adopt their perspective"
            )
        elif pt >= 60 and ec >= 60:
            style.empathy_mode = "Full-spectrum empathy: both feels with others and understands their viewpoint"
        elif pt >= 60 and ec < 45 and pd is not None and pd >= 45:
            style.empathy_mode = "Cognitive empathy: understands others' viewpoints but doesn't feel their emotions strongly"
        else:
            style.empathy_mode = "Moderate empathic engagement"

    # Fantasy dimension adds important color
    if fan is not None and fan >= 60:
        style.empathy_mode += (
            ". High fantasy engagement — deeply immerses in fictional characters' experiences, "
            "which may be a safer channel for empathic connection than real-world relationships."
        )

    # Ethical stance from HEXACO H-H + Dark Triad interaction
    hh = p.hexaco.honesty_humility
    mach = p.dark_triad.machiavellianism
    if hh is not None and mach is not None:
        if hh >= 60 and mach >= 55:
            style.ethical_stance = (
                "Understands strategic/manipulative dynamics intellectually but is ethically committed "
                "to transparency and sincerity. Has the cognitive machinery for social manipulation "
                "but dispositional and moral safeguards against its deployment."
            )
        elif hh >= 70:
            style.ethical_stance = "Strong ethical orientation; values fairness and sincerity; averse to manipulation"
        elif hh >= 50:
            style.ethical_stance = "Ethical with pragmatic flexibility"
        else:
            style.ethical_stance = "Pragmatic ethical stance; context-dependent moral reasoning"
    elif hh is not None:
        if hh >= 70:
            style.ethical_stance = "Strong ethical orientation; values fairness and sincerity"
        elif hh >= 50:
            style.ethical_stance = "Ethical with pragmatic flexibility"
        else:
            style.ethical_stance = "Pragmatic ethical stance"

    # Reciprocity from attachment + extraversion + interview evidence
    e = p.big_five.domains.get("E")
    if p.attachment.anxiety is not None and p.attachment.anxiety >= 50:
        if e and e.final_score < 40:
            style.reciprocity_expectation = (
                "Initiates contact but expects reciprocity; monitors relational balance closely. "
                "History of being the sole initiator creates sensitivity to one-directional effort."
            )
        else:
            style.reciprocity_expectation = "Expects reciprocity; monitors relational balance closely"
    elif e and e.final_score >= 55:
        style.reciprocity_expectation = "Initiates contact freely but expects some reciprocity"
    else:
        style.reciprocity_expectation = "Moderate reciprocity expectations"

    return style


# ─── Stress Response ─────────────────────────────────────────────

def _build_stress_response(p: PsycheProfile) -> StressResponse:
    style = StressResponse()

    # Crisis mode from N facets + clinical + ERQ
    n = p.big_five.domains.get("N")
    n3_depression = _facet(p, "N3")
    n6_vulnerability = _facet(p, "N6")

    if p.emotion_reg.reappraisal is not None and p.emotion_reg.reappraisal >= 80:
        if p.emotion_reg.suppression is not None and p.emotion_reg.suppression >= 70:
            style.crisis_mode = (
                "Under genuine distress: initial shutdown, dual-deployment emotion regulation "
                "(reframes then suppresses), forward momentum maintained through sheer will rather than plan"
            )
        else:
            style.crisis_mode = "Under distress: reframes aggressively; seeks meaning in suffering"
    elif n and n.final_score >= 60:
        style.crisis_mode = "Under distress: heightened emotional reactivity; may need stabilization support"
    else:
        style.crisis_mode = "Moderate stress response"

    # Recovery strategy from Grit perseverance + values + clinical
    if p.grit.perseverance is not None and p.grit.perseverance >= 40:
        style.recovery_strategy = "Pushes forward through difficulty; momentum-based recovery rather than planned recuperation"

    # Coping mechanisms from ERQ + clinical + extended battery
    coping: list[str] = []
    if p.emotion_reg.reappraisal is not None and p.emotion_reg.reappraisal >= 70:
        coping.append("cognitive reframing")
    if p.emotion_reg.suppression is not None and p.emotion_reg.suppression >= 70:
        coping.append("emotional suppression")
    if p.needs.autonomy is not None and p.needs.autonomy >= 70:
        coping.append("autonomous problem-solving")
    # Faith/philosophical framework (from values if available)
    tradition = p.values.values.get("Tradition")
    if tradition and tradition.final_score >= 30:
        coping.append("philosophical/spiritual framework")
    style.coping_mechanisms = coping

    # Resilience source
    if p.needs.autonomy is not None and p.needs.autonomy >= 80:
        style.resilience_source = "Autonomous will; an internal drive whose source may not be fully articulable"
    elif p.grit.perseverance is not None and p.grit.perseverance >= 60:
        style.resilience_source = "Gritty persistence; refusing to quit"

    return style


# ─── Relationship Patterns ───────────────────────────────────────

def _build_relationships(p: PsycheProfile) -> RelationshipPatterns:
    style = RelationshipPatterns()

    # Attachment style from ECR-R two-dimensional model
    if p.attachment.anxiety is not None and p.attachment.avoidance is not None:
        anx = p.attachment.anxiety
        avoid = p.attachment.avoidance
        if anx >= 50 and avoid < 40:
            style.attachment_style = (
                "Anxious-preoccupied: wants closeness intensely, monitors relational signals vigilantly, "
                "fears abandonment. Low avoidance means the desire for intimacy is genuine and strong."
            )
        elif anx >= 50 and avoid >= 50:
            style.attachment_style = "Fearful-avoidant: wants closeness but also fears it; oscillates between approach and withdrawal"
        elif anx < 40 and avoid >= 50:
            style.attachment_style = "Dismissive-avoidant: self-sufficient; comfortable without close relationships"
        elif anx < 40 and avoid < 40:
            style.attachment_style = "Secure: comfortable with intimacy and independence"
        else:
            style.attachment_style = "Mixed attachment pattern"

    # Initiation pattern from E + attachment
    e = p.big_five.domains.get("E")
    e1_friendliness = _facet(p, "E1")

    if e and e.final_score < 40 and p.attachment.anxiety is not None and p.attachment.anxiety >= 50:
        style.initiation_pattern = (
            "Historically the sole initiator in friendships; invests heavily when connected "
            "but struggles to form new connections. Low social energy means relationships must "
            "be high-value to justify the expenditure."
        )
    elif e and e.final_score < 40:
        style.initiation_pattern = "Rarely initiates; responds to others' approaches"
    elif e and e.final_score >= 55:
        style.initiation_pattern = "Naturally initiates and maintains social contact"

    # Maintenance from E facets + grit interest consistency
    if e1_friendliness is not None and e1_friendliness < 30:
        style.maintenance_pattern = (
            "Connection requires extraordinary conditions to activate; "
            "once activated, engages with intensity most people find exhausting. "
            "Sustained closeness needs high-bandwidth interaction (deep conversation, shared activity)."
        )
    elif e and e.final_score < 40:
        style.maintenance_pattern = "Maintains relationships through periodic deep engagement rather than frequent contact"

    # Loss response from attachment + ERQ + N
    if p.attachment.anxiety is not None and p.attachment.anxiety >= 50:
        if p.emotion_reg.reappraisal is not None and p.emotion_reg.reappraisal >= 70:
            style.loss_response = (
                "Relational loss is experienced as devastating (anxious attachment) but managed through "
                "philosophical reframing and time-bounded grief. Sets explicit recovery timelines."
            )
        else:
            style.loss_response = "Relational loss is experienced as devastating; recovery is slow and painful"

    return style


# ─── Flow States ─────────────────────────────────────────────────

def _build_flow_states(p: PsycheProfile) -> FlowStates:
    style = FlowStates()

    # Triggers from RIASEC + O + E
    triggers: list[str] = []
    o = p.big_five.domains.get("O")
    o5_intellect = _facet(p, "O5")

    if p.vocational.investigative is not None and p.vocational.investigative >= 80:
        triggers.append("deep intellectual exploration")
    if p.vocational.artistic is not None and p.vocational.artistic >= 60:
        triggers.append("creative/artistic engagement")
    if p.vocational.realistic is not None and p.vocational.realistic >= 50:
        triggers.append("embodied physical activity")

    e4_activity = _facet(p, "E4")
    e5_excitement = _facet(p, "E5")
    if e4_activity and e4_activity >= 55:
        triggers.append("active engagement (despite social introversion)")

    # Good conversation as rare peak experience (E < 40 + high O)
    e = p.big_five.domains.get("E")
    if e and e.final_score < 40 and o and o.final_score >= 60:
        triggers.append("rare deep conversation")

    style.triggers = triggers

    # Phenomenology from O1 (Imagination) + computer dissociation pattern
    o1_imagination = _facet(p, "O1")
    if o5_intellect and o5_intellect >= 80:
        style.phenomenology = "Experience of merging with the activity; self-boundary dissolution during deep engagement"
    elif o and o.final_score >= 60:
        style.phenomenology = "Deep absorption; loses track of time and surroundings"

    # Frequency
    if e and e.final_score < 35 and o and o.final_score >= 60:
        style.frequency = "Intellectual flow is frequent; social flow is rare but intense when it occurs"

    # Barriers from N4 + social context
    n4 = _facet(p, "N4")
    if n4 and n4 >= 65:
        style.barriers = "Self-consciousness disrupts flow in social contexts; solitary or close-dyad contexts required"

    return style


# ─── Self-Concept ────────────────────────────────────────────────

def _build_self_concept(p: PsycheProfile) -> SelfConcept:
    style = SelfConcept()

    # Identity model — hard to derive purely from scores, but some indicators
    o = p.big_five.domains.get("O")
    o5 = _facet(p, "O5")
    if o and o.final_score >= 65 and p.needs.autonomy is not None and p.needs.autonomy >= 80:
        style.identity_model = (
            "Identity is located in will/agency/essence rather than memory, narrative, or social role. "
            "Strong sense of core self that persists across changing circumstances."
        )

    # Competence gap from self-esteem + CRT + NCS
    se = p.cognitive.self_esteem
    crt = p.cognitive.crt_score
    ncs = p.cognitive.need_for_cognition
    if se is not None and se < 45 and crt is not None and crt >= 6:
        style.competence_gap = (
            "Significant gap between felt competence and demonstrated ability. "
            f"Self-esteem {se:.0f}/100 coexists with CRT {crt:.0f}/7 (top 5% analytical reasoning). "
            "Underestimates own capability."
        )
    elif se is not None and se < 45:
        style.competence_gap = "Low felt competence; may underestimate own capability"

    # Comparative orientation from N4 + self-esteem + interview signals
    n4 = _facet(p, "N4")
    if n4 and n4 >= 65 and se and se < 50:
        style.comparative_orientation = (
            "Avoids comparison; finds relative evaluation painful. "
            "Motivated by self-improvement rather than outperformance. "
            "Demotivated by 'there's always someone better' framing."
        )
    elif se and se >= 65:
        style.comparative_orientation = "Comfortable with comparison; uses it as motivation"
    else:
        style.comparative_orientation = "Moderate comfort with comparison"

    # Self-narrative from O + self-esteem interaction
    if o and o.final_score >= 60 and se and se < 50:
        style.self_narrative = (
            "Frames own abilities as 'efficiency' rather than intelligence; "
            "describes cognitive style as selective attention rather than processing power. "
            "Self-description is honest but systematically undervalues own capability."
        )

    return style


# ─── Phrase Extraction ───────────────────────────────────────────

def _extract_phrases(transcript: str) -> list[str]:
    """Extract characteristic phrases from interview transcript.

    Handles Q&A format: ## Q1: ... \\n <answer paragraphs>
    Extracts sentences with self-referential language that reveal personality.
    """
    phrases: list[str] = []
    self_markers = ("i ", "i'm ", "i've ", "my ", "me ", "i'd ", "i'll ", "i can")

    # Split transcript into Q&A sections, take only the answers
    sections = re.split(r'## Q\d+:', transcript)

    for section in sections:
        # Skip the header/metadata section
        if not section.strip() or section.strip().startswith('#'):
            continue

        # The section starts with the question text, then a blank line, then the answer
        lines = section.strip().split('\n')
        # Find where the answer starts (skip the question line)
        answer_lines = []
        past_question = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                past_question = True
                continue
            if past_question and stripped:
                answer_lines.append(stripped)

        answer_text = ' '.join(answer_lines)

        # Split into sentences (rough but functional)
        sentences = re.split(r'(?<=[.!?])\s+', answer_text)

        for sent in sentences:
            sent = sent.strip()
            words = sent.split()
            if len(words) < 8 or len(words) > 60:
                continue
            # Must contain self-referential language
            lower = sent.lower()
            if not any(lower.startswith(m) or f' {m}' in lower for m in self_markers):
                continue
            # Prefer sentences that are concrete/vivid (contain metaphor, example, or strong claim)
            if any(kw in lower for kw in (
                'like ', 'always', 'never', 'feel', 'think', 'can\'t', 'don\'t',
                'wish', 'hate', 'love', 'dream', 'need', 'best', 'worst',
                'glass', 'music', 'hurt', 'pain', 'drive', 'smart',
            )):
                phrases.append(sent)

    # Deduplicate and return top entries (longest as proxy for specificity)
    seen = set()
    unique: list[str] = []
    for ph in phrases:
        key = ph[:40].lower()
        if key not in seen:
            seen.add(key)
            unique.append(ph)
    unique.sort(key=len, reverse=True)
    return unique[:12]


def _extract_decision_examples(transcript: str) -> list[DecisionExample]:
    """Extract decision-making examples from interview Q3 (decision process)."""
    examples: list[DecisionExample] = []

    # Find Q3 section (decision process)
    q3_match = re.search(
        r'## Q3:.*?\n\n(.*?)(?=\n## Q\d+:|\n---|\Z)',
        transcript, re.DOTALL,
    )
    if q3_match:
        text = q3_match.group(1).strip()
        examples.append(DecisionExample(
            situation="General decision-making pattern",
            process=text,
            outcome="",
            source="interview",
        ))

    # Find Q8 section (building/becoming — contains goal-setting decisions)
    q8_match = re.search(
        r'## Q8:.*?\n\n(.*?)(?=\n## Q\d+:|\n---|\Z)',
        transcript, re.DOTALL,
    )
    if q8_match:
        text = q8_match.group(1).strip()
        examples.append(DecisionExample(
            situation="Life direction / goal-setting",
            process=text,
            outcome="",
            source="interview",
        ))

    return examples


def _extract_conflict_examples(transcript: str) -> list[ConflictExample]:
    """Extract conflict/surprise examples from interview Q5 (genuine surprise) and Q7 (crisis)."""
    examples: list[ConflictExample] = []

    # Q5: surprises (often interpersonal conflict/loss)
    q5_match = re.search(
        r'## Q5:.*?\n\n(.*?)(?=\n## Q\d+:|\n---|\Z)',
        transcript, re.DOTALL,
    )
    if q5_match:
        text = q5_match.group(1).strip()
        examples.append(ConflictExample(
            trigger="Interpersonal surprise/loss",
            response=text,
            resolution="",
            source="interview",
        ))

    # Q7: crisis response
    q7_match = re.search(
        r'## Q7:.*?\n\n(.*?)(?=\n## Q\d+:|\n---|\Z)',
        transcript, re.DOTALL,
    )
    if q7_match:
        text = q7_match.group(1).strip()
        examples.append(ConflictExample(
            trigger="Genuine distress / crisis state",
            response=text,
            resolution="",
            source="interview",
        ))

    return examples


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len characters at a word boundary."""
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    last_space = truncated.rfind(' ')
    if last_space > max_len * 0.7:
        return truncated[:last_space] + "..."
    return truncated + "..."


# ─── ChatLedger Integration ──────────────────────────────────────

def _integrate_chatledger(persona: PersonaModel, patterns: dict) -> None:
    """Integrate observed behavioral patterns from ChatLedger enrichment data."""
    if "communication_style" in patterns:
        cs = patterns["communication_style"]
        if "avg_message_length" in cs:
            if cs["avg_message_length"] < 20:
                persona.communication.directness += " (observed: very short messages in natural conversation)"
            elif cs["avg_message_length"] > 100:
                persona.communication.depth_preference += " (observed: long, detailed messages in natural conversation)"

    if "conflict_examples" in patterns:
        for ex in patterns["conflict_examples"][:3]:
            persona.conflict_examples.append(ConflictExample(
                trigger=ex.get("trigger", ""),
                response=ex.get("response", ""),
                resolution=ex.get("resolution", ""),
                source="chatledger",
            ))

    if "decision_examples" in patterns:
        for ex in patterns["decision_examples"][:3]:
            persona.decision_examples.append(DecisionExample(
                situation=ex.get("situation", ""),
                process=ex.get("process", ""),
                outcome=ex.get("outcome", ""),
                source="chatledger",
            ))
