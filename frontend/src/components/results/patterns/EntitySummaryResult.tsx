import type { ReactNode } from "react";
import type {
  AppliedFilter,
  QueryResponse,
  ResultMetadata,
  SectionRow,
} from "../../../api/types";
import {
  formatLongDateRange,
  formatProseValue,
  formatValue,
} from "../../tableFormatting";
import EntityIdentity from "../primitives/EntityIdentity";
import ResultHero from "../primitives/ResultHero";
import ResultTable, { type ResultTableColumn } from "../primitives/ResultTable";
import styles from "./EntitySummaryResult.module.css";

interface Props {
  data: QueryResponse;
  sectionKey?: string;
}

export default function EntitySummaryResult({
  data,
  sectionKey = "summary",
}: Props) {
  const row = data.result?.sections?.[sectionKey]?.[0];
  if (!row) return null;
  const bySeasonRows = sortedBySeasonRows(
    data.result?.sections?.by_season ?? [],
  );
  const showBySeason = shouldShowBySeason(data.result?.metadata, bySeasonRows);

  return (
    <section className={styles.pattern} aria-label="Player summary result">
      <ResultHero
        sentence={summarySentence(row, data.result?.metadata, data.query)}
        subjectIllustration={heroIdentity(row, data.result?.metadata)}
        disambiguationNote={disambiguationNote(data.result?.metadata)}
        tone="accent"
      />
      {showBySeason && (
        <ResultTable
          rows={bySeasonRows}
          columns={bySeasonColumns(bySeasonRows)}
          ariaLabel="Season breakdown"
          getRowKey={bySeasonRowKey}
        />
      )}
    </section>
  );
}

const MULTI_PERIOD_SCOPES = new Set([
  "career",
  "season_range",
  "all_time",
  "decade",
]);

const BY_SEASON_LABELS: Record<string, string> = {
  ast_avg: "APG",
  ast_pct_avg: "AST%",
  blk_avg: "BPG",
  def_rating: "DRtg",
  efg_pct_avg: "eFG%",
  fg_pct_avg: "FG%",
  fg3_pct_avg: "3P%",
  ft_pct_avg: "FT%",
  games: "GP",
  games_played: "GP",
  minutes_avg: "MPG",
  net_rating: "Net",
  off_rating: "ORtg",
  plus_minus_avg: "+/-",
  pts_avg: "PPG",
  reb_avg: "RPG",
  reb_pct_avg: "REB%",
  stl_avg: "SPG",
  tov_avg: "TOV",
  tov_pct_avg: "TOV%",
  ts_pct_avg: "TS%",
  usg_pct_avg: "USG%",
};

const BY_SEASON_STAT_COLUMNS = [
  "pts_avg",
  "reb_avg",
  "ast_avg",
  "minutes_avg",
  "fg_pct_avg",
  "fg3_pct_avg",
  "ft_pct_avg",
  "ts_pct_avg",
  "efg_pct_avg",
  "usg_pct_avg",
  "reb_pct_avg",
  "ast_pct_avg",
  "tov_pct_avg",
  "stl_avg",
  "blk_avg",
  "tov_avg",
  "plus_minus_avg",
  "off_rating",
  "def_rating",
  "net_rating",
];

function shouldShowBySeason(
  metadata: ResultMetadata | undefined,
  rows: SectionRow[],
): boolean {
  return (
    rows.length > 0 &&
    typeof metadata?.scope_kind === "string" &&
    MULTI_PERIOD_SCOPES.has(metadata.scope_kind)
  );
}

function sortedBySeasonRows(rows: SectionRow[]): SectionRow[] {
  return [...rows].sort((a, b) => {
    const aSeason = textValue(a, "season") ?? textValue(a, "seasons") ?? "";
    const bSeason = textValue(b, "season") ?? textValue(b, "seasons") ?? "";
    return bSeason.localeCompare(aSeason);
  });
}

