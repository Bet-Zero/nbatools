import type { ReactNode } from "react";
import type {
  QueryResponse,
  ResultMetadata,
  SectionRow,
} from "../../../api/types";
import { Stat } from "../../../design-system";
import { formatValue } from "../../tableFormatting";
import EntityIdentity from "../primitives/EntityIdentity";
import RawDetailToggle from "../primitives/RawDetailToggle";
import ResultTable, {
  type ResultTableColumn,
  type ResultTableFooterRow,
} from "../primitives/ResultTable";
import styles from "./GameLogResult.module.css";

type GameLogMode = "auto" | "player" | "team";

interface Props {
  data: QueryResponse;
  sectionKey?: string;
  summaryKey?: string;
  fallbackSectionKey?: string;
  mode?: GameLogMode;
  metricKey?: string;
  preserveOrder?: boolean;
  showSummaryStrip?: boolean;
  rawDetailTitle?: string;
  detailSectionKeys?: string[];
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
  "fg3m",
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
  fg3m: "3PM",
  fg3: "3P",
  ft: "FT",
  location: "",
  minutes: "MIN",
  opponent: "Opp",
  plus_minus: "+/-",
  pts: "PTS",
  reb: "REB",
  score: "Score",
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
  fallbackSectionKey,
  mode = "auto",
  metricKey,
  preserveOrder = false,
  showSummaryStrip = true,
  rawDetailTitle,
  detailSectionKeys = [],
}: Props) {
  const rawRows = sectionRows(data, sectionKey, fallbackSectionKey);
  if (rawRows.length === 0) return null;

  const rows = orderedRows(rawRows, preserveOrder);
  const summary = data.result?.sections?.[summaryKey]?.[0];
  const resolvedMode = gameLogMode(rows, mode);
  const metric = metricColumn(rows, data.result?.metadata, metricKey);
  const columns = tableColumns(rows, data, resolvedMode);
  const footerRows = summary ? tableFooters(rows, summary) : [];
  const items = summary ? summaryItems(summary) : contextItems(data, rows);

  return (
    <section className={styles.pattern} aria-label="Game log result">
      {showSummaryStrip && items.length > 0 && (
        <div className={styles.summaryStrip} aria-label="Game-log averages">
          {items.map((item) => (
            <Stat
              className={styles.summaryItem}
              key={item.key}
              label={item.label}
              value={item.value}
            />
          ))}
        </div>
      )}
      <ResultTable
        rows={rows}
        columns={columns}
        highlightColumnKey={metric ?? undefined}
        footerRows={footerRows}
        ariaLabel="Game log"
        getRowKey={rowKey}
      />
      {rawDetailTitle && <RawDetailToggle title={rawDetailTitle} rows={rows} />}
      {detailSectionKeys.map((key) => {
        const detailRows = data.result?.sections?.[key] ?? [];
        if (detailRows.length === 0) return null;
        return (
          <RawDetailToggle
            key={key}
            title={detailTitle(key)}
            rows={detailRows}
          />
        );
      })}
    </section>
  );
}

