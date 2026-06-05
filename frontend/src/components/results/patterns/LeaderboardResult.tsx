import type { ReactNode } from "react";
import type {
  QueryResponse,
  ResultMetadata,
  SectionRow,
} from "../../../api/types";
import { resolveTeamIdentity } from "../../../lib/identity";
import {
  formatColHeader,
  formatProseValue,
  formatValue,
} from "../../tableFormatting";
import EntityIdentity from "../primitives/EntityIdentity";
import ResultHero from "../primitives/ResultHero";
import ResultTable, { type ResultTableColumn } from "../primitives/ResultTable";
import styles from "./LeaderboardResult.module.css";

interface Props {
  data: QueryResponse;
  sectionKey?: string;
  metricKey?: string;
  metricLabel?: string;
  sentenceMetricLabel?: string;
  valueSuffix?: string;
  verb?: string;
  afterHero?: ReactNode;
}

type EntityKind = "player" | "team" | "unknown";
type LeaderboardRoute =
  | "season_leaders"
  | "season_team_leaders"
  | "team_record_leaderboard"
  | "player_occurrence_leaders"
  | "team_occurrence_leaders"
  | "playoff_appearances"
  | "lineup_leaderboard";

const ENTITY_COLUMNS = new Set([
  "player_name",
  "player",
  "team_name",
  "team_abbr",
  "team",
  "entity",
  "name",
  "lineup_name",
  "lineup",
  "player_names",
  "lineup_members",
  "members",
]);

const INTERNAL_COLUMNS = new Set([
  "rank",
  "player_id",
  "team_id",
  "game_id",
  "opponent_team_id",
  "lineup_id",
  "player_ids",
  "winner_team_id",
  "start_game_id",
  "end_game_id",
]);

const METRIC_EXCLUDED_COLUMNS = new Set([
  ...ENTITY_COLUMNS,
  ...INTERNAL_COLUMNS,
  "season",
  "seasons",
  "season_type",
  "game_date",
  "window_size",
  "stretch_metric",
  "window_start_date",
  "window_end_date",
  "window_start_season",
  "window_end_season",
  "games_in_window",
  "is_home",
  "is_away",
  "wl",
  "opponent_team_abbr",
  "opponent_team_name",
  "qualified",
  "qualifier",
  "qualification",
  "threshold",
  "min_games",
  "min_value",
  "max_value",
  "sample_size",
  "games_played",
]);

const DIRECT_STAT_COLUMNS = new Set([
  "pts",
  "reb",
  "ast",
  "stl",
  "blk",
  "tov",
  "fgm",
  "fga",
  "fg3m",
  "fg3a",
  "ftm",
  "fta",
  "minutes",
  "wins",
  "losses",
  "off_rating",
  "def_rating",
  "net_rating",
  "pace",
]);

const DISPLAY_ORDER = [
  "season",
  "seasons",
  "team_abbr",
  "games_played",
  "wins",
  "losses",
  "win_pct",
  "season_type",
  "minutes_per_game",
  "min_per_game",
  "minutes_total",
  "pts_per_game",
  "reb_per_game",
  "ast_per_game",
  "stl_per_game",
  "blk_per_game",
  "fg_pct",
  "fg3_pct",
  "ft_pct",
  "efg_pct",
  "ts_pct",
  "fgm_total",
  "fga_total",
  "fg3m_total",
  "fg3a_total",
  "ftm_total",
  "fta_total",
  "pf_total",
  "pts_total",
  "reb_total",
  "ast_total",
];

const TABLE_LABELS: Record<string, string> = {
  ast_per_game: "APG",
  blk_per_game: "BPG",
  def_rating: "DRtg",
  efg_pct: "eFG%",
  fg_pct: "FG%",
  fg3_pct: "3P%",
  fg3a_total: "3PA",
  fg3m_total: "3PM",
  fga_total: "FGA",
  fgm_total: "FGM",
  ft_pct: "FT%",
  fta_total: "FTA",
  ftm_total: "FTM",
  games_played: "GP",
  min_per_game: "MPG",
  minutes_per_game: "MPG",
  minutes_total: "MIN",
  net_rating: "Net",
  off_rating: "ORtg",
  pf_total: "PF",
  pts_per_game: "PPG",
  reb_per_game: "RPG",
  season_type: "Type",
  seasons: "Season",
  stl_per_game: "SPG",
  team_abbr: "TM",
  ts_pct: "TS%",
  win_pct: "Win %",
};

