import type { Instrument, InstrumentSession, InstrumentResult } from "./types";

type ScoringFn = (
  instrument: Instrument,
  session: InstrumentSession
) => InstrumentResult;

interface RegisteredInstrument {
  instrument: Instrument;
  score: ScoringFn;
}

const registry = new Map<string, RegisteredInstrument>();

export function registerInstrument(
  instrument: Instrument,
  score: ScoringFn
): void {
  registry.set(instrument.id, { instrument, score });
}

export function getInstrument(id: string): RegisteredInstrument | undefined {
  return registry.get(id);
}

export function getAllInstruments(): RegisteredInstrument[] {
  return Array.from(registry.values());
}

export function getInstrumentIds(): string[] {
  return Array.from(registry.keys());
}
