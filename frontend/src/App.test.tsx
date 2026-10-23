import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { Report } from "./types";

const health = { status: "ok", tfidf: true, encoder: "ready", encoder_name: "minilm-ft", thresholds: "t" };

const report: Report = {
  schema_version: "1.2",
  mode: "change",
  source: { kind: "manual", record_id: null, project: null, function: null, doc_version: null },
  finding: "potential_drift",
  summary: "The documentation describes parameter(s) `timeout` that the current code does not have.",
  observations: ["The code change removes 2 line(s) and adds 4."],
  evidence: [{ kind: "rule_r1", text: "Documented but not in the signature: timeout", lines: ["def fetch(session, retries=3):"] }],
  signals: { tfidf: { value: -0.147, kind: "delta" }, encoder: { value: -0.05, kind: "delta", model: "minilm-ft", truncated: false } },
  explanation: "Observed: …",
  uncertainties: ["Similarity signals measure shared words or meaning, not correctness."],
  review_recommended: true,
  next_step: "Update the parameter list.",
  meta: { thresholds_version: "t", tfidf_artifact_sha256: null, elapsed_ms: 5 },
};

function mockFetch(analyze: () => Promise<Response>) {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => (url.startsWith("/api/health") ? Promise.resolve(Response.json(health)) : analyze())),
  );
}

function fillChangeForm() {
  fireEvent.change(screen.getByLabelText("Documentation"), { target: { value: ":param timeout: seconds" } });
  fireEvent.change(screen.getByLabelText("Code before"), { target: { value: "def fetch(session, timeout=30): pass" } });
  fireEvent.change(screen.getByLabelText("Code after"), { target: { value: "def fetch(session, retries=3): pass" } });
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("disables Analyze until the required fields are filled", () => {
    mockFetch(() => Promise.resolve(Response.json(report)));
    render(<App />);
    const button = screen.getByRole("button", { name: /analyze consistency/i });
    expect(button).toBeDisabled();
    fillChangeForm();
    expect(button).toBeEnabled();
  });

  it("renders the finding, evidence and neutral signal caption", async () => {
    mockFetch(() => Promise.resolve(Response.json(report)));
    render(<App />);
    fillChangeForm();
    fireEvent.click(screen.getByRole("button", { name: /analyze consistency/i }));
    expect(await screen.findByTestId("finding")).toHaveTextContent("Potential drift");
    expect(screen.getByText(/Documented but not in the signature/)).toBeInTheDocument();
    expect(screen.getByText(/not probabilities/)).toBeInTheDocument();
    expect(screen.queryByText(/confidence/i)).not.toBeInTheDocument();
  });

  it("shows a field-level validation error from the API", async () => {
    const body = { error: { code: "invalid_input", message: "old_code: must not be empty", field: "old_code" } };
    mockFetch(() => Promise.resolve(Response.json(body, { status: 422 })));
    render(<App />);
    fillChangeForm();
    fireEvent.click(screen.getByRole("button", { name: /analyze consistency/i }));
    expect(await screen.findByText("old_code: must not be empty")).toBeInTheDocument();
  });

  it("explains how to start the service when the API is down", async () => {
    mockFetch(() => Promise.reject(new TypeError("fetch failed")));
    render(<App />);
    fillChangeForm();
    fireEvent.click(screen.getByRole("button", { name: /analyze consistency/i }));
    await waitFor(() => expect(screen.getByText(/uv run spequlator serve/)).toBeInTheDocument());
  });
});