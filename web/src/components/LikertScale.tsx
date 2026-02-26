import { useCallback, useEffect } from "react";

interface LikertScaleProps {
  min: number;
  max: number;
  labels: string[];
  value: number | null;
  onChange: (value: number) => void;
}

export function LikertScale({ min, max, labels, value, onChange }: LikertScaleProps) {
  const options = Array.from({ length: max - min + 1 }, (_, i) => min + i);

  const handleKeyPress = useCallback(
    (e: KeyboardEvent) => {
      const num = parseInt(e.key);
      if (num >= min && num <= max) {
        onChange(num);
      }
    },
    [min, max, onChange]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyPress);
    return () => window.removeEventListener("keydown", handleKeyPress);
  }, [handleKeyPress]);

  return (
    <div style={{ display: "flex", gap: "0.5rem", justifyContent: "center", flexWrap: "wrap" }}>
      {options.map((opt, idx) => {
        const isSelected = value === opt;
        const label = labels[idx] ?? String(opt);

        return (
          <button
            key={opt}
            onClick={() => onChange(opt)}
            style={{
              padding: "0.75rem 1.25rem",
              border: isSelected ? "2px solid #2563eb" : "2px solid #d1d5db",
              borderRadius: "0.5rem",
              background: isSelected ? "#2563eb" : "#fff",
              color: isSelected ? "#fff" : "#374151",
              cursor: "pointer",
              fontSize: "0.875rem",
              fontWeight: isSelected ? 600 : 400,
              minWidth: "120px",
              transition: "all 0.15s",
            }}
          >
            <div style={{ fontSize: "1.25rem", fontWeight: 700 }}>{opt}</div>
            <div style={{ fontSize: "0.75rem", marginTop: "0.25rem" }}>{label}</div>
          </button>
        );
      })}
    </div>
  );
}