const SENTENCE_LABELS: Record<string, string> = {
  ast_per_game: "assists per game",
  blk_per_game: "blocks per game",
  def_rating: "defensive rating",
  efg_pct: "effective field-goal percentage",
  fg_pct: "field-goal percentage",
  fg3_pct: "three-point percentage",
  fg3a_total: "three-point attempts",
  fg3m_total: "three-pointers made",
  fga_total: "field goals attempted",
  fgm_total: "field goals made",
  ft_pct: "free-throw percentage",
  fta_total: "free throws attempted",
  ftm_total: "free throws made",
  games_played: "games played",
  min_per_game: "minutes per game",
  minutes_per_game: "minutes per game",
  minutes_total: "minutes",
  net_rating: "net rating",
  off_rating: "offensive rating",
  pf_total: "personal fouls",
  pts_per_game: "points per game",
  reb_per_game: "rebounds per game",
  stl_per_game: "steals per game",
  ts_pct: "true-shooting percentage",
  win_pct: "winning percentage",
};

export default function LeaderboardResult({
  data,
  sectionKey = "leaderboard",
  metricKey,
  metricLabel,
  sentenceMetricLabel,
  valueSuffix,
  verb,
  afterHero,
}: Props) {
  const rows = data.result?.sections?.[sectionKey] ?? [];
  if (rows.length === 0) return null;

  const metric = metricColumn(rows, data, metricKey);
  const firstRow = rows[0];
  const entityKind = rowEntityKind(firstRow);
  const route = leaderboardRoute(data);
  const columns = tableColumns(rows, metric, entityKind, metricLabel, route);

  return (
    <section className={styles.pattern} aria-label="Leaderboard result">
      <ResultHero
        sentence={
          countHeadline(data.result?.metadata) ??
          heroSentence(firstRow, metric, data, {
            sentenceMetricLabel,
            valueSuffix,
            verb,
          })
        }
        subjectIllustration={heroIdentity(firstRow)}
        disambiguationNote={disambiguationNote(data.result?.metadata)}
        tone={entityKind === "team" ? "team" : "accent"}
        teamAccentAbbr={
          entityKind === "team" ? textValue(firstRow, "team_abbr") : null
        }
      />
      {afterHero}
      <ResultTable
        rows={rows}
        columns={columns}
        highlightColumnKey={metric ?? undefined}
        ariaLabel="Leaderboard"
        getRowKey={rowKey}
      />
    </section>
  );
}

function countHeadline(metadata: ResultMetadata | undefined): string | null {
  if (typeof metadata?.primary_count !== "number") return null;
  const phrase = metadata.count_phrase;
  return typeof phrase === "string" && phrase.trim() ? phrase.trim() : null;
}

function tableColumns(
  rows: SectionRow[],
  metric: string | null,
  entityKind: EntityKind,
  metricLabel: string | undefined,
  route: LeaderboardRoute | null,
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [
    {
      key: "rank",
      header: "#",
      align: "center",
      render: rankValue,
    },
    {
      key: "entity",
      header: entityHeader(route, entityKind),
      render: entityCell,
    },
  ];

  const configuredColumns = routeSpecificColumns(
    rows,
    metric,
    metricLabel,
    route,
  );
  if (configuredColumns) {
    columns.push(...configuredColumns);
    return columns;
  }

  if (metric) {
    columns.push(valueColumn(metric, rows, metricLabel));
  }

  for (const key of displayColumnKeys(rows, metric, entityKind)) {
    columns.push(valueColumn(key, rows));
  }

  return columns;
}

function leaderboardRoute(data: QueryResponse): LeaderboardRoute | null {
  const route = data.route ?? data.result?.metadata?.route;
  switch (route) {
    case "season_leaders":
    case "season_team_leaders":
    case "team_record_leaderboard":
    case "player_occurrence_leaders":
    case "team_occurrence_leaders":
    case "playoff_appearances":
    case "lineup_leaderboard":
      return route;
    default:
      return null;
  }
}

