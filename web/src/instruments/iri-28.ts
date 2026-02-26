import type { Instrument } from "./types";
import { registerInstrument } from "./registry";
import { scoreLikert } from "../scoring/engine";

/**
 * IRI-28: Interpersonal Reactivity Index
 * 28-item measure of empathy across 4 dimensions.
 * Source: Davis (1983) — public domain via Fetzer Institute.
 */

interface IriItem {
  text: string;
  scale: "fantasy" | "perspective_taking" | "empathic_concern" | "personal_distress";
  reversed: boolean;
}

// IRI items (Davis, 1983)
const ITEMS: IriItem[] = [
  // Fantasy Scale (7 items)
  { text: "I daydream and fantasize, with some regularity, about things that might happen to me.", scale: "fantasy", reversed: false },
  { text: "I really get involved with the feelings of the characters in a novel.", scale: "fantasy", reversed: false },
  { text: "I am usually objective when I watch a movie or play, and I don't often get completely caught up in it.", scale: "fantasy", reversed: true },
  { text: "Becoming extremely involved in a good book or movie is somewhat rare for me.", scale: "fantasy", reversed: true },
  { text: "After seeing a play or movie, I have felt as though I were one of the characters.", scale: "fantasy", reversed: false },
  { text: "When I am reading an interesting story or novel, I imagine how I would feel if the events in the story were happening to me.", scale: "fantasy", reversed: false },
  { text: "When I watch a good movie, I can very easily put myself in the place of a leading character.", scale: "fantasy", reversed: false },

  // Perspective Taking Scale (7 items)
  { text: "I sometimes find it difficult to see things from the 'other person's' point of view.", scale: "perspective_taking", reversed: true },
  { text: "I try to look at everybody's side of a disagreement before I make a decision.", scale: "perspective_taking", reversed: false },
  { text: "I sometimes try to understand my friends better by imagining how things look from their perspective.", scale: "perspective_taking", reversed: false },
  { text: "If I'm sure I'm right about something, I don't waste much time listening to other people's arguments.", scale: "perspective_taking", reversed: true },
  { text: "I believe that there are two sides to every question and try to look at them both.", scale: "perspective_taking", reversed: false },
  { text: "When I'm upset at someone, I usually try to 'put myself in their shoes' for a while.", scale: "perspective_taking", reversed: false },
  { text: "Before criticizing somebody, I try to imagine how I would feel if I were in their place.", scale: "perspective_taking", reversed: false },

  // Empathic Concern Scale (7 items)
  { text: "I often have tender, concerned feelings for people less fortunate than me.", scale: "empathic_concern", reversed: false },
  { text: "Sometimes I don't feel very sorry for other people when they are having problems.", scale: "empathic_concern", reversed: true },
  { text: "When I see someone being taken advantage of, I feel kind of protective towards them.", scale: "empathic_concern", reversed: false },
  { text: "Other people's misfortunes do not usually disturb me a great deal.", scale: "empathic_concern", reversed: true },
  { text: "When I see someone being treated unfairly, I sometimes don't feel very much pity for them.", scale: "empathic_concern", reversed: true },
  { text: "I am often quite touched by things that I see happen.", scale: "empathic_concern", reversed: false },
  { text: "I would describe myself as a pretty soft-hearted person.", scale: "empathic_concern", reversed: false },

  // Personal Distress Scale (7 items)
  { text: "In emergency situations, I feel apprehensive and ill-at-ease.", scale: "personal_distress", reversed: false },
  { text: "I sometimes feel helpless when I am in the middle of a very emotional situation.", scale: "personal_distress", reversed: false },
  { text: "When I see someone who badly needs help in an emergency, I go to pieces.", scale: "personal_distress", reversed: false },
  { text: "Being in a tense emotional situation scares me.", scale: "personal_distress", reversed: false },
  { text: "I am usually pretty effective in dealing with emergencies.", scale: "personal_distress", reversed: true },
  { text: "I tend to lose control during emergencies.", scale: "personal_distress", reversed: false },
  { text: "When I see someone get hurt, I tend to remain calm.", scale: "personal_distress", reversed: true },
];

const iri28: Instrument = {
  id: "iri-28",
  name: "Interpersonal Reactivity Index",
  shortName: "IRI",
  description:
    "Decomposes empathy into four dimensions: Fantasy (emotional identification with fiction), Perspective-Taking (cognitive empathy), Empathic Concern (affective empathy for others), and Personal Distress (self-focused anxiety in response to others' distress).",
  citation:
    "Davis, M. H. (1983). Measuring individual differences in empathy: Evidence for a multidimensional approach. Journal of Personality and Social Psychology, 44, 113-126.",
  itemCount: 28,
  estimatedMinutes: 5,
  scales: [
    { id: "fantasy", name: "Fantasy", description: "Tendency to imaginatively transpose oneself into fictional situations" },
    { id: "perspective_taking", name: "Perspective Taking", description: "Tendency to spontaneously adopt the psychological point of view of others" },
    { id: "empathic_concern", name: "Empathic Concern", description: "Tendency to experience feelings of warmth, compassion, and concern for others" },
    { id: "personal_distress", name: "Personal Distress", description: "Tendency to experience feelings of personal anxiety and discomfort in response to others' distress" },
  ],
  items: ITEMS.map((item, idx) => ({
    id: `iri-${idx + 1}`,
    text: item.text,
    response: {
      type: "likert" as const,
      min: 1,
      max: 5,
      labels: [
        "Does Not Describe Me Well",
        "Slightly",
        "Moderately",
        "Well",
        "Describes Me Very Well",
      ],
    },
    scaleId: item.scale,
    reversed: item.reversed,
  })),
};

registerInstrument(iri28, scoreLikert);

export default iri28;
