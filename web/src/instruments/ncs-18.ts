import type { Instrument } from "./types";
import { registerInstrument } from "./registry";
import { scoreLikert } from "../scoring/engine";

/**
 * Need for Cognition Scale — Short Form (NCS-18)
 * Cacioppo, Petty, & Kao (1984)
 * Measures tendency to engage in and enjoy thinking.
 */

const ITEMS: { text: string; reversed: boolean }[] = [
  { text: "I would prefer complex to simple problems.", reversed: false },
  { text: "I like to have the responsibility of handling a situation that requires a lot of thinking.", reversed: false },
  { text: "Thinking is not my idea of fun.", reversed: true },
  { text: "I would rather do something that requires little thought than something that is sure to challenge my thinking abilities.", reversed: true },
  { text: "I try to anticipate and avoid situations where there is a likely chance I will have to think in depth about something.", reversed: true },
  { text: "I find satisfaction in deliberating hard and for long hours.", reversed: false },
  { text: "I only think as hard as I have to.", reversed: true },
  { text: "I prefer to think about small, daily projects to long-term ones.", reversed: true },
  { text: "I like tasks that require little thought once I've learned them.", reversed: true },
  { text: "The idea of relying on thought to make my way to the top appeals to me.", reversed: false },
  { text: "I really enjoy a task that involves coming up with new solutions to problems.", reversed: false },
  { text: "Learning new ways to think doesn't excite me very much.", reversed: true },
  { text: "I prefer my life to be filled with puzzles that I must solve.", reversed: false },
  { text: "The notion of thinking abstractly is appealing to me.", reversed: false },
  { text: "I would prefer a task that is intellectual, difficult, and important to one that is somewhat important but does not require much thought.", reversed: false },
  { text: "I feel relief rather than satisfaction after completing a task that required a lot of mental effort.", reversed: true },
  { text: "It's enough for me that something gets the job done; I don't care how or why it works.", reversed: true },
  { text: "I usually end up deliberating about issues even when they do not affect me personally.", reversed: false },
];

const ncs18: Instrument = {
  id: "ncs-18",
  name: "Need for Cognition Scale (NCS-18)",
  shortName: "NCS",
  description:
    "Measures the tendency to engage in and enjoy effortful cognitive activity.",
  citation:
    "Cacioppo, J. T., Petty, R. E., & Kao, C. F. (1984). The efficient assessment of need for cognition. Journal of Personality Assessment, 48(3), 306-307.",
  itemCount: 18,
  estimatedMinutes: 3,
  scales: [{ id: "ncs", name: "Need for Cognition" }],
  items: ITEMS.map((item, idx) => ({
    id: `ncs-${idx + 1}`,
    text: item.text,
    response: {
      type: "likert" as const,
      min: 1,
      max: 5,
      labels: [
        "Extremely Uncharacteristic",
        "Somewhat Uncharacteristic",
        "Uncertain",
        "Somewhat Characteristic",
        "Extremely Characteristic",
      ],
    },
    scaleId: "ncs",
    reversed: item.reversed,
  })),
};

registerInstrument(ncs18, scoreLikert);

export default ncs18;
