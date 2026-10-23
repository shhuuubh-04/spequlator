import { useState } from "react";
import type { ApiError } from "../api";
import type { ExampleDetail, Mode } from "../types";
import { ExamplePicker } from "./ExamplePicker";

type Field = "documentation" | "code" | "old_code" | "new_code";

interface Props {
  mode: Mode;
  setMode: (m: Mode) => void;
  values: Record<Field, string>;
  setValue: (f: Field, v: string) => void;
  example: ExampleDetail | null;
  docVersion: "old" | "new";
  onPick: (e: ExampleDetail) => void;
  onDocVersion: (v: "old" | "new") => void;
  onClearExample: () => void;
  onSubmit: () => void;
  ready: boolean;
  loading: boolean;
  error: ApiError | null;
}

function Area(props: { id: Field; label: string; hint: string; value: string; onChange: (v: string) => void; code?: boolean; error?: string | null }) {
  return (
    <div className="field">
      <label htmlFor={props.id}>{props.label}</label>
      <textarea
        id={props.id}
        className={props.code ? "code" : ""}
        value={props.value}
        placeholder={props.hint}
        spellCheck={!props.code}
        aria-invalid={!!props.error}
        onChange={(e) => props.onChange(e.target.value)}
      />
      {props.error && <p className="error">{props.error}</p>}
    </div>
  );
}

export function InputForm(p: Props) {
  const [picking, setPicking] = useState(false);
  const fieldError = (f: Field) => (p.error && p.error.field === f ? p.error.message : null);
  const general = p.error && !["documentation", "code", "old_code", "new_code"].includes(p.error.field ?? "");

  return (
    <section className="inputs">
      <h1>Check a docstring against its code</h1>
      <p className="intro">
        Paste a docstring with the code before and after a change, or start from a real commit. The report shows what was found,
        every step of the calculation, and what was not checked.
      </p>

      <div className="mode" role="radiogroup" aria-label="What to compare">
        <button type="button" role="radio" aria-checked={p.mode === "change"} onClick={() => p.setMode("change")}>
          Compare a change
        </button>
        <button type="button" role="radio" aria-checked={p.mode === "snapshot"} onClick={() => p.setMode("snapshot")}>
          Check one snapshot
        </button>
      </div>

      {p.example && p.mode === "change" ? (
        <div className="example-bar">
          <p>
            From CoDocBench: <code>{p.example.function}</code> in {p.example.project}.
          </p>
          <div className="mode small" role="radiogroup" aria-label="Which docstring">
            <button type="button" role="radio" aria-checked={p.docVersion === "old"} onClick={() => p.onDocVersion("old")}>
              Docstring before the commit
            </button>
            <button type="button" role="radio" aria-checked={p.docVersion === "new"} onClick={() => p.onDocVersion("new")}>
              After the commit
            </button>
          </div>
          <button type="button" className="text-button" onClick={p.onClearExample}>
            Clear example
          </button>
        </div>
      ) : (
        <p>
          <button type="button" className="text-button" aria-expanded={picking} onClick={() => setPicking((o) => !o)}>
            {picking ? "Hide examples" : "Start from a real commit"}
          </button>
        </p>
      )}
      {picking && !p.example && (
        <ExamplePicker
          onPick={(e) => {
            setPicking(false);
            p.onPick(e);
          }}
        />
      )}

      <Area
        id="documentation"
        label="Documentation"
        hint="The docstring or documentation passage"
        value={p.values.documentation}
        onChange={(v) => p.setValue("documentation", v)}
        error={fieldError("documentation")}
      />
      {p.mode === "change" ? (
        <div className="pair">
          <Area id="old_code" label="Code before" hint="def f(x, timeout=30): …" value={p.values.old_code} onChange={(v) => p.setValue("old_code", v)} code error={fieldError("old_code")} />
          <Area id="new_code" label="Code after" hint="def f(x, retries=3): …" value={p.values.new_code} onChange={(v) => p.setValue("new_code", v)} code error={fieldError("new_code")} />
        </div>
      ) : (
        <Area id="code" label="Code" hint="def f(x): …" value={p.values.code} onChange={(v) => p.setValue("code", v)} code error={fieldError("code")} />
      )}

      <div className="submit-row">
        <button type="button" className="primary" disabled={!p.ready || p.loading} onClick={p.onSubmit}>
          {p.loading ? "Checking…" : "Check documentation"}
        </button>
        {!p.ready && (
          <span className="muted">
            {p.mode === "change" ? "Fill in the documentation and both code versions." : "Fill in the documentation and the code."}
          </span>
        )}
      </div>
      {general && <p className="error">{p.error!.message}</p>}
    </section>
  );
}