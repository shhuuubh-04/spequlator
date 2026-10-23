import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { explained } from "./test-fixture";

const health = { status: "ok", tfidf: true, encoder: "ready", encoder_name: "minilm-ft", thresholds: "t" };

function mockFetch(explain: () => Promise<Response>) {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => (url.startsWith("/api/health") ? Promise.resolve(Response.json(health)) : explain())),
  );
}

function fillChangeForm() {
  fireEvent.change(screen.getByLabelText("Documentation"), { target: { value: ":param timeout: seconds" } });
  fireEvent.change(screen.getByLabelText("Code before"), { target: { value: "def fetch(session, timeout=30): pass" } });
  fireEvent.change(screen.getByLabelText("Code after"), { target: { value: "def fetch(session, retries=3): pass" } });
}

async function openReport() {
  mockFetch(() => Promise.resolve(Response.json(explained)));
  render(<App />);
  fillChangeForm();
  fireEvent.click(screen.getByRole("button", { name: /check documentation/i }));
  return screen.findByTestId("finding");
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("disables the check until the required fields are filled", () => {
    mockFetch(() => Promise.resolve(Response.json(explained)));
    render(<App />);
    const button = screen.getByRole("button", { name: /check documentation/i });
    expect(button).toBeDisabled();
    fillChangeForm();
    expect(button).toBeEnabled();
  });

  it("renders the finding, marked evidence, signals and all ten method steps", async () => {
    expect(await openReport()).toHaveTextContent("Potential drift");
    const marks = document.querySelectorAll("mark.mark-r1");
    expect([...marks].some((m) => m.textContent?.startsWith("timeout"))).toBe(true);
    expect(screen.getByText(/not a parameter of the code/)).toBeInTheDocument();
    expect(screen.getAllByText(/not probabilities/).length).toBeGreaterThan(0);
    expect(document.querySelectorAll(".method > li")).toHaveLength(10);
    expect(screen.queryByText(/confidence/i)).not.toBeInTheDocument();
  });

  it("walks the decision checks and highlights the one that decided", async () => {
    await openReport();
    const chosen = document.querySelector('.checks [aria-current="step"]') as HTMLElement;
    expect(within(chosen).getByText("Does rule R1 fire?")).toBeInTheDocument();
    expect(within(chosen).getByText(/Yes, so: Potential drift/)).toBeInTheDocument();
    expect(document.querySelectorAll(".check-not-reached").length).toBe(explained.trace.decision.checks.length - 1);
  });

  it("shows the TF-IDF sums and expands to every term", async () => {
    await openReport();
    expect(screen.getByTestId("cos-new")).toHaveTextContent("0.2500");
    expect(screen.getByTestId("cos-old")).toHaveTextContent("0.3655");
    const hidden = () => document.querySelectorAll(".worked tbody tr.extra").length;
    expect(hidden()).toBe(explained.trace.tfidf.rows.length - 8);
    fireEvent.click(screen.getByRole("button", { name: /show all 10 terms/i }));
    expect(hidden()).toBe(0);
  });

  it("returns to the inputs with the text kept", async () => {
    await openReport();
    fireEvent.click(screen.getByRole("button", { name: /edit inputs/i }));
    expect(screen.getByLabelText("Documentation")).toHaveValue(":param timeout: seconds");
  });

  it("shows a field-level validation error from the API", async () => {
    const body = { error: { code: "invalid_input", message: "old_code: must not be empty", field: "old_code" } };
    mockFetch(() => Promise.resolve(Response.json(body, { status: 422 })));
    render(<App />);
    fillChangeForm();
    fireEvent.click(screen.getByRole("button", { name: /check documentation/i }));
    expect(await screen.findByText("old_code: must not be empty")).toBeInTheDocument();
  });

  it("explains how to start the service when the API is down", async () => {
    mockFetch(() => Promise.reject(new TypeError("fetch failed")));
    render(<App />);
    fillChangeForm();
    fireEvent.click(screen.getByRole("button", { name: /check documentation/i }));
    await waitFor(() => expect(screen.getByText(/uv run spequlator serve/)).toBeInTheDocument());
  });
});