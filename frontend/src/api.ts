import type { AnalyzePayload, ExampleDetail, ExampleSummary, Explained, Health, Report } from "./types";

/** Error from the API ({"error": {...}}) or a network failure (code "api_down"). */
export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public field: string | null = null,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch {
    throw new ApiError("api_down", "Can't reach the analysis service. Start it with `uv run spequlator serve`.");
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const err = body?.error;
    if (err) throw new ApiError(err.code, err.message, err.field ?? null);
    throw new ApiError("api_down", "Can't reach the analysis service. Start it with `uv run spequlator serve`.");
  }
  return body as T;
}

const json = (data: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(data),
});

export const api = {
  health: () => request<Health>("/api/health"),
  examples: (q = "") => request<ExampleSummary[]>(`/api/examples?limit=50&q=${encodeURIComponent(q)}`),
  example: (id: string) => request<ExampleDetail>(`/api/examples/${encodeURIComponent(id)}`),
  analyze: (payload: AnalyzePayload) => request<Report>("/api/analyze", json(payload)),
  explain: (payload: AnalyzePayload) => request<Explained>("/api/explain", json(payload)),
  explainExample: (record_id: string, doc_version: "old" | "new", cross_words = false) =>
    request<Explained>("/api/explain/example", json({ record_id, doc_version, cross_words })),
};