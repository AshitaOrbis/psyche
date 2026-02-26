import type { Instrument } from "./types";
import { registerInstrument } from "./registry";
import { scoreLikert } from "../scoring/engine";

/**
 * HEXACO-60 (IPIP version)
 * 60-item measure of 6 personality factors including Honesty-Humility.
 * Source: IPIP representation of HEXACO (ipip.ori.org) — public domain.
 * Ashton & Lee (2009). The HEXACO-60: A short measure of the major dimensions of personality.
 */

interface HexacoItem {
  text: string;
  scale: string;
  reversed: boolean;
}

const SCALES = [
  { id: "hh", name: "Honesty-Humility", description: "Sincerity, fairness, greed avoidance, modesty" },
  { id: "em", name: "Emotionality", description: "Fearfulness, anxiety, dependence, sentimentality" },
  { id: "ex", name: "Extraversion", description: "Social self-esteem, social boldness, sociability, liveliness" },
  { id: "ag", name: "Agreeableness", description: "Forgiveness, gentleness, flexibility, patience" },
  { id: "co", name: "Conscientiousness", description: "Organization, diligence, perfectionism, prudence" },
  { id: "op", name: "Openness to Experience", description: "Aesthetic appreciation, inquisitiveness, creativity, unconventionality" },
];

