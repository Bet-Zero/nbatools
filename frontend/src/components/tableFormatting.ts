/** Format a column header: short uppercase stat names stay as-is, others get title-cased. */
export function formatColHeader(col: string): string {
  if (col.length <= 5 && col === col.toUpperCase()) return col;
  return col.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Format a cell value for display. */
export function formatValue(val: unknown, col: string): string {
  if (val === null || val === undefined) return "—";
  if (typeof val === "number") {
    const lc = col.toLowerCase();
    if (lc.includes("pct")) {
      if (val >= 0 && val <= 1) return (val * 100).toFixed(1) + "%";
      return val.toFixed(1) + "%";
    }
    if (Number.isInteger(val) || Math.abs(val) >= 100) {
      return val.toLocaleString();
    }
    return val % 1 === 0 ? val.toString() : val.toFixed(1);
  }
  return String(val);
}
