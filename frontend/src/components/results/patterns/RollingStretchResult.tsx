import type { ReactNode } from "react";
import type {
  PlayerIdentityContext,
  QueryResponse,
  ResultMetadata,
  SectionRow,
} from "../../../api/types";
import { Badge } from "../../../design-system";
import {
  formatAverageValue,
  formatColHeader,
  formatCompactDate,
  formatValue,
} from "../../tableFormatting";
import EntityIdentity from "../primitives/EntityIdentity";
import ResultHero from "../primitives/ResultHero";
import ResultTable, {
  type ResultTableColumn,
} from "../primitives/ResultTable";
import styles from "./RollingStretchResult.module.css";

interface Props {
  data: QueryResponse;
  sectionKey?: string;
}

const STRETCH_METRIC_LABELS: Record<string, string> = {
  ast: "APG",
  blk: "BPG",
  efg_pct: "eFG%",
  fg_pct: "FG%",
  fg3_pct: "3P%",
  fg3m: "3PM/G",
  ft_pct: "FT%",
  game_score: "Game Score",
  minutes: "MPG",
  plus_minus: "+/-",
  pts: "PPG",
  reb: "RPG",
  stl: "SPG",
  ts_pct: "TS%",
};

const STRETCH_PHRASES: Record<string, string> = {
  ast: "assist stretch",
  blk: "block stretch",
  efg_pct: "effective-field-goal stretch",
  fg_pct: "shooting stretch",
  fg3_pct: "three-point shooting stretch",
  fg3m: "three-point stretch",
  ft_pct: "free-throw stretch",
  game_score: "Game Score stretch",
  minutes: "minute stretch",
  plus_minus: "plus-minus stretch",
  pts: "scoring stretch",
  reb: "rebounding stretch",
  stl: "steal stretch",
  ts_pct: "true-shooting stretch",
};

const WINDOW_SUPPORT_KEYS = [
  "games_played",
  "pts_per_game",
  "reb_per_game",
  "ast_per_game",
  "fg_pct",
  "fg3_pct",
  "ts_pct",
  "game_score",
  "minutes_per_game",
  "window_end_season",
];

const GAME_LOG_STAT_KEYS = [
  "pts",
  "reb",
  "ast",
  "fg3m",
  "stl",
  "blk",
  "tov",
  "minutes",
];

const TABLE_LABELS: Record<string, string> = {
  ast: "AST",
  ast_per_game: "APG",
  blk: "BLK",
  fg3m: "3PM",
  fg3_pct: "3P%",
  fg_pct: "FG%",
  game_score: "Game Score",
  games_played: "GP",
  minutes: "MIN",
  minutes_per_game: "MPG",
  plus_minus: "+/-",
  pts: "PTS",
  pts_per_game: "PPG",
  reb: "REB",
  reb_per_game: "RPG",
  stl: "STL",
  ts_pct: "TS%",
  tov: "TOV",
  window_end_season: "Season",
};

export default function RollingStretchResult({
  data,
  sectionKey = "leaderboard",
}: Props) {
  const rows = data.result?.sections?.[sectionKey] ?? [];
  if (rows.length === 0) return null;

  const metadata = data.result?.metadata;
  const topRow = rows[0];
  const metric = stretchMetric(rows, metadata, data.query);
  const namedPlayer = namedPlayerContext(metadata);
  const isNamedPlayer = Boolean(namedPlayer);
  const note = topCountNote(metadata, rows.length);

  return (
    <section className={styles.pattern} aria-label="Rolling stretch result">
      <ResultHero
        sentence={
          isNamedPlayer
            ? namedPlayerSentence(topRow, metric, data, namedPlayer)
            : leagueSentence(topRow, metric, data)
        }
        subjectIllustration={heroIdentity(topRow, namedPlayer)}
        tone="accent"
      />
      {isNamedPlayer ? (
        <NamedPlayerBody data={data} rows={rows} metric={metric} note={note} />
      ) : (
        <LeagueBody rows={rows} metric={metric} note={note} />
      )}
    </section>
  );
}

function LeagueBody({
  rows,
  metric,
  note,
}: {
  rows: SectionRow[];
  metric: string;
  note: string | null;
}) {
  return (
    <div className={styles.section}>
      <ResultTable
        rows={rows}
        columns={leagueColumns(rows, metric)}
        highlightColumnKey="stretch_value"
        ariaLabel="Rolling stretch leaderboard"
        getRowKey={windowRowKey}
      />
      {note && <p className={styles.tableNote}>{note}</p>}
    </div>
  );
}

