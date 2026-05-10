import type { ReactNode } from "react";
import type {
  QueryResponse,
  ResultMetadata,
  SectionRow,
} from "../../../api/types";
import { Badge } from "../../../design-system";
import { resolveTeamIdentity } from "../../../lib/identity";
import {
  formatColHeader,
  formatCompactDate,
  formatValue,
} from "../../tableFormatting";
import EntityIdentity from "../primitives/EntityIdentity";
import ResultHero from "../primitives/ResultHero";
import ResultTable, { type ResultTableColumn } from "../primitives/ResultTable";
import styles from "./TopPerformancesResult.module.css";

interface Props {
  data: QueryResponse;
  sectionKey?: string;
  subject: "player" | "team";
}

const STAT_ORDER = [
  "pts",
  "reb",
  "ast",
  "fg3m",
  "stl",
  "blk",
  "tov",
  "minutes",
  "plus_minus",
  "fgm",
  "fga",
  "fg3a",
  "ftm",
  "fta",
  "pf",
  "oreb",
  "dreb",
];

const STAT_LABELS: Record<string, string> = {
  ast: "AST",
  blk: "BLK",
  dreb: "DREB",
  fg3a: "3PA",
  fg3m: "3PM",
  fga: "FGA",
  fgm: "FGM",
  fta: "FTA",
  ftm: "FTM",
  minutes: "MIN",
  oreb: "OREB",
  pf: "PF",
  plus_minus: "+/-",
  pts: "PTS",
  reb: "REB",
  stl: "STL",
  tov: "TOV",
  triple_double: "PTS-REB-AST",
};

const STAT_SENTENCE_LABELS: Record<string, string> = {
  ast: "assist games",
  blk: "block games",
  fg3m: "three-point games",
  minutes: "minute games",
  plus_minus: "plus-minus games",
  pts: "scoring games",
  reb: "rebounding games",
  stl: "steal games",
  tov: "turnover games",
  triple_double: "triple-double games",
};

const VALUE_UNITS: Record<string, string> = {
  ast: "assists",
  blk: "blocks",
  fg3m: "threes",
  fgm: "field goals",
  fga: "field-goal attempts",
  ftm: "free throws",
  fta: "free-throw attempts",
  minutes: "minutes",
  pf: "fouls",
  pts: "points",
  reb: "rebounds",
  stl: "steals",
  tov: "turnovers",
};

const METRIC_HINT_KEYS = ["stat", "metric", "target_stat", "target_metric"];

const SUPPORTING_STATS_BY_METRIC: Record<string, string[]> = {
  ast: ["pts", "reb", "tov"],
  fg3m: ["pts", "fg3a"],
  pts: ["reb", "ast", "fg3m"],
  reb: ["pts", "ast"],
};

export default function TopPerformancesResult({
  data,
  sectionKey = "leaderboard",
  subject,
}: Props) {
  const rows = data.result?.sections?.[sectionKey] ?? [];
  if (rows.length === 0) return null;

  const firstRow = rows[0];
  const metric = primaryMetric(rows, data);
  const columns = tableColumns(rows, data, subject, metric);
  const note = topCountNote(data.result?.metadata, rows.length);

  return (
    <section className={styles.pattern} aria-label="Top performances result">
      <ResultHero
        sentence={heroSentence(firstRow, metric, data, subject)}
        subjectIllustration={heroIdentity(firstRow, subject)}
        tone={subject === "team" ? "team" : "accent"}
        teamAccentAbbr={
          subject === "team" ? textValue(firstRow, "team_abbr") : null
        }
      />
      <ResultTable
        rows={rows}
        columns={columns}
        highlightColumnKey={metric}
        ariaLabel="Top performances"
        getRowKey={rowKey}
      />
      {note && <p className={styles.tableNote}>{note}</p>}
    </section>
  );
}

function tableColumns(
  rows: SectionRow[],
  data: QueryResponse,
  subject: "player" | "team",
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
      key: "identity",
      header: subject === "team" ? "Team" : "Player",
      render: (row) =>
        subject === "team" ? teamCell(row, data) : playerCell(row),
    },
    {
      key: "date",
      header: "Date",
      render: (row) => formatCompactDate(textValue(row, "game_date")),
    },
    {
      key: "opponent",
      header: "Opp",
      render: (row) => opponentCell(row, data),
    },
    {
      key: "wl",
      header: "Result",
      align: "center",
      render: resultCell,
    },
  ];

  if (rows.some((row) => Boolean(scoreText(row, subject)))) {
    columns.push({
      key: "score",
      sourceKeys:
        subject === "team"
          ? ["pts", "opponent_pts", "team_score", "opponent_score"]
          : ["team_score", "team_pts", "opponent_score", "opponent_pts"],
      header: "Score",
      align: "center",
      render: (row) => scoreText(row, subject) ?? "—",
    });
  }

  columns.push({
    key: metric,
    header: statLabel(metric),
    numeric: metric !== "triple_double",
    align: metric === "triple_double" ? "center" : "right",
    render: (row) => metricTableValue(row, metric),
  });

  for (const key of supportingStatKeys(rows, metric)) {
    columns.push({
      key,
      header: statLabel(key),
      numeric: true,
      render: (row) => statValue(row, key),
    });
  }

  return columns;
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

