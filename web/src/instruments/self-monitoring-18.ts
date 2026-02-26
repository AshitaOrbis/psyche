import type { Instrument } from "./types";
import { registerInstrument } from "./registry";
import { scoreBinary } from "../scoring/engine";

/**
 * Self-Monitoring Scale (18-item revised)
 * Measures social adaptiveness vs. behavioral consistency.
 * Source: Snyder & Gangestad (1986) — public domain via openpsychometrics.org.
 *
 * High self-monitors: adapt behavior to social situations (chameleon-like).
 * Low self-monitors: consistent across contexts (what-you-see-is-what-you-get).
 */

interface SmItem {
  text: string;
  /** True = keyed toward high self-monitoring */
  keyedTrue: boolean;
}

// Self-Monitoring Scale-Revised (Snyder & Gangestad, 1986)
const ITEMS: SmItem[] = [
  { text: "I find it hard to imitate the behavior of other people.", keyedTrue: false },
  { text: "At parties and social gatherings, I do not attempt to do or say things that others will like.", keyedTrue: false },
  { text: "I can only argue for ideas which I already believe.", keyedTrue: false },
  { text: "I can make impromptu speeches even on topics about which I have almost no information.", keyedTrue: true },
  { text: "I guess I put on a show to impress or entertain others.", keyedTrue: true },
  { text: "I would probably make a good actor.", keyedTrue: true },
  { text: "In a group of people I am rarely the center of attention.", keyedTrue: false },
  { text: "In different situations and with different people, I often act like very different persons.", keyedTrue: true },
  { text: "I am not particularly good at making other people like me.", keyedTrue: false },
  { text: "I'm not always the person I appear to be.", keyedTrue: true },
  { text: "I would not change my opinions (or the way I do things) in order to please someone or win their favor.", keyedTrue: false },
  { text: "I have considered being an entertainer.", keyedTrue: true },
  { text: "I have never been good at games like charades or improvisational acting.", keyedTrue: false },
  { text: "I have trouble changing my behavior to suit different people and different situations.", keyedTrue: false },
  { text: "At a party I let others keep the jokes and stories going.", keyedTrue: false },
  { text: "I feel a bit awkward in company and do not show up quite as well as I should.", keyedTrue: false },
  { text: "I can look anyone in the eye and tell a lie with a straight face (if for a right end).", keyedTrue: true },
  { text: "I may deceive people by being friendly when I really dislike them.", keyedTrue: true },
];

const selfMonitoring18: Instrument = {
  id: "self-monitoring-18",
  name: "Self-Monitoring Scale (Revised)",
  shortName: "Self-Monitor",
  description:
    "Measures the extent to which people monitor and control their expressive behavior and self-presentation. High = social chameleon; Low = cross-situationally consistent.",
  citation:
    "Snyder, M., & Gangestad, S. (1986). On the nature of self-monitoring: Matters of assessment, matters of validity. Journal of Personality and Social Psychology, 51, 125-139.",
  itemCount: 18,
  estimatedMinutes: 3,
  scales: [
    { id: "self-monitoring", name: "Self-Monitoring", description: "Social adaptiveness vs. behavioral consistency" },
  ],
  items: ITEMS.map((item, idx) => ({
    id: `sm-${idx + 1}`,
    text: item.text,
    response: {
      type: "binary" as const,
      labels: ["True", "False"] as [string, string],
    },
    scaleId: "self-monitoring",
    // Items keyed "false" toward high SM need reversal:
    // keyedTrue=true means True=1 is the "high SM" answer (no reversal needed)
    // keyedTrue=false means False=0 is the "high SM" answer (reverse so True→0, False→1)
    reversed: !item.keyedTrue,
  })),
};

registerInstrument(selfMonitoring18, scoreBinary);

export default selfMonitoring18;
