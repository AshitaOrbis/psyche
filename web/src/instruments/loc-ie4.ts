import type { Instrument } from "./types";
import { registerInstrument } from "./registry";
import { scoreLikert } from "../scoring/engine";

/**
 * IE-4: Internal-External Locus of Control Scale
 * 4-item ultra-short measure of locus of control.
 * Source: Kovaleva, Beierlein, Kemper, & Rammstedt (2012) — PMC open access.
 */

const ITEMS: { text: string; scale: "internal" | "external" }[] = [
  { text: "If I work hard, I will succeed.", scale: "internal" },
  { text: "Whether at work or in my private life: What I do is mainly determined by others.", scale: "external" },
  { text: "My life is determined by my own actions.", scale: "internal" },
  { text: "Fate often gets in the way of my plans.", scale: "external" },
];

const locIe4: Instrument = {
  id: "loc-ie4",
  name: "Internal-External Locus of Control (IE-4)",
  shortName: "LOC",
  description:
    "Ultra-brief measure of locus of control: Internal (outcomes caused by own actions) vs. External (outcomes caused by outside forces).",
  citation:
    "Kovaleva, A., Beierlein, C., Kemper, C. J., & Rammstedt, B. (2012). Eine Kurzskala zur Messung von Kontrollueberzeugung [A short scale for measuring locus of control]. GESIS Working Papers, 2012/19.",
  itemCount: 4,
  estimatedMinutes: 1,
  scales: [
    { id: "internal", name: "Internal Locus", description: "Belief that outcomes are determined by own actions" },
    { id: "external", name: "External Locus", description: "Belief that outcomes are determined by external forces" },
  ],
  items: ITEMS.map((item, idx) => ({
    id: `loc-${idx + 1}`,
    text: item.text,
    response: {
      type: "likert" as const,
      min: 1,
      max: 5,
      labels: [
        "Strongly Disagree",
        "Disagree",
        "Neutral",
        "Agree",
        "Strongly Agree",
      ],
    },
    scaleId: item.scale,
    reversed: false,
  })),
};

registerInstrument(locIe4, scoreLikert);

export default locIe4;