function bySeasonColumns(
  rows: SectionRow[],
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [
    {
      key: "season",
      header: "Season",
      render: (row) => mutedCell(row, textValue(row, "season") ?? "—"),
    },
  ];

  const gamesKey = rows.some((row) => hasValue(row.games))
    ? "games"
    : rows.some((row) => hasValue(row.games_played))
      ? "games_played"
      : null;

  if (gamesKey) {
    columns.push({
      key: gamesKey,
      header: BY_SEASON_LABELS[gamesKey],
      numeric: true,
      render: (row) => mutedCell(row, formatValue(row[gamesKey], gamesKey)),
    });
  }

  if (rows.some((row) => hasValue(row.wins) || hasValue(row.losses))) {
    columns.push({
      key: "record",
      header: "W-L",
      align: "center",
      render: (row) => mutedCell(row, recordValue(row)),
    });
  }

  for (const key of BY_SEASON_STAT_COLUMNS) {
    if (!rows.some((row) => hasValue(row[key]))) continue;
    columns.push({
      key,
      header: BY_SEASON_LABELS[key] ?? key,
      numeric: true,
      render: (row) => averageCell(row, key),
    });
  }

  return columns;
}

function averageCell(row: SectionRow, key: string): ReactNode {
  if (isZeroGameRow(row)) {
    return <span className={styles.mutedCell}>—</span>;
  }
  return mutedCell(row, signedValue(row[key], key));
}

function mutedCell(row: SectionRow, value: ReactNode): ReactNode {
  return isZeroGameRow(row) ? (
    <span className={styles.mutedCell}>{value}</span>
  ) : (
    value
  );
}

function isZeroGameRow(row: SectionRow): boolean {
  const games = numericValue(row, "games") ?? numericValue(row, "games_played");
  return games === 0;
}

function recordValue(row: SectionRow): string {
  if (!hasValue(row.wins) && !hasValue(row.losses)) return "—";
  return `${formatValue(row.wins, "wins")}-${formatValue(row.losses, "losses")}`;
}

function signedValue(value: unknown, key: string): string {
  if (
    typeof value === "number" &&
    (key === "plus_minus_avg" || key === "net_rating") &&
    Number.isFinite(value)
  ) {
    const formatted = formatValue(value, key);
    return value > 0 ? `+${formatted}` : formatted;
  }
  return formatValue(value, key);
}

function bySeasonRowKey(row: SectionRow, index: number): string {
  return `${textValue(row, "season") ?? "season"}-${index}`;
}

function summarySentence(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
  query: string,
): string {
  const lineup = lineupName(row, metadata);
  if (lineup) {
    return lineupSummarySentence(lineup, row, metadata, query);
  }

  const name = playerName(row, metadata);
  const averages = averagePhrase(row);
  const context = summaryContext(row, metadata, query);

  if (!averages) {
    return `${name} has a summary available${context}.`;
  }

  return `${name} has averaged ${averages}${context}.`;
}

function lineupSummarySentence(
  lineup: string,
  row: SectionRow,
  metadata: ResultMetadata | undefined,
  query: string,
): string {
  const metrics = lineupMetricPhrase(row);
  const context = summaryContext(row, metadata, query);
  if (!metrics) return `${lineup} has a lineup summary available${context}.`;
  return `${lineup} posted ${metrics}${context}.`;
}

function lineupMetricPhrase(row: SectionRow): string | null {
  const parts = [
    lineupStatPhrase(row, "net_rating", "net rating", true),
    lineupStatPhrase(row, "off_rating", "offensive rating"),
    lineupStatPhrase(row, "def_rating", "defensive rating"),
    lineupStatPhrase(row, "pace", "pace"),
  ].filter((part): part is string => Boolean(part));

  if (parts.length === 0) return null;
  if (parts.length === 1) return parts[0];
  if (parts.length === 2) return `${parts[0]} and ${parts[1]}`;
  return `${parts.slice(0, -1).join(", ")} and ${parts[parts.length - 1]}`;
}

