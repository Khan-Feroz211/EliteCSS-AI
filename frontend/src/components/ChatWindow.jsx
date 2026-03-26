import { useEffect, useMemo, useRef } from "react";

import FeedbackButtons from "./FeedbackButtons";
import StreamingMessage from "./StreamingMessage";

function getLabel(model) {
  if (model === "gpt") return "GPT-4o-mini";
  if (model === "claude") return "Claude";
  if (model === "gemini") return "Gemini";
  return "Assistant";
}

export default function ChatWindow({ messages, onFeedback }) {
  const endRef = useRef(null);

  const visibleMessages = useMemo(
    () => messages.filter((msg) => msg.role !== "system"),
    [messages],
  );

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [visibleMessages]);

  return (
    <div className="chat-scroll h-[55vh] overflow-y-auto rounded-2xl border border-slate-300 bg-white/70 p-4 shadow-2xl dark:border-slate-700 dark:bg-slate-900/70">
      <div className="space-y-4">
        {visibleMessages.length === 0 && (
          <div className="rounded-xl border border-slate-300 bg-white/70 p-4 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900/70 dark:text-slate-400">
            Start by asking a CSS prep question. Your conversation will persist across refreshes.
          </div>
        )}

        {visibleMessages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm md:max-w-[70%] ${
                msg.role === "user"
                  ? "bg-cyan-500 text-slate-950"
                  : "border border-slate-300 bg-white/95 text-slate-800 dark:border-slate-700 dark:bg-slate-800/90 dark:text-slate-100"
              }`}
            >
              {msg.role === "assistant" && (
                <div className="mb-2 text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">{getLabel(msg.model)}</div>
              )}

              <div className="whitespace-pre-wrap leading-6">
                {msg.streaming ? <StreamingMessage text={msg.content} /> : msg.content}
              </div>

              {msg.role === "assistant" && !msg.streaming && (
                <FeedbackButtons messageId={msg.messageId} onDone={(rating) => onFeedback(msg.id, rating)} />
              )}
            </div>
          </div>
        ))}
      </div>
      <div ref={endRef} />
    </div>
  );
}
