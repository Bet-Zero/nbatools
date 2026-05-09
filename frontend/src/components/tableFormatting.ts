/** Format a column header: short uppercase stat names stay as-is, others get title-cased. */
export function formatColHeader(col: string): string {
  if (col.length <= 5 && col === col.toUpperCase()) return col;
  return col.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

const INTEGER_FORMATTER = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 0,
});

const ONE_DECIMAL_FORMATTER = new Intl.NumberFormat(undefined, {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const PROSE_NUMBER_FORMATTER = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 1,
});

const COMPACT_DATE_FORMATTER = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  timeZone: "UTC",
});

const LONG_DATE_FORMATTER = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

const COMPACT_DATE_COLUMNS = new Set([
  "game_date",
  "window_start_date",
  "window_end_date",
]);

const FORCE_ONE_DECIMAL_PATTERNS = [
  /_avg$/,
  /_per_game$/,
  /_rating$/,
  /^pace$/,
  /^stretch_value$/,
];

/** Format a cell value for display. */
export function formatValue(val: unknown, col: string): string {
  if (val === null || val === undefined) return "—";
  if (typeof val === "number") {
    return formatNumericValue(val, col);
  }
  if (typeof val === "string" && isCompactDateColumn(col)) {
    return formatCompactDate(val);
  }
  return String(val);
}

export function formatAverageValue(val: unknown, col: string): string {
  if (val === null || val === undefined) return "—";
  if (typeof val === "number") {
    const lc = col.toLowerCase();
    if (isPercentageColumn(lc)) return formatPercent(val);
    return ONE_DECIMAL_FORMATTER.format(val);
  }
  if (typeof val === "string" && isCompactDateColumn(col)) {
    return formatCompactDate(val);
  }
  return String(val);
}

export function formatProseValue(val: unknown, col: string): string {
  if (val === null || val === undefined) return "—";
  if (typeof val === "number") {
    return formatProseNumericValue(val, col);
  }
  if (typeof val === "string" && isCompactDateColumn(col)) {
    return formatCompactDate(val);
  }
  return String(val);
}

export function trimProseTrailingZeroes(value: string): string {
  return value.replace(/\b(-?\d+)\.0\b/g, "$1");
}

export function formatCompactDate(value: string | null): string {
  if (!value) return "—";
  const parsed = parseDate(value);
  if (!parsed) return value;
  return COMPACT_DATE_FORMATTER.format(parsed);
}

export function formatLongDate(value: string | null): string {
  if (!value) return "—";
  const parsed = parseDate(value);
  if (!parsed) return value;
  return LONG_DATE_FORMATTER.format(parsed);
}

export function formatLongDateRange(
  start: string | null,
  end: string | null,
): string | null {
  if (!start && !end) return null;
  if (start && end) {
    return start === end
      ? formatLongDate(start)
      : `${formatLongDate(start)} to ${formatLongDate(end)}`;
  }
  return formatLongDate(start ?? end);
}

function formatNumericValue(value: number, col: string): string {
  const lc = col.toLowerCase();
  if (isPercentageColumn(lc)) return formatPercent(value);
  if (shouldForceOneDecimal(lc)) return ONE_DECIMAL_FORMATTER.format(value);
  if (Number.isInteger(value)) return INTEGER_FORMATTER.format(value);
  return ONE_DECIMAL_FORMATTER.format(value);
}

function formatProseNumericValue(value: number, col: string): string {
  const lc = col.toLowerCase();
  if (isPercentageColumn(lc)) return formatProsePercent(value);
  if (Number.isInteger(value)) return INTEGER_FORMATTER.format(value);
  return PROSE_NUMBER_FORMATTER.format(value);
}

function formatPercent(value: number): string {
  const percent = value >= 0 && value <= 1 ? value * 100 : value;
  return `${ONE_DECIMAL_FORMATTER.format(percent)}%`;
}

function formatProsePercent(value: number): string {
  const percent = value >= 0 && value <= 1 ? value * 100 : value;
  const formatted = Number.isInteger(percent)
    ? INTEGER_FORMATTER.format(percent)
    : PROSE_NUMBER_FORMATTER.format(percent);
  return `${formatted}%`;
}

function isPercentageColumn(column: string): boolean {
  return column.includes("pct") || column.endsWith("%");
}

function shouldForceOneDecimal(column: string): boolean {
  return FORCE_ONE_DECIMAL_PATTERNS.some((pattern) => pattern.test(column));
}

function isCompactDateColumn(column: string): boolean {
  return COMPACT_DATE_COLUMNS.has(column.toLowerCase());
}

function parseDate(value: string): Date | null {
  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (match) {
    const year = Number(match[1]);
    const month = Number(match[2]);
    const day = Number(match[3]);
    return new Date(Date.UTC(year, month - 1, day));
  }

  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}
