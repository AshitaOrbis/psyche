import type { Instrument, InstrumentSession, InstrumentResult } from "./types";
import { registerInstrument } from "./registry";

/**
 * Open-Ended Qualitative Prompts
 * Semi-structured self-reflection questions for qualitative analysis.
 * No scoring — responses are exported for LLM analysis.
 */

const PROMPTS = [
  "Describe yourself as you would to a stranger who will never see you. Be as honest as possible.",
  "What are you most proud of? What are you least proud of?",
  "How do you typically respond to conflict or disagreement?",
  "Describe a decision you made recently that you found difficult. What made it hard?",
  "What gives you energy? What drains you?",
  "How have you changed in the last five years? What caused the change?",
  "What do your closest friends value most about you? What do they wish you'd change?",
  "Describe your relationship with uncertainty and ambiguity.",
  "What topic could you talk about for hours? Why does it matter to you?",
  "If you could design your ideal day with no obligations, what would it look like?",
];

const openEnded: Instrument = {
  id: "open-ended",
  name: "Self-Reflection Prompts",
  shortName: "Reflection",
  description:
    "Open-ended questions for qualitative personality analysis. No right answers — write freely.",
  citation: "Custom instrument for qualitative triangulation.",
  itemCount: PROMPTS.length,
  estimatedMinutes: 15,
  scales: [{ id: "qualitative", name: "Qualitative Responses" }],
  items: PROMPTS.map((text, idx) => ({
    id: `open-${idx + 1}`,
    text,
    response: { type: "text" as const, minWords: 30 },
    scaleId: "qualitative",
  })),
};

/** No scoring — just record completeness */
function scoreOpenEnded(_instrument: Instrument, session: InstrumentSession): InstrumentResult {
  const answered = session.responses.filter(
    (r) => typeof r.value === "string" && r.value.trim().length > 0
  ).length;

  const totalWords = session.responses.reduce((sum, r) => {
    if (typeof r.value === "string") {
      return sum + r.value.trim().split(/\s+/).length;
    }
    return sum;
  }, 0);

  return {
    instrumentId: "open-ended",
    completedAt: session.completedAt ?? Date.now(),
    scores: [
      {
        scaleId: "qualitative",
        scaleName: "Qualitative Responses",
        raw: answered,
        normalized: (answered / PROMPTS.length) * 100,
        itemCount: answered,
      },
      {
        scaleId: "word-count",
        scaleName: "Total Word Count",
        raw: totalWords,
        normalized: Math.min((totalWords / 1000) * 100, 100), // 1000 words = 100%
        itemCount: answered,
      },
    ],
  };
}

registerInstrument(openEnded, scoreOpenEnded);

export default openEnded;
