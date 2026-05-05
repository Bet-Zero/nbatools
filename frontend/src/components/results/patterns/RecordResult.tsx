import type { ReactNode } from "react";
import type {
  QueryResponse,
  ResultMetadata,
  SectionRow,
} from "../../../api/types";
import { formatColHeader, formatValue } from "../../tableFormatting";
import EntityIdentity from "../primitives/EntityIdentity";
import RawDetailToggle from "../primitives/RawDetailToggle";
import ResultHero from "../primitives/ResultHero";
import ResultTable, { type ResultTableColumn } from "../primitives/ResultTable";
import styles from "./RecordResult.module.css";

type RecordMode =
  | "team_record"
  | "record_by_decade"
  | "record_by_decade_leaderboard"
  | "matchup_by_decade";

interface Props {
  data: QueryResponse;
  mode: RecordMode;
}

type TeamDisplay = {
  id: number | string | null;
  abbr: string | null;
  name: string;
};

const TEAM_RECORD_STATS = [
  "games",
  "win_pct",
  "pts_avg",
  "opponent_pts_avg",
  "plus_minus_avg",
  "net_rating",
  "reb_avg",
  "ast_avg",
  "fg3m_avg",
  "season_type",
];

const RECORD_LABELS: Record<string, string> = {
  ast_avg: "AST",
  decade: "Decade",
  fg3m_avg: "3PM",
  games: "Games",
  games_played: "Games",
  losses: "Losses",
  net_rating: "Net",
  opponent_pts_avg: "Opp PPG",
  plus_minus_avg: "+/-",
  pts_avg: "PPG",
  reb_avg: "REB",
  season_type: "Type",
  seasons: "Seasons",
  seasons_appeared: "Seasons",
  win_pct: "Win %",
  wins: "Wins",
};

export default function RecordResult({ data, mode }: Props) {
  switch (mode) {
    case "team_record":
      return <TeamRecordResult data={data} />;
    case "record_by_decade":
      return <RecordByDecadeResult data={data} />;
    case "record_by_decade_leaderboard":
      return <RecordByDecadeLeaderboardResult data={data} />;
    case "matchup_by_decade":
      return <MatchupByDecadeResult data={data} />;
  }
}

function TeamRecordResult({ data }: { data: QueryResponse }) {
  const sections = data.result?.sections ?? {};
  const summary = sections.summary ?? [];
  const row = summary[0];
  if (!row) return null;

  const team = teamDisplay(data.result?.metadata, row);
  const opponent = opponentDisplay(data.result?.metadata);

  return (
    <section className={styles.pattern} aria-label="Team record result">
      <ResultHero
        sentence={teamRecordSentence(team, opponent, row, data)}
        subjectIllustration={teamIdentity(team)}
        tone="team"
      />
      <ResultTable
        rows={summary}
        columns={teamRecordColumns(team, opponent, summary)}
        highlightColumnKey="record"
        ariaLabel="Team record"
        getRowKey={(_summaryRow, index) => `${team.name}-${index}`}
      />
      <RawDetailToggle title="Record Detail" rows={summary} />
      <RawDetailToggle
        title="By Season Detail"
        rows={sections.by_season ?? []}
      />
    </section>
  );
}

function RecordByDecadeResult({ data }: { data: QueryResponse }) {
  const sections = data.result?.sections ?? {};
  const summary = sections.summary ?? [];
  const rows = sections.by_season ?? [];
  const row = summary[0];
  if (!row && rows.length === 0) return null;

  const team = teamDisplay(data.result?.metadata, row ?? rows[0]);

  return (
    <section className={styles.pattern} aria-label="Record by decade result">
      <ResultHero
        sentence={recordByDecadeSentence(team, row, data)}
        subjectIllustration={teamIdentity(team)}
        tone="team"
      />
      <ResultTable
        rows={rows}
        columns={decadeRecordColumns(rows)}
        highlightColumnKey="win_pct"
        ariaLabel="Record by decade"
        getRowKey={(decadeRow, index) =>
          `${textValue(decadeRow, "decade") ?? "decade"}-${index}`
        }
      />
      <RawDetailToggle title="Record Detail" rows={summary} />
    </section>
  );
}

