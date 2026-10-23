import { useState } from "react";
import { FINDING_LABEL, num } from "../format";
import type { DiffLine, Explained, Note } from "../types";
import { MarginNotes, Marked, Ticks } from "./Marked";
import { Method } from "./Method";

const DIFF_PREVIEW = 30;

function notesIn(notes: Note[], used: Set<number>) {
  return notes.filter((n) => used.has(n.n));
}

function Diff({ lines, notes }: { lines: DiffLine[]; notes: Note[] }) {
  const [all, setAll] = useState(false);
  const hidden = Math.max(0, lines.length - DIFF_PREVIEW);
  return (
    <>
      <pre className="code diff" aria-label="Code change">
        {lines.map((l, i) => (
          <span key={i} className={`diff-line ${l.sign === "-" ? "del" : "add"}${i >= DIFF_PREVIEW && !all ? " extra" : ""}`}>
            <span className="gutter" aria-hidden>
              {l.sign === "-" ? "−" : "+"}
            </span>
            <Marked text={l.text} spans={l.spans} notes={notes} />
            {"\n"}
          </span>
        ))}
      </pre>
      {hidden > 0 && (
        <button type="button" className="text-button no-print" onClick={() => setAll((a) => !a)}>
          {all ? "Show fewer lines" : `Show all ${lines.length} changed lines`}
        </button>
      )}
    </>
  );
}

/** One axis in combined-score units; each signal is divided by its train spread. */
function NumberLine({ value, eps, strong }: { value: number; eps: number; strong?: boolean }) {
  const lim = 2.5;
  const x = (v: number) => 10 + ((Math.max(-lim, Math.min(lim, v)) + lim) / (2 * lim)) * 380;
  return (
    <svg className="numline" viewBox="0 0 400 24" role="img" aria-label={`Value ${num(value, 2, true)} on a scale from −2.5 to +2.5`}>
      <line x1="10" x2="390" y1="12" y2="12" className="axis" />
      <rect x={x(-eps)} y="5" width={x(eps) - x(-eps)} height="14" className="band" />
      <line x1={x(0)} x2={x(0)} y1="6" y2="18" className="zero" />
      <circle cx={x(value)} cy="12" r={strong ? 5.5 : 4} className={strong ? "dot strong" : "dot"} />
    </svg>
  );
}

function Signals({ data }: { data: Explained }) {
  const { report, trace } = data;
  const c = trace.combine;
  const t = report.signals.tfidf;
  const e = report.signals.encoder;
  if (report.mode === "snapshot" || !c) {
    return (
      <>
        <div className="table-scroll">
        <table className="signals">
          <tbody>
            <tr>
              <th scope="row">Word overlap (TF-IDF cosine)</th>
              <td className="num">{num(t?.value ?? null)}</td>
            </tr>
            <tr>
              <th scope="row">Meaning (encoder cosine)</th>
              <td className="num">{e ? num(e.value) : "not computed"}</td>
            </tr>
          </tbody>
        </table>
        </div>
        <p className="caption">
          Similarity scores, not probabilities. With one snapshot of the code these scores cannot show drift on their own, so
          only rule R1 can decide.
        </p>
      </>
    );
  }
  const rows: [string, number | null, number | null, boolean][] = [
    ["Word overlap (TF-IDF)", c.tfidf, c.parts[0], false],
    ["Meaning (encoder)", c.encoder, c.encoder === null ? null : c.parts[1], false],
    ["Combined score", null, c.z, true],
  ];
  return (
    <>
      <div className="table-scroll">
      <table className="signals">
        <thead>
          <tr>
            <th scope="col">Signal</th>
            <th scope="col" className="num">
              Raw change
            </th>
            <th scope="col" className="num">
              Scaled
            </th>
            <th scope="col">
              <span className="sr-only">Position</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, raw, scaled, strong]) => (
            <tr key={label} className={strong ? "strong" : ""}>
              <th scope="row">{label}</th>
              <td className="num">{raw === null ? (strong ? "" : "not computed") : num(raw, 3, true)}</td>
              <td className="num">{scaled === null ? "" : num(scaled, 2, true)}</td>
              <td className="line-cell">{scaled !== null && <NumberLine value={scaled} eps={c.eps} strong={strong} />}</td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
      <p className="caption">
        Similarity scores, not probabilities. Each change is divided by its usual spread on the training data so the two share
        one scale. Left of the shaded band, the documentation fits the old code better; right of it, the new code. Inside the
        band (±{num(c.eps, 3)}) the tool makes no call.
      </p>
    </>
  );
}