function tableColumns(
  rows: SectionRow[],
  data: QueryResponse,
  mode: Exclude<GameLogMode, "auto">,
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [
    {
      key: "rank",
      header: "#",
      align: "center",
      render: (_row, index) => index + 1,
    },
  ];

  if (mode === "player") {
    columns.push(
      {
        key: "player",
        header: "Player",
        render: playerCell,
      },
      {
        key: "date",
        header: TABLE_LABELS.date,
        render: (row) => textValue(row, "game_date") ?? "—",
      },
      {
        key: "team",
        header: TABLE_LABELS.team,
        render: (row) => teamCell(row, data),
      },
    );
  } else {
    columns.push(
      {
        key: "date",
        header: TABLE_LABELS.date,
        render: (row) => textValue(row, "game_date") ?? "—",
      },
      {
        key: "team",
        header: "Team",
        render: (row) => teamCell(row, data),
      },
    );
  }

  columns.push(
    {
      key: "location",
      header: TABLE_LABELS.location,
      align: "center",
      render: locationCell,
    },
    {
      key: "opponent",
      header: TABLE_LABELS.opponent,
      render: (row) => opponentCell(row, data),
    },
  );

  if (hasScoreColumn(rows, mode)) {
    columns.push({
      key: "score",
      header: TABLE_LABELS.score,
      align: "center",
      render: scoreCell,
    });
  }

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

function sectionRows(
  data: QueryResponse,
  sectionKey: string,
  fallbackSectionKey: string | undefined,
): SectionRow[] {
  const rows = data.result?.sections?.[sectionKey] ?? [];
  if (rows.length > 0 || !fallbackSectionKey) return rows;
  return data.result?.sections?.[fallbackSectionKey] ?? [];
}

function orderedRows(rows: SectionRow[], preserveOrder: boolean): SectionRow[] {
  if (preserveOrder) return [...rows];
  return [...rows].sort((a, b) => {
    const aDate = textValue(a, "game_date");
    const bDate = textValue(b, "game_date");
    if (aDate && bDate && aDate !== bDate) return bDate.localeCompare(aDate);
    return 0;
  });
}

function gameLogMode(
  rows: SectionRow[],
  mode: GameLogMode,
): Exclude<GameLogMode, "auto"> {
  if (mode !== "auto") return mode;
  return rows.some(
    (row) =>
      hasValue(row.player_name) ||
      hasValue(row.player) ||
      hasValue(row.player_id),
  )
    ? "player"
    : "team";
}

function metricColumn(
  rows: SectionRow[],
  metadata: ResultMetadata | undefined,
  explicitMetric: string | undefined,
): string | null {
  if (explicitMetric && rows.some((row) => hasValue(row[explicitMetric]))) {
    return explicitMetric;
  }

  const stat = metadataText(metadata, "stat");
  if (stat && rows.some((row) => hasValue(row[stat]))) return stat;
  return null;
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

function teamCell(row: SectionRow, data: QueryResponse): ReactNode {
  const teamContext = data.result?.metadata?.team_context;
  return (
    <span className={styles.teamCell}>
      <EntityIdentity
        kind="team"
        teamId={identityId(row.team_id) ?? teamContext?.team_id}
        teamAbbr={textValue(row, "team_abbr") ?? teamContext?.team_abbr}
        teamName={
          textValue(row, "team_name") ??
          textValue(row, "team") ??
          teamContext?.team_name
        }
        size="sm"
      />
    </span>
  );
}

function opponentCell(row: SectionRow, data: QueryResponse): ReactNode {
  const opponentContext = data.result?.metadata?.opponent_context;
  return (
    <span className={styles.teamCell}>
      <EntityIdentity
        kind="team"
        teamId={identityId(row.opponent_team_id) ?? opponentContext?.team_id}
        teamAbbr={
          textValue(row, "opponent_team_abbr") ??
          textValue(row, "opponent") ??
          opponentContext?.team_abbr
        }
        teamName={
          textValue(row, "opponent_team_name") ??
          textValue(row, "opponent") ??
          opponentContext?.team_name
        }
        size="sm"
      />
    </span>
  );
}

function hasScoreColumn(
  rows: SectionRow[],
  mode: Exclude<GameLogMode, "auto">,
): boolean {
  return rows.some((row) => {
    if (hasValue(row.team_score) && hasValue(row.opponent_score)) return true;
    if (mode === "team" && hasValue(row.pts) && hasValue(row.opponent_pts)) {
      return true;
    }
    return false;
  });
}

function scoreCell(row: SectionRow): string {
  const teamScore =
    numericValue(row, "team_score") ??
    numericValue(row, "pts_team") ??
    numericValue(row, "team_pts") ??
    numericValue(row, "pts");
  const opponentScore =
    numericValue(row, "opponent_score") ??
    numericValue(row, "opponent_pts") ??
    numericValue(row, "opp_pts");

  if (teamScore === null || opponentScore === null) return "—";
  return `${formatValue(teamScore, "team_score")}-${formatValue(
    opponentScore,
    "opponent_score",
  )}`;
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
  return [
    row.game_id,
    row.player_id,
    row.team_id,
    row.game_date,
    index,
  ]
    .filter(hasValue)
    .join("-");
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

function numericValue(row: SectionRow, key: string): number | null {
  const value = row[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
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

function contextItems(data: QueryResponse, rows: SectionRow[]): SummaryItem[] {
  const metadata = data.result?.metadata;
  const items: SummaryItem[] = [
    {
      key: "games",
      label: rows.length === 1 ? "Game" : "Games",
      value: formatValue(rows.length, "games"),
    },
  ];

  const condition = conditionText(metadata);
  if (condition) {
    items.push({ key: "condition", label: "Filter", value: condition });
  }

  const season = seasonText(metadata);
  if (season) items.push({ key: "season", label: "Season", value: season });

  const seasonType = metadataText(metadata, "season_type");
  if (seasonType) {
    items.push({ key: "season_type", label: "Type", value: seasonType });
  }

  return items;
}

function conditionText(metadata: ResultMetadata | undefined): string | null {
  const conditions: string[] = [];
  for (const key of ["threshold_conditions", "extra_conditions"]) {
    const raw = metadata?.[key];
    if (!Array.isArray(raw)) continue;
    for (const condition of raw) {
      if (!condition || typeof condition !== "object") continue;
      const conditionRow = condition as Record<string, unknown>;
      if (typeof conditionRow.stat !== "string") continue;
      conditions.push(
        formatCondition(
          conditionRow.stat,
          typeof conditionRow.min_value === "number"
            ? conditionRow.min_value
            : null,
          typeof conditionRow.max_value === "number"
            ? conditionRow.max_value
            : null,
        ),
      );
    }
  }

  if (conditions.length === 0) {
    const occurrenceEvent = metadata?.occurrence_event;
    if (
      occurrenceEvent &&
      typeof occurrenceEvent === "object" &&
      !Array.isArray(occurrenceEvent)
    ) {
      const event = occurrenceEvent as Record<string, unknown>;
      if (typeof event.stat === "string") {
        conditions.push(
          formatCondition(
            event.stat,
            typeof event.min_value === "number" ? event.min_value : null,
            typeof event.max_value === "number" ? event.max_value : null,
          ),
        );
      }
    }
  }

  if (conditions.length === 0) {
    const stat = metadataText(metadata, "stat");
    if (stat) {
      conditions.push(
        formatCondition(
          stat,
          metadataNumber(metadata, "min_value"),
          metadataNumber(metadata, "max_value"),
        ),
      );
    }
  }

  return conditions.length > 0 ? Array.from(new Set(conditions)).join(", ") : null;
}

function formatCondition(
  stat: string,
  minValue: number | null,
  maxValue: number | null,
): string {
  const label = TABLE_LABELS[stat] ?? stat.toUpperCase();
  if (minValue !== null && maxValue !== null) {
    return `${formatValue(minValue, stat)}-${formatValue(maxValue, stat)} ${label}`;
  }
  if (minValue !== null) return `${formatValue(minValue, stat)}+ ${label}`;
  if (maxValue !== null) return `<= ${formatValue(maxValue, stat)} ${label}`;
  return label;
}

function seasonText(metadata: ResultMetadata | undefined): string | null {
  const start = metadataText(metadata, "start_season");
  const end = metadataText(metadata, "end_season");
  if (start && end) return start === end ? start : `${start} to ${end}`;
  return metadataText(metadata, "season") ?? start ?? end;
}

function metadataText(
  metadata: ResultMetadata | undefined,
  key: string,
): string | null {
  const value = metadata?.[key];
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function metadataNumber(
  metadata: ResultMetadata | undefined,
  key: string,
): number | null {
  const value = metadata?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function detailTitle(key: string): string {
  const labels: Record<string, string> = {
    by_season: "By Season Detail",
    summary: "Summary Detail",
    top_performers: "Top Performers Detail",
  };
  return labels[key] ?? `${key.replace(/_/g, " ")} Detail`;
}
