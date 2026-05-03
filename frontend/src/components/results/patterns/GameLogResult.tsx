import type { ReactNode } from "react";
import type { QueryResponse, SectionRow } from "../../../api/types";
import { formatValue } from "../../tableFormatting";
import EntityIdentity from "../primitives/EntityIdentity";
import ResultTable, {
  type ResultTableColumn,
  type ResultTableFooterRow,
} from "../primitives/ResultTable";
import styles from "./GameLogResult.module.css";

interface Props {
  data: QueryResponse;
  sectionKey?: string;
  summaryKey?: string;
}

interface SummaryItem {
  key: string;
  label: string;
  value: string;
}

const STAT_COLUMNS = [
  "minutes",
  "pts",
  "reb",
  "ast",
  "stl",
  "blk",
  "fg",
  "fg3",
  "ft",
  "tov",
  "plus_minus",
];

const TABLE_LABELS: Record<string, string> = {
  ast: "AST",
  blk: "BLK",
  date: "Date",
  fg: "FG",
  fg3: "3P",
  ft: "FT",
  location: "",
  minutes: "MIN",
  opponent: "Opp",
  plus_minus: "+/-",
  pts: "PTS",
  reb: "REB",
  stl: "STL",
  team: "TM",
  tov: "TOV",
  wl: "W/L",
};

const COMPOSITE_STATS: Record<
  string,
  { made: string; attempt: string; pct: string }
> = {
  fg: { made: "fgm", attempt: "fga", pct: "fg_pct" },
  fg3: { made: "fg3m", attempt: "fg3a", pct: "fg3_pct" },
  ft: { made: "ftm", attempt: "fta", pct: "ft_pct" },
};

export default function GameLogResult({
  data,
  sectionKey = "game_log",
  summaryKey = "summary",
}: Props) {
  const rawRows = data.result?.sections?.[sectionKey] ?? [];
  if (rawRows.length === 0) return null;

  const rows = orderedRows(rawRows);
  const summary = data.result?.sections?.[summaryKey]?.[0];
  const columns = tableColumns(rows);
  const footerRows = tableFooters(rows, summary);
  const items = summaryItems(summary);

  return (
    <section className={styles.pattern} aria-label="Game log result">
      {items.length > 0 && (
        <div className={styles.summaryStrip} aria-label="Game-log averages">
          {items.map((item) => (
            <span className={styles.summaryItem} key={item.key}>
              <span className={styles.summaryValue}>{item.value}</span>
              <span className={styles.summaryLabel}>{item.label}</span>
            </span>
          ))}
        </div>
      )}
      <ResultTable
        rows={rows}
        columns={columns}
        footerRows={footerRows}
        ariaLabel="Game log"
        getRowKey={rowKey}
      />
    </section>
  );
}

function tableColumns(
  rows: SectionRow[],
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [
    {
      key: "rank",
      header: "#",
      align: "center",
      render: (_row, index) => index + 1,
    },
    {
      key: "date",
      header: TABLE_LABELS.date,
      render: (row) => textValue(row, "game_date") ?? "—",
    },
    {
      key: "player",
      header: "Player",
      render: playerCell,
    },
    {
      key: "team",
      header: TABLE_LABELS.team,
      render: teamCell,
    },
    {
      key: "location",
      header: TABLE_LABELS.location,
      align: "center",
      render: locationCell,
    },
    {
      key: "opponent",
      header: TABLE_LABELS.opponent,
      render: opponentCell,
    },
  ];

  if (rows.some((row) => hasValue(row.wl))) {
    columns.push({
      key: "wl",
      header: TABLE_LABELS.wl,
      align: "center",
      render: (row) => textValue(row, "wl")?.toUpperCase() ?? "—",
    });
  }

  for (const key of STAT_COLUMNS) {
    if (!hasStatColumn(rows, key)) continue;
    columns.push(statColumn(key));
  }

  return columns;
}

function statColumn(key: string): ResultTableColumn<SectionRow> {
  return {
    key,
    header: TABLE_LABELS[key] ?? key,
    numeric: true,
    render: (row) => statValue(row, key),
  };
}

function tableFooters(
  rows: SectionRow[],
  summary: SectionRow | undefined,
): Array<ResultTableFooterRow<SectionRow>> {
  return [
    {
      key: "average",
      label: "Average",
      getValue: (column) => footerValue("avg", column.key, rows, summary),
    },
    {
      key: "total",
      label: "Total",
      getValue: (column) => footerValue("sum", column.key, rows, summary),
    },
  ];
}

function footerValue(
  kind: "avg" | "sum",
  key: string,
  rows: SectionRow[],
  summary: SectionRow | undefined,
): ReactNode {
  if (COMPOSITE_STATS[key]) {
    return compositeFooterValue(kind, key, rows, summary);
  }
  if (!STAT_COLUMNS.includes(key)) return null;

  const summaryKey = `${summaryPrefix(key)}_${kind}`;
  if (summary && hasValue(summary[summaryKey])) {
    return formatStatValue(summary[summaryKey], key);
  }

  const values = rows
    .map((row) => row[key])
    .filter((value): value is number => typeof value === "number");
  if (values.length === 0) return null;

  const total = values.reduce((sum, value) => sum + value, 0);
  const value = kind === "avg" ? total / values.length : total;
  return formatStatValue(value, key);
}

