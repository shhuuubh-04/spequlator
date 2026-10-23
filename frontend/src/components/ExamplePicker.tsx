import { useEffect, useState } from "react";
import { ApiError, api } from "../api";
import type { ExampleDetail, ExampleSummary } from "../types";

export function ExamplePicker({ onPick }: { onPick: (e: ExampleDetail) => void }) {
  const [q, setQ] = useState("");
  const [items, setItems] = useState<ExampleSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => {
      api
        .examples(q)
        .then((list) => {
          setItems(list);
          setError(null);
        })
        .catch((e: ApiError) => setError(e.message));
    }, 200);
    return () => clearTimeout(t);
  }, [q]);

  const pick = async (id: string) => {
    setBusy(true);
    try {
      onPick(await api.example(id));
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="picker">
      <label htmlFor="example-search">Find a commit by function or project</label>
      <input
        id="example-search"
        type="search"
        placeholder="observe_lr, pandas, tornado…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      {error && <p className="error">{error}</p>}
      <ul className="picker-list">
        {items.map((it) => (
          <li key={it.record_id}>
            <button type="button" disabled={busy} onClick={() => pick(it.record_id)}>
              <code>{it.function}</code>
              <span className="muted">{it.project}</span>
            </button>
          </li>
        ))}
        {!error && items.length === 0 && <li className="muted">No examples match.</li>}
      </ul>
      <p className="caption">From CoDocBench (CC BY 4.0): real commits that changed both the code and its docstring.</p>
    </div>
  );
}