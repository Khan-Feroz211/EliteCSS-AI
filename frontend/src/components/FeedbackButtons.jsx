import { useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function FeedbackButtons({ messageId, onDone }) {
  const [status, setStatus] = useState("idle");

  const submitFeedback = async (rating) => {
    if (!messageId || status === "sending") return;

    setStatus("sending");
    try {
      const res = await fetch(`${API_BASE}/api/v1/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message_id: messageId,
          rating,
          comment: "",
        }),
      });

      if (!res.ok) throw new Error("Feedback failed");
      setStatus("sent");
      onDone?.(rating);
    } catch {
      setStatus("error");
    }
  };

  if (!messageId) return null;

  return (
    <div className="mt-2 flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
      <button
        onClick={() => submitFeedback(5)}
        className="rounded-md border border-emerald-600/40 bg-emerald-600/10 px-2 py-1 hover:bg-emerald-600/20"
      >
        + Helpful
      </button>
      <button
        onClick={() => submitFeedback(1)}
        className="rounded-md border border-rose-600/40 bg-rose-600/10 px-2 py-1 hover:bg-rose-600/20"
      >
        - Not helpful
      </button>
      {status === "sending" && <span>saving...</span>}
      {status === "sent" && <span className="text-emerald-400">saved</span>}
      {status === "error" && <span className="text-rose-400">retry</span>}
    </div>
  );
}
