import type { ReactNode } from "react";
import type { Note, Span } from "../types";

/** Text with highlighter marks. Each mark carries the number of its margin note. */
export function Marked({ text, spans, notes }: { text: string; spans: Span[]; notes: Note[] }) {
  const kind = new Map(notes.map((n) => [n.n, n.kind]));
  const parts: ReactNode[] = [];
  let at = 0;
  spans.forEach((s, i) => {
    if (s.start > at) parts.push(text.slice(at, s.start));
    parts.push(
      <mark key={i} className={`mark mark-${kind.get(s.note) ?? "r1"}`}>
        {text.slice(s.start, s.end)}
        <sup className="note-ref">{s.note}</sup>
      </mark>,
    );
    at = s.end;
  });
  if (at < text.length) parts.push(text.slice(at));
  return <>{parts}</>;
}

export function MarginNotes({ notes }: { notes: Note[] }) {
  if (notes.length === 0) return null;
  return (
    <ol className="margin-notes">
      {notes.map((n) => (
        <li key={n.n} value={n.n}>
          {n.text}
        </li>
      ))}
    </ol>
  );
}

/** Report sentences quote identifiers in `backticks`; show those as code. */
export function Ticks({ text }: { text: string }) {
  return (
    <>
      {text.split("`").map((part, i) => (i % 2 === 1 ? <code key={i}>{part}</code> : part))}
    </>
  );
}