import type { Instrument, Item, Scale } from "./types";
import { registerInstrument } from "./registry";
import { scoreLikert } from "../scoring/engine";
import questionsData from "b5-johnson-120-ipip-neo-pi-r/data/en/questions.json";

/** Domain metadata */
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

/** Facet names per domain */
const FACETS: Record<string, string[]> = {
  N: ["Anxiety", "Anger", "Depression", "Self-Consciousness", "Immoderation", "Vulnerability"],
  E: ["Friendliness", "Gregariousness", "Assertiveness", "Activity Level", "Excitement-Seeking", "Cheerfulness"],
  O: ["Imagination", "Artistic Interests", "Emotionality", "Adventurousness", "Intellect", "Liberalism"],
  A: ["Trust", "Morality", "Altruism", "Cooperation", "Modesty", "Sympathy"],
  C: ["Self-Efficacy", "Orderliness", "Dutifulness", "Achievement-Striving", "Self-Discipline", "Cautiousness"],
};

/** Build scales: 5 domains + 30 facets */
function buildScales(): Scale[] {
  const scales: Scale[] = [];

  for (const [domainKey, meta] of Object.entries(DOMAINS)) {
    scales.push({
      id: domainKey,
      name: meta.name,
      description: meta.description,
    });

    const facetNames = FACETS[domainKey]!;
    for (let i = 0; i < facetNames.length; i++) {
      scales.push({
        id: `${domainKey}${i + 1}`,
        name: facetNames[i]!,
        parentId: domainKey,
      });
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

/** Convert npm package questions to our Item format */
function buildItems(): Item[] {
  return (questionsData as RawQuestion[]).map((q) => ({
    id: q.id,
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

const ipipNeo120: Instrument = {
  id: "ipip-neo-120",
  name: "IPIP-NEO-120",
  shortName: "Big Five",
  description:
    "International Personality Item Pool representation of the NEO PI-R. Measures 5 personality domains and 30 facets.",
  citation:
    'Johnson, J. A. (2014). Measuring thirty facets of the Five Factor Model with a 120-item public domain inventory. Journal of Research in Personality, 51, 78-89.',
  itemCount: 120,
  estimatedMinutes: 15,
  scales: buildScales(),
  items: buildItems(),
};

/**
 * Score IPIP-NEO-120.
 * Uses the generic Likert scorer — items keyed "minus" are reversed.
 * Then computes domain scores as the mean of their 6 facet scores.
 */
registerInstrument(ipipNeo120, (instrument, session) => {
  // First score at the facet level
  const facetResult = scoreLikert(instrument, session);

  // Compute domain scores as mean of facet scores
  const domainScores = Object.keys(DOMAINS).map((domainKey) => {
    const facetScores = facetResult.scores.filter((s) =>
      s.scaleId.startsWith(domainKey) && s.scaleId.length > 1
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

export default ipipNeo120;
