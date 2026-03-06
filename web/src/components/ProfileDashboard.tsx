import { useState, useEffect } from "react";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  Cell,
} from "recharts";

/** Manifest types for profile selector */
interface ManifestEntry {
  id: string;
  name: string;
  filename: string;
  date: string;
  description: string;
}

interface Manifest {
  profiles: ManifestEntry[];
  default: string;
}

/** Corpus comparison data for multi-level analysis tab */
interface EmpathDimension {
  z: number;
  label: string;
}

interface ComparisonLevel {
  level: string;
  description: string;
  llm_big_five?: Record<string, number | null>;
  corpus_words?: number;
  words_to_llm?: number;
  empath_lexical?: Record<string, EmpathDimension>;
  empath_words?: number;
}

interface ComparisonSummary {
  levels: Record<string, ComparisonLevel>;
}

/** Profile JSON types matching Python schema */
interface TraitEstimate {
  score: number;
  confidence: string;
  method: string;
  evidence: string[];
}

interface MergedTrait {
  final_score: number;
  ci_lower: number;
  ci_upper: number;
  confidence: string;
  estimates: TraitEstimate[];
  divergence: number;
}

interface ProfileData {
  version: number;
  created_at: string;
  big_five: {
    domains: Record<string, MergedTrait>;
    facets: Record<string, unknown>;
  };
  values: {
    values: Record<string, MergedTrait>;
    top_3: string[];
    bottom_3: string[];
  };
  cognitive: {
    crt_score: number | null;
    crt_percentile: number | null;
    need_for_cognition: number | null;
    self_esteem: number | null;
  };
  dark_triad: {
    machiavellianism: number | null;
    narcissism: number | null;
    psychopathy: number | null;
  };
  clinical: {
    phq9: number | null;
    gad7: number | null;
    phq9_severity: string | null;
    gad7_severity: string | null;
  };
  // Phase 3: Extended battery
  attachment?: {
    anxiety: number | null;
    avoidance: number | null;
  };
  emotion_reg?: {
    reappraisal: number | null;
    suppression: number | null;
  };
  empathy?: {
    fantasy: number | null;
    perspective_taking: number | null;
    empathic_concern: number | null;
    personal_distress: number | null;
  };
  social?: {
    self_monitoring: number | null;
    loc_internal: number | null;
    loc_external: number | null;
  };
  grit?: {
    perseverance: number | null;
    interest_consistency: number | null;
  };
  vocational?: {
    realistic: number | null;
    investigative: number | null;
    artistic: number | null;
    social: number | null;
    enterprising: number | null;
    conventional: number | null;
  };
  needs?: {
    autonomy: number | null;
    competence: number | null;
    relatedness: number | null;
  };
  hexaco?: {
    honesty_humility: number | null;
    emotionality: number | null;
    extraversion: number | null;
    agreeableness: number | null;
    conscientiousness: number | null;
    openness: number | null;
  };
  persona?: {
    communication: Record<string, unknown>;
    decision_making: Record<string, unknown>;
    conflict_response: Record<string, unknown>;
    motivation: Record<string, unknown>;
    epistemic_style: Record<string, unknown>;
    interpersonal: Record<string, unknown>;
    characteristic_phrases: string[];
    decision_examples: unknown[];
    conflict_examples: unknown[];
  };
  metadata: {
    methods_used: string[];
    corpus_word_count: number;
    corpus_sources: string[];
    llm_tokens_used: number;
    analysis_date: string | null;
  };
  narrative: string;
  claude_md_snippet: string;
}

const DOMAIN_LABELS: Record<string, string> = {
  O: "Openness",
  C: "Conscientiousness",
  E: "Extraversion",
  A: "Agreeableness",
  N: "Neuroticism",
};

const DOMAIN_ORDER = ["O", "C", "E", "A", "N"];

const METHOD_COLORS: Record<string, string> = {
  "self-report": "#2563eb",
  interview: "#7c3aed",
  "llm-claude": "#059669",
  "llm-gpt": "#dc2626",
  huggingface: "#6366f1",
};

const METHOD_LABELS: Record<string, string> = {
  "self-report": "Self-Report (IPIP-NEO-120)",
  interview: "Interview (Peters & Matz)",
  "llm-claude": "LLM Corpus (Claude)",
  "llm-gpt": "LLM Corpus (GPT)",
  huggingface: "HuggingFace (BERT)",
};

const VALUE_LABELS: Record<string, string> = {
  self_direction: "Self-Direction",
  stimulation: "Stimulation",
  hedonism: "Hedonism",
  achievement: "Achievement",
  power: "Power",
  security: "Security",
  conformity: "Conformity",
  tradition: "Tradition",
  benevolence: "Benevolence",
  universalism: "Universalism",
};

function scoreLabel(n: number): string {
  if (n >= 80) return "Very High";
  if (n >= 60) return "High";
  if (n >= 40) return "Average";
  if (n >= 20) return "Low";
  return "Very Low";
}

function confidenceColor(c: string): string {
  if (c === "high") return "#059669";
  if (c === "medium") return "#d97706";
  return "#dc2626";
}

function severityColor(s: string | null): string {
  if (!s) return "#9ca3af";
  if (s === "none") return "#059669";
  if (s === "mild") return "#d97706";
  if (s === "moderate") return "#f59e0b";
  return "#dc2626";
}