function entityHeader(
  route: LeaderboardRoute | null,
  entityKind: EntityKind,
): string {
  if (route === "lineup_leaderboard") return "Lineup";
  if (entityKind === "team") return "Team";
  if (entityKind === "player") return "Player";
  return "Name";
}

function routeSpecificColumns(
  rows: SectionRow[],
  metric: string | null,
  metricLabel: string | undefined,
  route: LeaderboardRoute | null,
): Array<ResultTableColumn<SectionRow>> | null {
  switch (route) {
    case "season_leaders":
      return seasonLeaderColumns(rows, metric, metricLabel);
    case "season_team_leaders":
      return seasonTeamLeaderColumns(rows, metric, metricLabel);
    case "team_record_leaderboard":
      return teamRecordLeaderboardColumns(rows, metric, metricLabel);
    case "player_occurrence_leaders":
      return playerOccurrenceColumns(rows, metric, metricLabel);
    case "team_occurrence_leaders":
      return teamOccurrenceColumns(rows, metric, metricLabel);
    case "playoff_appearances":
      return playoffAppearanceColumns(rows, metric, metricLabel);
    case "lineup_leaderboard":
      return lineupLeaderboardColumns(rows, metric, metricLabel);
    default:
      return null;
  }
}

function seasonLeaderColumns(
  rows: SectionRow[],
  metric: string | null,
  metricLabel: string | undefined,
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [];
  pushMetricColumn(columns, rows, metric, metricLabel);
  pushValueColumn(columns, rows, "team_abbr", "Team");
  pushValueColumn(columns, rows, "games_played", "GP");
  pushShootingColumns(columns, rows, metric);
  pushSeasonContextColumns(columns, rows);
  return columns;
}

function seasonTeamLeaderColumns(
  rows: SectionRow[],
  metric: string | null,
  metricLabel: string | undefined,
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [];
  pushMetricColumn(columns, rows, metric, metricLabel);
  pushRecordContextColumns(columns, rows);
  pushValueColumn(columns, rows, "games_played", "GP");
  pushShootingColumns(columns, rows, metric);
  pushSeasonContextColumns(columns, rows);
  return columns;
}

function teamRecordLeaderboardColumns(
  rows: SectionRow[],
  metric: string | null,
  metricLabel: string | undefined,
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [];
  if (
    metric &&
    !["wins", "losses", "win_pct", "games_played"].includes(metric)
  ) {
    pushMetricColumn(columns, rows, metric, metricLabel);
  }
  if (rowsHaveAnyValue(rows, ["wins", "losses"])) {
    columns.push(
      recordColumn(
        metric === "wins" || metric === "losses" ? metric : "record",
      ),
    );
  }
  pushValueColumn(columns, rows, "win_pct", "Win %");
  pushValueColumn(columns, rows, "games_played", "Games");
  pushValueColumn(columns, rows, "season", "Season");
  pushValueColumn(columns, rows, "seasons", "Seasons");
  pushValueColumn(columns, rows, "season_type", "Season Type");
  return columns;
}

function playerOccurrenceColumns(
  rows: SectionRow[],
  metric: string | null,
  metricLabel: string | undefined,
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [];
  pushMetricColumn(columns, rows, metric, metricLabel);
  pushValueColumn(columns, rows, "team_abbr", "Team");
  pushValueColumn(columns, rows, "games_played", "GP");
  pushSeasonContextColumns(columns, rows);
  return columns;
}

function teamOccurrenceColumns(
  rows: SectionRow[],
  metric: string | null,
  metricLabel: string | undefined,
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [];
  pushMetricColumn(columns, rows, metric, metricLabel);
  pushValueColumn(columns, rows, "games_played", "GP");
  pushSeasonContextColumns(columns, rows);
  return columns;
}

