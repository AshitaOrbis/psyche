import type { Instrument } from "./types";
import { registerInstrument } from "./registry";
import { scoreLikert } from "../scoring/engine";

/**
 * Short Grit Scale (Grit-S)
 * 8-item measure of grit: Perseverance of Effort + Consistency of Interest.
 * Source: Duckworth & Quinn (2009) — public domain via Duckworth Lab.
 */

interface GritItem {
  text: string;
  scale: "perseverance" | "interest_consistency";
  reversed: boolean;
}

// Grit-S items (Duckworth & Quinn, 2009)
const ITEMS: GritItem[] = [
  // Consistency of Interest (4 items) — all reverse-scored (high = inconsistent)
  { text: "New ideas and projects sometimes distract me from previous ones.", scale: "interest_consistency", reversed: true },
  { text: "I have been obsessed with a certain idea or project for a short time but later lost interest.", scale: "interest_consistency", reversed: true },
  { text: "I often set a goal but later choose to pursue a different one.", scale: "interest_consistency", reversed: true },
  { text: "I have difficulty maintaining my focus on projects that take more than a few months to complete.", scale: "interest_consistency", reversed: true },

  // Perseverance of Effort (4 items) — all forward-scored
  { text: "I finish whatever I begin.", scale: "perseverance", reversed: false },
  { text: "Setbacks don't discourage me.", scale: "perseverance", reversed: false },
  { text: "I am a hard worker.", scale: "perseverance", reversed: false },
  { text: "I am diligent.", scale: "perseverance", reversed: false },
];

const gritS: Instrument = {
  id: "grit-s",
  name: "Short Grit Scale (Grit-S)",
  shortName: "Grit",
  description:
    "Measures grit — sustained passion and perseverance for long-term goals. Two subscales: Perseverance of Effort (keeping going) and Consistency of Interest (staying focused on the same goals).",
  citation:
    "Duckworth, A. L., & Quinn, P. D. (2009). Development and validation of the Short Grit Scale (Grit-S). Journal of Personality Assessment, 91, 166-174.",
  itemCount: 8,
  estimatedMinutes: 1,
  scales: [
    { id: "perseverance", name: "Perseverance of Effort", description: "Tendency to work hard and finish what you start" },
    { id: "interest_consistency", name: "Consistency of Interest", description: "Tendency to maintain focus on the same goals over time" },
  ],
  items: ITEMS.map((item, idx) => ({
    id: `grit-${idx + 1}`,
    text: item.text,
    response: {
      type: "likert" as const,
      min: 1,
      max: 5,
      labels: [
        "Not at all like me",
        "Not much like me",
        "Somewhat like me",
        "Mostly like me",
        "Very much like me",
      ],
    },
    scaleId: item.scale,
    reversed: item.reversed,
  })),
};

registerInstrument(gritS, scoreLikert);

export default gritS;