export function ProfileDashboard() {
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [expandedDomain, setExpandedDomain] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "methods" | "values" | "cognitive" | "extended" | "persona" | "narrative" | "corpus">("overview");
  const [loading, setLoading] = useState(true);
  const [profileList, setProfileList] = useState<ManifestEntry[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState<string>("");

  // Load manifest and default profile on mount
  useEffect(() => {
    fetch("/profiles/manifest.json")
      .then((r) => {
        if (!r.ok) throw new Error("Not found");
        return r.json() as Promise<Manifest>;
      })
      .then((manifest) => {
        setProfileList(manifest.profiles);
        const defaultId = manifest.default;
        const defaultEntry = manifest.profiles.find((p) => p.id === defaultId) ?? manifest.profiles[0];
        if (defaultEntry) {
          setSelectedProfileId(defaultEntry.id);
          return fetch(`/profiles/${defaultEntry.filename}`).then((r) => r.json());
        }
        return null;
      })
      .then((data: ProfileData | null) => {
        if (data?.big_five && data?.version) {
          setProfile(data);
        }
      })
      .catch(() => {
        // Fallback: load /profile.json directly
        fetch("/profile.json")
          .then((r) => {
            if (!r.ok) throw new Error("Not found");
            return r.json();
          })
          .then((data: ProfileData) => {
            if (data.big_five && data.version) {
              setProfile(data);
            }
          })
          .catch(() => {});
      })
      .finally(() => setLoading(false));
  }, []);

  const handleProfileSelect = (id: string) => {
    if (id === "__import__") {
      handleImport();
      return;
    }
    const entry = profileList.find((p) => p.id === id);
    if (!entry) return;
    setSelectedProfileId(id);
    fetch(`/profiles/${entry.filename}`)
      .then((r) => r.json())
      .then((data: ProfileData) => {
        if (data.big_five && data.version) {
          setProfile(data);
        }
      })
      .catch(() => alert("Failed to load profile"));
  };

  const handleImport = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        if (typeof reader.result === "string") {
          try {
            const data = JSON.parse(reader.result) as ProfileData;
            if (data.big_five && data.version) {
              setProfile(data);
            }
          } catch {
            alert("Invalid profile JSON");
          }
        }
      };
      reader.readAsText(file);
    };
    input.click();
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "4rem 2rem" }}>
        <p style={{ color: "#6b7280" }}>Loading profile...</p>
      </div>
    );
  }

  if (!profile) {
    return (
      <div style={{ textAlign: "center", padding: "4rem 2rem" }}>
        <h2 style={{ marginBottom: "0.5rem" }}>Profile Dashboard</h2>
        <p style={{ color: "#6b7280", marginBottom: "2rem" }}>
          Import a synthesized profile JSON to visualize your results.
        </p>
        <button onClick={handleImport} style={btnPrimary}>
          Import Profile JSON
        </button>
      </div>
    );
  }

  const radarData = DOMAIN_ORDER.map((key) => {
    const d = profile.big_five.domains[key];
    return {
      trait: DOMAIN_LABELS[key] ?? key,
      score: d ? Math.round(d.final_score) : 0,
      ciLower: d ? Math.round(d.ci_lower) : 0,
      ciUpper: d ? Math.round(d.ci_upper) : 0,
    };
  });

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: "2rem" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "2rem" }}>
        <div>
          <h1 style={{ marginBottom: "0.25rem" }}>Psyche Profile</h1>
          <p style={{ color: "#6b7280", margin: 0, fontSize: "0.875rem" }}>
            Generated {new Date(profile.created_at).toLocaleDateString()} | Methods: {profile.metadata.methods_used.join(", ")} | Corpus: {profile.metadata.corpus_word_count.toLocaleString()} words
          </p>
        </div>
        {profileList.length > 0 ? (
          <select
            value={selectedProfileId}
            onChange={(e) => handleProfileSelect(e.target.value)}
            style={{
              padding: "0.5rem 0.75rem",
              border: "1px solid #d1d5db",
              borderRadius: "0.375rem",
              fontSize: "0.875rem",
              background: "#fff",
              cursor: "pointer",
              minWidth: 200,
            }}
          >
            {profileList.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.date})
              </option>
            ))}
            <option value="__import__">Import from file...</option>
          </select>
        ) : (
          <button onClick={handleImport} style={btnSecondary}>
            Load Different Profile
          </button>
        )}
      </div>

      {/* Tab navigation */}
      <div style={{ display: "flex", gap: "0.25rem", borderBottom: "2px solid #e5e7eb", marginBottom: "2rem" }}>
        {(["overview", "methods", "values", "cognitive", "extended", "corpus", "persona", "narrative"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: "0.75rem 1.25rem",
              background: "transparent",
              border: "none",
              borderBottom: activeTab === tab ? "2px solid #2563eb" : "2px solid transparent",
              color: activeTab === tab ? "#2563eb" : "#6b7280",
              fontWeight: activeTab === tab ? 600 : 400,
              cursor: "pointer",
              fontSize: "0.875rem",
              textTransform: "capitalize",
              marginBottom: "-2px",
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "overview" && (
        <OverviewTab profile={profile} radarData={radarData} expandedDomain={expandedDomain} setExpandedDomain={setExpandedDomain} />
      )}
      {activeTab === "methods" && <MethodsTab profile={profile} />}
      {activeTab === "values" && <ValuesTab profile={profile} />}
      {activeTab === "cognitive" && <CognitiveTab profile={profile} />}
      {activeTab === "extended" && <ExtendedBatteryTab profile={profile} />}
      {activeTab === "corpus" && <CorpusAnalysisTab />}
      {activeTab === "persona" && <PersonaTab profile={profile} />}
      {activeTab === "narrative" && <NarrativeTab profile={profile} />}
    </div>
  );
}

// ─── Overview Tab ────────────────────────────────────────────

