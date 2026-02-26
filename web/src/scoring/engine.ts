import type {
  Instrument,
  InstrumentSession,
  InstrumentResult,
  ScaleScore,
  Item,
  ItemResponse,
} from "../instruments/types";

/**
 * Generic binary (True/False) scoring engine.
 * True = 1, False = 0; reverse scoring supported.
 */
export function scoreBinary(
  instrument: Instrument,
  session: InstrumentSession
): InstrumentResult {
  const responseMap = new Map<string, ItemResponse>();
  for (const r of session.responses) {
    responseMap.set(r.itemId, r);
  }

  const scaleItems = new Map<string, { item: Item; value: number }[]>();

  for (const item of instrument.items) {
    const resp = responseMap.get(item.id);
    if (!resp || typeof resp.value !== "number") continue;

    let value = resp.value; // 1 = first label (True), 0 = second label (False)
    if (item.reversed) {
      value = 1 - value;
    }

    const existing = scaleItems.get(item.scaleId) ?? [];
    existing.push({ item, value });
    scaleItems.set(item.scaleId, existing);
  }

  const scores: ScaleScore[] = [];
  for (const scale of instrument.scales) {
    const items = scaleItems.get(scale.id);
    if (!items || items.length === 0) continue;

    const raw = items.reduce((sum, i) => sum + i.value, 0) / items.length;
    const normalized = raw * 100; // 0-1 → 0-100

    scores.push({
      scaleId: scale.id,
      scaleName: scale.name,
      raw,
      normalized,
      itemCount: items.length,
    });
  }

  return {
    instrumentId: instrument.id,
    completedAt: session.completedAt ?? Date.now(),
    scores,
  };
}

/**
 * Generic Likert scoring engine.
 * Handles reverse scoring, scale aggregation, and normalization.
 */
export function scoreLikert(
  instrument: Instrument,
  session: InstrumentSession
): InstrumentResult {
  const responseMap = new Map<string, ItemResponse>();
  for (const r of session.responses) {
    responseMap.set(r.itemId, r);
  }

  const scaleItems = new Map<string, { item: Item; value: number }[]>();

  for (const item of instrument.items) {
    const resp = responseMap.get(item.id);
    if (!resp || typeof resp.value !== "number") continue;

    let value = resp.value;
    if (item.reversed && item.response.type === "likert") {
      const { min, max } = item.response;
      value = max + min - value;
    }

    const existing = scaleItems.get(item.scaleId) ?? [];
    existing.push({ item, value });
    scaleItems.set(item.scaleId, existing);
  }

  const scores: ScaleScore[] = [];
  for (const scale of instrument.scales) {
    const items = scaleItems.get(scale.id);
    if (!items || items.length === 0) continue;

    const raw = items.reduce((sum, i) => sum + i.value, 0) / items.length;

    // Normalize assuming all items share the same response format
    const firstItem = instrument.items.find((i) => i.scaleId === scale.id);
    let normalized = raw;
    if (firstItem?.response.type === "likert") {
      const { min, max } = firstItem.response;
      normalized = ((raw - min) / (max - min)) * 100;
    }

    scores.push({
      scaleId: scale.id,
      scaleName: scale.name,
      raw,
      normalized,
      itemCount: items.length,
    });
  }

  return {
    instrumentId: instrument.id,
    completedAt: session.completedAt ?? Date.now(),
    scores,
  };
}
