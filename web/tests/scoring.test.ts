import { describe, it, expect } from "vitest";
import { scoreLikert } from "../src/scoring/engine";
import type { Instrument, InstrumentSession } from "../src/instruments/types";

function makeInstrument(items: { id: string; scaleId: string; reversed?: boolean }[]): Instrument {
  return {
    id: "test",
    name: "Test",
    shortName: "T",
    description: "",
    citation: "",
    itemCount: items.length,
    estimatedMinutes: 1,
    scales: [
      { id: "A", name: "Scale A" },
      { id: "B", name: "Scale B" },
    ],
    items: items.map((i) => ({
      ...i,
      text: "test item",
      response: { type: "likert" as const, min: 1, max: 5, labels: [] },
    })),
  };
}

describe("scoreLikert", () => {
  it("computes mean score for a scale", () => {
    const inst = makeInstrument([
      { id: "a1", scaleId: "A" },
      { id: "a2", scaleId: "A" },
      { id: "b1", scaleId: "B" },
    ]);

    const session: InstrumentSession = {
      instrumentId: "test",
      startedAt: 0,
      responses: [
        { itemId: "a1", value: 4, timestamp: 0 },
        { itemId: "a2", value: 2, timestamp: 0 },
        { itemId: "b1", value: 5, timestamp: 0 },
      ],
    };

    const result = scoreLikert(inst, session);
    const scaleA = result.scores.find((s) => s.scaleId === "A")!;
    const scaleB = result.scores.find((s) => s.scaleId === "B")!;

    expect(scaleA.raw).toBe(3); // (4+2)/2
    expect(scaleA.normalized).toBe(50); // (3-1)/(5-1)*100
    expect(scaleA.itemCount).toBe(2);
    expect(scaleB.raw).toBe(5);
    expect(scaleB.normalized).toBe(100);
  });

  it("reverse scores items", () => {
    const inst = makeInstrument([
      { id: "a1", scaleId: "A" },
      { id: "a2", scaleId: "A", reversed: true },
    ]);

    const session: InstrumentSession = {
      instrumentId: "test",
      startedAt: 0,
      responses: [
        { itemId: "a1", value: 5, timestamp: 0 }, // straight: 5
        { itemId: "a2", value: 5, timestamp: 0 }, // reversed: 1+5-5 = 1
      ],
    };

    const result = scoreLikert(inst, session);
    const scaleA = result.scores.find((s) => s.scaleId === "A")!;

    // Mean of (5 + 1) / 2 = 3
    expect(scaleA.raw).toBe(3);
    expect(scaleA.normalized).toBe(50);
  });

  it("handles missing responses gracefully", () => {
    const inst = makeInstrument([
      { id: "a1", scaleId: "A" },
      { id: "a2", scaleId: "A" },
    ]);

    const session: InstrumentSession = {
      instrumentId: "test",
      startedAt: 0,
      responses: [{ itemId: "a1", value: 4, timestamp: 0 }],
    };

    const result = scoreLikert(inst, session);
    const scaleA = result.scores.find((s) => s.scaleId === "A")!;

    // Only one response, mean is just that value
    expect(scaleA.raw).toBe(4);
    expect(scaleA.itemCount).toBe(1);
  });
});
