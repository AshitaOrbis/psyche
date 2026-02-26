import type { Instrument } from "./types";
import { registerInstrument } from "./registry";
import { scoreLikert } from "../scoring/engine";

/**
 * ERQ-10: Emotion Regulation Questionnaire
 * 10-item measure of habitual emotion regulation strategies.
 * Source: Gross & John (2003) — Stanford Psychophysiology Lab, public domain.
 */

interface ErqItem {
  text: string;
  scale: "reappraisal" | "suppression";
}

// ERQ items (Gross & John, 2003)
const ITEMS: ErqItem[] = [
  // Cognitive Reappraisal items (6)
  { text: "When I want to feel more positive emotion (such as joy or amusement), I change what I'm thinking about.", scale: "reappraisal" },
  { text: "When I want to feel less negative emotion (such as sadness or anger), I change what I'm thinking about.", scale: "reappraisal" },
  { text: "When I'm faced with a stressful situation, I make myself think about it in a way that helps me stay calm.", scale: "reappraisal" },
  { text: "When I want to feel more positive emotion, I change the way I'm thinking about the situation.", scale: "reappraisal" },
  { text: "I control my emotions by changing the way I think about the situation I'm in.", scale: "reappraisal" },
  { text: "When I want to feel less negative emotion, I change the way I'm thinking about the situation.", scale: "reappraisal" },

  // Expressive Suppression items (4)
  { text: "I keep my emotions to myself.", scale: "suppression" },
  { text: "When I am feeling positive emotions, I am careful not to express them.", scale: "suppression" },
  { text: "I control my emotions by not expressing them.", scale: "suppression" },
  { text: "When I am feeling negative emotions, I make sure not to express them.", scale: "suppression" },
];

const erq10: Instrument = {
  id: "erq-10",
  name: "Emotion Regulation Questionnaire",
  shortName: "ERQ",
  description:
    "Measures two emotion regulation strategies: Cognitive Reappraisal (reframing situations) and Expressive Suppression (hiding emotional expression).",
  citation:
    "Gross, J. J., & John, O. P. (2003). Individual differences in two emotion regulation processes. Journal of Personality and Social Psychology, 85, 348-362.",
  itemCount: 10,
  estimatedMinutes: 2,
  scales: [
    { id: "reappraisal", name: "Cognitive Reappraisal", description: "Changing how you think about emotion-eliciting situations" },
    { id: "suppression", name: "Expressive Suppression", description: "Inhibiting ongoing emotion-expressive behavior" },
  ],
  items: ITEMS.map((item, idx) => ({
    id: `erq-${idx + 1}`,
    text: item.text,
    response: {
      type: "likert" as const,
      min: 1,
      max: 7,
      labels: [
        "Strongly Disagree",
        "Disagree",
        "Slightly Disagree",
        "Neutral",
        "Slightly Agree",
        "Agree",
        "Strongly Agree",
      ],
    },
    scaleId: item.scale,
    reversed: false,
  })),
};

registerInstrument(erq10, scoreLikert);

export default erq10;