function playoffAppearanceColumns(
  rows: SectionRow[],
  metric: string | null,
  metricLabel: string | undefined,
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [];
  pushMetricColumn(columns, rows, metric ?? "appearances", metricLabel);
  pushValueColumn(columns, rows, "round", "Round");
  pushValueColumn(columns, rows, "seasons", "Seasons");
  pushValueColumn(columns, rows, "season", "Season");
  return columns;
}

function lineupLeaderboardColumns(
  rows: SectionRow[],
  metric: string | null,
  metricLabel: string | undefined,
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [];
  const primaryMetric = metric ?? "net_rating";
  pushValueColumn(columns, rows, "team_abbr", "Team");
  pushMetricColumn(columns, rows, primaryMetric, metricLabel);

  const supportOrder =
    primaryMetric === "minutes"
      ? ["net_rating", "off_rating", "def_rating", "pace", "ts_pct"]
      : [
          "minutes",
          "net_rating",
          "off_rating",
          "def_rating",
          "pace",
          "ts_pct",
        ];
  for (const key of supportOrder) {
    pushValueColumn(columns, rows, key);
  }
  return columns;
}

function pushMetricColumn(
  columns: Array<ResultTableColumn<SectionRow>>,
  rows: SectionRow[],
  metric: string | null,
  labelOverride?: string,
): void {
  if (!metric) return;
  pushValueColumn(columns, rows, metric, labelOverride);
}

function pushShootingColumns(
  columns: Array<ResultTableColumn<SectionRow>>,
  rows: SectionRow[],
  metric: string | null,
): void {
  if (!isShootingContext(rows, metric)) return;
  for (const key of [
    "fgm_total",
    "fga_total",
    "fg3m_total",
    "fg3a_total",
    "ftm_total",
    "fta_total",
  ]) {
    pushValueColumn(columns, rows, key);
  }
}

function isShootingContext(rows: SectionRow[], metric: string | null): boolean {
  if (
    metric &&
    ["fg_pct", "fg3_pct", "ft_pct", "efg_pct", "ts_pct"].includes(metric)
  ) {
    return true;
  }
  return rowsHaveAnyValue(rows, [
    "fgm_total",
    "fga_total",
    "fg3m_total",
    "fg3a_total",
    "ftm_total",
    "fta_total",
  ]);
}

function pushRecordContextColumns(
  columns: Array<ResultTableColumn<SectionRow>>,
  rows: SectionRow[],
): void {
  if (rowsHaveAnyValue(rows, ["wins", "losses"])) {
    columns.push(recordColumn("record"));
  }
  pushValueColumn(columns, rows, "win_pct", "Win %");
}

function pushSeasonContextColumns(
  columns: Array<ResultTableColumn<SectionRow>>,
  rows: SectionRow[],
): void {
  pushValueColumn(columns, rows, "season", "Season");
  pushValueColumn(columns, rows, "seasons", "Seasons");
  pushValueColumn(columns, rows, "season_type", "Season Type");
}

function pushValueColumn(
  columns: Array<ResultTableColumn<SectionRow>>,
  rows: SectionRow[],
  key: string,
  labelOverride?: string,
): void {
  if (columns.some((column) => column.key === key)) return;
  if (!rows.some((row) => hasValue(row[key]))) return;
  columns.push(valueColumn(key, rows, labelOverride));
}

function rowsHaveAnyValue(rows: SectionRow[], keys: string[]): boolean {
  return keys.some((key) => rows.some((row) => hasValue(row[key])));
}

function recordColumn(key: string): ResultTableColumn<SectionRow> {
  return {
    key,
    sourceKeys: ["wins", "losses"],
    header: "W-L",
    align: "center",
    render: recordValue,
  };
}

function displayColumnKeys(
  rows: SectionRow[],
  metric: string | null,
  entityKind: EntityKind,
): string[] {
  const rowKeys = Array.from(new Set(rows.flatMap((row) => Object.keys(row))));
  const visible = rowKeys.filter((key) => {
    if (key === metric) return false;
    if (INTERNAL_COLUMNS.has(key)) return false;
    if (key === "team_abbr" && entityKind === "team") return false;
    if (ENTITY_COLUMNS.has(key)) return key === "team_abbr";
    return rows.some((row) => hasValue(row[key]));
  });

  return visible.sort((a, b) => displayIndex(a) - displayIndex(b));
}

