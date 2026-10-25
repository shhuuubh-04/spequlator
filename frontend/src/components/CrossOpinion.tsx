import type { ReactNode } from "react";
import { num } from "../format";
import type { CrossStep } from "../types";

/** Docstring with each word tinted by how much it moved the cross-encoder's score. */
function Heat({ text, cross }: { text: string; cross: CrossStep }) {
  const max = Math.max(1e-9, ...cross.words.map((w) => Math.abs(w.weight)));
  const parts: ReactNode[] = [];
  let at = 0;
  cross.words.forEach((w, i) => {
    if (w.start > at) parts.push(text.slice(at, w.start));
    const a = Math.abs(w.weight) / max;
    const style =
      a < 0.08
        ? undefined
        : { background: w.weight < 0 ? `rgba(244, 63, 94, ${0.1 + 0.45 * a})` : `rgba(16, 185, 129, ${0.1 + 0.4 * a})` };
    parts.push(
      <span key={i} className="heat-word" style={style} title={`${num(w.weight, 3, true)} if removed`}>
        {text.slice(w.start, w.end)}
      </span>,
    );
    at = w.end;
  });
  if (at < text.length) parts.push(text.slice(at));
  return <pre className="code heat">{parts}</pre>;
}

export function CrossOpinion({
  cross,
  documentation,
  onExplainWords,
  busy,
}: {
  cross: CrossStep;
  documentation: string;
  onExplainWords?: () => void;
  busy?: boolean;
}) {
  const hasWords = cross.words.length > 0;
  return (
    <>
      <p className="lead">
        A second deep-learning model, added in phase 2. It reads the docstring and the code change together in one pass and
        was trained to tell the docstring the authors replaced from the one they wrote. It is shown beside the finding; it
        does not change it.
      </p>
      <div className="cross-score">
        <span className={`finding finding-${cross.lean === "fits" ? "no_obvious_drift" : "potential_drift"}`}>
          {cross.lean === "fits" ? "Leans: fits the new code" : "Leans: looks stale"}
        </span>
        <span className="num">score {num(cross.score, 2, true)}</span>
        <span className="muted">above 0 leans "fits", below 0 leans "stale"; a model score, not a probability</span>
      </div>

      {hasWords ? (
        <>
          <Heat text={documentation} cross={cross} />
          <p className="caption">
            Each word was removed in turn and the docstring scored again ({cross.passes} passes through the model). Red words
            pushed the score toward "stale"; green words toward "fits". Hover a word for its effect.
          </p>
          <dl className="sets">
            {cross.toward_stale.length > 0 && (
              <>
                <dt>Pushed most toward "stale"</dt>
                <dd>
                  <code className="set">{cross.toward_stale.join(", ")}</code>
                </dd>
              </>
            )}
            {cross.toward_fits.length > 0 && (
              <>
                <dt>Pushed most toward "fits"</dt>
                <dd>
                  <code className="set">{cross.toward_fits.join(", ")}</code>
                </dd>
              </>
            )}
          </dl>
        </>
      ) : (
        onExplainWords && (
          <button type="button" className="text-button no-print" onClick={onExplainWords} disabled={busy}>
            {busy ? "Scoring each word…" : "Show which words mattered"}
          </button>
        )
      )}
      <p className="caption">Model: {cross.model}. Input: {cross.input_format === "diff" ? "changed lines, then the new code" : "old code, then new code"}, up to {cross.max_len} tokens.</p>
    </>
  );
}