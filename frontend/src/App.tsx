import { useEffect, useState } from "react";
import { ApiError, api } from "./api";
import { ExamplePicker } from "./components/ExamplePicker";
import { Results } from "./components/Results";
import type { AnalyzePayload, ExampleDetail, Health, Mode, Report } from "./types";

type Field = "documentation" | "code" | "old_code" | "new_code";

function StatusPill({ health, down }: { health: Health | null; down: boolean }) {
  if (down) return <span className="pill pill-bad">Service offline</span>;
  if (!health) return <span className="pill">Checking…</span>;
  const enc = { ready: "ready", loading: "loading…", unavailable: "unavailable", disabled: "off" }[health.encoder];
  return (
    <span className={`pill ${health.tfidf ? "" : "pill-bad"}`} title={health.encoder_name ?? ""}>
      TF-IDF {health.tfidf ? "ready" : "missing"} · Encoder {enc}
    </span>
  );
}

function TextField(props: {
  id: Field;
  label: string;
  hint: string;
  value: string;
  onChange: (v: string) => void;
  mono?: boolean;
  error?: string | null;
}) {
  return (
    <div className="field">
      <label htmlFor={props.id}>{props.label}</label>
      <textarea
        id={props.id}
        className={props.mono ? "mono" : ""}
        value={props.value}
        placeholder={props.hint}
        onChange={(e) => props.onChange(e.target.value)}
        spellCheck={!props.mono}
        aria-invalid={!!props.error}
      />
      {props.error && <p className="error">{props.error}</p>}
    </div>
  );
}

export default function App() {
  const [mode, setMode] = useState<Mode>("change");
  const [documentation, setDocumentation] = useState("");
  const [code, setCode] = useState("");
  const [oldCode, setOldCode] = useState("");
  const [newCode, setNewCode] = useState("");
  const [example, setExample] = useState<ExampleDetail | null>(null);
  const [docVersion, setDocVersion] = useState<"old" | "new">("old");
  const [pickerOpen, setPickerOpen] = useState(false);
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [down, setDown] = useState(false);

  useEffect(() => {
    let tries = 0;
    let timer: ReturnType<typeof setTimeout>;
    const poll = () =>
      api
        .health()
        .then((h) => {
          setHealth(h);
          setDown(false);
          if (h.encoder === "loading" && tries++ < 20) timer = setTimeout(poll, 3000);
        })
        .catch(() => setDown(true));
    poll();
    return () => clearTimeout(timer);
  }, []);

  const pickExample = (e: ExampleDetail) => {
    setExample(e);
    setMode("change");
    setOldCode(e.old_code);
    setNewCode(e.new_code);
    setDocumentation(docVersion === "old" ? e.old_doc : e.new_doc);
    setPickerOpen(false);
    setReport(null);
    setError(null);
  };

  const switchDoc = (v: "old" | "new") => {
    setDocVersion(v);
    if (example) setDocumentation(v === "old" ? example.old_doc : example.new_doc);
  };

  const ready =
    documentation.trim() !== "" && (mode === "snapshot" ? code.trim() !== "" : oldCode.trim() !== "" && newCode.trim() !== "");

  const analyze = async () => {
    const payload: AnalyzePayload =
      mode === "snapshot" ? { documentation, code } : { documentation, old_code: oldCode, new_code: newCode };
    setLoading(true);
    setError(null);
    try {
      setReport(await api.analyze(payload));
      setDown(false);
    } catch (e) {
      const err = e as ApiError;
      setError(err);
      if (err.code === "api_down") setDown(true);
    } finally {
      setLoading(false);
    }
  };

  const fieldError = (f: Field) => (error && error.field === f ? error.message : null);
  const generalError = error && !(["documentation", "code", "old_code", "new_code"] as string[]).includes(error.field ?? "");
  const encoderMissing = report && !report.signals.encoder && health?.encoder !== "disabled";

  return (
    <div className="app">
      <header>
        <div>
          <h1>Spequlator</h1>
          <p className="subtitle">Understand potential gaps between code and documentation.</p>
        </div>
        <StatusPill health={health} down={down} />
      </header>

      <main className={report ? "with-results" : ""}>
        <section className="workspace">
          <div className="toolbar">
            <div className="segmented" role="tablist" aria-label="Analysis mode">
              <button role="tab" aria-selected={mode === "change"} onClick={() => setMode("change")}>
                Compare a change
              </button>
              <button role="tab" aria-selected={mode === "snapshot"} onClick={() => setMode("snapshot")}>
                Check a snapshot
              </button>
            </div>
            <button type="button" className="secondary" onClick={() => setPickerOpen((o) => !o)}>
              Load dataset example
            </button>
          </div>

          {pickerOpen && <ExamplePicker onPick={pickExample} onClose={() => setPickerOpen(false)} />}

          {example && mode === "change" && (
            <div className="example-bar">
              <span>
                Example: <strong>{example.function}</strong> <span className="muted">{example.project}</span>
              </span>
              <div className="segmented small" role="radiogroup" aria-label="Docstring version">
                <button role="radio" aria-checked={docVersion === "old"} onClick={() => switchDoc("old")}>
                  Docstring before commit
                </button>
                <button role="radio" aria-checked={docVersion === "new"} onClick={() => switchDoc("new")}>
                  after commit
                </button>
              </div>
            </div>
          )}

          <TextField
            id="documentation"
            label="Documentation"
            hint="Paste the docstring or documentation passage…"
            value={documentation}
            onChange={setDocumentation}
            error={fieldError("documentation")}
          />
          {mode === "change" ? (
            <div className="code-pair">
              <TextField id="old_code" label="Code before" hint="def f(x, timeout=30): …" value={oldCode} onChange={setOldCode} mono error={fieldError("old_code")} />
              <TextField id="new_code" label="Code after" hint="def f(x, retries=3): …" value={newCode} onChange={setNewCode} mono error={fieldError("new_code")} />
            </div>
          ) : (
            <TextField id="code" label="Code" hint="def f(x): …" value={code} onChange={setCode} mono error={fieldError("code")} />
          )}

          {example && mode === "change" && (
            <details className="diff">
              <summary>Show the commit's diffs</summary>
              <pre>
                {[...example.diff_docstring, "", ...example.diff_code].map((l, i) => (
                  <div key={i} className={l.startsWith("+ ") ? "add" : l.startsWith("- ") ? "del" : ""}>
                    {l || " "}
                  </div>
                ))}
              </pre>
            </details>
          )}

          <div className="analyze-row">
            <button type="button" className="primary" disabled={!ready || loading} onClick={analyze}>
              {loading ? <span className="spinner" aria-hidden /> : null}
              {loading ? "Analyzing…" : "Analyze consistency"}
            </button>
            {!ready && <span className="muted">Fill in the documentation and code, or load an example.</span>}
          </div>

          {generalError && <p className="error banner">{error!.message}</p>}
        </section>

        {report && (
          <div className={loading ? "dim" : ""}>
            {encoderMissing && (
              <p className="banner info">Deep-learning signal unavailable — showing TF-IDF and rule evidence only.</p>
            )}
            <Results report={report} />
          </div>
        )}
      </main>

      <footer className="muted">
        Findings are heuristics for review, not verdicts. Text is analysed locally and never leaves this machine.
      </footer>
    </div>
  );
}