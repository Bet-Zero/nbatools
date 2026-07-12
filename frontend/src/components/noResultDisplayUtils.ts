import type { ResultMetadata } from "../api/types";
import { formatColHeader } from "./tableFormatting";

export interface NoResultDetail {
  kind: "Note" | "Caveat";
  text: string;
}

export interface NoResultGuidance {
  querySuggestions: string[];
  nextSteps: string[];
}

const DATE_NO_MATCH_QUERIES = [
  "Who leads the NBA in points per game this season?",
  "What were the biggest scoring games this week?",
];

const RECENT_DEFENSE_ALTERNATIVES = [
  "Which teams have the best record recently?",
  "Lakers held opponents under 100 points this season",
];

const NO_DATA_STEPS = [
  "Try a season covered by the local data",
  "Broaden the date window",
  "Remove narrow split filters",
];

const GENERIC_NO_MATCH_STEPS = [
  "Try a different season or date range",
  "Broaden stat filters or split filters",
  "Remove narrow split filters",
];

const MONTH_LABELS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

export function buildNoResultDetails(
  notes: string[] = [],
  caveats: string[] = [],
  metadata?: ResultMetadata | null,
): NoResultDetail[] {
  return uniqueDetails([
    ...productFacingNotices(notes).map((text) => ({
      kind: "Note" as const,
      text,
    })),
    ...productFacingNotices(caveats).map((text) => ({
      kind: "Caveat" as const,
      text,
    })),
    ...productFacingNotices(metadataNotes(metadata?.notes)).map((text) => ({
      kind: "Note" as const,
      text,
    })),
  ]);
}

export function productFacingNotice(text: string): string | null {
  const trimmed = text.trim();
  if (!trimmed) return null;

  if (/^sample_advanced_metrics:/i.test(trimmed)) {
    return "Advanced rate stats were recalculated using only this filtered sample.";
  }

  if (/^season_high:/i.test(trimmed)) {
    return "Showing league-wide single-game scoring performances.";
  }

  if (/^multi-player availability filters are not supported/i.test(trimmed)) {
    return "Combining with-player and without-player filters is not supported yet.";
  }

  if (/^bare player-vs-player queries are ambiguous/i.test(trimmed)) {
    return "Bare player-vs-player queries need a comparison, head-to-head, or stats-vs scope.";
  }

  if (
    /^default:\s*player streak uses three-season window when no season specified$/i.test(
      trimmed,
    )
  ) {
    return "Because no season was specified, this search used the last three seasons.";
  }

  if (/^default:\s*<metric> only/i.test(trimmed)) return null;
  if (/^leaderboard_source:/i.test(trimmed)) return null;

  return trimmed;
}

export function productFacingNotices(texts: string[]): string[] {
  return texts
    .map((text) => productFacingNotice(text))
    .filter((text): text is string => text !== null);
}

export function buildNoResultGuidance(
  reason: string | null | undefined,
  status: string,
  metadata?: ResultMetadata | null,
  detailTexts: string[] = [],
): NoResultGuidance {
  const backendQueries = suggestedQueryLines(metadata);
  if (backendQueries.length > 0) {
    return { querySuggestions: backendQueries, nextSteps: [] };
  }

  if (isBarePlayerVsPlayerAmbiguity(reason, metadata)) {
    return {
      querySuggestions: [
        "Compare LeBron and KD this season",
        "LeBron stats vs KD",
      ],
      nextSteps: [],
    };
  }

  if (status === "error" || reason === "error" || reason === "unrouted") {
    return { querySuggestions: [], nextSteps: [] };
  }

  if (isDateNoMatch(reason, metadata)) {
    return {
      querySuggestions: DATE_NO_MATCH_QUERIES,
      nextSteps: ["Try the previous NBA game day", "Try the next NBA game day"],
    };
  }

  if (hasUnsupportedRecentDefensiveRating(reason, metadata, detailTexts)) {
    return {
      querySuggestions: RECENT_DEFENSE_ALTERNATIVES,
      nextSteps: [
        "Use team-record form for recent team performance",
        "Use a named-team opponent-points threshold for defense checks",
      ],
    };
  }

  if (reason === "no_data") {
    return { querySuggestions: [], nextSteps: NO_DATA_STEPS };
  }

  if (reason === "no_match" || !reason) {
    return { querySuggestions: [], nextSteps: GENERIC_NO_MATCH_STEPS };
  }

  return { querySuggestions: [], nextSteps: [] };
}

