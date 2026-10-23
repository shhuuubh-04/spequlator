// Mirrors spequlator.schemas.Report (schema 1.2) and spequlator.pipeline.trace.Trace (D-030).
// Signals are similarity scores, not probabilities. The UI only displays these values.
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

// ---- trace (how the report was computed) ------------------------------------------------
export interface TextStat { key: string; label: string; chars: number; words: number; lines: number }
export interface Note { n: number; kind: "r1" | "r2"; text: string }
export interface Span { start: number; end: number; note: number }
export interface DiffLine { sign: "-" | "+"; text: string; spans: Span[] }
export interface Token { t: string; vocab: boolean; content: boolean }

export interface TokenStep {
  key: string;
  label: string;
  n_tokens: number;
  n_vocab: number;
  n_content: number;
  splits: [string, string[]][];
  tokens: Token[];
  more: number;
}

export interface R1Step {
  applicable: boolean;
  def_line: string;
  signature: string[];
  has_kwargs: boolean;
  documented: string[];
  stale: string[];
  undocumented: string[];
  fired: boolean;
}

export interface R2Step {
  applicable: boolean;
  removed: string[];
  still_present: string[];
  gone: string[];
  doc: string[];
  hits: string[];
  lines: string[];
  fired: boolean;
}

export interface TermRow {
  term: string;
  df: number;
  idf: number;
  count: Record<string, number>;
  tf: Record<string, number>;
  weight: Record<string, number>;
  unit: Record<string, number>;
  contrib: Record<string, number>;
}

export interface VecStat { key: string; label: string; n_terms: number; out_of_vocab: number; sum_sq: number; norm: number }

export interface TfidfStep {
  n_train_texts: number;
  vocab_size: number;
  min_df: number;
  vectors: VecStat[];
  rows: TermRow[];
  cos: Record<string, number>;
  delta: number | null;
}

export interface EncText { key: string; label: string; n_tokens: number | null; truncated: boolean; pieces: string[]; head: number[]; norm: number }

export interface EncoderStep {
  status: "ok" | "off" | "unavailable";
  model: string;
  max_seq_length: number | null;
  dim: number | null;
  texts: EncText[];
  products: Record<string, number[]>;
  cos: Record<string, number>;
  delta: number | null;
}

export interface CombineStep {
  tfidf: number;
  encoder: number | null;
  scale_tfidf: number;
  scale_encoder: number;
  parts: number[];
  z: number;
  eps: number;
}

export interface Check {
  key: string;
  question: string;
  detail: string;
  result: "yes" | "no" | "not reached";
  outcome: Finding;
}

export interface Trace {
  trace_version: string;
  mode: Mode;
  inputs: TextStat[];
  documentation: string;
  doc_spans: Span[];
  notes: Note[];
  diff: DiffLine[] | null;
  tokens: TokenStep[];
  r1: R1Step;
  r2: R2Step | null;
  tfidf: TfidfStep;
  encoder: EncoderStep;
  combine: CombineStep | null;
  decision: { checks: Check[]; reason: string; finding: Finding };
  text: { reason: string; summary: string; next_step: string };
  constants: { thresholds_version: string; eps: number; scale_tfidf: number; scale_encoder: number; min_doc_words: number; encoder_key: string | null };
}

export interface Explained {
  report: Report;
  trace: Trace;
}

// ---- service and examples -----------------------------------------------------------------
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