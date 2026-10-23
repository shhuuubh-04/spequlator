import type { Finding } from "./types";

export const FINDING_LABEL: Record<Finding, string> = {
  potential_drift: "Potential drift",
  no_obvious_drift: "No obvious drift",
  inconclusive: "Inconclusive",
};

/** Fixed decimals with a true minus sign; `signed` adds "+" to positive values. */
export function num(v: number | null | undefined, digits = 3, signed = false): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "n/a";
  const s = Math.abs(v).toFixed(digits);
  if (v < 0 && Number(s) !== 0) return `−${s}`;
  return signed ? `+${s}` : s;
}

export const TEXT_LABEL: Record<string, string> = {
  doc: "documentation",
  old: "code before",
  new: "code after",
  code: "code",
};