function lineupStatPhrase(
  row: SectionRow,
  key: string,
  label: string,
  signed = false,
): string | null {
  if (!hasValue(row[key])) return null;
  const raw = row[key];
  const value =
    signed && typeof raw === "number" && raw > 0
      ? `+${formatProseValue(raw, key)}`
      : formatProseValue(raw, key);
  return `${value} ${label}`;
}

function averagePhrase(row: SectionRow): string | null {
  const parts = [
    statPhrase(row, "pts_avg", "points"),
    statPhrase(row, "reb_avg", "rebounds"),
    statPhrase(row, "ast_avg", "assists"),
  ].filter((part): part is string => Boolean(part));

  if (parts.length === 0) return null;
  if (parts.length === 1) return parts[0];
  if (parts.length === 2) return `${parts[0]} and ${parts[1]}`;
  return `${parts.slice(0, -1).join(", ")} and ${parts[parts.length - 1]}`;
}

function statPhrase(
  row: SectionRow,
  key: string,
  label: string,
): string | null {
  if (!hasValue(row[key])) return null;
  return `${formatProseValue(row[key], key)} ${label}`;
}

function summaryContext(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
  query: string,
): string {
  const lastN = lastNWindow(query, metadata);
  const filters = filterPhrases(metadata);
  const timeframe = lastN ? "" : timeframePhrase(row, metadata, query);
  const games = numericValue(row, "games");

  if (lastN || filters.length > 0) {
    const parts = [
      lastN
        ? `in his last ${lastN} games`
        : typeof games === "number" && Number.isFinite(games)
          ? `in ${formatValue(games, "games")} games`
          : null,
      ...filters,
      timeframe,
    ].filter((part): part is string => Boolean(part));

    return parts.length > 0 ? ` ${parts.join(" ")}` : "";
  }

  if (timeframe) return ` ${timeframe}`;

  if (typeof games === "number" && Number.isFinite(games)) {
    return ` in ${formatValue(games, "games")} games`;
  }

  return "";
}

function timeframePhrase(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
  query: string,
): string {
  const dateRange = formatLongDateRange(
    metadataText(metadata, "start_date"),
    metadataText(metadata, "end_date"),
  );
  if (dateRange) return dateRange;

  if (/\bthis\s+(?:season|year)\b/i.test(query)) return "this season";
  if (/\bcareer\b/i.test(query)) return "in his career";

  const seasonStart =
    textValue(row, "season_start") ?? metadataText(metadata, "season");
  const seasonEnd = textValue(row, "season_end");
  const seasonType =
    textValue(row, "season_type") ?? metadataText(metadata, "season_type");

  if (seasonStart && seasonEnd && seasonStart !== seasonEnd) {
    return `from ${seasonStart} to ${seasonEnd}`;
  }

  if (seasonStart) {
    return `in the ${seasonStart}${seasonType ? ` ${seasonType.toLowerCase()}` : ""}`;
  }

  return "";
}

function filterPhrases(metadata: ResultMetadata | undefined): string[] {
  const phrases: string[] = [];
  const filters = Array.isArray(metadata?.applied_filters)
    ? metadata.applied_filters
    : [];

  for (const filter of filters) {
    const phrase = appliedFilterPhrase(filter);
    if (phrase) phrases.push(phrase);
  }

  if (
    metadata?.opponent_context &&
    !phrases.some((phrase) => phrase.startsWith("against "))
  ) {
    const opponent =
      metadata.opponent_context.team_name ?? metadata.opponent_context.team_abbr;
    if (opponent) phrases.push(`against ${opponent}`);
  }

  const withoutPlayer = metadataText(metadata, "without_player");
  const withoutPhrase = withoutPlayer ? `without ${withoutPlayer}` : null;
  if (
    withoutPhrase &&
    !phrases.some(
      (phrase) => phrase.toLowerCase() === withoutPhrase.toLowerCase(),
    )
  ) {
    phrases.push(withoutPhrase);
  }

  return uniqueStrings(phrases);
}