function NamedPlayerBody({
  data,
  rows,
  metric,
  note,
}: {
  data: QueryResponse;
  rows: SectionRow[];
  metric: string;
  note: string | null;
}) {
  const gameRows = bestWindowGameRows(data);

  return (
    <>
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>Top Windows</h3>
        <ResultTable
          rows={rows}
          columns={namedWindowColumns(rows, metric)}
          highlightColumnKey="stretch_value"
          ariaLabel="Player rolling stretch windows"
          getRowKey={windowRowKey}
        />
        {note && <p className={styles.tableNote}>{note}</p>}
      </div>
      {gameRows.length > 0 && (
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>Best Window Games</h3>
          <ResultTable
            rows={gameRows}
            columns={gameLogColumns(gameRows)}
            highlightColumnKey={gameLogHighlightKey(gameRows, metric)}
            ariaLabel="Best stretch game log"
            getRowKey={gameRowKey}
          />
        </div>
      )}
    </>
  );
}

function leagueColumns(
  rows: SectionRow[],
  metric: string,
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [
    {
      key: "rank",
      header: "Rank",
      align: "center",
      render: rankCell,
    },
    {
      key: "player",
      header: "Player",
      render: playerCell,
    },
    {
      key: "window_size",
      header: "Window",
      align: "center",
      render: windowSizeCell,
    },
    stretchValueColumn(metric),
    {
      key: "window_start_date",
      header: "Start",
      render: (row) => formatCompactDate(textValue(row, "window_start_date")),
    },
    {
      key: "window_end_date",
      header: "End",
      render: (row) => formatCompactDate(textValue(row, "window_end_date")),
    },
  ];

  for (const key of supportingWindowKeys(rows, metric, 2)) {
    columns.push(valueColumn(key));
  }

  return columns;
}

function namedWindowColumns(
  rows: SectionRow[],
  metric: string,
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [
    {
      key: "rank",
      header: "Rank",
      align: "center",
      render: rankCell,
    },
    {
      key: "window_size",
      header: "Window",
      align: "center",
      render: windowSizeCell,
    },
    {
      key: "date_range",
      header: "Dates",
      render: (row) => (
        <span className={styles.dateRange}>
          {formatCompactDate(textValue(row, "window_start_date"))} to{" "}
          {formatCompactDate(textValue(row, "window_end_date"))}
        </span>
      ),
    },
    stretchValueColumn(metric),
  ];

  for (const key of supportingWindowKeys(rows, metric, 2)) {
    columns.push(valueColumn(key));
  }

  return columns;
}

function gameLogColumns(
  rows: SectionRow[],
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [
    {
      key: "date",
      header: "Date",
      render: (row) => formatCompactDate(textValue(row, "game_date")),
    },
    {
      key: "opponent",
      header: "Opp",
      render: opponentCell,
    },
    {
      key: "wl",
      header: "Result",
      align: "center",
      render: resultCell,
    },
  ];

  for (const key of GAME_LOG_STAT_KEYS) {
    if (!rows.some((row) => hasValue(row[key]))) continue;
    columns.push(valueColumn(key));
  }

  return columns;
}

function stretchValueColumn(metric: string): ResultTableColumn<SectionRow> {
  return {
    key: "stretch_value",
    header: STRETCH_METRIC_LABELS[metric] ?? tableLabel(metric),
    numeric: true,
    render: (row) => (
      <span className={styles.metricValue}>
        {stretchValue(row, metric, true)}
      </span>
    ),
  };
}

function valueColumn(key: string): ResultTableColumn<SectionRow> {
  return {
    key,
    header: tableLabel(key),
    numeric: isNumericKey(key),
    render: (row) => formatTableValue(row[key], key),
  };
}

function rankCell(row: SectionRow, index: number): ReactNode {
  return (
    <Badge className={styles.rankBadge} variant="accent" size="sm">
      {rankValue(row, index)}
    </Badge>
  );
}

function playerCell(row: SectionRow): ReactNode {
  return (
    <EntityIdentity
      kind="player"
      playerId={identityId(row.player_id)}
      playerName={textValue(row, "player_name") ?? textValue(row, "player")}
      teamAbbr={textValue(row, "team_abbr")}
      teamName={textValue(row, "team_name")}
      size="sm"
    />
  );
}

