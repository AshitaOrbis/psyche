import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  InstrumentSession,
  InstrumentResult,
  ItemResponse,
} from "../instruments/types";
import { getInstrument } from "../instruments/registry";

interface PsycheState {
  /** Active sessions keyed by instrument ID */
  sessions: Record<string, InstrumentSession>;
  /** Computed results keyed by instrument ID */
  results: Record<string, InstrumentResult>;
  /** Current instrument being taken */
  activeInstrumentId: string | null;
  /** Current item index within the active instrument */
  currentItemIndex: number;

  // Actions
  startInstrument: (instrumentId: string) => void;
  recordResponse: (response: ItemResponse) => void;
  advanceItem: () => void;
  goBackItem: () => void;
  completeInstrument: (result: InstrumentResult) => void;
  setActiveInstrument: (id: string | null) => void;
  resetInstrument: (instrumentId: string) => void;
  exportData: () => string;
  importData: (json: string) => void;
}

export const usePsycheStore = create<PsycheState>()(
  persist(
    (set, get) => ({
      sessions: {},
      results: {},
      activeInstrumentId: null,
      currentItemIndex: 0,

      startInstrument: (instrumentId) =>
        set((state) => ({
          activeInstrumentId: instrumentId,
          currentItemIndex: 0,
          sessions: {
            ...state.sessions,
            [instrumentId]: state.sessions[instrumentId] ?? {
              instrumentId,
              startedAt: Date.now(),
              responses: [],
            },
          },
        })),

      recordResponse: (response) =>
        set((state) => {
          const id = state.activeInstrumentId;
          if (!id) return state;
          const session = state.sessions[id];
          if (!session) return state;

          // Replace existing response for this item or append
          const existing = session.responses.findIndex(
            (r) => r.itemId === response.itemId
          );
          const responses = [...session.responses];
          if (existing >= 0) {
            responses[existing] = response;
          } else {
            responses.push(response);
          }

          return {
            sessions: {
              ...state.sessions,
              [id]: { ...session, responses },
            },
          };
        }),

      advanceItem: () =>
        set((state) => ({
          currentItemIndex: state.currentItemIndex + 1,
        })),

      goBackItem: () =>
        set((state) => ({
          currentItemIndex: Math.max(0, state.currentItemIndex - 1),
        })),

      completeInstrument: (result) =>
        set((state) => {
          const id = state.activeInstrumentId;
          if (!id) return state;
          const session = state.sessions[id];
          if (!session) return state;

          return {
            activeInstrumentId: null,
            currentItemIndex: 0,
            sessions: {
              ...state.sessions,
              [id]: { ...session, completedAt: Date.now() },
            },
            results: {
              ...state.results,
              [id]: result,
            },
          };
        }),

      setActiveInstrument: (id) =>
        set(() => ({
          activeInstrumentId: id,
          currentItemIndex: 0,
        })),

      resetInstrument: (instrumentId) =>
        set((state) => {
          const { [instrumentId]: _s, ...sessions } = state.sessions;
          const { [instrumentId]: _r, ...results } = state.results;
          return { sessions, results };
        }),

      exportData: () => {
        const { sessions, results } = get();
        return JSON.stringify({ sessions, results, exportedAt: Date.now() }, null, 2);
      },

      importData: (json) => {
        const data = JSON.parse(json);
        if (data.sessions && data.results) {
          // Merge with existing data (don't overwrite completed results)
          const currentState = get();
          const mergedSessions = { ...data.sessions, ...currentState.sessions };
          const mergedResults = { ...data.results, ...currentState.results };
          set({ sessions: mergedSessions, results: mergedResults });
          // Auto-score any sessions that have all responses but no result
          autoScoreCompleted();
        }
      },
    }),
    {
      name: "psyche-store",
      onRehydrateStorage: () => (state) => {
        // Always try to merge seed data (fills in any missing sessions/results)
        fetch("/seed-data.json")
          .then((r) => (r.ok ? r.json() : null))
          .then((data) => {
            if (data?.sessions) {
              const current = usePsycheStore.getState();
              const seedSessionCount = Object.keys(data.sessions).length;
              const currentSessionCount = Object.keys(current.sessions).length;
              if (seedSessionCount > currentSessionCount) {
                usePsycheStore.setState({
                  sessions: { ...data.sessions, ...current.sessions },
                  results: { ...(data.results ?? {}), ...current.results },
                });
              }
              autoScoreCompleted();
            }
          })
          .catch(() => {
            // No seed file or fetch failed — still auto-score existing data
            if (state) autoScoreCompleted();
          });
      },
    }
  )
);

/** Score any sessions that have all responses but no result yet. */
function autoScoreCompleted(): void {
  const { sessions, results } = usePsycheStore.getState();
  const newResults: Record<string, InstrumentResult> = {};

  for (const [id, session] of Object.entries(sessions)) {
    if (results[id]) continue; // already scored
    const registered = getInstrument(id);
    if (!registered) continue; // instrument not in registry
    const { instrument, score } = registered;
    if (session.responses.length >= instrument.items.length) {
      try {
        newResults[id] = score(instrument, session);
      } catch {
        // scoring failed — skip
      }
    }
  }

  if (Object.keys(newResults).length > 0) {
    const current = usePsycheStore.getState();
    usePsycheStore.setState({
      results: { ...current.results, ...newResults },
      sessions: Object.fromEntries(
        Object.entries(current.sessions).map(([id, s]) =>
          newResults[id] ? [id, { ...s, completedAt: s.completedAt ?? Date.now() }] : [id, s]
        )
      ),
    });
  }
}
