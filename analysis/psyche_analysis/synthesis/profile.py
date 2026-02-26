"""Profile schema: the unified output of all analysis methods."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class TraitEstimate(BaseModel):
    """A single trait estimate with confidence and method provenance."""
    score: float  # 0-100
    confidence: str = "medium"  # high, medium, low
    method: str = ""  # which method produced this
    evidence: list[str] = []


class MergedTrait(BaseModel):
    """A trait with estimates from multiple methods, merged into a final score."""
    final_score: float  # 0-100 weighted average
    ci_lower: float = 0.0  # 95% confidence interval
    ci_upper: float = 100.0
    confidence: str = "medium"
    estimates: list[TraitEstimate] = []
    divergence: float = 0.0  # SD across methods; >15 = noteworthy


class FacetScore(BaseModel):
    """A single facet score, optionally from multiple instruments."""
    facet_id: str = ""  # e.g., "N1"
    name: str = ""  # e.g., "Anxiety"
    domain: str = ""  # e.g., "N"
    neo120: float | None = None  # 0-100
    neo300: float | None = None  # 0-100
    average: float | None = None  # mean of available scores


class BigFiveProfile(BaseModel):
    domains: dict[str, MergedTrait] = {}  # N, E, O, A, C
    facets: dict[str, MergedTrait] = {}  # N1, N2, ... C6
    facet_scores: list[FacetScore] = []  # detailed facet comparison


class ValuesProfile(BaseModel):
    values: dict[str, MergedTrait] = {}  # Schwartz values
    top_3: list[str] = []
    bottom_3: list[str] = []


class ClinicalScreen(BaseModel):
    phq9: float | None = None  # 0-27
    gad7: float | None = None  # 0-21
    phq9_severity: str = ""  # none, mild, moderate, moderately severe, severe
    gad7_severity: str = ""  # none, mild, moderate, severe


class CognitiveProfile(BaseModel):
    crt_score: float | None = None  # 0-7
    crt_percentile: float | None = None
    need_for_cognition: float | None = None  # 0-100
    self_esteem: float | None = None  # 0-100


class DarkTriadProfile(BaseModel):
    machiavellianism: float | None = None  # 0-100
    narcissism: float | None = None  # 0-100
    psychopathy: float | None = None  # 0-100


class AnalysisMetadata(BaseModel):
    methods_used: list[str] = []
    corpus_word_count: int = 0
    corpus_sources: list[str] = []
    llm_tokens_used: int = 0
    analysis_date: datetime | None = None


# ─── Phase 3: Extended Battery Profiles ──────────────────────────


class AttachmentProfile(BaseModel):
    """ECR-R attachment dimensions."""
    anxiety: float | None = None  # 0-100
    avoidance: float | None = None  # 0-100


class EmotionRegProfile(BaseModel):
    """ERQ emotion regulation strategies."""
    reappraisal: float | None = None  # 0-100
    suppression: float | None = None  # 0-100


class EmpathyProfile(BaseModel):
    """IRI empathy decomposition."""
    fantasy: float | None = None  # 0-100
    perspective_taking: float | None = None  # 0-100
    empathic_concern: float | None = None  # 0-100
    personal_distress: float | None = None  # 0-100


class SocialProfile(BaseModel):
    """Self-monitoring and locus of control."""
    self_monitoring: float | None = None  # 0-100
    loc_internal: float | None = None  # 0-100
    loc_external: float | None = None  # 0-100


class GritProfile(BaseModel):
    """Grit-S subscales."""
    perseverance: float | None = None  # 0-100
    interest_consistency: float | None = None  # 0-100


class VocationalProfile(BaseModel):
    """RIASEC vocational interests."""
    realistic: float | None = None  # 0-100
    investigative: float | None = None  # 0-100
    artistic: float | None = None  # 0-100
    social: float | None = None  # 0-100
    enterprising: float | None = None  # 0-100
    conventional: float | None = None  # 0-100


class NeedsProfile(BaseModel):
    """BPNS basic psychological needs satisfaction."""
    autonomy: float | None = None  # 0-100
    competence: float | None = None  # 0-100
    relatedness: float | None = None  # 0-100


class HexacoProfile(BaseModel):
    """HEXACO-60 factor scores."""
    honesty_humility: float | None = None  # 0-100
    emotionality: float | None = None  # 0-100
    extraversion: float | None = None  # 0-100
    agreeableness: float | None = None  # 0-100
    conscientiousness: float | None = None  # 0-100
    openness: float | None = None  # 0-100


# ─── Persona Model ──────────────────────────────────────────────


class CommunicationStyle(BaseModel):
    """How this person communicates."""
    directness: str = ""  # e.g., "Prefers blunt, direct responses"
    depth_preference: str = ""  # e.g., "Wants depth over brevity"
    rationale_need: str = ""  # e.g., "Rejects instructions without WHY"
    audience_adaptation: str = ""  # Self-Monitoring: chameleon vs consistent
    analogy_domains: list[str] = []  # From RIASEC: what domains they think in


class DecisionStyle(BaseModel):
    """How this person makes decisions."""
    attribution_style: str = ""  # LOC: internal vs external
    risk_orientation: str = ""  # From multiple sources
    deliberation_style: str = ""  # How they process decisions
    loss_aversion: str = ""  # Relative weight of losses vs gains


class ConflictStyle(BaseModel):
    """How this person handles conflict and criticism."""
    under_criticism: str = ""  # ECR-R → attachment-based response
    regulation_strategy: str = ""  # ERQ → reappraisal vs suppression
    manipulation_tolerance: str = ""  # HEXACO H-H
    feedback_preference: str = ""  # Blunt vs diplomatic


class MotivationStyle(BaseModel):
    """What drives this person."""
    primary_needs: list[str] = []  # BPNS: which needs are most/least satisfied
    persistence_pattern: str = ""  # Grit perseverance
    interest_consistency: str = ""  # Grit interest
    domain_preferences: list[str] = []  # RIASEC top types


class EpistemicStyle(BaseModel):
    """How this person processes information and forms beliefs."""
    analytical_tendency: str = ""  # CRT + NCS
    uncertainty_tolerance: str = ""  # From multiple sources
    source_preference: str = ""  # Primary vs secondary sources
    framework_building: str = ""  # How they organize knowledge


class InterpersonalStyle(BaseModel):
    """How this person relates to others."""
    trust_threshold: str = ""  # ECR-R avoidance → trust
    empathy_mode: str = ""  # IRI: affective vs cognitive empathy
    ethical_stance: str = ""  # HEXACO H-H
    reciprocity_expectation: str = ""  # From attachment + interview


class StressResponse(BaseModel):
    """How this person responds under genuine distress."""
    crisis_mode: str = ""  # What shutdown/activation looks like
    recovery_strategy: str = ""  # How they come back
    coping_mechanisms: list[str] = []  # Ordered by deployment
    resilience_source: str = ""  # What sustains them

class RelationshipPatterns(BaseModel):
    """How this person forms and maintains relationships."""
    attachment_style: str = ""  # Derived from ECR-R dimensions
    initiation_pattern: str = ""  # Who initiates, how
    maintenance_pattern: str = ""  # What sustains or erodes connection
    loss_response: str = ""  # How they handle relational loss

class FlowStates(BaseModel):
    """When this person feels most present and engaged."""
    triggers: list[str] = []  # Activities/conditions that produce flow
    phenomenology: str = ""  # What the experience feels like from inside
    frequency: str = ""  # How often flow states occur
    barriers: str = ""  # What prevents flow

class SelfConcept(BaseModel):
    """How this person understands their own identity."""
    identity_model: str = ""  # What they think the self IS
    competence_gap: str = ""  # Gap between felt and demonstrated ability
    comparative_orientation: str = ""  # How they relate to others' abilities
    self_narrative: str = ""  # The story they tell about themselves

class DecisionExample(BaseModel):
    """A concrete example of a decision-making pattern."""
    situation: str = ""
    process: str = ""
    outcome: str = ""
    source: str = ""  # "interview", "corpus", "chatledger"


class ConflictExample(BaseModel):
    """A concrete example of a conflict response pattern."""
    trigger: str = ""
    response: str = ""
    resolution: str = ""
    source: str = ""


class PersonaModel(BaseModel):
    """Structured behavioral patterns for AI agent simulation.

    Goes beyond trait labels to capture actionable behavioral predictions
    derived from psychometric scores, interview evidence, and corpus analysis.
    """
    communication: CommunicationStyle = CommunicationStyle()
    decision_making: DecisionStyle = DecisionStyle()
    conflict_response: ConflictStyle = ConflictStyle()
    motivation: MotivationStyle = MotivationStyle()
    epistemic_style: EpistemicStyle = EpistemicStyle()
    interpersonal: InterpersonalStyle = InterpersonalStyle()
    stress_response: StressResponse = StressResponse()
    relationships: RelationshipPatterns = RelationshipPatterns()
    flow_states: FlowStates = FlowStates()
    self_concept: SelfConcept = SelfConcept()

    # Behavioral examples extracted from corpus/interview
    characteristic_phrases: list[str] = []
    decision_examples: list[DecisionExample] = []
    conflict_examples: list[ConflictExample] = []


# ─── Top-Level Profile ──────────────────────────────────────────


class PsycheProfile(BaseModel):
    """Complete psychometric profile — the primary output artifact."""
    version: int = 2
    created_at: datetime = datetime.now()

    big_five: BigFiveProfile = BigFiveProfile()
    values: ValuesProfile = ValuesProfile()
    clinical: ClinicalScreen = ClinicalScreen()
    cognitive: CognitiveProfile = CognitiveProfile()
    dark_triad: DarkTriadProfile = DarkTriadProfile()

    # Phase 3: Extended battery
    attachment: AttachmentProfile = AttachmentProfile()
    emotion_reg: EmotionRegProfile = EmotionRegProfile()
    empathy: EmpathyProfile = EmpathyProfile()
    social: SocialProfile = SocialProfile()
    grit: GritProfile = GritProfile()
    vocational: VocationalProfile = VocationalProfile()
    needs: NeedsProfile = NeedsProfile()
    hexaco: HexacoProfile = HexacoProfile()

    # Persona model
    persona: PersonaModel = PersonaModel()

    metadata: AnalysisMetadata = AnalysisMetadata()

    # Human-readable outputs
    narrative: str = ""  # 2000-4000 word narrative report
    claude_md_snippet: str = ""  # ~500 word CLAUDE.md context
