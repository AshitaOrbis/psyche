import type { Instrument } from "./types";
import { registerInstrument } from "./registry";
import { scoreLikert } from "../scoring/engine";

/**
 * RIASEC Markers (48-item)
 * Vocational interest inventory based on Holland's 6 types.
 * Source: Public domain IPIP RIASEC markers (openpsychometrics.org / ipip.ori.org).
 */

const SCALES = [
  { id: "realistic", name: "Realistic", description: "Hands-on, mechanical, athletic activities" },
  { id: "investigative", name: "Investigative", description: "Analytical, intellectual, scientific activities" },
  { id: "artistic", name: "Artistic", description: "Creative, expressive, unstructured activities" },
  { id: "social", name: "Social", description: "Helping, teaching, counseling activities" },
  { id: "enterprising", name: "Enterprising", description: "Persuading, leading, managing activities" },
  { id: "conventional", name: "Conventional", description: "Organizing, data-handling, detail-oriented activities" },
];

interface RiasecItem {
  text: string;
  scale: string;
  reversed: boolean;
}

// RIASEC-48 items (public domain IPIP markers)
const ITEMS: RiasecItem[] = [
  // Realistic (8 items)
  { text: "Like to work on cars.", scale: "realistic", reversed: false },
  { text: "Like to build things.", scale: "realistic", reversed: false },
  { text: "Like to take care of animals.", scale: "realistic", reversed: false },
  { text: "Like to do outdoor activities.", scale: "realistic", reversed: false },
  { text: "Am good at making and repairing things.", scale: "realistic", reversed: false },
  { text: "Like to tinker with machines and equipment.", scale: "realistic", reversed: false },
  { text: "Enjoy working with tools.", scale: "realistic", reversed: false },
  { text: "Prefer to work with my hands.", scale: "realistic", reversed: false },

  // Investigative (8 items)
  { text: "Like to explore ideas.", scale: "investigative", reversed: false },
  { text: "Like to figure out how things work.", scale: "investigative", reversed: false },
  { text: "Like to analyze problems.", scale: "investigative", reversed: false },
  { text: "Like to do research.", scale: "investigative", reversed: false },
  { text: "Am interested in science.", scale: "investigative", reversed: false },
  { text: "Like to solve complex problems.", scale: "investigative", reversed: false },
  { text: "Am curious about many different things.", scale: "investigative", reversed: false },
  { text: "Enjoy thinking about abstract concepts.", scale: "investigative", reversed: false },

  // Artistic (8 items)
  { text: "Like to create art.", scale: "artistic", reversed: false },
  { text: "Like to play musical instruments.", scale: "artistic", reversed: false },
  { text: "Like to write stories or poetry.", scale: "artistic", reversed: false },
  { text: "Like to act in plays.", scale: "artistic", reversed: false },
  { text: "Am good at expressing myself creatively.", scale: "artistic", reversed: false },
  { text: "Like to design things.", scale: "artistic", reversed: false },
  { text: "Have a vivid imagination.", scale: "artistic", reversed: false },
  { text: "Appreciate beautiful or aesthetic things.", scale: "artistic", reversed: false },

  // Social (8 items)
  { text: "Like to help people with their problems.", scale: "social", reversed: false },
  { text: "Like to teach or train people.", scale: "social", reversed: false },
  { text: "Like to do volunteer work.", scale: "social", reversed: false },
  { text: "Like to work in teams.", scale: "social", reversed: false },
  { text: "Am good at mediating disputes.", scale: "social", reversed: false },
  { text: "Enjoy caring for others.", scale: "social", reversed: false },
  { text: "Am sensitive to the needs of others.", scale: "social", reversed: false },
  { text: "Enjoy cooperating with others to get things done.", scale: "social", reversed: false },

  // Enterprising (8 items)
  { text: "Like to lead a group.", scale: "enterprising", reversed: false },
  { text: "Like to persuade people to see my side.", scale: "enterprising", reversed: false },
  { text: "Like to sell things.", scale: "enterprising", reversed: false },
  { text: "Am good at managing people.", scale: "enterprising", reversed: false },
  { text: "Like to start new projects.", scale: "enterprising", reversed: false },
  { text: "Am ambitious and driven to succeed.", scale: "enterprising", reversed: false },
  { text: "Like to take charge of situations.", scale: "enterprising", reversed: false },
  { text: "Am comfortable making decisions that affect others.", scale: "enterprising", reversed: false },

  // Conventional (8 items)
  { text: "Like to organize files and records.", scale: "conventional", reversed: false },
  { text: "Like to follow a set schedule.", scale: "conventional", reversed: false },
  { text: "Am good at keeping records and tracking details.", scale: "conventional", reversed: false },
  { text: "Like to work with numbers and data.", scale: "conventional", reversed: false },
  { text: "Prefer to follow established procedures.", scale: "conventional", reversed: false },
  { text: "Am accurate and pay attention to details.", scale: "conventional", reversed: false },
  { text: "Like to use computers for data entry or analysis.", scale: "conventional", reversed: false },
  { text: "Prefer work that has clear rules and expectations.", scale: "conventional", reversed: false },
];

const riasec48: Instrument = {
  id: "riasec-48",
  name: "RIASEC Vocational Interest Inventory",
  shortName: "RIASEC",
  description:
    "Measures Holland's 6 vocational interest types: Realistic (hands-on), Investigative (analytical), Artistic (creative), Social (helping), Enterprising (leading), Conventional (organizing). Your top 2-3 types form your Holland Code.",
  citation:
    "Holland, J. L. (1997). Making vocational choices: A theory of vocational personalities and work environments. Public domain IPIP RIASEC markers from ipip.ori.org.",
  itemCount: 48,
  estimatedMinutes: 7,
  scales: SCALES,
  items: ITEMS.map((item, idx) => ({
    id: `riasec-${idx + 1}`,
    text: item.text,
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
    scaleId: item.scale,
    reversed: item.reversed,
  })),
};

registerInstrument(riasec48, scoreLikert);

export default riasec48;
