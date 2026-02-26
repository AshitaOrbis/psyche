import type { Instrument } from "./types";
import { registerInstrument } from "./registry";
import { scoreLikert } from "../scoring/engine";

/**
 * BPNS-9: Basic Psychological Needs Satisfaction Scale (Short Form)
 * 9-item measure of three fundamental human needs from Self-Determination Theory.
 * Source: Deci & Ryan — SDT website, public domain.
 */

interface BpnsItem {
  text: string;
  scale: "autonomy" | "competence" | "relatedness";
  reversed: boolean;
}

// BPNS short form items
const ITEMS: BpnsItem[] = [
  // Autonomy (3 items)
  { text: "I feel like I am free to decide for myself how to live my life.", scale: "autonomy", reversed: false },
  { text: "I generally feel free to express my ideas and opinions.", scale: "autonomy", reversed: false },
  { text: "In my daily life, I frequently have to do what I am told.", scale: "autonomy", reversed: true },

  // Competence (3 items)
  { text: "Most days I feel a sense of accomplishment from what I do.", scale: "competence", reversed: false },
  { text: "People I know tell me I am good at what I do.", scale: "competence", reversed: false },
  { text: "I often do not feel very capable.", scale: "competence", reversed: true },

  // Relatedness (3 items)
  { text: "People in my life care about me.", scale: "relatedness", reversed: false },
  { text: "I feel connected to people who care for me, and for whom I care.", scale: "relatedness", reversed: false },
  { text: "I feel excluded from the group I want to belong to.", scale: "relatedness", reversed: true },
];

const bpns9: Instrument = {
  id: "bpns-9",
  name: "Basic Psychological Needs Satisfaction",
  shortName: "BPNS",
  description:
    "Measures satisfaction of three fundamental needs from Self-Determination Theory: Autonomy (volition), Competence (effectiveness), and Relatedness (connection with others).",
  citation:
    "Deci, E. L., & Ryan, R. M. (2000). The 'what' and 'why' of goal pursuits: Human needs and the self-determination of behavior. Psychological Inquiry, 11, 227-268. Short form from selfdeterminationtheory.org.",
  itemCount: 9,
  estimatedMinutes: 1,
  scales: [
    { id: "autonomy", name: "Autonomy", description: "Need to feel volitional and self-endorsed in one's actions" },
    { id: "competence", name: "Competence", description: "Need to feel effective and capable" },
    { id: "relatedness", name: "Relatedness", description: "Need to feel connected and cared for by others" },
  ],
  items: ITEMS.map((item, idx) => ({
    id: `bpns-${idx + 1}`,
    text: item.text,
    response: {
      type: "likert" as const,
      min: 1,
      max: 7,
      labels: [
        "Not at all true",
        "Rarely true",
        "Seldom true",
        "Somewhat true",
        "Often true",
        "Usually true",
        "Very true",
      ],
    },
    scaleId: item.scale,
    reversed: item.reversed,
  })),
};

registerInstrument(bpns9, scoreLikert);

export default bpns9;