export function hasGuidedNoResultRecovery(
  reason: string | null | undefined,
  status: string,
  metadata?: ResultMetadata | null,
  detailTexts: string[] = [],
): boolean {
  const guidance = buildNoResultGuidance(reason, status, metadata, detailTexts);
  return guidance.querySuggestions.length > 0 || guidance.nextSteps.length > 0;
}

export function readableNoResultMessage(
  fallback: string,
  reason: string | null | undefined,
  metadata: ResultMetadata | null | undefined,
  detailTexts: string[],
): string {
  const unsupportedPhrase = unsupportedPhraseMessage(metadata);
  if (unsupportedPhrase) return unsupportedPhrase;

  const unsupportedBoundary = unsupportedBoundaryMessage(metadata);
  if (unsupportedBoundary) return unsupportedBoundary;

  if (isMultiPlayerAvailabilityUnsupported(metadata, detailTexts)) {
    return "This version does not support combining with-player and without-player filters yet. Try one availability filter at a time.";
  }

  if (isBarePlayerVsPlayerAmbiguity(reason, metadata)) {
    return "This could mean a few different things. Try a more specific query, such as a season comparison or stats-vs phrasing.";
  }

  if (isDateNoMatch(reason, metadata)) {
    const dateRange = noResultDateRange(metadata);
    if (dateRange) return `No NBA games matched ${dateRange}.`;
  }

  const columnMessage =
    columnUnavailableMessage(reason, metadata) ??
    detailTexts
      .map((text) => columnUnavailableMessage(text, metadata))
      .find(Boolean);
  if (columnMessage) return columnMessage;

  const unsupportedStatMessage =
    unsupportedStatCopy(reason, metadata) ??
    detailTexts
      .map((text) => unsupportedStatCopy(text, metadata))
      .find(Boolean);
  if (unsupportedStatMessage) return unsupportedStatMessage;

  if (reason === "filter_not_supported") {
    const metric = metricFromMetadata(metadata);
    if (metric) {
      return `${metricLabel(metric)} is not available for this query.`;
    }
  }

  return humanizeBackendCopy(fallback, metadata);
}

export function unsupportedBoundaryTitle(
  metadata: ResultMetadata | null | undefined,
): string | null {
  const filters = unsupportedFilters(metadata);
  if (
    filters.includes("personal_foul_leaderboard") ||
    filters.includes("rookie_leaderboard") ||
    filters.includes("role_leaderboard")
  ) {
    return "Unsupported Leaderboard";
  }
  if (filters.includes("team_bench_scoring")) {
    return "Unsupported Summary";
  }
  if (filters.includes("unsupported_concept")) {
    return "Unsupported Question";
  }
  if (filters.includes("player_playoff_appearances")) {
    return "Unsupported Question";
  }
  if (filters.includes("opponent_conference")) {
    return "Unavailable Filter";
  }
  return null;
}

function unsupportedBoundaryMessage(
  metadata: ResultMetadata | null | undefined,
): string | null {
  const filters = unsupportedFilters(metadata);
  if (filters.includes("personal_foul_leaderboard")) {
    return "Personal-foul leaderboards are not supported yet.";
  }
  if (filters.includes("rookie_leaderboard")) {
    return "Rookie leaderboards are not supported yet.";
  }
  if (filters.includes("role_leaderboard")) {
    return "League-wide starter/bench leaderboards are not supported yet.";
  }
  if (filters.includes("team_bench_scoring")) {
    return "Team bench-scoring summaries are not supported yet.";
  }
  if (filters.includes("unsupported_concept")) {
    return "That concept is not supported yet. Try asking for a specific player, team, game, or stat.";
  }
  if (filters.includes("player_playoff_appearances")) {
    return "Player playoff-appearance counts are not supported yet. Try asking about a team or the league leaderboard.";
  }
  if (filters.includes("opponent_conference")) {
    return "Opponent-conference record filters are not supported yet.";
  }
  return null;
}

function unsupportedFilters(
  metadata: ResultMetadata | null | undefined,
): string[] {
  const raw = metadata?.unsupported_filters;
  if (!Array.isArray(raw)) return [];
  return raw
    .map((filter) => (typeof filter === "string" ? filter.trim() : ""))
    .filter(Boolean);
}

function unsupportedPhraseMessage(
  metadata: ResultMetadata | null | undefined,
): string | null {
  const query = String(metadata?.query_text ?? "").toLowerCase();
  if (query.includes("cooled off")) {
    return 'I couldn\'t interpret "cooled off" as a supported stat query yet.';
  }
  return null;
}