function displayIndex(key: string): number {
  const index = DISPLAY_ORDER.indexOf(key);
  return index === -1 ? DISPLAY_ORDER.length + 1 : index;
}

function valueColumn(
  key: string,
  rows: SectionRow[],
  labelOverride?: string,
): ResultTableColumn<SectionRow> {
  const numeric = isNumericColumn(rows, key);
  return {
    key,
    header: labelOverride ?? tableLabel(key),
    numeric,
    align: numeric ? "right" : "left",
    render: (row) => renderValue(row, key),
  };
}

function isNumericColumn(rows: SectionRow[], key: string): boolean {
  return rows.some((row) => typeof row[key] === "number");
}

function renderValue(row: SectionRow, key: string): ReactNode {
  if (key === "team_abbr") {
    const teamAbbr = textValue(row, "team_abbr");
    if (!teamAbbr) return formatValue(row[key], key);
    return (
      <span className={styles.teamCell}>
        <EntityIdentity
          kind="team"
          teamId={identityId(row.team_id)}
          teamAbbr={teamAbbr}
          teamName={textValue(row, "team_name")}
          size="sm"
        />
      </span>
    );
  }
  return formatValue(row[key], key);
}

function metricColumn(
  rows: SectionRow[],
  data: QueryResponse,
  metricKey: string | undefined,
): string | null {
  const firstRow = rows[0];
  if (!firstRow) return null;

  if (metricKey && rows.some((row) => hasValue(row[metricKey]))) {
    return metricKey;
  }

  const hinted = queryMetricHint(data);
  if (hinted && rows.some((row) => hasValue(row[hinted]))) {
    return hinted;
  }

  const candidates = Object.keys(firstRow)
    .map((key, index) => ({
      key,
      index,
      priority: METRIC_EXCLUDED_COLUMNS.has(key)
        ? -1
        : metricPriority(firstRow, key),
    }))
    .filter((candidate) => candidate.priority >= 0)
    .sort((a, b) => b.priority - a.priority || a.index - b.index);

  return (
    candidates[0]?.key ??
    (rows.some((row) => hasValue(row.games_played)) ? "games_played" : null)
  );
}

function queryMetricHint(data: QueryResponse): string | null {
  const metadata = data.result?.metadata ?? {};
  for (const key of ["stat", "metric", "target_stat", "target_metric"]) {
    const value = metadata[key];
    if (typeof value === "string" && value.trim()) {
      return normalizeMetricHint(value.trim());
    }
  }

  const query =
    `${data.query ?? ""} ${metadata.query_text ?? ""}`.toLowerCase();
  if (
    /\b(win pct|winning percentage|winning pct|best record|record)\b/.test(
      query,
    )
  ) {
    return "win_pct";
  }
  if (/\b(most wins|wins|won)\b/.test(query)) return "wins";
  if (/\b(losses|worst record)\b/.test(query)) return "losses";
  if (/\b(ppg|points per game|scoring)\b/.test(query)) return "pts_per_game";
  if (/\b(rpg|rebounds per game|rebounds)\b/.test(query)) return "reb_per_game";
  if (/\b(apg|assists per game|assists)\b/.test(query)) return "ast_per_game";
  return null;
}

function normalizeMetricHint(value: string): string {
  const totalMetricMap: Record<string, string> = {
    fga: "fga_total",
    fg3a: "fg3a_total",
    fgm: "fgm_total",
    fta: "fta_total",
    ftm: "ftm_total",
    minutes: "minutes_total",
    pf: "pf_total",
  };
  return totalMetricMap[value] ?? value;
}

function metricPriority(row: SectionRow, key: string): number {
  if (!hasValue(row[key])) return -1;

  const lower = key.toLowerCase();
  if (lower.endsWith("_per_game")) return 95;
  if (lower.endsWith("_pct") || lower.includes("pct")) return 90;
  if (DIRECT_STAT_COLUMNS.has(lower)) return 85;
  if (typeof row[key] === "number") return 80;
  return 10;
}

