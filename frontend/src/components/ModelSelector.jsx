const MODEL_OPTIONS = [
  { value: "gpt", label: "GPT-4o-mini", icon: "◉" },
  { value: "claude", label: "Claude", icon: "◈" },
  { value: "gemini", label: "Gemini", icon: "◎" },
];

export default function ModelSelector({ value, onChange }) {
  return (
    <div className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white/80 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900/80">
      <span className="text-slate-600 dark:text-slate-400">Model</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-slate-800 outline-none dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
      >
        {MODEL_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.icon} {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
