import { useCallback, useEffect, useState } from "react";
import { usePsycheStore } from "../state/store";
import { getInstrument } from "../instruments/registry";
import { LikertScale } from "./LikertScale";
import { ProgressBar } from "./ProgressBar";

export function TestRunner() {
  const activeId = usePsycheStore((s) => s.activeInstrumentId);
  const currentIndex = usePsycheStore((s) => s.currentItemIndex);
  const sessions = usePsycheStore((s) => s.sessions);
  const recordResponse = usePsycheStore((s) => s.recordResponse);
  const advanceItem = usePsycheStore((s) => s.advanceItem);
  const goBackItem = usePsycheStore((s) => s.goBackItem);
  const completeInstrument = usePsycheStore((s) => s.completeInstrument);
  const setActiveInstrument = usePsycheStore((s) => s.setActiveInstrument);

  const registered = activeId ? getInstrument(activeId) : undefined;
  const instrument = registered?.instrument;
  const scoreFn = registered?.score;
  const session = activeId ? sessions[activeId] : undefined;

  const currentItem = instrument?.items[currentIndex];
  const totalItems = instrument?.itemCount ?? 0;
  const answeredCount = session?.responses.length ?? 0;

  // Get existing response for current item
  const existingResponse = currentItem
    ? session?.responses.find((r) => r.itemId === currentItem.id)
    : undefined;

  // Local state for text/numeric inputs
  const [textValue, setTextValue] = useState("");
  const [numericValue, setNumericValue] = useState("");

  // Sync local state with existing response when item changes
  useEffect(() => {
    if (existingResponse) {
      if (typeof existingResponse.value === "string") {
        setTextValue(existingResponse.value);
        setNumericValue("");
      } else if (typeof existingResponse.value === "number") {
        setNumericValue(String(existingResponse.value));
        setTextValue("");
      }
    } else {
      setTextValue("");
      setNumericValue("");
    }
  }, [existingResponse, currentIndex]);

  const handleLikertResponse = useCallback(
    (value: number) => {
      if (!currentItem) return;
      recordResponse({
        itemId: currentItem.id,
        value,
        timestamp: Date.now(),
      });

      // Auto-advance after a brief delay
      setTimeout(() => {
        if (currentIndex < totalItems - 1) {
          advanceItem();
        }
      }, 200);
    },
    [currentItem, currentIndex, totalItems, recordResponse, advanceItem]
  );

  const handleBinaryResponse = useCallback(
    (value: number) => {
      if (!currentItem) return;
      recordResponse({
        itemId: currentItem.id,
        value,
        timestamp: Date.now(),
      });

      // Auto-advance after a brief delay
      setTimeout(() => {
        if (currentIndex < totalItems - 1) {
          advanceItem();
        }
      }, 200);
    },
    [currentItem, currentIndex, totalItems, recordResponse, advanceItem]
  );

  // Binary keyboard handler (T/F or 1/2)
  useEffect(() => {
    if (!currentItem || currentItem.response.type !== "binary") return;
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") return;
      const key = e.key.toLowerCase();
      if (key === "t" || key === "1") {
        e.preventDefault();
        handleBinaryResponse(1);
      } else if (key === "f" || key === "2") {
        e.preventDefault();
        handleBinaryResponse(0);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [currentItem, handleBinaryResponse]);

  const handleTextSubmit = useCallback(() => {
    if (!currentItem) return;
    const value = currentItem.response.type === "numeric" ? numericValue : textValue;
    if (!value.trim()) return;

    recordResponse({
      itemId: currentItem.id,
      value: currentItem.response.type === "numeric" ? Number(value) : value,
      timestamp: Date.now(),
    });

    if (currentIndex < totalItems - 1) {
      advanceItem();
    }
  }, [currentItem, textValue, numericValue, currentIndex, totalItems, recordResponse, advanceItem]);

  // Arrow key navigation (only for non-text inputs)
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Don't capture keys when typing in a text input
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") return;

      if (e.key === "ArrowLeft" || e.key === "Backspace") {
        e.preventDefault();
        goBackItem();
      }
      if (e.key === "ArrowRight" && existingResponse) {
        e.preventDefault();
        if (currentIndex < totalItems - 1) {
          advanceItem();
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [goBackItem, advanceItem, currentIndex, totalItems, existingResponse]);

  if (!instrument || !activeId || !session) {
    return null;
  }

  // All items answered — show completion
  if (currentIndex >= totalItems) {
    const allAnswered = answeredCount >= totalItems;

    return (
      <div style={{ maxWidth: 600, margin: "0 auto", padding: "2rem", textAlign: "center" }}>
        <h2>{instrument.name}</h2>
        <ProgressBar current={answeredCount} total={totalItems} />
        {allAnswered ? (
          <>
            <p>All {totalItems} items completed!</p>
            <button
              onClick={() => {
                if (scoreFn) {
                  const result = scoreFn(instrument, session);
                  completeInstrument(result);
                }
              }}
              style={{
                padding: "0.75rem 2rem",
                background: "#2563eb",
                color: "#fff",
                border: "none",
                borderRadius: "0.5rem",
                fontSize: "1rem",
                cursor: "pointer",
                marginTop: "1rem",
              }}
            >
              Calculate Scores
            </button>
          </>
        ) : (
          <p>
            {answeredCount} of {totalItems} answered. Go back to complete remaining items.
          </p>
        )}
        <button
          onClick={() => setActiveInstrument(null)}
          style={{
            padding: "0.5rem 1rem",
            background: "transparent",
            border: "1px solid #d1d5db",
            borderRadius: "0.5rem",
            cursor: "pointer",
            marginTop: "1rem",
            marginLeft: "0.5rem",
          }}
        >
          Back to Dashboard
        </button>
      </div>
    );
  }

  if (!currentItem) return null;

  // Context-appropriate instruction text
  const instructionText =
    currentItem.response.type === "likert"
      ? "How accurately does this describe you?"
      : currentItem.response.type === "binary"
        ? "Is this true or false for you?"
        : currentItem.response.type === "numeric"
          ? "Enter your answer:"
          : "Write your response:";

  const hintText =
    currentItem.response.type === "likert"
      ? `Press 1-${currentItem.response.max} or click to answer`
      : currentItem.response.type === "binary"
        ? "Press T/1 for True, F/2 for False"
        : currentItem.response.type === "numeric"
          ? "Type a number and press Enter"
          : "Write freely, then click Next";

  return (
    <div style={{ maxWidth: 700, margin: "0 auto", padding: "2rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>{instrument.shortName}</h2>
        <button
          onClick={() => setActiveInstrument(null)}
          style={{
            padding: "0.25rem 0.75rem",
            background: "transparent",
            border: "1px solid #d1d5db",
            borderRadius: "0.25rem",
            cursor: "pointer",
            fontSize: "0.875rem",
          }}
        >
          Save & Exit
        </button>
      </div>

      <ProgressBar
        current={answeredCount}
        total={totalItems}
        label={`Question ${currentIndex + 1} of ${totalItems}`}
      />

      <div
        style={{
          textAlign: "center",
          padding: "2rem 1rem",
          marginBottom: "1.5rem",
        }}
      >
        <p style={{ fontSize: "0.875rem", color: "#6b7280", marginBottom: "0.5rem" }}>
          {instructionText}
        </p>
        <p style={{ fontSize: "1.5rem", fontWeight: 500, margin: "1rem 0 2rem" }}>
          {currentItem.text}
        </p>

        {/* Likert response */}
        {currentItem.response.type === "likert" && (
          <LikertScale
            min={currentItem.response.min}
            max={currentItem.response.max}
            labels={currentItem.response.labels}
            value={typeof existingResponse?.value === "number" ? existingResponse.value : null}
            onChange={handleLikertResponse}
          />
        )}

        {/* Binary response (True/False) */}
        {currentItem.response.type === "binary" && (
          <div style={{ display: "flex", gap: "1rem", justifyContent: "center" }}>
            {currentItem.response.labels.map((label, idx) => {
              const btnValue = idx === 0 ? 1 : 0;
              const isSelected = existingResponse?.value === btnValue;
              return (
                <button
                  key={label}
                  onClick={() => handleBinaryResponse(btnValue)}
                  style={{
                    padding: "1rem 2.5rem",
                    border: isSelected ? "2px solid #2563eb" : "2px solid #d1d5db",
                    borderRadius: "0.5rem",
                    background: isSelected ? "#2563eb" : "#fff",
                    color: isSelected ? "#fff" : "#374151",
                    cursor: "pointer",
                    fontSize: "1.125rem",
                    fontWeight: isSelected ? 600 : 400,
                    minWidth: "140px",
                    transition: "all 0.15s",
                  }}
                >
                  <div style={{ fontSize: "0.75rem", color: isSelected ? "#dbeafe" : "#9ca3af" }}>
                    {idx === 0 ? "T / 1" : "F / 2"}
                  </div>
                  <div>{label}</div>
                </button>
              );
            })}
          </div>
        )}

        {/* Numeric response */}
        {currentItem.response.type === "numeric" && (
          <div>
            <input
              type="number"
              value={numericValue}
              onChange={(e) => setNumericValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleTextSubmit();
              }}
              autoFocus
              style={{
                fontSize: "1.5rem",
                padding: "0.5rem 1rem",
                border: "2px solid #d1d5db",
                borderRadius: "0.5rem",
                textAlign: "center",
                width: "200px",
              }}
            />
            <br />
            <button onClick={handleTextSubmit} style={{ ...btnNext, marginTop: "1rem" }}>
              Next
            </button>
          </div>
        )}

        {/* Text response */}
        {currentItem.response.type === "text" && (
          <div style={{ textAlign: "left" }}>
            <textarea
              value={textValue}
              onChange={(e) => setTextValue(e.target.value)}
              rows={8}
              autoFocus
              style={{
                width: "100%",
                fontSize: "1rem",
                padding: "0.75rem",
                border: "2px solid #d1d5db",
                borderRadius: "0.5rem",
                resize: "vertical",
                fontFamily: "inherit",
              }}
            />
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginTop: "0.5rem",
              }}
            >
              <span style={{ fontSize: "0.75rem", color: "#9ca3af" }}>
                {textValue.trim().split(/\s+/).filter(Boolean).length} words
                {currentItem.response.type === "text" && currentItem.response.minWords
                  ? ` (min ${currentItem.response.minWords})`
                  : ""}
              </span>
              <button onClick={handleTextSubmit} style={btnNext}>
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: "0.75rem",
          color: "#9ca3af",
        }}
      >
        <span>{currentIndex > 0 ? "← Backspace/Left to go back" : ""}</span>
        <span>{hintText}</span>
        <span>{existingResponse ? "→ Right to skip forward" : ""}</span>
      </div>
    </div>
  );
}

const btnNext: React.CSSProperties = {
  padding: "0.5rem 1.5rem",
  background: "#2563eb",
  color: "#fff",
  border: "none",
  borderRadius: "0.375rem",
  cursor: "pointer",
  fontSize: "0.875rem",
  fontWeight: 500,
};