function RecordByDecadeLeaderboardResult({ data }: { data: QueryResponse }) {
  const rows = data.result?.sections?.leaderboard ?? [];
  if (rows.length === 0) return null;

  const metric = recordLeaderboardMetric(rows, data);
  const first = rows[0];
  const team = teamDisplay(data.result?.metadata, first);

  return (
    <section
      className={styles.pattern}
      aria-label="Record by decade leaderboard result"
    >
      <ResultHero
        sentence={recordLeaderboardSentence(team, first, metric, data)}
        subjectIllustration={teamIdentity(team)}
        tone="team"
      />
      <ResultTable
        rows={rows}
        columns={recordLeaderboardColumns(rows, metric)}
        highlightColumnKey={metric}
        ariaLabel="Record by decade leaderboard"
        getRowKey={(leaderboardRow, index) =>
          `${rankValue(leaderboardRow, index)}-${teamNameFromRow(leaderboardRow)}-${
            textValue(leaderboardRow, "decade") ?? "decade"
          }`
        }
      />
    </section>
  );
}

function MatchupByDecadeResult({ data }: { data: QueryResponse }) {
  const sections = data.result?.sections ?? {};
  const summary = sections.summary ?? [];
  const comparison = sections.comparison ?? [];
  if (summary.length === 0 && comparison.length === 0) return null;

  const teams = matchupTeams(data.result?.metadata, summary, comparison[0]);

  return (
    <section className={styles.pattern} aria-label="Matchup by decade result">
      <ResultHero
        sentence={matchupByDecadeSentence(teams, summary, data)}
        subjectIllustration={<MatchupIdentity teams={teams} />}
        tone="team"
      />
      <ResultTable
        rows={comparison}
        columns={matchupColumns(comparison, teams)}
        ariaLabel="Matchup by decade"
        getRowKey={(row, index) =>
          `${textValue(row, "decade") ?? "decade"}-${index}`
        }
      />
      <RawDetailToggle title="Matchup Summary Detail" rows={summary} />
    </section>
  );
}

function teamRecordColumns(
  team: TeamDisplay,
  opponent: TeamDisplay | null,
  rows: SectionRow[],
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [
    {
      key: "team",
      header: "Team",
      render: () => (
        <span className={styles.entityCell}>{teamIdentity(team)}</span>
      ),
    },
  ];

  if (opponent) {
    columns.push({
      key: "opponent",
      header: "Opponent",
      render: () => (
        <span className={styles.entityCell}>{teamIdentity(opponent)}</span>
      ),
    });
  }

  columns.push({
    key: "record",
    header: "W-L",
    align: "center",
    render: (row) => recordText(row),
  });

  for (const key of TEAM_RECORD_STATS) {
    if (rows.some((row) => hasValue(row[key]))) {
      columns.push(valueColumn(key));
    }
  }

  return columns;
}

function decadeRecordColumns(
  rows: SectionRow[],
): Array<ResultTableColumn<SectionRow>> {
  return [
    valueColumn("decade"),
    optionalValueColumn("seasons_appeared", rows),
    {
      key: "record",
      header: "W-L",
      align: "center",
      render: (row: SectionRow) => recordText(row),
    },
    valueColumn("win_pct"),
    optionalValueColumn("games", rows),
    optionalValueColumn("season_type", rows),
  ].filter((column): column is ResultTableColumn<SectionRow> =>
    Boolean(column),
  );
}

function recordLeaderboardColumns(
  rows: SectionRow[],
  metric: string,
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow> | null> = [
    {
      key: "rank",
      header: "#",
      align: "center",
      render: rankValue,
    },
    {
      key: "team",
      header: "Team",
      render: (row) => (
        <span className={styles.entityCell}>
          {teamIdentity(teamDisplay(undefined, row))}
        </span>
      ),
    },
    optionalValueColumn("decade", rows),
    valueColumn(metric),
    {
      key: "record",
      header: "W-L",
      align: "center",
      render: (row) => recordText(row),
    },
    metric === "games_played"
      ? null
      : optionalValueColumn("games_played", rows),
    metric === "games" ? null : optionalValueColumn("games", rows),
    metric === "win_pct" ? null : optionalValueColumn("win_pct", rows),
    optionalValueColumn("seasons", rows),
    optionalValueColumn("season_type", rows),
  ];

  return columns.filter((column): column is ResultTableColumn<SectionRow> =>
    Boolean(column),
  );
}

