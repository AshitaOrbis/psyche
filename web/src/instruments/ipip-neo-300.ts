import type { Instrument, Item, Scale } from "./types";
import { registerInstrument } from "./registry";
import { scoreLikert } from "../scoring/engine";
import questionsData from "@alheimsins/b5-costa-mccrae-300-ipip-neo-pi-r/data/en/questions.json";

/**
 * IPIP-NEO-300 (Costa & McCrae framework)
 * 300-item measure of Big Five domains + 30 facets (10 items/facet).
 * Higher precision than NEO-120 (4 items/facet).
 * Source: ipip.ori.org — public domain IPIP items.
 */

const DOMAINS: Record<string, { name: string; description: string }> = {
  N: {
    name: "Neuroticism",
    description:
      "Tendency to experience negative emotions such as anxiety, anger, and depression.",
  },
  E: {
    name: "Extraversion",
    description:
      "Tendency to seek stimulation in the company of others and to experience positive emotions.",
  },
  O: {
    name: "Openness",
    description:
      "Tendency to be imaginative, creative, and open to new experiences and ideas.",
  },
  A: {
    name: "Agreeableness",
    description:
      "Tendency to be compassionate, cooperative, and trusting toward others.",
  },
  C: {
    name: "Conscientiousness",
    description:
      "Tendency to be organized, dependable, disciplined, and goal-oriented.",
  },
};

const FACETS: Record<string, string[]> = {
  N: ["Anxiety", "Anger", "Depression", "Self-Consciousness", "Immoderation", "Vulnerability"],
  E: ["Friendliness", "Gregariousness", "Assertiveness", "Activity Level", "Excitement-Seeking", "Cheerfulness"],
  O: ["Imagination", "Artistic Interests", "Emotionality", "Adventurousness", "Intellect", "Liberalism"],
  A: ["Trust", "Morality", "Altruism", "Cooperation", "Modesty", "Sympathy"],
  C: ["Self-Efficacy", "Orderliness", "Dutifulness", "Achievement-Striving", "Self-Discipline", "Cautiousness"],
};

function buildScales(): Scale[] {
  const scales: Scale[] = [];
  for (const [domainKey, meta] of Object.entries(DOMAINS)) {
    scales.push({ id: domainKey, name: meta.name, description: meta.description });
    const facetNames = FACETS[domainKey]!;
    for (let i = 0; i < facetNames.length; i++) {
      scales.push({ id: `${domainKey}${i + 1}`, name: facetNames[i]!, parentId: domainKey });
    }
  }
  return scales;
}

interface RawQuestion {
  id: string;
  text: string;
  keyed: "plus" | "minus";
  domain: string;
  facet: number;
}

function buildItems(): Item[] {
  return (questionsData as RawQuestion[]).map((q) => ({
    id: `neo300-${q.id}`,
    text: q.text,
    response: {
      type: "likert" as const,
      min: 1,
      max: 5,
      labels: [
        "Very Inaccurate",
        "Moderately Inaccurate",
        "Neither",
        "Moderately Accurate",
        "Very Accurate",
      ],
    },
    scaleId: `${q.domain}${q.facet}`,
    reversed: q.keyed === "minus",
  }));
}

const ipipNeo300: Instrument = {
  id: "ipip-neo-300",
  name: "IPIP-NEO-300",
  shortName: "Big Five (300)",
  description:
    "300-item IPIP representation of the NEO PI-R. Same 30 facets as NEO-120 but with 10 items per facet for higher precision.",
  citation:
    'Costa, P. T., & McCrae, R. R. (1992). Revised NEO Personality Inventory (NEO PI-R) and NEO Five-Factor Inventory (NEO-FFI) professional manual. IPIP items from ipip.ori.org.',
  itemCount: 300,
  estimatedMinutes: 40,
  scales: buildScales(),
  items: buildItems(),
};

registerInstrument(ipipNeo300, (instrument, session) => {
  const facetResult = scoreLikert(instrument, session);

  const domainScores = Object.keys(DOMAINS).map((domainKey) => {
    const facetScores = facetResult.scores.filter(
      (s) => s.scaleId.startsWith(domainKey) && s.scaleId.length > 1
    );
    const avgNorm =
      facetScores.length > 0
        ? facetScores.reduce((sum, s) => sum + s.normalized, 0) / facetScores.length
        : 0;
    const avgRaw =
      facetScores.length > 0
        ? facetScores.reduce((sum, s) => sum + s.raw, 0) / facetScores.length
        : 0;

    return {
      scaleId: domainKey,
      scaleName: DOMAINS[domainKey]!.name,
      raw: avgRaw,
      normalized: avgNorm,
      itemCount: facetScores.reduce((sum, s) => sum + s.itemCount, 0),
    };
  });

  return {
    instrumentId: instrument.id,
    completedAt: session.completedAt ?? Date.now(),
    scores: [...domainScores, ...facetResult.scores],
  };
});

export default ipipNeo300;