function opponentCell(row: SectionRow): ReactNode {
  return (
    <span className={styles.teamCell}>
      <EntityIdentity
        kind="team"
        teamId={identityId(row.opponent_team_id)}
        teamAbbr={textValue(row, "opponent_team_abbr") ?? textValue(row, "opponent")}
        teamName={textValue(row, "opponent_team_name") ?? textValue(row, "opponent")}
        size="sm"
      />
    </span>
  );
}

function resultCell(row: SectionRow): ReactNode {
  const wl = textValue(row, "wl")?.toUpperCase();
  if (wl !== "W" && wl !== "L") return "—";
  return (
    <Badge
      className={styles.resultBadge}
      variant={wl === "W" ? "win" : "loss"}
      size="sm"
    >
      {wl}
    </Badge>
  );
}

function windowSizeCell(row: SectionRow): string {
  const size =
    numericValue(row, "window_size") ?? numericValue(row, "games_in_window");
  return size ? `${size} games` : "—";
}

function leagueSentence(
  row: SectionRow,
  metric: string,
  data: QueryResponse,
): string {
  const scope = scopePhrase(row, data.result?.metadata, data.query);
  return `Best ${windowSize(row, data.result?.metadata)}-game ${metricPhrase(metric)}${
    scope ? ` ${scope}` : ""
  }: ${playerName(
    row,
  )} averaged ${stretchValue(row, metric)} from ${formatCompactDate(
    textValue(row, "window_start_date"),
  )} to ${formatCompactDate(textValue(row, "window_end_date"))}.`;
}

function namedPlayerSentence(
  row: SectionRow,
  metric: string,
  data: QueryResponse,
  player: PlayerIdentityContext | null,
): string {
  const name = player?.player_name ?? playerName(row);
  const scope = scopePhrase(row, data.result?.metadata, data.query);
  return `${name}'s best ${windowSize(row, data.result?.metadata)}-game ${metricPhrase(
    metric,
  )}${scope ? ` ${scope}` : ""}: ${stretchValue(
    row,
    metric,
  )} from ${formatCompactDate(textValue(row, "window_start_date"))} to ${formatCompactDate(
    textValue(row, "window_end_date"),
  )}.`;
}

function heroIdentity(
  row: SectionRow,
  player: PlayerIdentityContext | null,
): ReactNode {
  return (
    <EntityIdentity
      kind="player"
      playerId={player?.player_id ?? identityId(row.player_id)}
      playerName={
        player?.player_name ??
        textValue(row, "player_name") ??
        textValue(row, "player")
      }
      teamAbbr={textValue(row, "team_abbr")}
    />
  );
}

function namedPlayerContext(
  metadata: ResultMetadata | undefined,
): PlayerIdentityContext | null {
  const context = metadata?.player_context;
  if (
    context &&
    typeof context === "object" &&
    typeof context.player_name === "string"
  ) {
    return context;
  }
  return null;
}

function bestWindowGameRows(data: QueryResponse): SectionRow[] {
  const sections = data.result?.sections ?? {};
  for (const key of ["best_window_game_log", "window_game_log", "game_log"]) {
    const rows = sections[key] ?? [];
    if (rows.length > 0) return rows;
  }
  return [];
}

function supportingWindowKeys(
  rows: SectionRow[],
  metric: string,
  limit: number,
): string[] {
  const excluded = new Set([
    "rank",
    "player_id",
    "player_name",
    "player",
    "team_abbr",
    "team_id",
    "team_name",
    "window_size",
    "stretch_metric",
    "stretch_value",
    "window_start_date",
    "window_end_date",
    "window_start_season",
    "games_in_window",
  ]);
  if (metric !== "stretch_value") excluded.add(metric);

  return WINDOW_SUPPORT_KEYS.filter(
    (key) => !excluded.has(key) && rows.some((row) => hasValue(row[key])),
  ).slice(0, limit);
}

function gameLogHighlightKey(rows: SectionRow[], metric: string): string | undefined {
  return rows.some((row) => hasValue(row[metric])) ? metric : undefined;
}