function matchupColumns(
  rows: SectionRow[],
  teams: TeamDisplay[],
): Array<ResultTableColumn<SectionRow>> {
  const [first, second] = matchupPrefixes(rows, teams);
  const columns: Array<ResultTableColumn<SectionRow>> = [valueColumn("decade")];

  for (const prefix of [first, second]) {
    columns.push({
      key: `${prefix}_record`,
      header: `${prefix} W-L`,
      align: "center",
      render: (row) => prefixedRecordText(row, prefix),
    });
    const pctKey = `${prefix}_win_pct`;
    if (rows.some((row) => hasValue(row[pctKey]))) {
      columns.push(valueColumn(pctKey, `${prefix} Win %`));
    }
    for (const key of [`${prefix}_pts_avg`, `${prefix}_pts_per_game`]) {
      if (rows.some((row) => hasValue(row[key]))) {
        columns.push(valueColumn(key, `${prefix} PPG`));
      }
    }
  }

  return columns;
}

function valueColumn(
  key: string,
  labelOverride?: string,
): ResultTableColumn<SectionRow> {
  return {
    key,
    header: labelOverride ?? columnLabel(key),
    numeric: isNumericKey(key),
    align: isNumericKey(key) ? "right" : "left",
    render: (row) => formatValue(row[key], key),
  };
}

function optionalValueColumn(
  key: string,
  rows: SectionRow[],
): ResultTableColumn<SectionRow> | null {
  return rows.some((row) => hasValue(row[key])) ? valueColumn(key) : null;
}

function teamRecordSentence(
  team: TeamDisplay,
  opponent: TeamDisplay | null,
  row: SectionRow,
  data: QueryResponse,
): string {
  const context = recordContext(row, data.result?.metadata, data.query);
  const opponentPhrase = opponent ? ` against the ${opponent.name}` : "";
  const record = recordText(row);
  const winPct = hasValue(row.win_pct)
    ? `, a ${formatValue(row.win_pct, "win_pct")} win rate`
    : "";

  if (record) {
    return `The ${team.name} are ${record}${context}${opponentPhrase}${winPct}.`;
  }
  return `The ${team.name} have a record summary${context}${opponentPhrase}.`;
}

function recordByDecadeSentence(
  team: TeamDisplay,
  row: SectionRow | undefined,
  data: QueryResponse,
): string {
  if (!row) return `The ${team.name} have decade records available.`;

  const context = recordRangeContext(row, data.result?.metadata);
  const record = recordText(row);
  const winPct = hasValue(row.win_pct)
    ? ` (${formatValue(row.win_pct, "win_pct")})`
    : "";

  if (record) {
    return `The ${team.name} are ${record}${winPct}${context}, grouped by decade.`;
  }
  return `The ${team.name} have records${context}, grouped by decade.`;
}

function recordLeaderboardSentence(
  team: TeamDisplay,
  row: SectionRow,
  metric: string,
  data: QueryResponse,
): string {
  const decade = textValue(row, "decade");
  const decadeContext = decade ? ` in the ${decade}` : "";
  const since = sinceContext(data.query);
  const metricValue = formatValue(row[metric], metric);

  if (metric === "wins") {
    return `The ${team.name} won the most games${decadeContext}${since}, with ${metricValue} wins.`;
  }
  if (metric === "losses") {
    return `The ${team.name} had the most losses${decadeContext}${since}, with ${metricValue} losses.`;
  }
  if (metric === "win_pct") {
    return `The ${team.name} had the best winning percentage${decadeContext}${since}, at ${metricValue}.`;
  }
  if (metric === "games_played" || metric === "games") {
    return `The ${team.name} played the most games${decadeContext}${since}, with ${metricValue}.`;
  }
  return `The ${team.name} led the historical leaderboard${decadeContext}${since}, with ${metricValue} ${columnLabel(
    metric,
  ).toLowerCase()}.`;
}

