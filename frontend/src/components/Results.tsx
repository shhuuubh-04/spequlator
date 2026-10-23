import type { Evidence, Finding, Report, SignalValue } from "../types";

const FINDING_LABEL: Record<Finding, string> = {
  potential_drift: "Potential drift",
  no_obvious_drift: "No obvious drift",
  inconclusive: "Inconclusive",
};

const EVIDENCE_TAG: Record<Evidence["kind"], string> = {
  rule_r1: "Parameter check",
  rule_r2: "Removed identifier",
  term_overlap: "Term overlap",
  diff: "Diff",
};

/** Tokens named in rule evidence ("...: a, b") so they can be highlighted in the lines. */
function evidenceTokens(e: Evidence): string[] {
  if (e.kind !== "rule_r1" && e.kind !== "rule_r2") return [];
  const list = e.text.split(":").slice(1).join(":");
  return list
    .split(",")
    .map((t) => t.trim())
    .filter((t) => t.length > 1);
}

function Highlight({ text, tokens }: { text: string; tokens: string[] }) {
  if (!tokens.length) return <>{text}</>;
  const escaped = tokens.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const parts = text.split(new RegExp(`(${escaped.join("|")})`, "gi"));
  return (
    <>
      {parts.map((p, i) =>
        tokens.some((t) => t.toLowerCase() === p.toLowerCase()) ? <mark key={i}>{p}</mark> : <span key={i}>{p}</span>,
      )}
    </>
  );
}

function SignalBar({ label, signal, detail }: { label: string; signal: SignalValue | null; detail?: string }) {
  if (!signal) {
    return (
      <div className="signal">
        <div className="signal-label">{label}</div>
        <div className="signal-na">not available</div>
      </div>
    );
  }
  const span = 0.5; // deltas are small; clip the bar at +/-0.5 and always print the number
  const clipped = Math.max(-span, Math.min(span, signal.value));
  const width = (Math.abs(clipped) / span) * 50;
  const left = clipped < 0 ? 50 - width : 50;
  return (
    <div className="signal">
      <div className="signal-label">
        {label} <span className="muted">{detail}</span>
      </div>
      <div className="signal-track" role="img" aria-label={`${label}: ${signal.value.toFixed(3)}`}>
        <div className="signal-zero" />
        <div className={`signal-fill ${signal.value < 0 ? "neg" : "pos"}`} style={{ left: `${left}%`, width: `${width}%` }} />
      </div>
      <div className="signal-value">{signal.value >= 0 ? "+" : ""}{signal.value.toFixed(3)}</div>
    </div>
  );
}

export function toMarkdown(r: Report): string {
  const lines = [
    `# Spequlator report`,
    ``,
    `**Finding:** ${FINDING_LABEL[r.finding]} (heuristic)`,
    ``,
    r.summary,
    ``,
    `## Observed`,
    ...r.evidence.map((e) => `- [${EVIDENCE_TAG[e.kind]}] ${e.text}${e.lines.length ? "\n  " + e.lines.map((l) => "`" + l + "`").join("\n  ") : ""}`),
    ...r.observations.map((o) => `- ${o}`),
    ``,
    `## Signals (similarity, not probabilities)`,
    r.signals.tfidf ? `- TF-IDF ${r.signals.tfidf.kind}: ${r.signals.tfidf.value.toFixed(3)}` : `- TF-IDF: n/a`,
    r.signals.encoder ? `- Encoder ${r.signals.encoder.kind}: ${r.signals.encoder.value.toFixed(3)} (${r.signals.encoder.model})` : `- Encoder: n/a`,
    ``,
    `## What we can't tell`,
    ...r.uncertainties.map((u) => `- ${u}`),
    ``,
    `## Suggested review step`,
    r.next_step,
    ``,
  ];
  return lines.join("\n");
}

export function Results({ report }: { report: Report }) {
  const isDelta = report.mode === "change";
  const copyJson = () => navigator.clipboard?.writeText(JSON.stringify(report, null, 2));
  const downloadMd = () => {
    const url = URL.createObjectURL(new Blob([toMarkdown(report)], { type: "text/markdown" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "spequlator-report.md";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="results" aria-live="polite">
      <div className="results-head">
        <span className={`badge badge-${report.finding}`} data-testid="finding">
          {FINDING_LABEL[report.finding]}
        </span>
        <span className="muted">heuristic{report.review_recommended ? " · review recommended" : ""}</span>
      </div>
      <p className="summary">{report.summary}</p>

      <h3>Observed</h3>
      {report.evidence.length === 0 && report.observations.length === 0 ? (
        <p className="muted">No rule evidence for this input.</p>
      ) : (
        <ul className="evidence">
          {report.evidence.map((e, i) => (
            <li key={i}>
              <span className="tag">{EVIDENCE_TAG[e.kind]}</span> {e.text}
              {e.lines.length > 0 && (
                <pre className="evidence-lines">
                  {e.lines.map((l, j) => (
                    <div key={j}>
                      <Highlight text={l} tokens={evidenceTokens(e)} />
                    </div>
                  ))}
                </pre>
              )}
            </li>
          ))}
          {report.observations.map((o, i) => (
            <li key={`o${i}`} className="muted">
              {o}
            </li>
          ))}
        </ul>
      )}

      <h3>Signals</h3>
      <p className="caption">
        Similarity signals, not probabilities.{" "}
        {isDelta ? "Negative = the documentation still fits the old code better." : "Higher = more shared wording."}
      </p>
      <SignalBar label={isDelta ? "TF-IDF alignment shift" : "TF-IDF similarity"} signal={report.signals.tfidf} />
      <SignalBar
        label={isDelta ? "Encoder alignment shift" : "Encoder similarity"}
        signal={report.signals.encoder}
        detail={report.signals.encoder?.truncated ? "(input truncated)" : ""}
      />

      <h3>What we can't tell</h3>
      <ul className="uncertain">
        {report.uncertainties.map((u, i) => (
          <li key={i}>{u}</li>
        ))}
      </ul>

      <h3>Suggested review step</h3>
      <p>{report.next_step}</p>

      <div className="actions">
        <button type="button" className="secondary" onClick={copyJson}>
          Copy JSON
        </button>
        <button type="button" className="secondary" onClick={downloadMd}>
          Download Markdown
        </button>
      </div>
    </section>
  );
}