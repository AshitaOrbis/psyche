import type { Instrument, InstrumentSession, InstrumentResult } from "./types";
import { registerInstrument } from "./registry";

/**
 * PHQ-9 (Patient Health Questionnaire) + GAD-7 (Generalized Anxiety Disorder)
 * Kroenke et al. (2001) / Spitzer et al. (2006)
 * Clinical screening tools for depression and anxiety.
 */

const PHQ9_ITEMS = [
  "Little interest or pleasure in doing things",
  "Feeling down, depressed, or hopeless",
  "Trouble falling or staying asleep, or sleeping too much",
  "Feeling tired or having little energy",
  "Poor appetite or overeating",
  "Feeling bad about yourself — or that you are a failure or have let yourself or your family down",
  "Trouble concentrating on things, such as reading the newspaper or watching television",
  "Moving or speaking so slowly that other people could have noticed? Or the opposite — being so fidgety or restless that you have been moving around a lot more than usual",
  "Thoughts that you would be better off dead or of hurting yourself in some way",
];

const GAD7_ITEMS = [
  "Feeling nervous, anxious, or on edge",
  "Not being able to stop or control worrying",
  "Worrying too much about different things",
  "Trouble relaxing",
  "Being so restless that it's hard to sit still",
  "Becoming easily annoyed or irritable",
  "Feeling afraid as if something awful might happen",
];

const phq9Gad7: Instrument = {
  id: "phq9-gad7",
  name: "PHQ-9 + GAD-7",
  shortName: "PHQ/GAD",
  description:
    "Brief screening tools for depression (PHQ-9) and generalized anxiety (GAD-7). Over the last 2 weeks, how often have you been bothered by the following?",
  citation:
    "Kroenke, K., Spitzer, R. L., & Williams, J. B. (2001). The PHQ-9. J Gen Intern Med, 16(9), 606-613.",
  itemCount: 16,
  estimatedMinutes: 3,
  scales: [
    { id: "phq9", name: "Depression (PHQ-9)" },
    { id: "gad7", name: "Anxiety (GAD-7)" },
  ],
  items: [
    ...PHQ9_ITEMS.map((text, idx) => ({
      id: `phq9-${idx + 1}`,
      text,
      response: {
        type: "likert" as const,
        min: 0,
        max: 3,
        labels: ["Not at all", "Several days", "More than half the days", "Nearly every day"],
      },
      scaleId: "phq9",
    })),
    ...GAD7_ITEMS.map((text, idx) => ({
      id: `gad7-${idx + 1}`,
      text,
      response: {
        type: "likert" as const,
        min: 0,
        max: 3,
        labels: ["Not at all", "Several days", "More than half the days", "Nearly every day"],
      },
      scaleId: "gad7",
    })),
  ],
};

/** PHQ-9 and GAD-7 use sum scoring (not mean) */
function scorePhqGad(instrument: Instrument, session: InstrumentSession): InstrumentResult {
  const responseMap = new Map(session.responses.map((r) => [r.itemId, r]));

  const phq9Sum = PHQ9_ITEMS.reduce((sum, _, idx) => {
    const r = responseMap.get(`phq9-${idx + 1}`);
    return sum + (typeof r?.value === "number" ? r.value : 0);
  }, 0);

  const gad7Sum = GAD7_ITEMS.reduce((sum, _, idx) => {
    const r = responseMap.get(`gad7-${idx + 1}`);
    return sum + (typeof r?.value === "number" ? r.value : 0);
  }, 0);

  return {
    instrumentId: instrument.id,
    completedAt: session.completedAt ?? Date.now(),
    scores: [
      {
        scaleId: "phq9",
        scaleName: "Depression (PHQ-9)",
        raw: phq9Sum,
        normalized: (phq9Sum / 27) * 100, // max = 9 items * 3
        itemCount: 9,
      },
      {
        scaleId: "gad7",
        scaleName: "Anxiety (GAD-7)",
        raw: gad7Sum,
        normalized: (gad7Sum / 21) * 100, // max = 7 items * 3
        itemCount: 7,
      },
    ],
  };
}

registerInstrument(phq9Gad7, scorePhqGad);

export default phq9Gad7;