function OverviewTab({
  profile,
  radarData,
  expandedDomain,
  setExpandedDomain,
}: {
  profile: ProfileData;
  radarData: { trait: string; score: number; ciLower: number; ciUpper: number }[];
  expandedDomain: string | null;
  setExpandedDomain: (d: string | null) => void;
}) {
  return (
    <>
      {/* Radar Chart */}
      <div style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>Big Five Personality</h2>
        <ResponsiveContainer width="100%" height={380}>
          <RadarChart data={radarData}>
            <PolarGrid />
            <PolarAngleAxis dataKey="trait" tick={{ fontSize: 13 }} />
            <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
            <Radar dataKey="ciUpper" stroke="none" fill="#2563eb" fillOpacity={0.08} isAnimationActive={false} />
            <Radar dataKey="score" stroke="#2563eb" fill="#2563eb" fillOpacity={0.25} strokeWidth={2} dot isAnimationActive={false} />
            <Radar dataKey="ciLower" stroke="none" fill="#ffffff" fillOpacity={0.9} isAnimationActive={false} />
          </RadarChart>
        </ResponsiveContainer>
        <p style={{ textAlign: "center", fontSize: "0.75rem", color: "#9ca3af" }}>
          Shaded band shows confidence interval. Click domains below for detail.
        </p>
      </div>

      {/* Domain cards */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {DOMAIN_ORDER.map((key) => {
          const d = profile.big_five.domains[key];
          if (!d) return null;
          const isExpanded = expandedDomain === key;
          return (
            <div
              key={key}
              style={{
                border: "1px solid #e5e7eb",
                borderRadius: "0.5rem",
                overflow: "hidden",
              }}
            >
              <button
                onClick={() => setExpandedDomain(isExpanded ? null : key)}
                style={{
                  width: "100%",
                  padding: "1rem 1.5rem",
                  background: isExpanded ? "#f9fafb" : "#fff",
                  border: "none",
                  cursor: "pointer",
                  textAlign: "left",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <span style={{ fontWeight: 600, fontSize: "1rem" }}>{DOMAIN_LABELS[key]}</span>
                  <span style={{ color: "#9ca3af", marginLeft: "0.75rem", fontSize: "0.875rem" }}>
                    {scoreLabel(d.final_score)}
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                  {/* Score bar */}
                  <div style={{ width: 180, position: "relative" }}>
                    <div style={{ height: 8, background: "#f3f4f6", borderRadius: 4 }}>
                      {/* CI band */}
                      <div
                        style={{
                          position: "absolute",
                          left: `${d.ci_lower}%`,
                          width: `${d.ci_upper - d.ci_lower}%`,
                          height: 8,
                          background: "#dbeafe",
                          borderRadius: 4,
                        }}
                      />
                      {/* Score dot */}
                      <div
                        style={{
                          position: "absolute",
                          left: `${d.final_score}%`,
                          top: -2,
                          width: 12,
                          height: 12,
                          background: "#2563eb",
                          borderRadius: "50%",
                          transform: "translateX(-50%)",
                        }}
                      />
                    </div>
                  </div>
                  <span style={{ fontWeight: 700, fontSize: "1.25rem", minWidth: 32, textAlign: "right" }}>
                    {Math.round(d.final_score)}
                  </span>
                  <span style={{ color: "#9ca3af", fontSize: "0.75rem" }}>
                    {isExpanded ? "▲" : "▼"}
                  </span>
                </div>
              </button>

              {isExpanded && (
                <div style={{ padding: "1rem 1.5rem", borderTop: "1px solid #e5e7eb", background: "#fafafa" }}>
                  {/* Method comparison */}
                  <div style={{ marginBottom: "1rem" }}>
                    <h4 style={{ fontSize: "0.875rem", marginBottom: "0.5rem", color: "#374151" }}>Method Comparison</h4>
                    {d.estimates.map((est) => (
                      <div key={est.method} style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.5rem" }}>
                        <span style={{ fontSize: "0.75rem", width: 140, color: "#6b7280" }}>
                          {METHOD_LABELS[est.method] ?? est.method}
                        </span>
                        <div style={{ flex: 1, height: 6, background: "#e5e7eb", borderRadius: 3, position: "relative" }}>
                          <div
                            style={{
                              height: 6,
                              width: `${est.score}%`,
                              background: METHOD_COLORS[est.method] ?? "#6b7280",
                              borderRadius: 3,
                            }}
                          />
                        </div>
                        <span style={{ fontSize: "0.875rem", fontWeight: 600, minWidth: 28, textAlign: "right" }}>
                          {Math.round(est.score)}
                        </span>
                        <span
                          style={{
                            fontSize: "0.625rem",
                            color: confidenceColor(est.confidence),
                            textTransform: "uppercase",
                            fontWeight: 600,
                            minWidth: 50,
                          }}
                        >
                          {est.confidence}
                        </span>
                      </div>
                    ))}
                    {d.divergence > 0 && (
                      <p style={{ fontSize: "0.75rem", color: d.divergence > 15 ? "#dc2626" : "#9ca3af", marginTop: "0.5rem" }}>
                        Cross-method divergence: {d.divergence.toFixed(1)} SD
                        {d.divergence > 15 && " — methods disagree significantly"}
                      </p>
                    )}
                  </div>

                  {/* Evidence quotes */}
                  {d.estimates.some((e) => e.evidence.length > 0) && (
                    <div>
                      <h4 style={{ fontSize: "0.875rem", marginBottom: "0.5rem", color: "#374151" }}>Evidence</h4>
                      {d.estimates
                        .filter((e) => e.evidence.length > 0)
                        .map((est) =>
                          est.evidence.slice(0, 2).map((quote, i) => (
                            <blockquote
                              key={`${est.method}-${i}`}
                              style={{
                                borderLeft: `3px solid ${METHOD_COLORS[est.method] ?? "#d1d5db"}`,
                                paddingLeft: "0.75rem",
                                margin: "0.5rem 0",
                                fontSize: "0.8rem",
                                color: "#4b5563",
                                lineHeight: 1.5,
                              }}
                            >
                              "{quote}"
                              <span style={{ color: "#9ca3af", fontSize: "0.7rem", marginLeft: "0.5rem" }}>
                                — {est.method}
                              </span>
                            </blockquote>
                          ))
                        )}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </>
  );
}

// ─── Methods Tab ─────────────────────────────────────────────

function MethodsTab({ profile }: { profile: ProfileData }) {
  const methods = profile.metadata.methods_used;

  const comparisonData = DOMAIN_ORDER.map((key) => {
    const d = profile.big_five.domains[key];
    const row: Record<string, string | number> = { trait: DOMAIN_LABELS[key] ?? key };
    if (d) {
      for (const est of d.estimates) {
        row[est.method] = Math.round(est.score);
      }
    }
    return row;
  });

  return (
    <>
      <h2 style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>Cross-Method Comparison</h2>
      <p style={{ color: "#6b7280", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
        Each bar shows a different assessment method's score for the same trait.
        Divergence between methods reveals where self-perception differs from behavioral expression.
      </p>

      <ResponsiveContainer width="100%" height={350}>
        <BarChart data={comparisonData} layout="vertical" barGap={2}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" domain={[0, 100]} />
          <YAxis type="category" dataKey="trait" width={130} fontSize={13} />
          <Tooltip />
          <Legend />
          {methods.map((method) => (
            <Bar
              key={method}
              dataKey={method}
              name={METHOD_LABELS[method] ?? method}
              fill={METHOD_COLORS[method] ?? "#6b7280"}
              radius={[0, 3, 3, 0]}
              barSize={12}
              isAnimationActive={false}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>

      {/* Divergence highlights */}
      <div style={{ marginTop: "2rem" }}>
        <h3 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>Notable Divergences</h3>
        {DOMAIN_ORDER.map((key) => {
          const d = profile.big_five.domains[key];
          if (!d || d.divergence < 10) return null;
          const sorted = [...d.estimates].sort((a, b) => b.score - a.score);
          const highest = sorted[0]!;
          const lowest = sorted[sorted.length - 1]!;
          return (
            <div key={key} style={{ padding: "0.75rem 1rem", background: "#fef3c7", borderRadius: "0.375rem", marginBottom: "0.5rem" }}>
              <strong>{DOMAIN_LABELS[key]}</strong>: {METHOD_LABELS[highest.method] ?? highest.method} scored {Math.round(highest.score)} vs {METHOD_LABELS[lowest.method] ?? lowest.method} scored {Math.round(lowest.score)} (gap: {Math.round(highest.score - lowest.score)})
            </div>
          );
        })}
      </div>

      {/* Method reliability legend */}
      <div style={{ marginTop: "2rem", padding: "1rem", background: "#f9fafb", borderRadius: "0.5rem" }}>
        <h3 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>Method Weights</h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", fontSize: "0.875rem" }}>
          {[
            ["Self-Report", "35%", "Psychometric instruments (alpha ~.85+)"],
            ["Interview", "20%", "Semi-structured assessment (r~.44)"],
            ["LLM Corpus", "20%", "Assessment-optimized prompting"],
          ].map(([name, weight, desc]) => (
            <div key={name as string} style={{ display: "flex", gap: "0.5rem" }}>
              <span style={{ fontWeight: 600, minWidth: 80 }}>{name}</span>
              <span style={{ color: "#2563eb", minWidth: 32 }}>{weight}</span>
              <span style={{ color: "#9ca3af" }}>{desc}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

// ─── Values Tab ──────────────────────────────────────────────

function ValuesTab({ profile }: { profile: ProfileData }) {
  const vals = profile.values.values;
  const sortedKeys = Object.keys(vals).sort(
    (a, b) => (vals[b]?.final_score ?? 0) - (vals[a]?.final_score ?? 0)
  ) as string[];

  const barData = sortedKeys.map((key) => ({
    name: VALUE_LABELS[key] ?? key,
    score: Math.round(vals[key]?.final_score ?? 0),
    isTop: profile.values.top_3.includes(key),
    isBottom: profile.values.bottom_3.includes(key),
  }));

  return (
    <>
      <h2 style={{ fontSize: "1.25rem", marginBottom: "0.5rem" }}>Schwartz Values</h2>
      <p style={{ color: "#6b7280", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
        Values represent broad motivational goals. Based on LLM corpus analysis + interview assessment.
      </p>

      <ResponsiveContainer width="100%" height={400}>
        <BarChart data={barData} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" domain={[0, 100]} />
          <YAxis type="category" dataKey="name" width={120} fontSize={13} />
          <Tooltip />
          <Bar dataKey="score" radius={[0, 4, 4, 0]} isAnimationActive={false}>
            {barData.map((entry, index) => (
              <Cell
                key={index}
                fill={entry.isTop ? "#059669" : entry.isBottom ? "#dc2626" : "#6b7280"}
                fillOpacity={0.8}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Value evidence cards */}
      <div style={{ marginTop: "2rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
        {sortedKeys.slice(0, 3).map((key) => {
          const v = vals[key] as MergedTrait | undefined;
          if (!v) return null;
          return (
            <div key={key} style={{ padding: "1rem", border: "1px solid #d1fae5", borderRadius: "0.5rem", background: "#f0fdf4" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
                <strong style={{ color: "#059669" }}>{VALUE_LABELS[key] ?? key}</strong>
                <span style={{ fontWeight: 700, color: "#059669" }}>{Math.round(v.final_score)}/100</span>
              </div>
              {v.estimates?.slice(0, 2).flatMap((est) =>
                est.evidence.slice(0, 1).map((quote, i) => (
                  <blockquote
                    key={`${est.method}-${i}`}
                    style={{ borderLeft: "3px solid #6ee7b7", paddingLeft: "0.75rem", margin: "0.25rem 0", fontSize: "0.8rem", color: "#4b5563" }}
                  >
                    "{quote}"
                  </blockquote>
                ))
              )}
            </div>
          );
        })}
      </div>
    </>
  );
}

// ─── Cognitive Tab ───────────────────────────────────────────

function CognitiveTab({ profile }: { profile: ProfileData }) {
  const { cognitive, dark_triad, clinical } = profile;
  return (
    <>
      {/* Cognitive Profile */}
      <h2 style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>Cognitive Profile</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginBottom: "2.5rem" }}>
        <MetricCard
          label="Cognitive Reflection"
          value={cognitive.crt_score !== null ? `${cognitive.crt_score}/7` : "—"}
          sublabel={cognitive.crt_score === 7 ? "Perfect analytical thinking" : ""}
          color="#2563eb"
        />
        <MetricCard
          label="Need for Cognition"
          value={cognitive.need_for_cognition !== null ? `${Math.round(cognitive.need_for_cognition)}` : "—"}
          sublabel={cognitive.need_for_cognition !== null ? scoreLabel(cognitive.need_for_cognition) : ""}
          color="#7c3aed"
        />
        <MetricCard
          label="Self-Esteem"
          value={cognitive.self_esteem !== null ? `${Math.round(cognitive.self_esteem)}` : "—"}
          sublabel={cognitive.self_esteem !== null ? scoreLabel(cognitive.self_esteem) : ""}
          color="#059669"
        />
      </div>

      {/* Dark Triad */}
      <h2 style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>Dark Triad</h2>
      <p style={{ color: "#6b7280", fontSize: "0.875rem", marginBottom: "1rem" }}>
        Short Dark Triad (SD3). Scores on 0-100 scale, 50 = population average.
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginBottom: "2.5rem" }}>
        {([
          ["Machiavellianism", dark_triad.machiavellianism, "#374151"],
          ["Narcissism", dark_triad.narcissism, "#374151"],
          ["Psychopathy", dark_triad.psychopathy, "#374151"],
        ] as const).map(([label, score, color]) => (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
            <span style={{ width: 150, fontSize: "0.875rem", fontWeight: 500 }}>{label}</span>
            <div style={{ flex: 1, height: 10, background: "#f3f4f6", borderRadius: 5, position: "relative" }}>
              <div style={{ height: 10, width: `${score ?? 0}%`, background: color, borderRadius: 5, opacity: 0.6 }} />
              {/* 50 marker */}
              <div style={{ position: "absolute", left: "50%", top: -2, height: 14, width: 1, background: "#d1d5db" }} />
            </div>
            <span style={{ fontWeight: 700, minWidth: 28, textAlign: "right" }}>{score !== null ? Math.round(score) : "—"}</span>
          </div>
        ))}
      </div>

      {/* Clinical Screens */}
      <h2 style={{ fontSize: "1.25rem", marginBottom: "0.5rem" }}>Clinical Screens</h2>
      <p style={{ color: "#dc2626", fontSize: "0.75rem", marginBottom: "1rem", fontStyle: "italic" }}>
        These are screening tools, not diagnoses. Consult a professional for clinical interpretation.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        <div style={{ padding: "1.25rem", border: "1px solid #e5e7eb", borderRadius: "0.5rem" }}>
          <div style={{ fontSize: "0.75rem", color: "#6b7280", marginBottom: "0.25rem" }}>PHQ-9 (Depression)</div>
          <div style={{ fontSize: "2rem", fontWeight: 700 }}>
            {clinical.phq9 !== null ? `${clinical.phq9}/27` : "—"}
          </div>
          {clinical.phq9_severity && (
            <span style={{ fontSize: "0.8rem", color: severityColor(clinical.phq9_severity), fontWeight: 600, textTransform: "capitalize" }}>
              {clinical.phq9_severity}
            </span>
          )}
          {clinical.phq9 !== null && (
            <div style={{ marginTop: "0.5rem", height: 6, background: "#f3f4f6", borderRadius: 3 }}>
              <div style={{ height: 6, width: `${(clinical.phq9 / 27) * 100}%`, background: severityColor(clinical.phq9_severity), borderRadius: 3 }} />
            </div>
          )}
        </div>
        <div style={{ padding: "1.25rem", border: "1px solid #e5e7eb", borderRadius: "0.5rem" }}>
          <div style={{ fontSize: "0.75rem", color: "#6b7280", marginBottom: "0.25rem" }}>GAD-7 (Anxiety)</div>
          <div style={{ fontSize: "2rem", fontWeight: 700 }}>
            {clinical.gad7 !== null ? `${clinical.gad7}/21` : "—"}
          </div>
          {clinical.gad7_severity && (
            <span style={{ fontSize: "0.8rem", color: severityColor(clinical.gad7_severity), fontWeight: 600, textTransform: "capitalize" }}>
              {clinical.gad7_severity}
            </span>
          )}
          {clinical.gad7 !== null && (
            <div style={{ marginTop: "0.5rem", height: 6, background: "#f3f4f6", borderRadius: 3 }}>
              <div style={{ height: 6, width: `${(clinical.gad7 / 21) * 100}%`, background: severityColor(clinical.gad7_severity), borderRadius: 3 }} />
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function MetricCard({ label, value, sublabel, color }: { label: string; value: string; sublabel: string; color: string }) {
  return (
    <div style={{ padding: "1.25rem", border: "1px solid #e5e7eb", borderRadius: "0.5rem", textAlign: "center" }}>
      <div style={{ fontSize: "0.75rem", color: "#6b7280", marginBottom: "0.5rem" }}>{label}</div>
      <div style={{ fontSize: "2rem", fontWeight: 700, color }}>{value}</div>
      {sublabel && <div style={{ fontSize: "0.75rem", color: "#9ca3af" }}>{sublabel}</div>}
    </div>
  );
}

// ─── Extended Battery Tab ────────────────────────────────────

function ExtendedBatteryTab({ profile }: { profile: ProfileData }) {
  return (
    <>
      <h2 style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>Extended Battery</h2>
      <p style={{ color: "#6b7280", fontSize: "0.875rem", marginBottom: "2rem" }}>
        Additional personality dimensions beyond the Big Five.
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
        {/* Attachment */}
        {profile.attachment && (profile.attachment.anxiety !== null || profile.attachment.avoidance !== null) && (
          <ScoreSection title="Attachment Style (ECR-R)" subtitle="Patterns in close relationships">
            {profile.attachment.anxiety !== null && (
              <ScoreBar label="Anxiety" score={profile.attachment.anxiety} description="Fear of rejection and abandonment" />
            )}
            {profile.attachment.avoidance !== null && (
              <ScoreBar label="Avoidance" score={profile.attachment.avoidance} description="Discomfort with closeness" />
            )}
          </ScoreSection>
        )}

        {/* Emotion Regulation */}
        {profile.emotion_reg && (profile.emotion_reg.reappraisal !== null || profile.emotion_reg.suppression !== null) && (
          <ScoreSection title="Emotion Regulation (ERQ)" subtitle="How you manage emotions">
            {profile.emotion_reg.reappraisal !== null && (
              <ScoreBar label="Reappraisal" score={profile.emotion_reg.reappraisal} description="Changing how you think about situations" color="#059669" />
            )}
            {profile.emotion_reg.suppression !== null && (
              <ScoreBar label="Suppression" score={profile.emotion_reg.suppression} description="Inhibiting emotional expression" color="#d97706" />
            )}
          </ScoreSection>
        )}

        {/* Empathy */}
        {profile.empathy && (
          <ScoreSection title="Empathy (IRI)" subtitle="Multi-dimensional empathy decomposition">
            {profile.empathy.fantasy !== null && (
              <ScoreBar label="Fantasy" score={profile.empathy.fantasy} description="Identification with fictional characters" />
            )}
            {profile.empathy.perspective_taking !== null && (
              <ScoreBar label="Perspective Taking" score={profile.empathy.perspective_taking} description="Cognitive empathy" />
            )}
            {profile.empathy.empathic_concern !== null && (
              <ScoreBar label="Empathic Concern" score={profile.empathy.empathic_concern} description="Affective empathy for others" />
            )}
            {profile.empathy.personal_distress !== null && (
              <ScoreBar label="Personal Distress" score={profile.empathy.personal_distress} description="Self-focused anxiety from others' distress" />
            )}
          </ScoreSection>
        )}

        {/* HEXACO */}
        {profile.hexaco && profile.hexaco.honesty_humility !== null && (
          <ScoreSection title="HEXACO" subtitle="Including Honesty-Humility (not measured by Big Five)">
            {profile.hexaco.honesty_humility !== null && (
              <ScoreBar label="Honesty-Humility" score={profile.hexaco.honesty_humility} description="Sincerity, fairness, greed avoidance" color="#7c3aed" />
            )}
            {profile.hexaco.emotionality !== null && (
              <ScoreBar label="Emotionality" score={profile.hexaco.emotionality} description="Fearfulness, anxiety, sentimentality" />
            )}
            {profile.hexaco.extraversion !== null && (
              <ScoreBar label="Extraversion" score={profile.hexaco.extraversion} />
            )}
            {profile.hexaco.agreeableness !== null && (
              <ScoreBar label="Agreeableness" score={profile.hexaco.agreeableness} />
            )}
            {profile.hexaco.conscientiousness !== null && (
              <ScoreBar label="Conscientiousness" score={profile.hexaco.conscientiousness} />
            )}
            {profile.hexaco.openness !== null && (
              <ScoreBar label="Openness" score={profile.hexaco.openness} />
            )}
          </ScoreSection>
        )}

        {/* Self-Monitoring + LOC */}
        {profile.social && (
          <ScoreSection title="Social & Control" subtitle="Self-monitoring and locus of control">
            {profile.social.self_monitoring !== null && (
              <ScoreBar label="Self-Monitoring" score={profile.social.self_monitoring} description="High = social chameleon; Low = consistent" />
            )}
            {profile.social.loc_internal !== null && (
              <ScoreBar label="Internal Locus" score={profile.social.loc_internal} description="Outcomes from own actions" color="#059669" />
            )}
            {profile.social.loc_external !== null && (
              <ScoreBar label="External Locus" score={profile.social.loc_external} description="Outcomes from external forces" color="#d97706" />
            )}
          </ScoreSection>
        )}

        {/* Grit */}
        {profile.grit && (profile.grit.perseverance !== null || profile.grit.interest_consistency !== null) && (
          <ScoreSection title="Grit" subtitle="Sustained passion and perseverance">
            {profile.grit.perseverance !== null && (
              <ScoreBar label="Perseverance" score={profile.grit.perseverance} description="Finishing what you start" color="#059669" />
            )}
            {profile.grit.interest_consistency !== null && (
              <ScoreBar label="Interest Consistency" score={profile.grit.interest_consistency} description="Maintaining focus on same goals" color="#2563eb" />
            )}
          </ScoreSection>
        )}

        {/* RIASEC */}
        {profile.vocational && (
          <ScoreSection title="Vocational Interests (RIASEC)" subtitle="Holland's 6 interest types">
            {(["realistic", "investigative", "artistic", "social", "enterprising", "conventional"] as const).map((key) => {
              const val = profile.vocational?.[key];
              if (val === null || val === undefined) return null;
              const labels: Record<string, string> = {
                realistic: "Realistic", investigative: "Investigative", artistic: "Artistic",
                social: "Social", enterprising: "Enterprising", conventional: "Conventional",
              };
              return <ScoreBar key={key} label={labels[key] ?? key} score={val} />;
            })}
          </ScoreSection>
        )}

        {/* BPNS */}
        {profile.needs && (
          <ScoreSection title="Basic Needs (BPNS)" subtitle="Self-Determination Theory needs satisfaction">
            {profile.needs.autonomy !== null && (
              <ScoreBar label="Autonomy" score={profile.needs.autonomy} description="Feeling free and volitional" />
            )}
            {profile.needs.competence !== null && (
              <ScoreBar label="Competence" score={profile.needs.competence} description="Feeling effective and capable" />
            )}
            {profile.needs.relatedness !== null && (
              <ScoreBar label="Relatedness" score={profile.needs.relatedness} description="Feeling connected to others" />
            )}
          </ScoreSection>
        )}
      </div>
    </>
  );
}

function ScoreSection({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div style={{ padding: "1.25rem", border: "1px solid #e5e7eb", borderRadius: "0.5rem" }}>
      <h3 style={{ fontSize: "1rem", marginBottom: "0.25rem" }}>{title}</h3>
      {subtitle && <p style={{ fontSize: "0.75rem", color: "#9ca3af", marginTop: 0, marginBottom: "1rem" }}>{subtitle}</p>}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {children}
      </div>
    </div>
  );
}

function ScoreBar({ label, score, description, color }: { label: string; score: number; description?: string; color?: string }) {
  const barColor = color ?? "#374151";
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
        <span style={{ width: 160, fontSize: "0.875rem", fontWeight: 500 }}>{label}</span>
        <div style={{ flex: 1, height: 10, background: "#f3f4f6", borderRadius: 5, position: "relative" }}>
          <div style={{ height: 10, width: `${score}%`, background: barColor, borderRadius: 5, opacity: 0.6 }} />
          <div style={{ position: "absolute", left: "50%", top: -2, height: 14, width: 1, background: "#d1d5db" }} />
        </div>
        <span style={{ fontWeight: 700, minWidth: 28, textAlign: "right" }}>{Math.round(score)}</span>
        <span style={{ fontSize: "0.75rem", color: "#9ca3af", minWidth: 60 }}>{scoreLabel(score)}</span>
      </div>
      {description && (
        <div style={{ marginLeft: 160 + 16, fontSize: "0.7rem", color: "#9ca3af", marginTop: "0.15rem" }}>{description}</div>
      )}
    </div>
  );
}

// ─── Corpus Analysis Tab ────────────────────────────────────

const DOMAIN_COLORS: Record<string, string> = {
  O: "#f59e0b",
  C: "#2563eb",
  E: "#059669",
  A: "#7c3aed",
  N: "#dc2626",
};

const SOURCE_LABELS: Record<string, string> = {
  academic: "Academic",
  sms: "SMS",
  messenger: "Messenger",
  chatgpt: "ChatGPT",
  claude_ai: "Claude AI",
};

const ERA_LABELS: Record<string, string> = {
  "era-2008-2015": "2008-2015",
  "era-2015-2019": "2015-2019",
  "era-2019-2024": "2019-2024",
  "era-2024-2026": "2024-2026",
};

const MEDIUM_LABELS: Record<string, string> = {
  "medium-formal": "Formal",
  "medium-messaging": "Messaging",
  "medium-ai": "AI",
};

function CorpusAnalysisTab() {
  const [data, setData] = useState<ComparisonSummary | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch("/profiles/corpus/comparison-summary.json")
      .then((r) => {
        if (!r.ok) throw new Error("Not found");
        return r.json() as Promise<ComparisonSummary>;
      })
      .then(setData)
      .catch(() => setError(true));
  }, []);

  if (error) {
    return (
      <div style={{ textAlign: "center", padding: "3rem", color: "#6b7280" }}>
        <h2>Corpus Analysis</h2>
        <p>No corpus analysis data available. Run the multi-level analysis pipeline first.</p>
      </div>
    );
  }

  if (!data) {
    return <p style={{ color: "#6b7280", textAlign: "center", padding: "2rem" }}>Loading corpus data...</p>;
  }

  const sourceKeys = Object.keys(SOURCE_LABELS).filter((k) => k in data.levels);
  const eraKeys = Object.keys(ERA_LABELS).filter((k) => k in data.levels);
  const mediumKeys = Object.keys(MEDIUM_LABELS).filter((k) => k in data.levels);

  const buildChartData = (keys: string[], labels: Record<string, string>) =>
    keys.map((key) => {
      const level = data.levels[key];
      const bf = level?.llm_big_five ?? {};
      return {
        name: labels[key] ?? key,
        O: bf.O ?? 0,
        C: bf.C ?? 0,
        E: bf.E ?? 0,
        A: bf.A ?? 0,
        N: bf.N ?? 0,
        words: level?.corpus_words ?? 0,
      };
    });

  const sourceData = buildChartData(sourceKeys, SOURCE_LABELS);
  const eraData = buildChartData(eraKeys, ERA_LABELS);
  const mediumData = buildChartData(mediumKeys, MEDIUM_LABELS);

  // Build lexical profile data for the heatmap
  const buildLexicalData = (keys: string[], labels: Record<string, string>) =>
    keys
      .filter((key) => data.levels[key]?.empath_lexical)
      .map((key) => ({
        name: labels[key] ?? key,
        ...Object.fromEntries(
          DOMAIN_ORDER.map((d) => [d, data.levels[key]?.empath_lexical?.[d]?.z ?? 0])
        ),
        labels: Object.fromEntries(
          DOMAIN_ORDER.map((d) => [d, data.levels[key]?.empath_lexical?.[d]?.label ?? "average"])
        ),
      }));

  const hasLexical = Object.values(data.levels).some((l) => l.empath_lexical);

  return (
    <>
      <h2 style={{ fontSize: "1.25rem", marginBottom: "0.5rem" }}>Corpus Analysis</h2>
      <p style={{ color: "#6b7280", fontSize: "0.875rem", marginBottom: "2rem" }}>
        Big Five personality scores across 13 analysis levels from a 1.47M word corpus (5 sources).
        LLM scores are from Claude Opus inference on text chunks. Lexical profiles show relative
        word-frequency patterns (what you write about varies by context, not who you are).
      </p>

      {/* By Source */}
      <CorpusChart
        title="By Source"
        description="How personality expression varies by communication context. Note that Conscientiousness is much higher in AI conversations (71) than in messaging (35) — a register effect consistent with genre-influenced expression."
        data={sourceData}
      />

      {/* By Era */}
      <CorpusChart
        title="By Era"
        description="Longitudinal personality development across four time periods. The 2015-2019 era shows peak Neuroticism (76) during a turbulent life period, while the AI era (2024-2026) shows regression toward the mean."
        data={eraData}
      />

      {/* By Medium */}
      <CorpusChart
        title="By Medium"
        description="Register effects on personality expression. Conscientiousness is notably higher in AI conversations (72) vs casual messaging (35). Neuroticism is much higher in messaging (70) than in AI contexts (40) — people express anxiety differently across mediums."
        data={mediumData}
      />

      {/* Lexical Profile */}
      {hasLexical && (
        <div style={{ marginTop: "2rem" }}>
          <h2 style={{ fontSize: "1.25rem", marginBottom: "0.5rem" }}>Lexical Profile (Empath)</h2>
          <p style={{ color: "#6b7280", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
            Word frequency patterns across Big-Five-aligned dimensions. These are <strong>ordinal comparisons</strong> between
            corpus segments — not personality scores. A &ldquo;high&rdquo; Openness label means more intellectual/creative
            vocabulary relative to the corpus average, not a personality assessment.
          </p>
          <LexicalHeatmap title="By Source" data={buildLexicalData(sourceKeys, SOURCE_LABELS)} />
          <LexicalHeatmap title="By Medium" data={buildLexicalData(mediumKeys, MEDIUM_LABELS)} />
          <LexicalHeatmap title="By Era" data={buildLexicalData(eraKeys, ERA_LABELS)} />
        </div>
      )}
    </>
  );
}

function CorpusChart({
  title,
  description,
  data,
}: {
  title: string;
  description: string;
  data: { name: string; O: number; C: number; E: number; A: number; N: number; words: number }[];
}) {
  return (
    <div style={{ marginBottom: "2.5rem" }}>
      <h3 style={{ fontSize: "1rem", marginBottom: "0.25rem" }}>{title}</h3>
      <p style={{ fontSize: "0.8rem", color: "#6b7280", marginBottom: "1rem", lineHeight: 1.5 }}>{description}</p>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} barGap={1}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" fontSize={12} />
          <YAxis domain={[0, 100]} fontSize={11} />
          <Tooltip
            formatter={(value: number, name: string) => [`${value}`, DOMAIN_LABELS[name] ?? name]}
            labelFormatter={(label: string) => {
              const entry = data.find((d) => d.name === label);
              return entry ? `${label} (${entry.words.toLocaleString()} words)` : label;
            }}
          />
          <Legend formatter={(value: string) => DOMAIN_LABELS[value] ?? value} />
          {DOMAIN_ORDER.map((key) => (
            <Bar
              key={key}
              dataKey={key}
              fill={DOMAIN_COLORS[key]}
              fillOpacity={0.8}
              radius={[2, 2, 0, 0]}
              barSize={16}
              isAnimationActive={false}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

const LEXICAL_Z_COLORS: Record<string, string> = {
  high: "#166534",
  "above average": "#4ade80",
  average: "#e5e7eb",
  "below average": "#fca5a5",
  low: "#991b1b",
};

const LEXICAL_Z_TEXT: Record<string, string> = {
  high: "#fff",
  "above average": "#14532d",
  average: "#374151",
  "below average": "#7f1d1d",
  low: "#fff",
};

function LexicalHeatmap({
  title,
  data,
}: {
  title: string;
  data: { name: string; labels: Record<string, string>; [k: string]: unknown }[];
}) {
  if (!data.length) return null;

  return (
    <div style={{ marginBottom: "2rem" }}>
      <h3 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>{title}</h3>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: "0.5rem", borderBottom: "2px solid #e5e7eb", minWidth: 100 }}></th>
              {DOMAIN_ORDER.map((d) => (
                <th key={d} style={{ padding: "0.5rem", borderBottom: "2px solid #e5e7eb", textAlign: "center", minWidth: 100 }}>
                  {DOMAIN_LABELS[d]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row) => (
              <tr key={row.name}>
                <td style={{ padding: "0.5rem", fontWeight: 600, borderBottom: "1px solid #f3f4f6" }}>{row.name}</td>
                {DOMAIN_ORDER.map((d) => {
                  const label = (row.labels as Record<string, string>)[d] ?? "average";
                  const z = row[d] as number;
                  return (
                    <td
                      key={d}
                      style={{
                        padding: "0.5rem",
                        textAlign: "center",
                        borderBottom: "1px solid #f3f4f6",
                        background: LEXICAL_Z_COLORS[label] ?? "#e5e7eb",
                        color: LEXICAL_Z_TEXT[label] ?? "#374151",
                        fontWeight: label === "average" ? 400 : 600,
                        borderRadius: "0.25rem",
                      }}
                      title={`z = ${z >= 0 ? "+" : ""}${z.toFixed(2)}`}
                    >
                      {label}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Persona Tab ────────────────────────────────────────────

function PersonaTab({ profile }: { profile: ProfileData }) {
  const persona = profile.persona;

  if (!persona) {
    return (
      <div style={{ textAlign: "center", padding: "3rem", color: "#6b7280" }}>
        <h2>Persona Model</h2>
        <p>No persona model available. Run the synthesis pipeline with extended battery data.</p>
      </div>
    );
  }

  const sections: { title: string; data: Record<string, unknown> }[] = [
    { title: "Communication Style", data: persona.communication },
    { title: "Decision-Making", data: persona.decision_making },
    { title: "Conflict Response", data: persona.conflict_response },
    { title: "Motivation", data: persona.motivation },
    { title: "Epistemic Style", data: persona.epistemic_style },
    { title: "Interpersonal", data: persona.interpersonal },
  ];

  return (
    <>
      <h2 style={{ fontSize: "1.25rem", marginBottom: "0.5rem" }}>Persona Model</h2>
      <p style={{ color: "#6b7280", fontSize: "0.875rem", marginBottom: "2rem" }}>
        Structured behavioral patterns derived from psychometric scores, suitable for AI agent simulation.
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        {sections.map(({ title, data }) => {
          const entries = Object.entries(data).filter(
            ([, v]) => v && (typeof v === "string" ? v.length > 0 : Array.isArray(v) ? v.length > 0 : true)
          );
          if (entries.length === 0) return null;

          return (
            <div key={title} style={{ padding: "1.25rem", border: "1px solid #e5e7eb", borderRadius: "0.5rem" }}>
              <h3 style={{ fontSize: "1rem", marginBottom: "0.75rem", color: "#2563eb" }}>{title}</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {entries.map(([key, value]) => (
                  <div key={key} style={{ display: "flex", gap: "0.75rem", fontSize: "0.875rem" }}>
                    <span style={{ fontWeight: 600, minWidth: 180, color: "#374151" }}>
                      {key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                    </span>
                    <span style={{ color: "#4b5563", lineHeight: 1.5 }}>
                      {Array.isArray(value) ? value.join(", ") : String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}

        {/* Characteristic Phrases */}
        {persona.characteristic_phrases && persona.characteristic_phrases.length > 0 && (
          <div style={{ padding: "1.25rem", border: "1px solid #e5e7eb", borderRadius: "0.5rem" }}>
            <h3 style={{ fontSize: "1rem", marginBottom: "0.75rem", color: "#7c3aed" }}>Characteristic Phrases</h3>
            {persona.characteristic_phrases.map((phrase, i) => (
              <blockquote
                key={i}
                style={{
                  borderLeft: "3px solid #7c3aed",
                  paddingLeft: "0.75rem",
                  margin: "0.5rem 0",
                  fontSize: "0.85rem",
                  color: "#4b5563",
                  fontStyle: "italic",
                }}
              >
                "{phrase}"
              </blockquote>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

// ─── Narrative Tab ───────────────────────────────────────────

function NarrativeTab({ profile }: { profile: ProfileData }) {
  const [showSnippet, setShowSnippet] = useState(false);

  return (
    <>
      <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem" }}>
        <button
          onClick={() => setShowSnippet(false)}
          style={showSnippet ? btnSecondary : btnPrimary}
        >
          Full Report
        </button>
        <button
          onClick={() => setShowSnippet(true)}
          style={showSnippet ? btnPrimary : btnSecondary}
        >
          CLAUDE.md Snippet
        </button>
      </div>

      <div
        style={{
          padding: "2rem",
          background: "#fafafa",
          borderRadius: "0.5rem",
          fontSize: "0.875rem",
          lineHeight: 1.7,
          whiteSpace: "pre-wrap",
          fontFamily: "system-ui, -apple-system, sans-serif",
          maxHeight: "70vh",
          overflow: "auto",
        }}
      >
        {showSnippet ? profile.claude_md_snippet : profile.narrative}
      </div>

      <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem" }}>
        <button
          onClick={() => {
            const text = showSnippet ? profile.claude_md_snippet : profile.narrative;
            navigator.clipboard.writeText(text);
          }}
          style={btnSecondary}
        >
          Copy to Clipboard
        </button>
        <button
          onClick={() => {
            const text = showSnippet ? profile.claude_md_snippet : profile.narrative;
            const blob = new Blob([text], { type: "text/markdown" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = showSnippet ? "claude-context.md" : "profile-report.md";
            a.click();
            URL.revokeObjectURL(url);
          }}
          style={btnSecondary}
        >
          Download .md
        </button>
      </div>
    </>
  );
}

// ─── Shared Styles ───────────────────────────────────────────

const btnPrimary: React.CSSProperties = {
  padding: "0.5rem 1rem",
  background: "#2563eb",
  color: "#fff",
  border: "none",
  borderRadius: "0.375rem",
  cursor: "pointer",
  fontSize: "0.875rem",
  fontWeight: 500,
};

const btnSecondary: React.CSSProperties = {
  padding: "0.5rem 1rem",
  background: "transparent",
  color: "#374151",
  border: "1px solid #d1d5db",
  borderRadius: "0.375rem",
  cursor: "pointer",
  fontSize: "0.875rem",
};
