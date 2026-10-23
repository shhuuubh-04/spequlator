// Mirrors spequlator.schemas.Report (schema 1.2). Signals are similarity scores, not probabilities.
export type Finding = "potential_drift" | "no_obvious_drift" | "inconclusive";
export type Mode = "change" | "snapshot";

export interface Evidence {
  kind: "rule_r1" | "rule_r2" | "diff" | "term_overlap";
  text: string;
  lines: string[];
}

export interface SignalValue {
  value: number;
  kind: "delta" | "absolute";
}

export interface EncoderSignal extends SignalValue {
  model: string;
  truncated: boolean;
}

export interface Report {
  schema_version: string;
  mode: Mode;
  source: { kind: string; record_id: string | null; project: string | null; function: string | null; doc_version: string | null };
  finding: Finding;
  summary: string;
  observations: string[];
  evidence: Evidence[];
  signals: { tfidf: SignalValue | null; encoder: EncoderSignal | null };
  explanation: string;
  uncertainties: string[];
  review_recommended: boolean;
  next_step: string;
  meta: { thresholds_version: string | null; tfidf_artifact_sha256: string | null; elapsed_ms: number | null };
}

export interface Health {
  status: "ok" | "degraded";
  tfidf: boolean;
  encoder: "ready" | "loading" | "unavailable" | "disabled";
  encoder_name: string | null;
  thresholds: string;
}

export interface ExampleSummary {
  record_id: string;
  project: string;
  function: string;
}

export interface ExampleDetail extends ExampleSummary {
  file_path: string;
  old_code: string;
  new_code: string;
  old_doc: string;
  new_doc: string;
  diff_code: string[];
  diff_docstring: string[];
}

export interface AnalyzePayload {
  documentation: string;
  code?: string;
  old_code?: string;
  new_code?: string;
}