// HEXACO-60 IPIP items (public domain from ipip.ori.org)
const ITEMS: HexacoItem[] = [
  // Honesty-Humility (10 items)
  { text: "I would never accept a bribe, even if it were very large.", scale: "hh", reversed: false },
  { text: "I would be tempted to use counterfeit money, if I were sure I could get away with it.", scale: "hh", reversed: true },
  { text: "If I knew that I could never get caught, I would be willing to steal a million dollars.", scale: "hh", reversed: true },
  { text: "I would never take things that aren't mine.", scale: "hh", reversed: false },
  { text: "I would like to be seen driving around in a very expensive car.", scale: "hh", reversed: true },
  { text: "I would get a lot of pleasure from owning expensive luxury goods.", scale: "hh", reversed: true },
  { text: "Having a lot of money is not especially important to me.", scale: "hh", reversed: false },
  { text: "I think that I am entitled to more respect than the average person is.", scale: "hh", reversed: true },
  { text: "I want people to know that I am an important person of high status.", scale: "hh", reversed: true },
  { text: "I am an ordinary person who is no better than others.", scale: "hh", reversed: false },

  // Emotionality (10 items)
  { text: "I would feel afraid if I had to travel in bad weather conditions.", scale: "em", reversed: false },
  { text: "I don't mind doing jobs that involve dangerous work.", scale: "em", reversed: true },
  { text: "When it comes to physical danger, I am very fearful.", scale: "em", reversed: false },
  { text: "Even in an emergency I wouldn't feel like panicking.", scale: "em", reversed: true },
  { text: "I sometimes can't help worrying about little things.", scale: "em", reversed: false },
  { text: "I worry a lot less than most people do.", scale: "em", reversed: true },
  { text: "I can handle difficult situations without needing emotional support from anyone else.", scale: "em", reversed: true },
  { text: "Whenever I feel worried about something, I want to share my concern with another person.", scale: "em", reversed: false },
  { text: "I feel like crying when I see other people crying.", scale: "em", reversed: false },
  { text: "I remain unemotional even in situations where most people get very sentimental.", scale: "em", reversed: true },

  // Extraversion (10 items)
  { text: "I feel reasonably satisfied with myself overall.", scale: "ex", reversed: false },
  { text: "I think most people like some aspects of my personality.", scale: "ex", reversed: false },
  { text: "I feel that I am an unpopular person.", scale: "ex", reversed: true },
  { text: "I sometimes feel that I am a worthless person.", scale: "ex", reversed: true },
  { text: "In social situations, I'm usually the one who makes the first move.", scale: "ex", reversed: false },
  { text: "When I'm in a group of people, I'm often the one who speaks on behalf of the group.", scale: "ex", reversed: false },
  { text: "I tend to feel quite self-conscious when speaking in front of a group of people.", scale: "ex", reversed: true },
  { text: "I prefer jobs that involve active social interaction to those that involve working alone.", scale: "ex", reversed: false },
  { text: "The first thing that I always do in a new place is to make friends.", scale: "ex", reversed: false },
  { text: "On most days, I feel cheerful and optimistic.", scale: "ex", reversed: false },

  // Agreeableness (10 items)
  { text: "I rarely hold a grudge, even against people who have badly wronged me.", scale: "ag", reversed: false },
  { text: "My attitude toward people who have treated me badly is 'forgive and forget'.", scale: "ag", reversed: false },
  { text: "If someone has cheated me once, I will always feel suspicious of that person.", scale: "ag", reversed: true },
  { text: "I find it hard to fully forgive someone who has done something mean to me.", scale: "ag", reversed: true },
  { text: "I tend to be lenient in judging other people.", scale: "ag", reversed: false },
  { text: "People sometimes tell me that I am too critical of others.", scale: "ag", reversed: true },
  { text: "Even when people make a lot of mistakes, I rarely say anything negative.", scale: "ag", reversed: false },
  { text: "People sometimes tell me that I'm too stubborn.", scale: "ag", reversed: true },
  { text: "I am usually quite flexible in my opinions when people disagree with me.", scale: "ag", reversed: false },
  { text: "When people tell me that I'm wrong, my first reaction is to argue with them.", scale: "ag", reversed: true },

  // Conscientiousness (10 items)
  { text: "I plan ahead and organize things, to avoid scrambling at the last minute.", scale: "co", reversed: false },
  { text: "I often push myself very hard when trying to achieve a goal.", scale: "co", reversed: false },
  { text: "When working on something, I don't pay much attention to small details.", scale: "co", reversed: true },
  { text: "I make a lot of mistakes because I don't think before I act.", scale: "co", reversed: true },
  { text: "People often call me a perfectionist.", scale: "co", reversed: false },
  { text: "I prefer to do whatever comes to mind, rather than stick to a plan.", scale: "co", reversed: true },
  { text: "I do only the minimum amount of work needed to get by.", scale: "co", reversed: true },
  { text: "When working, I sometimes have difficulties due to being disorganized.", scale: "co", reversed: true },
  { text: "I always try to be accurate in my work, even at the expense of time.", scale: "co", reversed: false },
  { text: "When I have a deadline, I often leave things to the last minute.", scale: "co", reversed: true },

  // Openness to Experience (10 items)
  { text: "I would be quite bored by a visit to an art gallery.", scale: "op", reversed: true },
  { text: "I would enjoy creating a work of art, such as a novel, a song, or a painting.", scale: "op", reversed: false },
  { text: "If I had the opportunity, I would like to attend a classical music concert.", scale: "op", reversed: false },
  { text: "Sometimes I like to just watch the wind as it blows through the trees.", scale: "op", reversed: false },
  { text: "I enjoy looking at maps of different places.", scale: "op", reversed: false },
  { text: "I think of myself as a somewhat eccentric person.", scale: "op", reversed: false },
  { text: "I find it boring to discuss philosophy.", scale: "op", reversed: true },
  { text: "People have often told me that I have a good imagination.", scale: "op", reversed: false },
  { text: "I like people who have unconventional views.", scale: "op", reversed: false },
  { text: "I have never really enjoyed looking through an encyclopedia.", scale: "op", reversed: true },
];

const hexaco60: Instrument = {
  id: "hexaco-60",
  name: "HEXACO-60",
  shortName: "HEXACO",
  description:
    "6-factor personality model including Honesty-Humility, which is not measured by the Big Five. Provides a complementary perspective to NEO instruments.",
  citation:
    "Ashton, M. C., & Lee, K. (2009). The HEXACO-60: A short measure of the major dimensions of personality. Journal of Personality Assessment, 91, 340-345. IPIP items from ipip.ori.org.",
  itemCount: 60,
  estimatedMinutes: 8,
  scales: SCALES,
  items: ITEMS.map((item, idx) => ({
    id: `hexaco-${idx + 1}`,
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
    reversed: item.reversed,
  })),
};

registerInstrument(hexaco60, scoreLikert);

export default hexaco60;
