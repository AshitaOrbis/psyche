interface ProgressBarProps {
  current: number;
  total: number;
  label?: string;
}

export function ProgressBar({ current, total, label }: ProgressBarProps) {
  const pct = total > 0 ? Math.round((current / total) * 100) : 0;

  return (
    <div style={{ marginBottom: "1.5rem" }}>
      {label && (
        <div style={{ fontSize: "0.875rem", color: "#6b7280", marginBottom: "0.25rem" }}>
          {label}
        </div>
      )}
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
        <div
          style={{
            flex: 1,
            height: "8px",
            background: "#e5e7eb",
            borderRadius: "4px",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              width: `${pct}%`,
              height: "100%",
              background: "#2563eb",
              borderRadius: "4px",
              transition: "width 0.3s ease",
            }}
          />
        </div>
        <span style={{ fontSize: "0.875rem", color: "#374151", minWidth: "80px" }}>
          {current} / {total} ({pct}%)
        </span>
      </div>
    </div>
  );
}
