import { type Key, type ReactNode } from "react";
import styles from "./ResultTable.module.css";

export type ResultTableAlignment = "left" | "right" | "center";

export interface ResultTableColumn<Row> {
  /** Stable key used to identify the column for highlight + react keys. */
  key: string;
  header: ReactNode;
  align?: ResultTableAlignment;
  /** True for numeric stat columns; right-aligns and uses tabular-nums. */
  numeric?: boolean;
  className?: string;
  headerClassName?: string;
  cellClassName?: string;
  render: (row: Row, rowIndex: number) => ReactNode;
}

/** A footer row (e.g. Average, Total). Rendered inside `<tfoot>`. */
export interface ResultTableFooterRow<Row> {
  /** Visible label rendered into the first column's footer cell. */
  label: ReactNode;
  /** Per-column footer value getter. Return `null` to leave the cell empty. */
  getValue: (column: ResultTableColumn<Row>) => ReactNode;
  /** Stable key for react. */
  key: string;
  className?: string;
}

export interface ResultTableProps<Row> {
  columns: ResultTableColumn<Row>[];
  rows: Row[];
  /** Row key extractor. Falls back to row index. */
  getRowKey?: (row: Row, rowIndex: number) => Key;
  /**
   * The column key whose values should be visually emphasized as the
   * queried metric (subtle background tint, slightly bolder text).
   * Optional — leaderboards set this; game logs typically don't.
   */
  highlightColumnKey?: string;
  /** Footer rows rendered inside `<tfoot>`. Empty array to omit. */
  footerRows?: ResultTableFooterRow<Row>[];
  /** Aria label for the table. Patterns should set this. */
  ariaLabel?: string;
  className?: string;
}

function joinClassNames(...names: Array<string | false | undefined>) {
  return names.filter(Boolean).join(" ");
}

const ALIGN_CLASS: Record<ResultTableAlignment, string> = {
  left: styles.alignLeft,
  right: styles.alignRight,
  center: styles.alignCenter,
};

/**
 * The primary answer-table primitive used inside result patterns.
 * Renders a real `<table>` with `<thead>`, `<tbody>`, optional
 * `<tfoot>` for Average/Total rows, and visual emphasis on the queried
 * metric column.
 *
 * Designed to be the dense, scannable table StatMuse uses underneath
 * its hero card — not card-per-row layouts. Patterns should not wrap
 * rows in cards or add per-row dividers; if you need a different
 * visual shape, use a different primitive.
 */
export default function ResultTable<Row>({
  columns,
  rows,
  getRowKey,
  highlightColumnKey,
  footerRows,
  ariaLabel,
  className,
}: ResultTableProps<Row>) {
  if (rows.length === 0) return null;

  const keyFor = getRowKey ?? ((_row: Row, index: number) => index);

  const renderColumnCell = (
    column: ResultTableColumn<Row>,
    cell: ReactNode,
    isHeader: boolean,
  ) => {
    const isHighlighted = column.key === highlightColumnKey;
    const Tag = isHeader ? "th" : "td";
    return (
      <Tag
        key={column.key}
        scope={isHeader ? "col" : undefined}
        className={joinClassNames(
          ALIGN_CLASS[column.align ?? (column.numeric ? "right" : "left")],
          column.numeric && styles.numeric,
          isHighlighted && styles.highlightCell,
          isHeader ? column.headerClassName : column.cellClassName,
          column.className,
        )}
      >
        {cell}
      </Tag>
    );
  };

  return (
    <div className={joinClassNames(styles.tableScroll, className)}>
      <table className={styles.table} aria-label={ariaLabel}>
        <thead>
          <tr>
            {columns.map((column) =>
              renderColumnCell(column, column.header, true),
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={keyFor(row, rowIndex)}>
              {columns.map((column) =>
                renderColumnCell(column, column.render(row, rowIndex), false),
              )}
            </tr>
          ))}
        </tbody>
        {footerRows && footerRows.length > 0 && (
          <tfoot>
            {footerRows.map((footer) => (
              <tr
                key={footer.key}
                className={joinClassNames(styles.footerRow, footer.className)}
              >
                {columns.map((column, columnIndex) => {
                  const value =
                    columnIndex === 0 ? footer.label : footer.getValue(column);
                  return renderColumnCell(column, value, false);
                })}
              </tr>
            ))}
          </tfoot>
        )}
      </table>
    </div>
  );
}