function compositeFooterValue(
  kind: "avg" | "sum",
  key: string,
  rows: SectionRow[],
  summary: SectionRow | undefined,
): string | null {
  const config = COMPOSITE_STATS[key];
  const madeKey = `${config.made}_${kind}`;
  const attemptKey = `${config.attempt}_${kind}`;

  if (summary && hasValue(summary[madeKey]) && hasValue(summary[attemptKey])) {
    return `${formatValue(summary[madeKey], madeKey)}-${formatValue(
      summary[attemptKey],
      attemptKey,
    )}`;
  }

  const made = numericValues(rows, config.made);
  const attempts = numericValues(rows, config.attempt);
  if (made.length === 0 || attempts.length === 0) return null;

  const madeTotal = made.reduce((sum, value) => sum + value, 0);
  const attemptTotal = attempts.reduce((sum, value) => sum + value, 0);
  if (kind === "sum") {
    return `${formatValue(madeTotal, config.made)}-${formatValue(
      attemptTotal,
      config.attempt,
    )}`;
  }

  return `${formatValue(madeTotal / made.length, config.made)}-${formatValue(
    attemptTotal / attempts.length,
    config.attempt,
  )}`;
}

function summaryItems(summary: SectionRow | undefined): SummaryItem[] {
  if (!summary) return [];
  const items: SummaryItem[] = [];
  addSummaryItem(items, summary, "games", "GP");
  addSummaryItem(items, summary, "pts_avg", "PTS");
  addSummaryItem(items, summary, "reb_avg", "REB");
  addSummaryItem(items, summary, "ast_avg", "AST");
  addSummaryItem(items, summary, "minutes_avg", "MIN");
  return items;
}

function addSummaryItem(
  items: SummaryItem[],
  row: SectionRow,
  key: string,
  label: string,
) {
  if (!hasValue(row[key])) return;
  items.push({ key, label, value: formatValue(row[key], key) });
}

function orderedRows(rows: SectionRow[]): SectionRow[] {
  return [...rows].sort((a, b) => {
    const aDate = textValue(a, "game_date");
    const bDate = textValue(b, "game_date");
    if (aDate && bDate && aDate !== bDate) return bDate.localeCompare(aDate);
    return 0;
  });
}

function playerCell(row: SectionRow): ReactNode {
  return (
    <EntityIdentity
      kind="player"
      playerId={identityId(row.player_id)}
      playerName={textValue(row, "player_name") ?? textValue(row, "player")}
      teamAbbr={textValue(row, "team_abbr")}
      size="sm"
    />
  );
}

function teamCell(row: SectionRow): ReactNode {
  return (
    <span className={styles.teamCell}>
      <EntityIdentity
        kind="team"
        teamId={identityId(row.team_id)}
        teamAbbr={textValue(row, "team_abbr")}
        teamName={textValue(row, "team_name")}
        size="sm"
      />
    </span>
  );
}

function opponentCell(row: SectionRow): ReactNode {
  return (
    <span className={styles.teamCell}>
      <EntityIdentity
        kind="team"
        teamId={identityId(row.opponent_team_id)}
        teamAbbr={textValue(row, "opponent_team_abbr")}
        teamName={textValue(row, "opponent_team_name")}
        size="sm"
      />
    </span>
  );
}

function locationCell(row: SectionRow): string {
  if (isTruthyFlag(row.is_away)) return "@";
  if (isTruthyFlag(row.is_home)) return "vs";
  return "—";
}

function hasStatColumn(rows: SectionRow[], key: string): boolean {
  const config = COMPOSITE_STATS[key];
  if (config) {
    return rows.some(
      (row) =>
        hasValue(row[config.made]) ||
        hasValue(row[config.attempt]) ||
        hasValue(row[config.pct]),
    );
  }
  return rows.some((row) => hasValue(row[key]));
}

function statValue(row: SectionRow, key: string): ReactNode {
  const config = COMPOSITE_STATS[key];
  if (config) {
    return madeAttemptStat(row, config.made, config.attempt, config.pct);
  }
  return formatStatValue(row[key], key);
}

function madeAttemptStat(
  row: SectionRow,
  madeKey: string,
  attemptKey: string,
  pctKey: string,
): string {
  if (hasValue(row[madeKey]) && hasValue(row[attemptKey])) {
    return `${formatValue(row[madeKey], madeKey)}-${formatValue(
      row[attemptKey],
      attemptKey,
    )}`;
  }
  if (hasValue(row[pctKey])) return formatValue(row[pctKey], pctKey);
  if (hasValue(row[madeKey])) return formatValue(row[madeKey], madeKey);
  return "—";
}

function formatStatValue(value: unknown, key: string): string {
  if (key === "plus_minus" && typeof value === "number") {
    const formatted = formatValue(value, key);
    return value > 0 ? `+${formatted}` : formatted;
  }
  return formatValue(value, key);
}

function summaryPrefix(key: string): string {
  return key === "minutes" ? "minutes" : key;
}

function numericValues(rows: SectionRow[], key: string): number[] {
  return rows
    .map((row) => row[key])
    .filter((value): value is number => typeof value === "number");
}

function rowKey(row: SectionRow, index: number): string {
  return String(row.game_id ?? `${row.game_date ?? "game"}-${index}`);
}

function textValue(row: SectionRow, key: string): string | null {
  const value = row[key];
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function identityId(value: unknown): number | string | null {
  return typeof value === "number" || typeof value === "string" ? value : null;
}

function isTruthyFlag(value: unknown): boolean {
  if (value === true || value === 1) return true;
  if (typeof value === "string") {
    return ["1", "true", "yes", "y"].includes(value.trim().toLowerCase());
  }
  return false;
}

function hasValue(value: unknown): boolean {
  return value !== null && value !== undefined && value !== "";
}
