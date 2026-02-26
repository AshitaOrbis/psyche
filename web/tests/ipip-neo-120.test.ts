import { describe, it, expect } from "vitest";
import "../src/instruments/ipip-neo-120";
import { getInstrument } from "../src/instruments/registry";
import type { InstrumentSession, ItemResponse } from "../src/instruments/types";

describe("IPIP-NEO-120 instrument", () => {
  const registered = getInstrument("ipip-neo-120")!;
  const { instrument, score } = registered;

  it("is registered with correct metadata", () => {
    expect(instrument).toBeDefined();
    expect(instrument.id).toBe("ipip-neo-120");
    expect(instrument.itemCount).toBe(120);
    expect(instrument.items).toHaveLength(120);
  });

  it("has 5 domain scales and 30 facet scales", () => {
    const domains = instrument.scales.filter((s) => !s.parentId);
    const facets = instrument.scales.filter((s) => s.parentId);
    expect(domains).toHaveLength(5);
    expect(facets).toHaveLength(30);
  });

  it("each facet has exactly 4 items", () => {
    const facetItemCounts = new Map<string, number>();
    for (const item of instrument.items) {
      facetItemCounts.set(item.scaleId, (facetItemCounts.get(item.scaleId) ?? 0) + 1);
    }
    for (const [facetId, count] of facetItemCounts) {
      expect(count, `Facet ${facetId} should have 4 items`).toBe(4);
    }
  });

  it("scores all 5 domains on neutral responses", () => {
    const responses: ItemResponse[] = instrument.items.map((item) => ({
      itemId: item.id,
      value: 3, // neutral
      timestamp: 0,
    }));

    const session: InstrumentSession = {
      instrumentId: "ipip-neo-120",
      startedAt: 0,
      completedAt: 1,
      responses,
    };

    const result = score(instrument, session);

    // Should have 5 domain + 30 facet scores
    expect(result.scores).toHaveLength(35);

    // All domain scores should be ~50 (neutral)
    const domains = result.scores.filter((s) => s.scaleId.length === 1);
    expect(domains).toHaveLength(5);

    for (const d of domains) {
      expect(d.normalized).toBeCloseTo(50, 0);
    }
  });

  it("scores high on all-5 responses", () => {
    const responses: ItemResponse[] = instrument.items.map((item) => ({
      itemId: item.id,
      value: 5, // max agreement
      timestamp: 0,
    }));

    const session: InstrumentSession = {
      instrumentId: "ipip-neo-120",
      startedAt: 0,
      completedAt: 1,
      responses,
    };

    const result = score(instrument, session);
    const domains = result.scores.filter((s) => s.scaleId.length === 1);

    // Reversed items will get low scores, so domains won't be 100
    // But unreversed facets should be 100
    for (const d of domains) {
      // Should be somewhere between 0-100, not all 100 due to reverse coding
      expect(d.normalized).toBeGreaterThan(0);
      expect(d.normalized).toBeLessThanOrEqual(100);
    }
  });
});
