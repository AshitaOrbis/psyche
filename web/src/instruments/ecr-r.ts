import type { Instrument } from "./types";
import { registerInstrument } from "./registry";
import { scoreLikert } from "../scoring/engine";

/**
 * ECR-R: Experiences in Close Relationships—Revised
 * 36-item measure of adult attachment: Anxiety and Avoidance.
 * Source: Fraley, Waller, & Brennan (2000) — public domain.
 */

interface EcrItem {
  text: string;
  scale: "anxiety" | "avoidance";
  reversed: boolean;
}

// ECR-R items (Fraley et al., 2000)
// Odd-numbered items = Avoidance, Even-numbered items = Anxiety
const ITEMS: EcrItem[] = [
  // Avoidance items
  { text: "I prefer not to show a partner how I feel deep down.", scale: "avoidance", reversed: false },
  { text: "I feel comfortable sharing my private thoughts and feelings with my partner.", scale: "avoidance", reversed: true },
  { text: "I find it difficult to allow myself to depend on romantic partners.", scale: "avoidance", reversed: false },
  { text: "I am very comfortable being close to romantic partners.", scale: "avoidance", reversed: true },
  { text: "I prefer not to be too close to romantic partners.", scale: "avoidance", reversed: false },
  { text: "I get uncomfortable when a romantic partner wants to be very close.", scale: "avoidance", reversed: false },
  { text: "I find it relatively easy to get close to my partner.", scale: "avoidance", reversed: true },
  { text: "It's not difficult for me to get close to my partner.", scale: "avoidance", reversed: true },
  { text: "I usually discuss my problems and concerns with my partner.", scale: "avoidance", reversed: true },
  { text: "It helps to turn to my romantic partner in times of need.", scale: "avoidance", reversed: true },
  { text: "I tell my partner just about everything.", scale: "avoidance", reversed: true },
  { text: "I talk things over with my partner.", scale: "avoidance", reversed: true },
  { text: "I am nervous when partners get too close to me.", scale: "avoidance", reversed: false },
  { text: "I feel comfortable depending on romantic partners.", scale: "avoidance", reversed: true },
  { text: "I find it easy to depend on romantic partners.", scale: "avoidance", reversed: true },
  { text: "It's easy for me to be affectionate with my partner.", scale: "avoidance", reversed: true },
  { text: "My partner really understands me and my needs.", scale: "avoidance", reversed: true },
  { text: "I don't feel comfortable opening up to romantic partners.", scale: "avoidance", reversed: false },

  // Anxiety items
  { text: "I'm afraid that I will lose my partner's love.", scale: "anxiety", reversed: false },
  { text: "I often worry that my partner will not want to stay with me.", scale: "anxiety", reversed: false },
  { text: "I often worry that my partner doesn't really love me.", scale: "anxiety", reversed: false },
  { text: "I worry that romantic partners won't care about me as much as I care about them.", scale: "anxiety", reversed: false },
  { text: "I often wish that my partner's feelings for me were as strong as my feelings for them.", scale: "anxiety", reversed: false },
  { text: "I worry a lot about my relationships.", scale: "anxiety", reversed: false },
  { text: "When my partner is out of sight, I worry that they might become interested in someone else.", scale: "anxiety", reversed: false },
  { text: "When I show my feelings for romantic partners, I'm afraid they will not feel the same about me.", scale: "anxiety", reversed: false },
  { text: "I rarely worry about my partner leaving me.", scale: "anxiety", reversed: true },
  { text: "My romantic partner makes me doubt myself.", scale: "anxiety", reversed: false },
  { text: "I do not often worry about being abandoned.", scale: "anxiety", reversed: true },
  { text: "I find that my partners don't want to get as close as I would like.", scale: "anxiety", reversed: false },
  { text: "Sometimes romantic partners change their feelings about me for no apparent reason.", scale: "anxiety", reversed: false },
  { text: "My desire to be very close sometimes scares people away.", scale: "anxiety", reversed: false },
  { text: "I'm afraid that once a romantic partner gets to know me, they won't like who I really am.", scale: "anxiety", reversed: false },
  { text: "It makes me mad that I don't get the affection and support I need from my partner.", scale: "anxiety", reversed: false },
  { text: "I worry that I won't measure up to other people.", scale: "anxiety", reversed: false },
  { text: "My partner only seems to notice me when I'm angry.", scale: "anxiety", reversed: false },
];

const ecrR: Instrument = {
  id: "ecr-r",
  name: "Experiences in Close Relationships—Revised",
  shortName: "ECR-R",
  description:
    "Measures adult attachment style along two dimensions: Anxiety (fear of abandonment) and Avoidance (discomfort with closeness).",
  citation:
    "Fraley, R. C., Waller, N. G., & Brennan, K. A. (2000). An item response theory analysis of self-report measures of adult attachment. Journal of Personality and Social Psychology, 78, 350-365.",
  itemCount: 36,
  estimatedMinutes: 5,
  scales: [
    { id: "anxiety", name: "Attachment Anxiety", description: "Fear of rejection and abandonment" },
    { id: "avoidance", name: "Attachment Avoidance", description: "Discomfort with closeness and dependence" },
  ],
  items: ITEMS.map((item, idx) => ({
    id: `ecr-${idx + 1}`,
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
    reversed: item.reversed,
  })),
};

registerInstrument(ecrR, scoreLikert);

export default ecrR;