export function ReportView({ data }: { data: Explained }) {
  const { report, trace } = data;
  const src = report.source;
  const docLabel =
    src.doc_version === "new" ? "Docstring after the commit" : src.doc_version === "old" ? "Docstring before the commit" : "Documentation";
  const docNotes = notesIn(trace.notes, new Set(trace.doc_spans.map((s) => s.note)));
  const diffNotes = notesIn(trace.notes, new Set((trace.diff ?? []).flatMap((l) => l.spans.map((s) => s.note))));
  const shared = report.evidence.find((e) => e.kind === "term_overlap");

  return (
    <article className="report">
      <header className="report-head">
        <h1>{src.function ?? "Your documentation"}</h1>
        <p className="context">
          {src.project ? <>In {src.project}. </> : null}
          {report.mode === "change"
            ? `${docLabel}, checked against the code change.`
            : `${docLabel}, checked against one snapshot of the code.`}
        </p>
      </header>

      <section className="verdict" aria-label="Finding">
        <p className={`finding finding-${report.finding}`} data-testid="finding">
          {FINDING_LABEL[report.finding]}
        </p>
        <p className="summary">
          <Ticks text={report.summary} />
        </p>
        <p className="next">
          <span className="next-label">Next step.</span> <Ticks text={report.next_step} />
        </p>
      </section>

      <section aria-labelledby="h-evidence">
        <h2 id="h-evidence">Evidence</h2>
        <div className="specimen">
          <figure>
            <figcaption>{docLabel}</figcaption>
            <pre className="code">
              <Marked text={trace.documentation} spans={trace.doc_spans} notes={trace.notes} />
            </pre>
          </figure>
          <aside className="margin">
            <MarginNotes notes={docNotes} />
          </aside>
        </div>
        {trace.diff && (
          <div className="specimen">
            <figure>
              <figcaption>
                Code change: {trace.diff.filter((l) => l.sign === "-").length} lines removed,{" "}
                {trace.diff.filter((l) => l.sign === "+").length} added
              </figcaption>
              {trace.diff.length ? <Diff lines={trace.diff} notes={trace.notes} /> : <p className="muted">The two versions are identical.</p>}
            </figure>
            <aside className="margin">
              <MarginNotes notes={diffNotes} />
            </aside>
          </div>
        )}
        {trace.notes.length === 0 && (
          <p className="muted">Neither rule found a word to point at; the finding rests on the similarity signals below.</p>
        )}
        {shared && <p className="shared">{shared.text}.</p>}
      </section>

      <section aria-labelledby="h-signals">
        <h2 id="h-signals">Signals</h2>
        <Signals data={data} />
      </section>

      <section aria-labelledby="h-method">
        <h2 id="h-method">How it was computed</h2>
        <Method data={data} />
      </section>

      <section aria-labelledby="h-limits">
        <h2 id="h-limits">What was not checked</h2>
        <ul className="limits">
          {report.uncertainties.map((u) => (
            <li key={u}>{u}</li>
          ))}
        </ul>
      </section>

      <footer className="report-foot">
        <p>
          Settings {report.meta.thresholds_version ?? "default"}, learned on the CoDocBench training split. TF-IDF model{" "}
          {report.meta.tfidf_artifact_sha256?.slice(0, 12) ?? "n/a"}. Computed in {num(report.meta.elapsed_ms, 0)} ms on this
          machine. Findings are heuristics for review, not verdicts.
        </p>
        <p>Examples from CoDocBench (Pai, Devanbu and Ahmed, MSR 2025), CC BY 4.0.</p>
      </footer>
    </article>
  );
}