function matchupByDecadeSentence(
  teams: TeamDisplay[],
  summary: SectionRow[],
  data: QueryResponse,
): string {
  const [first, second] = teams;
  const firstName = first?.name ?? "Team 1";
  const secondName = second?.name ?? "Team 2";
  const firstRow = summary[0];
  const record = firstRow ? recordText(firstRow) : null;
  const wins = firstRow ? numericValue(firstRow, "wins") : null;
  const losses = firstRow ? numericValue(firstRow, "losses") : null;
  const context = matchupContext(data.result?.metadata);

  if (record && wins !== null && losses !== null) {
    if (wins > losses) {
      return `The ${firstName} lead the ${secondName} ${record}${context}, grouped by decade.`;
    }
    if (wins < losses) {
      return `The ${secondName} lead the ${firstName} ${losses}-${wins}${context}, grouped by decade.`;
    }
    return `The ${firstName} and ${secondName} are tied ${record}${context}, grouped by decade.`;
  }

  return `The ${firstName} and ${secondName} have matchup records${context}, grouped by decade.`;
}

function recordLeaderboardMetric(
  rows: SectionRow[],
  data: QueryResponse,
): string {
  const metadata = data.result?.metadata;
  const stat =
    metadataText(metadata, "stat") ?? metadataText(metadata, "metric");
  if (stat && rows.some((row) => hasValue(row[stat]))) return stat;

  const query =
    `${data.query ?? ""} ${metadata?.query_text ?? ""}`.toLowerCase();
  if (
    /\b(losses|worst)\b/.test(query) &&
    rows.some((row) => hasValue(row.losses))
  ) {
    return "losses";
  }
  if (
    /\b(win pct|winning percentage|winning pct|winningest|best record)\b/.test(
      query,
    ) &&
    rows.some((row) => hasValue(row.win_pct))
  ) {
    return "win_pct";
  }
  if (/\b(games played|most games)\b/.test(query)) {
    if (rows.some((row) => hasValue(row.games_played))) return "games_played";
    if (rows.some((row) => hasValue(row.games))) return "games";
  }
  if (rows.some((row) => hasValue(row.wins))) return "wins";
  if (rows.some((row) => hasValue(row.win_pct))) return "win_pct";
  return (
    Object.keys(rows[0] ?? {}).find((key) =>
      rows.some((row) => hasValue(row[key])),
    ) ?? "rank"
  );
}

function recordContext(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
  query: string,
): string {
  if (/\bthis season\b/i.test(query)) return " this season";

  const season = metadataText(metadata, "season");
  const seasonType =
    textValue(row, "season_type") ?? metadataText(metadata, "season_type");
  if (season) {
    return ` in the ${season}${seasonType ? ` ${seasonType.toLowerCase()}` : ""}`;
  }

  return recordRangeContext(row, metadata);
}

function recordRangeContext(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
): string {
  const start =
    textValue(row, "season_start") ?? metadataText(metadata, "start_season");
  const end =
    textValue(row, "season_end") ?? metadataText(metadata, "end_season");
  const seasonType =
    textValue(row, "season_type") ?? metadataText(metadata, "season_type");
  const singleSeasonSuffix = seasonType ? ` ${seasonType.toLowerCase()}` : "";
  const rangeSuffix = seasonType ? ` in the ${seasonType.toLowerCase()}` : "";

  if (start && end) {
    return start === end
      ? ` in the ${start}${singleSeasonSuffix}`
      : ` from ${start} to ${end}${rangeSuffix}`;
  }
  if (start) return ` since ${start}${rangeSuffix}`;
  if (end) return ` through ${end}${rangeSuffix}`;
  return seasonType ? ` in the ${seasonType.toLowerCase()}` : "";
}

function matchupContext(metadata: ResultMetadata | undefined): string {
  const seasonType = metadataText(metadata, "season_type");
  return seasonType ? ` in ${seasonType.toLowerCase()} games` : "";
}

function sinceContext(query: string): string {
  const match = query.match(/\bsince\s+(\d{4})\b/i);
  return match ? ` since ${match[1]}` : "";
}

function MatchupIdentity({ teams }: { teams: TeamDisplay[] }) {
  if (teams.length === 0) return null;

  return (
    <span className={styles.matchupIdentity}>
      {teams[0] && teamIdentity(teams[0])}
      {teams[1] && <span className={styles.vsBadge}>vs</span>}
      {teams[1] && teamIdentity(teams[1])}
    </span>
  );
}

