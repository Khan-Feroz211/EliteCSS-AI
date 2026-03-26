export default function StreamingMessage({ text }) {
  return (
    <span>
      {text}
      <span className="ml-1 inline-block h-4 w-[2px] animate-pulse bg-cyan-400 align-middle" />
    </span>
  );
}