function heroSentence(
  row: SectionRow,
  metric: string | null,
  data: QueryResponse,
  options: {
    sentenceMetricLabel?: string;
    valueSuffix?: string;
    verb?: string;
  },
): string {
  const leader = entityLabel(row);
  const context = contextPhrase(row, data.result?.metadata, data.query);
  const leadScope = playerLeaderboardLeadScope(data.result?.metadata);

  if (!metric) {
    return `${leader} leads ${
      leadScope ? `the ${leadScope} leaderboard` : "the leaderboard"
    }${context}.`;
  }

  if (rowEntityKind(row) === "team") {
    return teamHeroSentence(
      row,
      metric,
      leader,
      context,
      options,
      data.result?.metadata,
    );
  }

  if (!options.verb && !options.sentenceMetricLabel && !options.valueSuffix) {
    return `${leader} led ${leadScope ?? "the NBA"} with ${metricLeaderValuePhrase(
      row,
      metric,
    )}${context}.`;
  }

  const value = metricValuePhrase(row, metric, options.valueSuffix);
  return `${leader} ${options.verb ?? metricVerb(metric)} the most ${
    options.sentenceMetricLabel ?? sentenceMetricLabel(metric)
  }${leadScope ? ` among ${leadScope}` : ""}${context}, with ${value}.`;
}

function teamHeroSentence(
  row: SectionRow,
  metric: string,
  leader: string,
  context: string,
  options: {
    sentenceMetricLabel?: string;
    valueSuffix?: string;
    verb?: string;
  },
  metadata: ResultMetadata | undefined,
): string {
  if (metric === "win_pct" && hasValue(row.wins) && hasValue(row.losses)) {
    return `The ${leader} had the best record${context}, going ${formatValue(
      row.wins,
      "wins",
    )}-${formatValue(row.losses, "losses")} (${formatValue(row.win_pct, "win_pct")}).`;
  }

  if (metric === "wins") {
    return `The ${leader} won the most games${context}, with ${formatValue(
      row.wins,
      "wins",
    )} wins.`;
  }

  if (metric === "losses") {
    return `The ${leader} had the most losses${context}, with ${formatValue(
      row.losses,
      "losses",
    )} losses.`;
  }

  if (metric === "opponent_pts_per_game") {
    const direction = metadata?.ascending === true ? "fewest" : "most";
    const value = metricValuePhrase(row, metric, options.valueSuffix);
    return `The ${leader} allowed the ${direction} points per game${context}, with ${value}.`;
  }

  return `The ${leader} ${options.verb ?? "had"} the most ${
    options.sentenceMetricLabel ?? sentenceMetricLabel(metric)
  }${context}, with ${metricValuePhrase(row, metric, options.valueSuffix)}.`;
}

function metricVerb(metric: string): string {
  if (metric.startsWith("pts")) return "scored";
  if (metric.endsWith("_per_game")) return "averaged";
  return "had";
}

function metricValuePhrase(
  row: SectionRow,
  metric: string,
  suffix: string | undefined,
): string {
  const formatted = formatProseValue(row[metric], metric);
  if (suffix) return `${formatted} ${suffix}`;
  return metric.endsWith("_per_game") ? `${formatted} per game` : formatted;
}

function metricLeaderValuePhrase(row: SectionRow, metric: string): string {
  const formatted = formatProseValue(row[metric], metric);
  if (metric.endsWith("_per_game")) {
    return `${formatted} ${tableLabel(metric)}`;
  }

  const label = sentenceMetricLabel(metric);
  return label ? `${formatted} ${label}` : formatted;
}

function contextPhrase(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
  query: string,
): string {
  const since = query.match(/\bsince\s+(\d{4})\b/i);
  if (since) return ` since ${since[1]}`;

  const seasonType =
    textValue(row, "season_type") ?? metadataText(metadata, "season_type");
  const season = textValue(row, "season") ?? metadataText(metadata, "season");
  const seasons =
    textValue(row, "seasons") ??
    seasonRange(
      metadataText(metadata, "start_season"),
      metadataText(metadata, "end_season"),
    );

  if (seasonType?.toLowerCase() === "playoffs" && season) {
    return ` in the ${playoffYear(season)} playoffs`;
  }

  if (season) {
    return ` in the ${season}${seasonType ? ` ${seasonType.toLowerCase()}` : ""}`;
  }

  if (seasons) {
    return ` from ${seasons}`;
  }

  return "";
}

