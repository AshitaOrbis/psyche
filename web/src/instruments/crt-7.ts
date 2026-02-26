import type { Instrument, InstrumentSession, InstrumentResult } from "./types";
import { registerInstrument } from "./registry";

/**
 * Cognitive Reflection Test (CRT-7)
 * Extended version by Toplak et al. (2014)
 * Tests analytical vs intuitive thinking
 */

const crt7: Instrument = {
  id: "crt-7",
  name: "Cognitive Reflection Test (CRT-7)",
  shortName: "CRT",
  description:
    "Measures tendency to override intuitive but incorrect responses with reflective, correct ones.",
  citation:
    "Toplak, M. E., West, R. F., & Stanovich, K. E. (2014). Assessing miserly information processing. Thinking & Reasoning, 20(2), 219-243.",
  itemCount: 7,
  estimatedMinutes: 5,
  scales: [
    { id: "crt-analytic", name: "Analytic Thinking" },
  ],
  items: [
    {
      id: "crt-1",
      text: "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost? (in cents)",
      response: { type: "numeric" },
      scaleId: "crt-analytic",
    },
    {
      id: "crt-2",
      text: "If it takes 5 machines 5 minutes to make 5 widgets, how long would it take 100 machines to make 100 widgets? (in minutes)",
      response: { type: "numeric" },
      scaleId: "crt-analytic",
    },
    {
      id: "crt-3",
      text: "In a lake, there is a patch of lily pads. Every day, the patch doubles in size. If it takes 48 days for the patch to cover the entire lake, how long would it take for the patch to cover half of the lake? (in days)",
      response: { type: "numeric" },
      scaleId: "crt-analytic",
    },
    {
      id: "crt-4",
      text: "If John can drink one barrel of water in 6 days, and Mary can drink one barrel of water in 12 days, how long would it take them to drink one barrel of water together? (in days)",
      response: { type: "numeric" },
      scaleId: "crt-analytic",
    },
    {
      id: "crt-5",
      text: "Jerry received both the 15th highest and the 15th lowest mark in the class. How many students are in the class?",
      response: { type: "numeric" },
      scaleId: "crt-analytic",
    },
    {
      id: "crt-6",
      text: "A man buys a pig for $60, sells it for $70, buys it back for $80, and sells it finally for $90. How much has he made? (in dollars)",
      response: { type: "numeric" },
      scaleId: "crt-analytic",
    },
    {
      id: "crt-7",
      text: "Simon decided to invest $8,000 in the stock market one day early in 2008. Six months after he invested, on July 17, the stocks he had purchased were down 50%. Fortunately for Simon, from July 17 to October 17, the stocks he had purchased went up 75%. At this point, Simon has: (a) broken even in the stock market, (b) is ahead of where he began, (c) has lost money. Enter a, b, or c.",
      response: { type: "text" },
      scaleId: "crt-analytic",
    },
  ],
};

/** Correct answers for CRT-7 */
const CORRECT_ANSWERS: Record<string, (value: number | string) => boolean> = {
  "crt-1": (v) => Number(v) === 5,
  "crt-2": (v) => Number(v) === 5,
  "crt-3": (v) => Number(v) === 47,
  "crt-4": (v) => Number(v) === 4,
  "crt-5": (v) => Number(v) === 29,
  "crt-6": (v) => Number(v) === 20,
  "crt-7": (v) => String(v).toLowerCase().trim() === "c",
};

function scoreCrt(instrument: Instrument, session: InstrumentSession): InstrumentResult {
  let correct = 0;
  for (const resp of session.responses) {
    const checker = CORRECT_ANSWERS[resp.itemId];
    if (checker?.(resp.value)) {
      correct++;
    }
  }

  return {
    instrumentId: instrument.id,
    completedAt: session.completedAt ?? Date.now(),
    scores: [
      {
        scaleId: "crt-analytic",
        scaleName: "Analytic Thinking",
        raw: correct,
        normalized: (correct / 7) * 100,
        itemCount: session.responses.length,
      },
    ],
  };
}

registerInstrument(crt7, scoreCrt);

export default crt7;
