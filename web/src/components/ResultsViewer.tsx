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
} from "recharts";
import type { InstrumentResult } from "../instruments/types";
import { getInstrument } from "../instruments/registry";

interface ResultsViewerProps {
  result: InstrumentResult;
}

export function ResultsViewer({ result }: ResultsViewerProps) {
  const registered = getInstrument(result.instrumentId);
  if (!registered) return <p>Unknown instrument: {result.instrumentId}</p>;

  const { instrument } = registered;

  // Separate domain and facet scores
  const domainScores = result.scores.filter(
    (s) => instrument.scales.find((sc) => sc.id === s.scaleId && !sc.parentId)
  );
  const facetScores = result.scores.filter(
    (s) => instrument.scales.find((sc) => sc.id === s.scaleId && sc.parentId)
  );

  // Group facets by domain
  const facetsByDomain = new Map<string, typeof facetScores>();
  for (const fs of facetScores) {
    const scale = instrument.scales.find((s) => s.id === fs.scaleId);
    if (!scale?.parentId) continue;
    const existing = facetsByDomain.get(scale.parentId) ?? [];
    existing.push(fs);
    facetsByDomain.set(scale.parentId, existing);
  }

  const radarData = domainScores.map((s) => ({
    trait: s.scaleName,
    score: Math.round(s.normalized),
    fullMark: 100,
  }));

  return (
    <div style={{ maxWidth: 800, margin: "0 auto" }}>
      <h3>{instrument.name} Results</h3>
      <p style={{ color: "#6b7280", fontSize: "0.875rem" }}>
        Completed {new Date(result.completedAt).toLocaleDateString()}
      </p>

      {/* Radar chart for domain scores */}
      {domainScores.length >= 3 && (
        <div style={{ marginBottom: "2rem" }}>
          <h4>Domain Overview</h4>
          <ResponsiveContainer width="100%" height={350}>
            <RadarChart data={radarData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="trait" />
              <PolarRadiusAxis domain={[0, 100]} />
              <Radar
                dataKey="score"
                stroke="#2563eb"
                fill="#2563eb"
                fillOpacity={0.3}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Domain score cards */}
      <div style={{ display: "grid", gap: "1rem", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))" }}>
        {domainScores.map((ds) => (
          <div
            key={ds.scaleId}
            style={{
              padding: "1rem",
              border: "1px solid #e5e7eb",
              borderRadius: "0.5rem",
            }}
          >
            <div style={{ fontWeight: 600 }}>{ds.scaleName}</div>
            <div style={{ fontSize: "2rem", fontWeight: 700, color: "#2563eb" }}>
              {Math.round(ds.normalized)}
            </div>
            <div style={{ fontSize: "0.75rem", color: "#9ca3af" }}>
              out of 100 ({scoreLabel(ds.normalized)})
            </div>
          </div>
        ))}
      </div>

      {/* Facet breakdown per domain */}
      {domainScores.map((ds) => {
        const facets = facetsByDomain.get(ds.scaleId);
        if (!facets || facets.length === 0) return null;

        const barData = facets.map((f) => ({
          name: f.scaleName,
          score: Math.round(f.normalized),
        }));

        return (
          <div key={ds.scaleId} style={{ marginTop: "2rem" }}>
            <h4>{ds.scaleName} Facets</h4>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={barData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" domain={[0, 100]} />
                <YAxis type="category" dataKey="name" width={130} fontSize={12} />
                <Tooltip />
                <Bar dataKey="score" fill="#2563eb" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        );
      })}
    </div>
  );
}

function scoreLabel(normalized: number): string {
  if (normalized >= 80) return "Very High";
  if (normalized >= 60) return "High";
  if (normalized >= 40) return "Average";
  if (normalized >= 20) return "Low";
  return "Very Low";
}
