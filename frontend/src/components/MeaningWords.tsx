import type { ReactNode } from "react";
import { num } from "../format";
import type { WordsStep } from "../types";

/** Docstring with each word tinted by how much it moved the encoder's meaning score. */
function Heat({ text, words }: { text: string; words: WordsStep }) {
  const max = Math.max(1e-9, ...words.words.map((w) => Math.abs(w.weight)));
  const parts: ReactNode[] = [];
  let at = 0;
  words.words.forEach((w, i) => {
    if (w.start > at) parts.push(text.slice(at, w.start));
    const a = Math.abs(w.weight) / max;
    const style =
      a < 0.08
        ? undefined
        : { background: w.weight < 0 ? `rgba(244, 63, 94, ${0.1 + 0.45 * a})` : `rgba(16, 185, 129, ${0.1 + 0.4 * a})` };
    parts.push(
      <span key={i} className="heat-word" style={style} title={`${num(w.weight, 4, true)} to the meaning score`}>
        {text.slice(w.start, w.end)}
      </span>,
    );
    at = w.end;
  });
  if (at < text.length) parts.push(text.slice(at));
  return <pre className="code heat">{parts}</pre>;
}

export function MeaningWords({
  words,
  documentation,
  onExplainWords,
  busy,
}: {
  words: WordsStep | null | undefined;
  documentation: string;
  onExplainWords?: () => void;
  busy?: boolean;
}) {
  return (
    <>
      <p className="lead">
        The deep-learning signal is one number: how much closer the docstring's meaning is to the new code than to the old
        code. To see what drove it, each word is removed in turn and the docstring is encoded again.
      </p>
      {words ? (
        <>
          <Heat text={documentation} words={words} />
          <p className="caption">
            Meaning score for the full docstring {num(words.delta, 4, true)}; {words.passes} passes through {words.model}. Red
            words pulled the docstring toward the old code; green words toward the new code. Hover a word for its effect.
          </p>
          <dl className="sets">
            {words.toward_stale.length > 0 && (
              <>
                <dt>Pulled most toward the old code</dt>
                <dd>
                  <code className="set">{words.toward_stale.join(", ")}</code>
                </dd>
              </>
            )}
            {words.toward_fits.length > 0 && (
              <>
                <dt>Pulled most toward the new code</dt>
                <dd>
                  <code className="set">{words.toward_fits.join(", ")}</code>
                </dd>
              </>
            )}
          </dl>
        </>
      ) : (
        onExplainWords && (
          <button type="button" className="text-button no-print" onClick={onExplainWords} disabled={busy}>
            {busy ? "Encoding each variant…" : "Show which words mattered"}
          </button>
        )
      )}
    </>
  );
}
