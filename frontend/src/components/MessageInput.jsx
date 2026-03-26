const MAX_LEN = 2000;

export default function MessageInput({ value, onChange, onSend, disabled }) {
  const remaining = MAX_LEN - value.length;

  return (
    <div className="rounded-2xl border border-slate-300 bg-white/90 p-3 shadow-xl dark:border-slate-700 dark:bg-slate-900/90">
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value.slice(0, MAX_LEN))}
        rows={4}
        placeholder="Ask about Pakistan Affairs, History, Current Affairs, Essay, or General Knowledge..."
        className="w-full resize-none rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-slate-800 outline-none placeholder:text-slate-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
      />
      <div className="mt-2 flex items-center justify-between">
        <span className={`text-xs ${remaining < 200 ? "text-amber-400" : "text-slate-500"}`}>
          {value.length}/2000
        </span>
        <button
          onClick={onSend}
          disabled={disabled || value.trim().length === 0}
          className="rounded-xl bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
        >
          {disabled ? "Streaming..." : "Send"}
        </button>
      </div>
    </div>
  );
}
