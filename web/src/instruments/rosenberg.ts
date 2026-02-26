import type { Instrument } from "./types";
import { registerInstrument } from "./registry";
import { scoreLikert } from "../scoring/engine";

/**
 * Rosenberg Self-Esteem Scale (RSES)
 * Rosenberg (1965)
 * 10-item measure of global self-worth.
 */

const ITEMS: { text: string; reversed: boolean }[] = [
  { text: "On the whole, I am satisfied with myself.", reversed: false },
  { text: "At times I think I am no good at all.", reversed: true },
  { text: "I feel that I have a number of good qualities.", reversed: false },
  { text: "I am able to do things as well as most other people.", reversed: false },
  { text: "I feel I do not have much to be proud of.", reversed: true },
  { text: "I certainly feel useless at times.", reversed: true },
  { text: "I feel that I'm a person of worth, at least on an equal plane with others.", reversed: false },
  { text: "I wish I could have more respect for myself.", reversed: true },
  { text: "All in all, I am inclined to feel that I am a failure.", reversed: true },
  { text: "I take a positive attitude toward myself.", reversed: false },
];

const rosenberg: Instrument = {
  id: "rosenberg",
  name: "Rosenberg Self-Esteem Scale",
  shortName: "RSES",
  description: "Measures global self-worth by assessing positive and negative feelings about the self.",
  citation:
    "Rosenberg, M. (1965). Society and the adolescent self-image. Princeton University Press.",
  itemCount: 10,
  estimatedMinutes: 2,
  scales: [{ id: "self-esteem", name: "Self-Esteem" }],
  items: ITEMS.map((item, idx) => ({
    id: `rses-${idx + 1}`,
    text: item.text,
    response: {
      type: "likert" as const,
      min: 1,
      max: 4,
      labels: ["Strongly Disagree", "Disagree", "Agree", "Strongly Agree"],
    },
    scaleId: "self-esteem",
    reversed: item.reversed,
  })),
};

registerInstrument(rosenberg, scoreLikert);

export default rosenberg;
