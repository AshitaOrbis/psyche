import { useState } from "react";
import { usePsycheStore } from "./state/store";
import { getAllInstruments } from "./instruments/registry";
import { TestRunner } from "./components/TestRunner";
import { ResultsViewer } from "./components/ResultsViewer";
import { ProfileDashboard } from "./components/ProfileDashboard";

// Register instruments (side-effect imports)
import "./instruments/init";

type View = "instruments" | "dashboard";

function getInitialView(): View {
  return window.location.hash === "#dashboard" ? "dashboard" : "instruments";
}

export default function App() {
  const [view, setView] = useState<View>(getInitialView);
  const activeId = usePsycheStore((s) => s.activeInstrumentId);
  const results = usePsycheStore((s) => s.results);
  const sessions = usePsycheStore((s) => s.sessions);
  const startInstrument = usePsycheStore((s) => s.startInstrument);
  const resetInstrument = usePsycheStore((s) => s.resetInstrument);
  const exportData = usePsycheStore((s) => s.exportData);
  const importData = usePsycheStore((s) => s.importData);

  const instruments = getAllInstruments();

  // Active test in progress — always show TestRunner
  if (activeId) {
    return <TestRunner />;
  }

  // Profile Dashboard view
  if (view === "dashboard") {
    return (
      <div>
        <div style={{ maxWidth: 960, margin: "0 auto", padding: "1rem 2rem 0" }}>
          <button onClick={() => setView("instruments")} style={btnLink}>
            &larr; Back to Instruments
          </button>
        </div>
        <ProfileDashboard />
      </div>
    );
  }

  // Instruments view
  const handleExport = () => {
    const json = exportData();
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `psyche-data-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        if (typeof reader.result === "string") {
          importData(reader.result);
        }
      };
      reader.readAsText(file);
    };
    input.click();
  };

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: "2rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ marginBottom: "0.25rem" }}>Psyche</h1>
          <p style={{ color: "#6b7280", marginTop: 0 }}>
            Psychometric persona profiling framework
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button onClick={() => setView("dashboard")} style={btnPrimary}>
            Profile Dashboard
          </button>
          <button onClick={handleExport} style={btnSecondary}>
            Export JSON
          </button>
          <button onClick={handleImport} style={btnSecondary}>
            Import
          </button>
        </div>
      </div>

      <h2>Instrument Battery</h2>
      {instruments.length === 0 ? (
        <p>No instruments registered yet.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {instruments.map(({ instrument: inst }) => {
            const session = sessions[inst.id];
            const result = results[inst.id];
            const status = result
              ? "completed"
              : session
                ? "in-progress"
                : "not-started";

            return (
              <div
                key={inst.id}
                style={{
                  padding: "1rem 1.5rem",
                  border: "1px solid #e5e7eb",
                  borderRadius: "0.5rem",
                  borderLeft: `4px solid ${
                    status === "completed"
                      ? "#10b981"
                      : status === "in-progress"
                        ? "#f59e0b"
                        : "#d1d5db"
                  }`,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <strong>{inst.name}</strong>
                    <span style={{ color: "#9ca3af", marginLeft: "0.5rem" }}>
                      {inst.itemCount} items, ~{inst.estimatedMinutes} min
                    </span>
                  </div>
                  <div style={{ display: "flex", gap: "0.5rem" }}>
                    {status === "completed" && (
                      <button onClick={() => resetInstrument(inst.id)} style={btnSecondary}>
                        Retake
                      </button>
                    )}
                    {status !== "completed" && (
                      <button onClick={() => startInstrument(inst.id)} style={btnPrimary}>
                        {status === "in-progress" ? "Resume" : "Start"}
                      </button>
                    )}
                  </div>
                </div>
                <p style={{ fontSize: "0.875rem", color: "#6b7280", margin: "0.5rem 0 0" }}>
                  {inst.description}
                </p>
                {status === "in-progress" && session && (
                  <p style={{ fontSize: "0.75rem", color: "#f59e0b", margin: "0.25rem 0 0" }}>
                    {session.responses.length} of {inst.itemCount} answered
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Results section */}
      {Object.keys(results).length > 0 && (
        <div style={{ marginTop: "3rem" }}>
          <h2>Results</h2>
          {Object.values(results).map((result) => (
            <ResultsViewer key={result.instrumentId} result={result} />
          ))}
        </div>
      )}
    </div>
  );
}

const btnPrimary: React.CSSProperties = {
  padding: "0.5rem 1rem",
  background: "#2563eb",
  color: "#fff",
  border: "none",
  borderRadius: "0.375rem",
  cursor: "pointer",
  fontSize: "0.875rem",
  fontWeight: 500,
};

const btnSecondary: React.CSSProperties = {
  padding: "0.5rem 1rem",
  background: "transparent",
  color: "#374151",
  border: "1px solid #d1d5db",
  borderRadius: "0.375rem",
  cursor: "pointer",
  fontSize: "0.875rem",
};

const btnLink: React.CSSProperties = {
  padding: "0.25rem 0",
  background: "transparent",
  color: "#2563eb",
  border: "none",
  cursor: "pointer",
  fontSize: "0.875rem",
};