function playerLeaderboardLeadScope(
  metadata: ResultMetadata | undefined,
): string | null {
  const direct = metadataText(metadata, "position_filter");
  const applied = metadata?.applied_filters?.find(
    (filter) =>
      filter.kind.trim().toLowerCase() === "position" ||
      filter.label.trim().toLowerCase() === "position",
  )?.value;
  const value = direct ?? applied;
  return value ? positionGroupLabel(value) : null;
}

function positionGroupLabel(value: string): string | null {
  const normalized = value
    .trim()
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/^position\s+group[:\s]*/i, "")
    .replace(/^position[:\s]*/i, "")
    .trim();
  if (!normalized) return null;

  const labels: Record<string, string> = {
    guard: "guards",
    guards: "guards",
    center: "centers",
    centers: "centers",
    forward: "forwards",
    forwards: "forwards",
  };

  return labels[normalized] ?? normalized;
}

function seasonRange(start: string | null, end: string | null): string | null {
  if (!start && !end) return null;
  if (start && end) return start === end ? start : `${start} to ${end}`;
  return start ?? end;
}

function playoffYear(season: string): string {
  const match = season.match(/^(\d{4})-(\d{2})$/);
  if (!match) return season;
  const startYear = Number(match[1]);
  const endTwoDigits = Number(match[2]);
  const startCentury = Math.floor(startYear / 100) * 100;
  const sameCenturyEnd = startCentury + endTwoDigits;
  return String(
    sameCenturyEnd <= startYear ? sameCenturyEnd + 100 : sameCenturyEnd,
  );
}

function disambiguationNote(
  metadata: ResultMetadata | undefined,
): string | null {
  for (const key of [
    "disambiguation_note",
    "interpreted_as",
    "interpretation",
  ]) {
    const value = metadata?.[key];
    if (typeof value !== "string") continue;
    const trimmed = value.trim();
    if (!trimmed) continue;
    return trimmed.toLowerCase().startsWith("interpreted as:")
      ? trimmed
      : `Interpreted as: ${trimmed}`;
  }
  return null;
}

function heroIdentity(row: SectionRow): ReactNode {
  const kind = rowEntityKind(row);
  if (kind === "player") {
    return (
      <EntityIdentity
        kind="player"
        playerId={identityId(row.player_id)}
        playerName={textValue(row, "player_name") ?? textValue(row, "player")}
        teamAbbr={textValue(row, "team_abbr")}
      />
    );
  }

  if (kind === "team") {
    return (
      <EntityIdentity
        kind="team"
        teamId={identityId(row.team_id)}
        teamAbbr={textValue(row, "team_abbr")}
        teamName={textValue(row, "team_name") ?? textValue(row, "team")}
      />
    );
  }

  return null;
}

function entityCell(row: SectionRow): ReactNode {
  const kind = rowEntityKind(row);
  if (kind === "player") {
    return (
      <EntityIdentity
        kind="player"
        playerId={identityId(row.player_id)}
        playerName={textValue(row, "player_name") ?? textValue(row, "player")}
        teamAbbr={textValue(row, "team_abbr")}
      />
    );
  }

  if (kind === "team") {
    return (
      <EntityIdentity
        kind="team"
        teamId={identityId(row.team_id)}
        teamAbbr={textValue(row, "team_abbr")}
        teamName={textValue(row, "team_name") ?? textValue(row, "team")}
      />
    );
  }

  return <span className={styles.entityFallback}>{entityLabel(row)}</span>;
}

function rowEntityKind(row: SectionRow): EntityKind {
  if (textValue(row, "player_name") ?? textValue(row, "player"))
    return "player";
  if (hasLineupIdentity(row)) return "unknown";
  if (
    textValue(row, "team_name") ??
    textValue(row, "team_abbr") ??
    textValue(row, "team")
  ) {
    return "team";
  }
  return "unknown";
}