function metricTableValue(row: SectionRow, metric: string): ReactNode {
  return <span className={styles.metricValue}>{metricValue(row, metric)}</span>;
}

function statValue(row: SectionRow, key: string): string {
  if (key === "plus_minus" && typeof row[key] === "number") {
    const formatted = formatValue(row[key], key);
    return row[key] > 0 ? `+${formatted}` : formatted;
  }
  return formatValue(row[key], key);
}

function supportingStatKeys(rows: SectionRow[], metric: string): string[] {
  const used = new Set([
    metric,
    "rank",
    "player_id",
    "player_name",
    "player",
    "team_id",
    "team_name",
    "team_abbr",
    "team",
    "game_date",
    "game_id",
    "opponent_team_id",
    "opponent_team_abbr",
    "opponent_team_name",
    "opponent",
    "wl",
    "is_home",
    "is_away",
    "season",
    "season_type",
    "opponent_pts",
    "team_score",
    "opponent_score",
  ]);

  if (metric === "triple_double") {
    used.add("pts");
    used.add("reb");
    used.add("ast");
  }

  const preferred = SUPPORTING_STATS_BY_METRIC[metric];
  if (preferred) {
    return preferred.filter(
      (key) => !used.has(key) && rows.some((row) => hasValue(row[key])),
    );
  }

  return STAT_ORDER.filter(
    (key) => !used.has(key) && rows.some((row) => hasValue(row[key])),
  ).slice(0, 3);
}

function primaryMetric(rows: SectionRow[], data: QueryResponse): string {
  if (
    isTripleDoubleIntent(data.result?.metadata, data.query) &&
    rows.some(
      (row) => hasValue(row.pts) && hasValue(row.reb) && hasValue(row.ast),
    )
  ) {
    return "triple_double";
  }

  for (const key of METRIC_HINT_KEYS) {
    const value = data.result?.metadata?.[key];
    if (typeof value === "string" && rows.some((row) => hasValue(row[value]))) {
      return value;
    }
  }

  const queryMetric = metricFromQuery(
    `${data.query ?? ""} ${data.result?.metadata?.query_text ?? ""}`,
  );
  if (queryMetric && rows.some((row) => hasValue(row[queryMetric]))) {
    return queryMetric;
  }

  return (
    STAT_ORDER.find((key) => rows.some((row) => hasValue(row[key]))) ?? "pts"
  );
}

function metricFromQuery(query: string): string | null {
  const lower = query.toLowerCase();
  if (/\b(points?|scoring|score)\b/.test(lower)) return "pts";
  if (/\b(rebounds?|boards?)\b/.test(lower)) return "reb";
  if (/\b(assists?|passing)\b/.test(lower)) return "ast";
  if (/\b(steals?)\b/.test(lower)) return "stl";
  if (/\b(blocks?)\b/.test(lower)) return "blk";
  if (/\b(threes?|three-pointers?|3pm|fg3m)\b/.test(lower)) return "fg3m";
  if (/\bplus[- ]minus|\+\/-\b/.test(lower)) return "plus_minus";
  return null;
}

function heroSentence(
  row: SectionRow,
  metric: string,
  data: QueryResponse,
  subject: "player" | "team",
): string {
  const leader = subject === "team" ? teamLabel(row) : entityLabel(row);
  const scope = scopePhrase(row, data.result?.metadata, data.query);
  const context = gameContextPhrase(row, data, subject);
  return `${leader} had the top ${singleGameMetricPhrase(metric)}${
    scope ? ` ${scope}` : ""
  } with ${metricSentenceValue(row, metric)}${context}.`;
}

function metricPhrase(metric: string): string {
  return (
    STAT_SENTENCE_LABELS[metric] ?? `${statLabel(metric).toLowerCase()} games`
  );
}

function singleGameMetricPhrase(metric: string): string {
  return metricPhrase(metric).replace(/\s+games$/, " game");
}

function metricSentenceValue(row: SectionRow, metric: string): string {
  if (metric === "triple_double") return metricValue(row, metric);
  const value = metricValue(row, metric);
  const unit = VALUE_UNITS[metric];
  return unit ? `${value} ${unit}` : value;
}

function metricValue(row: SectionRow, metric: string): string {
  if (metric === "triple_double") {
    return `${formatValue(row.pts, "pts")}-${formatValue(
      row.reb,
      "reb",
    )}-${formatValue(row.ast, "ast")}`;
  }
  return statValue(row, metric);
}

