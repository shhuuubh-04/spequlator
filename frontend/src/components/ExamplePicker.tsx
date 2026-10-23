import { useEffect, useState } from "react";
import { ApiError, api } from "../api";
import type { ExampleDetail, ExampleSummary } from "../types";

export function ExamplePicker({ onPick, onClose }: { onPick: (e: ExampleDetail) => void; onClose: () => void }) {
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
    <div className="picker" role="dialog" aria-label="Dataset examples">
      <div className="picker-head">
        <input
          type="search"
          placeholder="Search project or function…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          aria-label="Search examples"
        />
        <button type="button" className="secondary" onClick={onClose}>
          Close
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      <ul className="picker-list">
        {items.map((it) => (
          <li key={it.record_id}>
            <button type="button" disabled={busy} onClick={() => pick(it.record_id)}>
              <strong>{it.function}</strong> <span className="muted">{it.project}</span>
            </button>
          </li>
        ))}
        {!error && items.length === 0 && <li className="muted">No examples match.</li>}
      </ul>
      <p className="caption">CoDocBench (CC BY 4.0). Each example is a real commit that changed both code and docstring.</p>
    </div>
  );
}