function entityLabel(row: SectionRow): string {
  const lineupLabel = lineupIdentityLabel(row);
  if (lineupLabel) return lineupLabel;

  if (!hasLineupIdentity(row) && rowEntityKind(row) === "team") {
    const team = resolveTeamIdentity({
      teamId: identityId(row.team_id),
      teamAbbr: textValue(row, "team_abbr"),
      teamName: textValue(row, "team_name") ?? textValue(row, "team"),
    });
    return (
      team.teamName ??
      textValue(row, "team_name") ??
      team.teamAbbr ??
      textValue(row, "team_abbr") ??
      "Team"
    );
  }

  for (const key of ENTITY_COLUMNS) {
    const value = row[key];
    if (Array.isArray(value) && value.length > 0) {
      return value.map(String).join(" / ");
    }
    const text = textValue(row, key);
    if (text) return text;
  }
  return "Leaderboard entry";
}

function hasLineupIdentity(row: SectionRow): boolean {
  return Boolean(lineupIdentityLabel(row));
}

function lineupIdentityLabel(row: SectionRow): string | null {
  for (const key of [
    "lineup_name",
    "lineup",
    "player_names",
    "lineup_members",
    "members",
  ]) {
    const label = readableNameList(row[key]);
    if (label) return label;
  }
  return null;
}

function readableNameList(value: unknown): string | null {
  if (Array.isArray(value)) {
    const parts = value.map(String).map((part) => part.trim()).filter(Boolean);
    return parts.length > 0 ? parts.join(" / ") : null;
  }

  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!trimmed) return null;

  const parsed = parseArrayLikeNames(trimmed);
  if (parsed.length > 0) return parsed.join(" / ");

  if (trimmed.includes("|")) {
    const parts = trimmed.split("|").map((part) => part.trim()).filter(Boolean);
    return parts.length > 0 ? parts.join(" / ") : null;
  }

  return trimmed;
}

function parseArrayLikeNames(value: string): string[] {
  if (!value.startsWith("[") || !value.endsWith("]")) return [];

  try {
    const parsed = JSON.parse(value);
    if (Array.isArray(parsed)) {
      return parsed.map(String).map((part) => part.trim()).filter(Boolean);
    }
  } catch {
    // Some backend/debug paths stringify arrays with single quotes.
  }

  return value
    .slice(1, -1)
    .split(",")
    .map((part) => part.trim().replace(/^['"]|['"]$/g, ""))
    .filter(Boolean);
}

function recordValue(row: SectionRow): string {
  if (!hasValue(row.wins) && !hasValue(row.losses)) return "—";
  return `${formatValue(row.wins, "wins")}-${formatValue(
    row.losses,
    "losses",
  )}`;
}

function rankValue(row: SectionRow, index: number): string {
  if (typeof row.rank === "number" || typeof row.rank === "string") {
    return String(row.rank);
  }
  return String(index + 1);
}

function rowKey(row: SectionRow, index: number): string {
  return `${rankValue(row, index)}-${entityLabel(row)}-${index}`;
}

function tableLabel(key: string): string {
  return TABLE_LABELS[key] ?? metricLabel(key);
}

function sentenceMetricLabel(key: string): string {
  return SENTENCE_LABELS[key] ?? metricLabel(key).toLowerCase();
}

function metricLabel(key: string): string {
  return formatColHeader(key)
    .replace(/\bPts\b/g, "PTS")
    .replace(/\bReb\b/g, "REB")
    .replace(/\bAst\b/g, "AST")
    .replace(/\bStl\b/g, "STL")
    .replace(/\bBlk\b/g, "BLK")
    .replace(/\bTov\b/g, "TOV")
    .replace(/\bFg3\b/g, "3P")
    .replace(/\bFg\b/g, "FG")
    .replace(/\bFt\b/g, "FT")
    .replace(/\bPct\b/g, "Pct");
}

function textValue(row: SectionRow, key: string): string | null {
  const value = row[key];
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
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

function identityId(value: unknown): number | string | null {
  return typeof value === "number" || typeof value === "string" ? value : null;
}

function hasValue(value: unknown): boolean {
  return value !== null && value !== undefined && value !== "";
}