function gameContextPhrase(
  row: SectionRow,
  data: QueryResponse,
  subject: "player" | "team",
): string {
  const parts: string[] = [];
  const outcome = outcomeText(row);
  const score = scoreText(row, subject);
  if (outcome && score) {
    parts.push(`in a ${score} ${outcome}`);
  } else if (outcome) {
    parts.push(`in a ${outcome}`);
  } else if (score) {
    parts.push(`in a ${score} game`);
  }

  const opponent = opponentLabel(row, data);
  if (opponent) parts.push(`against ${opponent}`);

  const date = formatCompactDate(textValue(row, "game_date"));
  if (date !== "—") parts.push(`on ${date}`);

  return parts.length > 0 ? ` ${parts.join(" ")}` : "";
}

function outcomeText(row: SectionRow): string | null {
  const wl = textValue(row, "wl")?.toUpperCase();
  if (wl === "W") return "win";
  if (wl === "L") return "loss";
  return null;
}

function scoreText(row: SectionRow, subject: "player" | "team"): string | null {
  const teamScore =
    numericValue(row, "team_score") ??
    numericValue(row, "team_pts") ??
    (subject === "team" ? numericValue(row, "pts") : null);
  const opponentScore =
    numericValue(row, "opponent_score") ?? numericValue(row, "opponent_pts");
  if (teamScore === null || opponentScore === null) return null;
  return `${formatValue(teamScore, "pts")}-${formatValue(opponentScore, "pts")}`;
}

function opponentLabel(row: SectionRow, data: QueryResponse): string | null {
  const opponentContext = data.result?.metadata?.opponent_context;
  const team = resolveTeamIdentity({
    teamId: identityId(row.opponent_team_id) ?? opponentContext?.team_id,
    teamAbbr:
      textValue(row, "opponent_team_abbr") ??
      textValue(row, "opponent") ??
      opponentContext?.team_abbr,
    teamName:
      textValue(row, "opponent_team_name") ??
      textValue(row, "opponent") ??
      opponentContext?.team_name,
  });
  return (
    team.teamName ??
    team.teamAbbr ??
    textValue(row, "opponent_team_name") ??
    textValue(row, "opponent_team_abbr") ??
    textValue(row, "opponent")
  );
}

function scopePhrase(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
  query: string,
): string {
  const combinedQuery = `${query ?? ""} ${metadata?.query_text ?? ""}`;
  if (/\b(this season|this year)\b/i.test(combinedQuery)) return "this season";

  const season = textValue(row, "season") ?? metadataText(metadata, "season");
  const seasonType =
    textValue(row, "season_type") ?? metadataText(metadata, "season_type");
  if (season) {
    return `in the ${season}${seasonType ? ` ${seasonType.toLowerCase()}` : ""}`;
  }

  const since = combinedQuery.match(/\bsince\s+(\d{4})\b/i);
  if (since) return `since ${since[1]}`;

  return "";
}

function heroIdentity(row: SectionRow, subject: "player" | "team"): ReactNode {
  if (subject === "team") {
    return (
      <EntityIdentity
        kind="team"
        teamId={identityId(row.team_id)}
        teamAbbr={textValue(row, "team_abbr")}
        teamName={textValue(row, "team_name") ?? textValue(row, "team")}
      />
    );
  }

  return (
    <EntityIdentity
      kind="player"
      playerId={identityId(row.player_id)}
      playerName={textValue(row, "player_name") ?? textValue(row, "player")}
      teamAbbr={textValue(row, "team_abbr")}
    />
  );
}

function entityLabel(row: SectionRow): string {
  return textValue(row, "player_name") ?? textValue(row, "player") ?? "Player";
}

function teamLabel(row: SectionRow): string {
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

function isTripleDoubleIntent(
  metadata: ResultMetadata | undefined,
  query: string,
): boolean {
  const occurrence = metadata?.occurrence_event;
  if (
    occurrence &&
    typeof occurrence === "object" &&
    !Array.isArray(occurrence)
  ) {
    const event = occurrence as Record<string, unknown>;
    if (event.special_event === "triple_double") return true;
  }

  if (metadata?.special_event === "triple_double") return true;

  const notes = metadata?.notes;
  const unsupportedFallback =
    Array.isArray(notes) &&
    notes.some(
      (note) =>
        typeof note === "string" && note.includes("unsupported_boundary"),
    );
  return (
    !unsupportedFallback &&
    /\btriple[- ]double\b/i.test(`${query ?? ""} ${metadata?.query_text ?? ""}`)
  );
}

function statLabel(key: string): string {
  return (
    STAT_LABELS[key] ??
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

function rankValue(row: SectionRow, index: number): string {
  return typeof row.rank === "number" || typeof row.rank === "string"
    ? String(row.rank)
    : String(index + 1);
}

function rowKey(row: SectionRow, index: number): string {
  return [
    row.rank,
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
  ...keys: string[]
): number | null {
  for (const key of keys) {
    const value = metadata?.[key];
    if (typeof value === "number" && Number.isFinite(value)) return value;
  }
  return null;
}

function numericValue(row: SectionRow, key: string): number | null {
  const value = row[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function identityId(value: unknown): number | string | null {
  return typeof value === "number" || typeof value === "string" ? value : null;
}

function hasValue(value: unknown): boolean {
  return value !== null && value !== undefined && value !== "";
}
