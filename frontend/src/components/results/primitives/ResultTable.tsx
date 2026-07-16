import {
  useState,
  type CSSProperties,
  type Key,
  type ReactNode,
} from "react";
import styles from "./ResultTable.module.css";

export type ResultTableAlignment = "left" | "right" | "center";

export interface ResultTableColumn<Row> {
  /** Stable key used to identify the column for highlight + react keys. */
  key: string;
  /** Source row keys represented by this visible column. Used by detail dedupe. */
  sourceKeys?: string[];
  header: ReactNode;
  align?: ResultTableAlignment;
  /** True for numeric stat columns; right-aligns and uses tabular-nums. */
  numeric?: boolean;
  /** Optional low-risk sizing hints for dense answer tables. */
  minWidth?: CSSProperties["minWidth"];
  width?: CSSProperties["width"];
  nowrap?: boolean;
  /** Hide lower-priority columns on narrow screens while preserving desktop. */
  mobilePriority?: "primary" | "secondary";
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
  highlightColumnKeys?: string[];
  /** Footer rows rendered inside `<tfoot>`. Empty array to omit. */
  footerRows?: ResultTableFooterRow<Row>[];
  /** Product row cap. When set, rows above the cap are hidden behind a toggle. */
  rowLimit?: number;
  /** Noun used in the row-cap control label. */
  rowNoun?: string;
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

function columnStyle<Row>(
  column: ResultTableColumn<Row>,
): CSSProperties | undefined {
  const minWidth = column.minWidth ?? defaultMinWidth(column);
  if (!minWidth && !column.width) return undefined;
  return {
    minWidth,
    width: column.width,
  };
}

function defaultMinWidth<Row>(
  column: ResultTableColumn<Row>,
): CSSProperties["minWidth"] | undefined {
  const key = column.key.toLowerCase();
  const header =
    typeof column.header === "string" ? column.header.toLowerCase() : "";
  const text = `${key} ${header}`;

  if (key === "rank" || header === "#" || header === "rank") return "3.5rem";
  if (column.numeric) return "5.25rem";
  if (/\b(date|season|start|end)\b/.test(text)) return "6.75rem";
  if (/\b(player|team|opponent|winner|entity|name|lineup)\b/.test(text)) {
    return "10rem";
  }
  if (/\b(round|result|record|w-l|metric|streak)\b/.test(text)) {
    return "7rem";
  }
  return undefined;
}

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
  highlightColumnKeys,
  footerRows,
  rowLimit,
  rowNoun = "rows",
  ariaLabel,
  className,
}: ResultTableProps<Row>) {
  const [expanded, setExpanded] = useState(false);
  if (rows.length === 0) return null;

  const keyFor = getRowKey ?? ((_row: Row, index: number) => index);
  const highlightKeys = new Set(
    [highlightColumnKey, ...(highlightColumnKeys ?? [])].filter(
      (key): key is string => Boolean(key),
    ),
  );
  const capped = Boolean(rowLimit && rows.length > rowLimit);
  const visibleRows =
    capped && !expanded && rowLimit ? rows.slice(0, rowLimit) : rows;

  const renderColumnCell = (
    column: ResultTableColumn<Row>,
    cell: ReactNode,
    isHeader: boolean,
  ) => {
    const isHighlighted = highlightKeys.has(column.key);
    const Tag = isHeader ? "th" : "td";
    return (
      <Tag
        key={column.key}
        scope={isHeader ? "col" : undefined}
        className={joinClassNames(
          ALIGN_CLASS[column.align ?? (column.numeric ? "right" : "left")],
          column.numeric && styles.numeric,
          isHighlighted && styles.highlightCell,
          column.nowrap === false && styles.allowWrap,
          column.mobilePriority === "secondary" &&
            styles.mobileSecondaryColumn,
          isHeader ? column.headerClassName : column.cellClassName,
          column.className,
        )}
        data-mobile-priority={column.mobilePriority}
        style={columnStyle(column)}
      >
        {cell}
      </Tag>
    );
  };

  return (
    <div className={joinClassNames(styles.tableFrame, className)}>
      <div
        role="region"
        aria-label={
          ariaLabel ? `${ariaLabel} scroll area` : "Scrollable results table"
        }
        tabIndex={0}
        className={styles.tableScroll}
      >
        <table className={styles.table} aria-label={ariaLabel}>
          <thead>
            <tr>
              {columns.map((column) =>
                renderColumnCell(column, column.header, true),
              )}
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row, rowIndex) => (
              <tr key={keyFor(row, rowIndex)}>
                {columns.map((column) =>
                  renderColumnCell(
                    column,
                    column.render(row, rowIndex),
                    false,
                  ),
                )}
              </tr>
            ))}
          </tbody>
          {footerRows && footerRows.length > 0 && (
            <tfoot>
              {footerRows.map((footer) => (
                <tr
                  key={footer.key}
                  className={joinClassNames(
                    styles.footerRow,
                    footer.className,
                  )}
                >
                  {columns.map((column, columnIndex) => {
                    const value =
                      columnIndex === 0
                        ? footer.label
                        : footer.getValue(column);
                    return renderColumnCell(column, value, false);
                  })}
                </tr>
              ))}
            </tfoot>
          )}
        </table>
      </div>
      {capped && rowLimit && (
        <button
          type="button"
          className={styles.rowToggle}
          onClick={() => setExpanded((current) => !current)}
        >
          {expanded
            ? `Show first ${rowLimit} ${rowNoun}`
            : `Show all ${rows.length} ${rowNoun}`}
        </button>
      )}
    </div>
  );
}