function teamIdentity(team: TeamDisplay): ReactNode {
  return (
    <EntityIdentity
      kind="team"
      teamId={team.id}
      teamAbbr={team.abbr}
      teamName={team.name}
    />
  );
}

function teamDisplay(
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
): TeamDisplay {
  const context = metadata?.team_context;
  return {
    id: identityId(row?.team_id) ?? context?.team_id ?? null,
    abbr:
      textValue(row, "team_abbr") ??
      context?.team_abbr ??
      textValue(row, "team") ??
      null,
    name:
      textValue(row, "team_name") ??
      context?.team_name ??
      textValue(row, "team") ??
      textValue(row, "team_abbr") ??
      "Team",
  };
}

function opponentDisplay(
  metadata: ResultMetadata | undefined,
): TeamDisplay | null {
  const context = metadata?.opponent_context;
  if (!context) return null;
  return {
    id: context.team_id,
    abbr: context.team_abbr,
    name: context.team_name,
  };
}

function matchupTeams(
  metadata: ResultMetadata | undefined,
  summary: SectionRow[],
  comparisonRow: SectionRow | undefined,
): TeamDisplay[] {
  const contexts = metadata?.teams_context ?? [];
  const prefixes = matchupPrefixes(comparisonRow ? [comparisonRow] : [], []);
  return [0, 1].map((index) => {
    const context = contexts[index];
    const row = summary[index];
    return {
      id: identityId(row?.team_id) ?? context?.team_id ?? null,
      abbr:
        textValue(row, "team_abbr") ??
        context?.team_abbr ??
        prefixes[index] ??
        null,
      name:
        textValue(row, "team_name") ??
        context?.team_name ??
        textValue(row, "team") ??
        prefixes[index] ??
        `Team ${index + 1}`,
    };
  });
}

function matchupPrefixes(
  rows: SectionRow[],
  teams: TeamDisplay[],
): [string, string] {
  const fromTeams = teams
    .map((team) => team.abbr)
    .filter((abbr): abbr is string => Boolean(abbr));
  if (fromTeams.length >= 2) return [fromTeams[0], fromTeams[1]];

  const prefixes = rows
    .flatMap((row) => Object.keys(row))
    .map((key) => key.match(/^(.+)_wins$/)?.[1])
    .filter((prefix): prefix is string => Boolean(prefix));

  return [
    prefixes[0] ?? fromTeams[0] ?? "Team 1",
    prefixes[1] ?? fromTeams[1] ?? "Team 2",
  ];
}

function rankValue(row: SectionRow, index: number): string {
  if (typeof row.rank === "number" || typeof row.rank === "string") {
    return String(row.rank);
  }
  return String(index + 1);
}

function recordText(row: SectionRow): string | null {
  const wins = row.wins;
  const losses = row.losses;
  if (!hasValue(wins) || !hasValue(losses)) return null;
  return `${formatValue(wins, "wins")}-${formatValue(losses, "losses")}`;
}

function prefixedRecordText(row: SectionRow, prefix: string): string | null {
  const wins = row[`${prefix}_wins`];
  const losses = row[`${prefix}_losses`];
  if (!hasValue(wins) || !hasValue(losses)) return null;
  return `${formatValue(wins, "wins")}-${formatValue(losses, "losses")}`;
}

function teamNameFromRow(row: SectionRow): string {
  return (
    textValue(row, "team_name") ??
    textValue(row, "team") ??
    textValue(row, "team_abbr") ??
    "Team"
  );
}

function columnLabel(key: string): string {
  if (RECORD_LABELS[key]) return RECORD_LABELS[key];

  const prefixedPct = key.match(/^(.+)_win_pct$/);
  if (prefixedPct) return `${prefixedPct[1]} Win %`;

  return formatColHeader(key)
    .replace(/\bPts\b/g, "PTS")
    .replace(/\bReb\b/g, "REB")
    .replace(/\bAst\b/g, "AST")
    .replace(/\bFg3m\b/g, "3PM")
    .replace(/\bPct\b/g, "%");
}

function isNumericKey(key: string): boolean {
  return ![
    "team",
    "opponent",
    "record",
    "decade",
    "season_type",
    "seasons",
  ].includes(key);
}

function numericValue(row: SectionRow, key: string): number | null {
  const value = row[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function textValue(row: SectionRow | undefined, key: string): string | null {
  const value = row?.[key];
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