function isBarePlayerVsPlayerAmbiguity(
  reason: string | null | undefined,
  metadata: ResultMetadata | null | undefined,
): boolean {
  return (
    reason === "ambiguous_query" &&
    metadata?.ambiguous_intent === "bare_player_vs_player"
  );
}

function isMultiPlayerAvailabilityUnsupported(
  metadata: ResultMetadata | null | undefined,
  detailTexts: string[],
): boolean {
  const filters = unsupportedFilters(metadata);
  if (filters.includes("multi_player_availability")) return true;

  return detailTexts.some((text) =>
    /multi-player availability filters are not supported|combining with-player and without-player filters/i.test(
      text,
    ),
  );
}

export function isColumnUnavailableReason(
  text: string | null | undefined,
): boolean {
  return Boolean(columnUnavailableMatch(text));
}

export function isMetricUnavailableNoResult(
  reason: string | null | undefined,
  metadata: ResultMetadata | null | undefined,
  detailTexts: string[] = [],
): boolean {
  if (isColumnUnavailableReason(reason)) return true;
  if (unsupportedStatCopy(reason, metadata)) return true;
  return detailTexts.some(
    (text) =>
      Boolean(columnUnavailableMatch(text)) ||
      Boolean(unsupportedStatCopy(text, metadata)),
  );
}

export function formatReadableDateRange(
  start: string | null | undefined,
  end: string | null | undefined,
): string | null {
  if (!start && !end) return null;
  const startParts = parseIsoDateParts(start ?? end);
  const endParts = parseIsoDateParts(end ?? start);
  if (!startParts || !endParts) return start ?? end ?? null;

  if (sameDate(startParts, endParts)) {
    return formatDateParts(startParts);
  }

  if (
    startParts.year === endParts.year &&
    startParts.month === endParts.month
  ) {
    return `${MONTH_LABELS[startParts.month - 1]} ${startParts.day}\u2013${endParts.day}, ${startParts.year}`;
  }

  return `${formatDateParts(startParts)} \u2013 ${formatDateParts(endParts)}`;
}

function isDateNoMatch(
  reason: string | null | undefined,
  metadata: ResultMetadata | null | undefined,
): boolean {
  if (reason !== "no_match") return false;
  return Boolean(noResultDateRange(metadata));
}

function noResultDateRange(
  metadata: ResultMetadata | null | undefined,
): string | null {
  return formatReadableDateRange(metadata?.start_date, metadata?.end_date);
}

function hasUnsupportedRecentDefensiveRating(
  reason: string | null | undefined,
  metadata: ResultMetadata | null | undefined,
  detailTexts: string[],
): boolean {
  if (reason !== "unsupported") return false;
  if (metricFromMetadata(metadata) !== "def_rating") return false;
  if (!isTeamLeaderboardRoute(metadata)) return false;
  if (!hasRecentWindow(metadata)) return false;
  return detailTexts.some((text) => columnUnavailableMatch(text));
}

function isTeamLeaderboardRoute(metadata: ResultMetadata | null | undefined) {
  return metadata?.route === "season_team_leaders";
}

function hasRecentWindow(metadata: ResultMetadata | null | undefined): boolean {
  if (metadata?.start_date || metadata?.end_date) return true;
  const filters = metadata?.applied_filters;
  if (!Array.isArray(filters)) return false;
  return filters.some((filter) => {
    const kind = String(filter.kind ?? "").toLowerCase();
    const label = String(filter.label ?? "").toLowerCase();
    return kind === "window" || label.includes("last n");
  });
}

function columnUnavailableMessage(
  text: string | null | undefined,
  metadata: ResultMetadata | null | undefined,
): string | null {
  const match = columnUnavailableMatch(text);
  if (!match) return null;

  const metric = metricLabel(match.metric);
  const context = match.context?.trim();
  if (context) return `${metric} is not available for ${context}.`;

  if (
    match.metric.toLowerCase() === "def_rating" &&
    isTeamLeaderboardRoute(metadata) &&
    hasRecentWindow(metadata)
  ) {
    return `${metric} is not available for recent team leaderboards in the current dataset.`;
  }

  return `${metric} is not available in the current dataset.`;
}

function columnUnavailableMatch(
  text: string | null | undefined,
): { metric: string; context?: string } | null {
  if (!text) return null;
  const match = text.match(
    /^Column '([^']+)' not available(?: for ([^.]+))?\.?$/i,
  );
  if (!match) return null;
  return { metric: match[1], context: match[2] };
}