function stretchMetric(
  rows: SectionRow[],
  metadata: ResultMetadata | undefined,
  query: string,
): string {
  const rowMetric = textValue(rows[0], "stretch_metric");
  if (rowMetric) return rowMetric;

  for (const key of ["stretch_metric", "metric", "stat", "target_metric"]) {
    const value = metadata?.[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }

  const lower = `${query ?? ""} ${metadata?.query_text ?? ""}`.toLowerCase();
  if (/\b(points?|scoring|score)\b/.test(lower)) return "pts";
  if (/\b(rebounds?|boards?)\b/.test(lower)) return "reb";
  if (/\b(assists?|passing)\b/.test(lower)) return "ast";
  if (/\b(true shooting|ts%)\b/.test(lower)) return "ts_pct";
  if (/\b(game score)\b/.test(lower)) return "game_score";
  return "stretch_value";
}

function stretchValue(
  row: SectionRow,
  metric: string,
  table = false,
): string {
  const value = hasValue(row.stretch_value) ? row.stretch_value : row[metric];
  const formatted = hasValue(row.stretch_value)
    ? formatAverageValue(value, metric)
    : formatTableValue(value, metric);
  if (table) return formatted;
  const label = STRETCH_METRIC_LABELS[metric];
  return label ? `${formatted} ${label}` : formatted;
}

function metricPhrase(metric: string): string {
  return STRETCH_PHRASES[metric] ?? `${tableLabel(metric).toLowerCase()} stretch`;
}

function windowSize(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
): number | string {
  return (
    numericValue(row, "window_size") ??
    numericValue(row, "games_in_window") ??
    metadataNumber(metadata, "window_size") ??
    textMetadata(metadata, "window_size") ??
    "N"
  );
}

function scopePhrase(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
  query: string,
): string {
  const combinedQuery = `${query ?? ""} ${metadata?.query_text ?? ""}`;
  if (/\b(this season|this year)\b/i.test(combinedQuery)) return "this season";

  const season =
    textValue(row, "window_end_season") ??
    textValue(row, "season") ??
    textMetadata(metadata, "season");
  const seasonType = textMetadata(metadata, "season_type");
  if (season) {
    return `in the ${season}${seasonType ? ` ${seasonType.toLowerCase()}` : ""}`;
  }

  const since = combinedQuery.match(/\bsince\s+(\d{4})\b/i);
  if (since) return `since ${since[1]}`;
  return "";
}

function playerName(row: SectionRow): string {
  return textValue(row, "player_name") ?? textValue(row, "player") ?? "Player";
}

function topCountNote(
  metadata: ResultMetadata | undefined,
  shown: number,
): string | null {
  const total = metadataNumber(
    metadata,
    "total_count",
    "total_rows",
    "total",
    "matching_count",
    "full_count",
  );
  if (total === null || total <= shown) return null;
  return `Showing top ${shown} of ${formatValue(total, "total_count")}`;
}

function tableLabel(key: string): string {
  return (
    TABLE_LABELS[key] ??
    formatColHeader(key)
      .replace(/\bPts\b/g, "PTS")
      .replace(/\bReb\b/g, "REB")
      .replace(/\bAst\b/g, "AST")
      .replace(/\bStl\b/g, "STL")
      .replace(/\bBlk\b/g, "BLK")
      .replace(/\bTov\b/g, "TOV")
      .replace(/\bFg3\b/g, "3P")
  );
}

function formatTableValue(value: unknown, key: string): string {
  if (key === "plus_minus" && typeof value === "number") {
    const formatted = formatValue(value, key);
    return value > 0 ? `+${formatted}` : formatted;
  }
  return formatValue(value, key);
}

function isNumericKey(key: string): boolean {
  return !key.includes("season") && key !== "date_range";
}

function rankValue(row: SectionRow, index: number): string {
  return typeof row.rank === "number" || typeof row.rank === "string"
    ? String(row.rank)
    : String(index + 1);
}

function windowRowKey(row: SectionRow, index: number): string {
  return [
    row.rank,
    row.player_id,
    row.window_start_date,
    row.window_end_date,
    index,
  ]
    .filter(hasValue)
    .join("-");
}

function gameRowKey(row: SectionRow, index: number): string {
  return [row.game_id, row.game_date, row.player_id, index].filter(hasValue).join("-");
}

function textValue(row: SectionRow, key: string): string | null {
  const value = row[key];
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function textMetadata(
  metadata: ResultMetadata | undefined,
  key: string,
): string | null {
  const value = metadata?.[key];
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function numericValue(row: SectionRow, key: string): number | null {
  const value = row[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function metadataNumber(
  metadata: ResultMetadata | undefined,
  ...keys: string[]
): number | null {
  for (const key of keys) {
    const value = metadata?.[key];
    if (typeof value === "number" && Number.isFinite(value)) return value;
    if (typeof value === "string" && value.trim() && Number.isFinite(Number(value))) {
      return Number(value);
    }
  }
  return null;
}

function identityId(value: unknown): number | string | null {
  return typeof value === "number" || typeof value === "string" ? value : null;
}

function hasValue(value: unknown): boolean {
  return value !== null && value !== undefined && value !== "";
}
