import type { SectionRow } from "../api/types";

interface Props {
  rows: SectionRow[];
  highlight?: boolean;
}

/** Format a column header: short uppercase stat names stay as-is, others get title-cased. */
function formatColHeader(col: string): string {
  if (col.length <= 5 && col === col.toUpperCase()) return col;
  return col.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Format a cell value for display. */
function formatValue(val: unknown, col: string): string {
  if (val === null || val === undefined) return "—";
  if (typeof val === "number") {
    const lc = col.toLowerCase();
    if (lc.includes("pct")) {
      if (val >= 0 && val <= 1) return (val * 100).toFixed(1) + "%";
      return val.toFixed(1) + "%";
    }
    if (Number.isInteger(val) || Math.abs(val) >= 100)
      return val.toLocaleString();
    return val % 1 === 0 ? val.toString() : val.toFixed(1);
  }
  return String(val);
}

/** Check whether a column contains numeric values (sample first 5 rows). */
function isNumericCol(col: string, rows: SectionRow[]): boolean {
  for (let i = 0; i < Math.min(rows.length, 5); i++) {
    const v = rows[i][col];
    if (v !== null && v !== undefined) return typeof v === "number";
  }
  return false;
}

export default function DataTable({ rows, highlight = false }: Props) {
  if (!rows.length) return null;
  const cols = Object.keys(rows[0]);

  return (
    <div className="table-scroll">
      <table
        className={`data-table${highlight ? " data-table-highlight" : ""}`}
      >
        <thead>
          <tr>
            {cols.map((col) => (
              <th key={col} className={isNumericCol(col, rows) ? "num" : ""}>
                {formatColHeader(col)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri}>
              {cols.map((col) => (
                <td key={col} className={isNumericCol(col, rows) ? "num" : ""}>
                  {formatValue(row[col], col)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