function unsupportedStatCopy(
  text: string | null | undefined,
  metadata: ResultMetadata | null | undefined,
): string | null {
  if (!text) return null;
  const match = text.match(/^Unsupported stat '([^']+)'/i);
  if (!match) return null;
  const metric = metricLabel(match[1]);
  const route = metadata?.route;
  if (route === "season_team_leaders") {
    return `${metric} is not available for team leaderboards in the current dataset.`;
  }
  return `${metric} is not available for this query.`;
}

function humanizeBackendCopy(
  text: string,
  metadata: ResultMetadata | null | undefined,
): string {
  const columnMessage = columnUnavailableMessage(text, metadata);
  if (columnMessage) return columnMessage;
  const unsupportedStatMessage = unsupportedStatCopy(text, metadata);
  if (unsupportedStatMessage) return unsupportedStatMessage;
  return humanizeIsoDatesInText(text);
}

function humanizeIsoDatesInText(text: string): string {
  return text.replace(
    /(\d{4}-\d{2}-\d{2})(?:\s*(?:to|\u2013|-)\s*(\d{4}-\d{2}-\d{2}))?/g,
    (match, start: string, end?: string) =>
      formatReadableDateRange(start, end ?? start) ?? match,
  );
}

function metricFromMetadata(
  metadata: ResultMetadata | null | undefined,
): string | null {
  if (!metadata) return null;
  for (const key of ["stat", "metric", "target_stat", "target_metric"]) {
    const value = metadata[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return null;
}

function metricLabel(metric: string): string {
  const normalized = metric.trim().toLowerCase();
  const labels: Record<string, string> = {
    ast: "Assists",
    ast_avg: "Assists per game",
    def_rating: "Defensive rating",
    efg_pct: "Effective field-goal percentage",
    fg3_pct: "Three-point percentage",
    fg_pct: "Field-goal percentage",
    net_rating: "Net rating",
    off_rating: "Offensive rating",
    opponent_pts: "Opponent points",
    pace: "Pace",
    pf: "Personal fouls",
    pts: "Points",
    pts_avg: "Points per game",
    reb: "Rebounds",
    reb_avg: "Rebounds per game",
    ts_pct: "True-shooting percentage",
    win_pct: "Winning percentage",
  };
  return labels[normalized] ?? formatColHeader(metric);
}

function suggestedQueryLines(
  metadata: ResultMetadata | null | undefined,
): string[] {
  const direct = Array.isArray(metadata?.suggested_queries)
    ? metadata.suggested_queries
    : [];
  const clarificationOptions = Array.isArray(metadata?.clarification_options)
    ? metadata.clarification_options
        .map((option) =>
          option &&
          typeof option === "object" &&
          "query" in option &&
          typeof option.query === "string"
            ? option.query
            : null,
        )
        .filter((query): query is string => Boolean(query))
    : [];

  return uniqueStrings(
    [...direct, ...clarificationOptions]
      .map(stringValue)
      .filter((query): query is string => Boolean(query)),
  );
}

function metadataNotes(notes: unknown): string[] {
  if (!Array.isArray(notes)) return [];
  return notes.map(stringValue).filter((note): note is string => Boolean(note));
}

function uniqueDetails(details: NoResultDetail[]): NoResultDetail[] {
  const seen = new Set<string>();
  const output: NoResultDetail[] = [];
  for (const detail of details) {
    const text = stringValue(detail.text);
    if (!text) continue;
    const key = `${detail.kind}:${text}`;
    if (seen.has(key)) continue;
    seen.add(key);
    output.push({ kind: detail.kind, text });
  }
  return output;
}

function uniqueStrings(values: string[]): string[] {
  const seen = new Set<string>();
  const output: string[] = [];
  for (const value of values) {
    if (seen.has(value)) continue;
    seen.add(value);
    output.push(value);
  }
  return output;
}

function stringValue(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

interface DateParts {
  year: number;
  month: number;
  day: number;
}

function parseIsoDateParts(value: string | null | undefined): DateParts | null {
  if (!value) return null;
  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!match) return null;
  return {
    year: Number(match[1]),
    month: Number(match[2]),
    day: Number(match[3]),
  };
}

function sameDate(a: DateParts, b: DateParts): boolean {
  return a.year === b.year && a.month === b.month && a.day === b.day;
}

function formatDateParts(parts: DateParts): string {
  return `${MONTH_LABELS[parts.month - 1]} ${parts.day}, ${parts.year}`;
}