function appliedFilterPhrase(filter: AppliedFilter): string | null {
  const kind = filter.kind.toLowerCase();
  const label = filter.label.toLowerCase();
  const value = filter.value.trim();
  if (!value) return null;

  if (kind === "quality") return `against ${value}`;
  if (kind === "team" && label.includes("opponent")) {
    return `against ${value}`;
  }
  if (kind === "location") {
    const normalized = value.toLowerCase();
    if (normalized === "home") return "at home";
    if (normalized === "away") return "on the road";
    return value;
  }
  if (kind === "outcome") {
    const normalized = value.toLowerCase();
    if (normalized.startsWith("win")) return "in wins";
    if (normalized.startsWith("loss")) return "in losses";
    return `in ${value}`;
  }
  if (kind === "player" && label.includes("without")) {
    return `without ${value}`;
  }
  if (kind === "date") return null;
  if (kind === "season" || kind === "window") return null;
  if (kind === "threshold") return thresholdPhrase(filter.label, value);
  if (kind === "situation" || kind === "schedule") {
    return value.toLowerCase() === "true"
      ? `in ${filter.label.toLowerCase()} games`
      : `${filter.label.toLowerCase()}: ${value}`;
  }
  if (kind === "role" || kind === "position" || kind === "period") {
    return `${filter.label.toLowerCase()}: ${value}`;
  }

  return null;
}

function thresholdPhrase(label: string, value: string): string {
  const match = label.match(/^(.+)\s+(min|max)$/i);
  if (!match) return `${label}: ${value}`;

  const [, stat, direction] = match;
  const numeric = Number(value);
  const threshold = Number.isFinite(numeric)
    ? formatValue(
        Math.abs(numeric - Math.round(numeric)) < 0.001 ||
          Math.abs(numeric - Math.round(numeric) - 0.0001) < 0.001
          ? Math.round(numeric)
          : numeric,
        stat,
      )
    : value;
  const statText = stat.replace(/_/g, " ").toUpperCase();
  return direction.toLowerCase() === "min"
    ? `with at least ${threshold} ${statText}`
    : `with at most ${threshold} ${statText}`;
}

function uniqueStrings(values: string[]): string[] {
  const seen = new Set<string>();
  return values.filter((value) => {
    const key = value.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function heroIdentity(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
): ReactNode {
  if (lineupName(row, metadata)) return null;

  return (
    <EntityIdentity
      kind="player"
      playerId={
        metadata?.player_context?.player_id ?? identityId(row.player_id)
      }
      playerName={playerName(row, metadata)}
    />
  );
}

function lineupName(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
): string | null {
  for (const key of ["lineup_name", "lineup"]) {
    const label = readableNameList(row[key]);
    if (label) return label;
  }

  for (const key of ["player_names", "lineup_members", "members"]) {
    const label = readableNameList(row[key]);
    if (label) return label;
  }

  return readableNameList(metadata?.lineup_members);
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

function playerName(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
): string {
  return (
    metadata?.player_context?.player_name ??
    metadataText(metadata, "player") ??
    textValue(row, "player_name") ??
    textValue(row, "player") ??
    "Player"
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

function lastNWindow(
  query: string,
  metadata: ResultMetadata | undefined,
): number | null {
  const windowSize = metadata?.window_size;
  if (typeof windowSize === "number" && Number.isFinite(windowSize)) {
    return windowSize;
  }

  const queryText = `${query} ${metadata?.query_text ?? ""}`;
  const match = queryText.match(/\blast\s+(\d+)\s*(?:games?|gms?)?\b/i);
  return match ? Number(match[1]) : null;
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

function numericValue(row: SectionRow, key: string): number | null {
  const value = row[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function hasValue(value: unknown): boolean {
  return value !== null && value !== undefined && value !== "";
}
