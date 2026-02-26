import type { Instrument } from "./types";
import { registerInstrument } from "./registry";
import { scoreLikert } from "../scoring/engine";

/**
 * Short Dark Triad (SD3)
 * Jones & Paulhus (2014)
 * 27 items measuring Machiavellianism, Narcissism, and Psychopathy.
 */

interface SD3Item {
  text: string;
  scale: "mach" | "narc" | "psych";
  reversed: boolean;
}

const ITEMS: SD3Item[] = [
  // Machiavellianism (9 items)
  { text: "It's not wise to tell your secrets.", scale: "mach", reversed: false },
  { text: "I like to use clever manipulation to get my way.", scale: "mach", reversed: false },
  { text: "Whatever it takes, you must get the important people on your side.", scale: "mach", reversed: false },
  { text: "Avoid direct conflict with others because they may be useful in the future.", scale: "mach", reversed: false },
  { text: "It's wise to keep track of information that you can use against people later.", scale: "mach", reversed: false },
  { text: "You should wait for the right time to get back at people.", scale: "mach", reversed: false },
  { text: "There are things you should hide from other people to preserve your reputation.", scale: "mach", reversed: false },
  { text: "Make sure your plans benefit yourself, not others.", scale: "mach", reversed: false },
  { text: "Most people can be manipulated.", scale: "mach", reversed: false },

  // Narcissism (9 items)
  { text: "People see me as a natural leader.", scale: "narc", reversed: false },
  { text: "I hate being the center of attention.", scale: "narc", reversed: true },
  { text: "Many group activities tend to be dull without me.", scale: "narc", reversed: false },
  { text: "I know that I am special because everyone keeps telling me so.", scale: "narc", reversed: false },
  { text: "I like to get acquainted with important people.", scale: "narc", reversed: false },
  { text: "I feel embarrassed if someone compliments me.", scale: "narc", reversed: true },
  { text: "I have been compared to famous people.", scale: "narc", reversed: false },
  { text: "I am an average person.", scale: "narc", reversed: true },
  { text: "I insist on getting the respect I deserve.", scale: "narc", reversed: false },

  // Psychopathy (9 items)
  { text: "I like to get revenge on authorities.", scale: "psych", reversed: false },
  { text: "I avoid dangerous situations.", scale: "psych", reversed: true },
  { text: "Payback needs to be quick and nasty.", scale: "psych", reversed: false },
  { text: "People often say I'm out of control.", scale: "psych", reversed: false },
  { text: "It's true that I can be mean to others.", scale: "psych", reversed: false },
  { text: "People who mess with me always regret it.", scale: "psych", reversed: false },
  { text: "I have never gotten into trouble with the law.", scale: "psych", reversed: true },
  { text: "I enjoy having sex with people I hardly know.", scale: "psych", reversed: false },
  { text: "I'll say anything to get what I want.", scale: "psych", reversed: false },
];

const sd3: Instrument = {
  id: "sd3",
  name: "Short Dark Triad (SD3)",
  shortName: "Dark Triad",
  description:
    "Measures three socially aversive personality traits: Machiavellianism, Narcissism, and Psychopathy.",
  citation:
    "Jones, D. N., & Paulhus, D. L. (2014). Introducing the Short Dark Triad (SD3). Assessment, 21(1), 28-41.",
  itemCount: 27,
  estimatedMinutes: 5,
  scales: [
    { id: "mach", name: "Machiavellianism" },
    { id: "narc", name: "Narcissism" },
    { id: "psych", name: "Psychopathy" },
  ],
  items: ITEMS.map((item, idx) => ({
    id: `sd3-${idx + 1}`,
    text: item.text,
    response: {
      type: "likert" as const,
      min: 1,
      max: 5,
      labels: [
        "Strongly Disagree",
        "Disagree",
        "Neither",
        "Agree",
        "Strongly Agree",
      ],
    },
    scaleId: item.scale,
    reversed: item.reversed,
  })),
};

registerInstrument(sd3, scoreLikert);

export default sd3;
