import { useEffect, useState } from "react";
import { ApiError, api } from "./api";
import { InputForm } from "./components/InputForm";
import { ReportView } from "./components/ReportView";
import type { ExampleDetail, Explained, Health, Mode } from "./types";

type Field = "documentation" | "code" | "old_code" | "new_code";
const EMPTY: Record<Field, string> = { documentation: "", code: "", old_code: "", new_code: "" };

function Status({ health, down }: { health: Health | null; down: boolean }) {
  if (down) return <p className="status bad">Analysis service offline</p>;
  if (!health) return <p className="status">Connecting…</p>;
  const enc = { ready: "encoder ready", loading: "encoder loading…", unavailable: "encoder unavailable", disabled: "encoder off" }[
    health.encoder
  ];
  const cross = health.cross === "ready" ? ", cross-encoder ready" : health.cross === "loading" ? ", cross-encoder loading…" : "";
  return (
    <p className={`status ${health.tfidf ? "" : "bad"}`} title={health.encoder_name ?? ""}>
      {health.tfidf ? "TF-IDF ready" : "TF-IDF model missing"}, {enc}
      {cross}
    </p>
  );
}

export default function App() {
  const [view, setView] = useState<"inputs" | "report">("inputs");
  const [mode, setMode] = useState<Mode>("change");
  const [values, setValues] = useState(EMPTY);
  const [example, setExample] = useState<ExampleDetail | null>(null);
  const [docVersion, setDocVersion] = useState<"old" | "new">("old");
  const [result, setResult] = useState<Explained | null>(null);
  const [wordsBusy, setWordsBusy] = useState(false);
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

  const setValue = (f: Field, v: string) => setValues((s) => ({ ...s, [f]: v }));

  const pickExample = (e: ExampleDetail) => {
    setExample(e);
    setMode("change");
    setValues({ documentation: docVersion === "old" ? e.old_doc : e.new_doc, code: "", old_code: e.old_code, new_code: e.new_code });
    setError(null);
  };

  const switchDoc = (v: "old" | "new") => {
    setDocVersion(v);
    if (example) setValue("documentation", v === "old" ? example.old_doc : example.new_doc);
  };

  const ready =
    values.documentation.trim() !== "" &&
    (mode === "snapshot" ? values.code.trim() !== "" : values.old_code.trim() !== "" && values.new_code.trim() !== "");

  // Use the dataset route only when the fields still hold the example unchanged,
  // so the report can name the project and function.
  const untouchedExample =
    example !== null &&
    mode === "change" &&
    values.old_code === example.old_code &&
    values.new_code === example.new_code &&
    values.documentation === (docVersion === "old" ? example.old_doc : example.new_doc);

  const request = (crossWords: boolean) =>
    untouchedExample
      ? api.explainExample(example!.record_id, docVersion, crossWords)
      : api.explain(
          mode === "snapshot"
            ? { documentation: values.documentation, code: values.code }
            : { documentation: values.documentation, old_code: values.old_code, new_code: values.new_code, cross_words: crossWords },
        );

  // The word heatmap costs one model pass per word, so it is fetched only when asked for.
  const explainWords = async () => {
    setWordsBusy(true);
    try {
      setResult(await request(true));
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setWordsBusy(false);
    }
  };

  const check = async () => {
    setLoading(true);
    setError(null);
    try {
      const out = await request(false);
      setResult(out);
      setView("report");
      setDown(false);
      window.scrollTo?.(0, 0);
    } catch (e) {
      const err = e as ApiError;
      setError(err);
      if (err.code === "api_down") setDown(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <header className="masthead">
        <p className="wordmark">Spequlator</p>
        {view === "report" && result ? (
          <nav className="actions no-print" aria-label="Report actions">
            <button type="button" className="text-button" onClick={() => setView("inputs")}>
              Edit inputs
            </button>
            <button type="button" className="text-button" onClick={() => window.print()}>
              Print or save as PDF
            </button>
          </nav>
        ) : (
          <Status health={health} down={down} />
        )}
      </header>

      <main>
        {view === "report" && result ? (
          <ReportView data={result} onExplainWords={explainWords} busy={wordsBusy} />
        ) : (
          <InputForm
            mode={mode}
            setMode={setMode}
            values={values}
            setValue={setValue}
            example={example}
            docVersion={docVersion}
            onPick={pickExample}
            onDocVersion={switchDoc}
            onClearExample={() => {
              setExample(null);
              setValues(EMPTY);
            }}
            onSubmit={check}
            ready={ready}
            loading={loading}
            error={error}
          />
        )}
      </main>
    </div>
  );
}