import type { ReactNode } from "react";
import type {
  QueryResponse,
  ResultMetadata,
  SectionRow,
} from "../../../api/types";
import { Badge } from "../../../design-system";
import { formatColHeader, formatValue } from "../../tableFormatting";
import EntityIdentity from "../primitives/EntityIdentity";
import RawDetailToggle from "../primitives/RawDetailToggle";
import ResultHero from "../primitives/ResultHero";
import ResultTable, { type ResultTableColumn } from "../primitives/ResultTable";
import {
  resultTableSourceKeys,
  rowsHaveAdditionalDetailFields,
} from "../primitives/detailTables";
import styles from "./PlayoffHistoryResult.module.css";

type PlayoffMode = "history" | "round_record" | "matchup";

interface Props {
  data: QueryResponse;
  mode?: PlayoffMode;
}

type TeamDisplay = {
  id: number | string | null;
  name: string;
  teamAbbr: string | null;
};

const HISTORY_DETAIL_TITLES: Record<string, string> = {
  summary: "Postseason Summary Detail",
  by_season: "Season Breakdown Detail",
};

const MATCHUP_DETAIL_TITLES: Record<string, string> = {
  summary: "Postseason Summary Detail",
  comparison: "Series Detail",
};

const EMPTY_CELL = "—";
const ROUND_UNAVAILABLE = "Round unavailable";
const RESULT_UNAVAILABLE = "Result unavailable";

export default function PlayoffHistoryResult({ data, mode }: Props) {
  const route = data.route ?? data.result?.metadata?.route;
  const resolvedMode = mode ?? modeFromRoute(route);

  if (resolvedMode === "matchup") {
    return <PlayoffMatchupResult data={data} />;
  }

  if (resolvedMode === "round_record") {
    return <PlayoffRoundRecordResult data={data} />;
  }

  return <PlayoffTeamHistoryResult data={data} />;
}

function PlayoffTeamHistoryResult({ data }: { data: QueryResponse }) {
  const sections = data.result?.sections ?? {};
  const summaryRows = sections.summary ?? [];
  const seasonRows = sections.by_season ?? [];
  const summary = summaryRows[0] ?? seasonRows[0];

  if (!summary) return null;

  const team = teamDisplay(data.result?.metadata, summary);
  const rows = seasonRows.length > 0 ? seasonRows : summaryRows;
  const columns = historyColumns(rows);
  const visibleDetailKeys: Record<string, Iterable<string>> = {};
  visibleDetailKeys[seasonRows.length > 0 ? "by_season" : "summary"] =
    resultTableSourceKeys(columns);

  return (
    <section className={styles.pattern} aria-label="Playoff history result">
      <ResultHero
        sentence={historySentence(team.name, data.result?.metadata, summary)}
        subjectIllustration={teamIdentity(team)}
        tone="team"
        teamAccentAbbr={team.teamAbbr}
      />
      <ResultTable
        rows={rows}
        columns={columns}
        ariaLabel="Playoff season breakdown"
        getRowKey={rowKey}
      />
      {detailToggles(sections, HISTORY_DETAIL_TITLES, visibleDetailKeys)}
    </section>
  );
}

function PlayoffRoundRecordResult({ data }: { data: QueryResponse }) {
  const rows =
    data.result?.sections?.leaderboard ??
    data.result?.sections?.summary ??
    data.result?.sections?.by_season ??
    [];

  if (rows.length === 0) return null;

  const leader = rows[0];
  const team = teamDisplay(data.result?.metadata, leader);
  const columns = roundRecordColumns(rows, data.result?.metadata);
  const hasAdditionalDetail = rowsHaveAdditionalDetailFields(
    rows,
    resultTableSourceKeys(columns),
  );

  return (
    <section
      className={styles.pattern}
      aria-label="Playoff round record result"
    >
      <ResultHero
        sentence={roundRecordSentence(team.name, data.result?.metadata, leader)}
        subjectIllustration={teamIdentity(team)}
        tone="team"
        teamAccentAbbr={team.teamAbbr}
      />
      <ResultTable
        rows={rows}
        columns={columns}
        ariaLabel="Playoff round records"
        getRowKey={rowKey}
        highlightColumnKey={roundRecordMetricKey(rows)}
      />
      {hasAdditionalDetail && (
        <RawDetailToggle
          title="Playoff Round Detail"
          rows={rows}
          highlight
          collapsedLabel="Show additional columns"
          expandedLabel="Hide additional columns"
        />
      )}
    </section>
  );
}

function PlayoffMatchupResult({ data }: { data: QueryResponse }) {
  const sections = data.result?.sections ?? {};
  const summaryRows = sections.summary ?? [];
  const seriesRows = sections.comparison ?? [];
  const teams = matchupTeams(data.result?.metadata, summaryRows);
  const rows = seriesRows.length > 0 ? seriesRows : summaryRows;
  const columns = matchupColumns(rows, teams);
  const visibleDetailKeys = {
    [seriesRows.length > 0 ? "comparison" : "summary"]:
      resultTableSourceKeys(columns),
  };

  if (teams.length === 0 && rows.length === 0) return null;

  return (
    <section className={styles.pattern} aria-label="Playoff matchup result">
      <ResultHero
        sentence={matchupSentence(teams, summaryRows)}
        subjectIllustration={<MatchupIdentity teams={teams} />}
        tone="neutral"
      />
      <ResultTable
        rows={rows}
        columns={columns}
        ariaLabel={
          seriesRows.length > 0 ? "Playoff series" : "Playoff matchup teams"
        }
        getRowKey={rowKey}
      />
      {detailToggles(sections, MATCHUP_DETAIL_TITLES, visibleDetailKeys)}
    </section>
  );
}

function historySentence(
  teamName: string,
  metadata: ResultMetadata | undefined,
  row: SectionRow,
): ReactNode {
  const appearances =
    numericValue(row, "appearances") ?? numericValue(row, "seasons_appeared");
  const record = recordText(row);
  const range = seasonRange(metadata, row);
  const titleCount =
    numericValue(row, "titles") ?? numericValue(row, "championships");
  const finals =
    numericValue(row, "finals") ?? numericValue(row, "finals_appearances");
  const context = [
    range,
    textValue(row, "season_type") ?? metadataText(metadata, "season_type"),
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <>
      {teamName} have{" "}
      {appearances !== null ? (
        <>
          <span className={styles.heroValue}>
            {formatValue(appearances, "appearances")}
          </span>{" "}
          playoff {appearances === 1 ? "appearance" : "appearances"}
        </>
      ) : (
        "a playoff history"
      )}
      {context ? ` across ${context}` : ""}
      {record ? `, going ${record}` : ""}
      {titleCount !== null
        ? ` with ${titleCount} ${titleCount === 1 ? "title" : "titles"}`
        : ""}
      {titleCount === null && finals !== null
        ? ` with ${finals} ${finals === 1 ? "Finals trip" : "Finals trips"}`
        : ""}
      .
    </>
  );
}

function roundRecordSentence(
  teamName: string,
  metadata: ResultMetadata | undefined,
  row: SectionRow,
): ReactNode {
  const round = roundLabel(metadata, row);
  const record = recordText(row);
  const metricKey = roundRecordMetricKey([row]);
  const metric = metricKey ? formatValue(row[metricKey], metricKey) : null;
  const games =
    numericValue(row, "games_played") ??
    numericValue(row, "games") ??
    numericValue(row, "series");

  return (
    <>
      {teamName} own{" "}
      {metric ? <span className={styles.heroValue}>{metric}</span> : "the top"}{" "}
      {round ? `${round.toLowerCase()} playoff mark` : "playoff round mark"}
      {record ? ` (${record})` : ""}
      {games !== null ? ` across ${formatValue(games, "games")} games` : ""}.
    </>
  );
}

function matchupSentence(teams: TeamDisplay[], rows: SectionRow[]): string {
  const first = teams[0]?.name ?? "Team 1";
  const second = teams[1]?.name ?? "Team 2";
  const firstRecord = recordText(rows[0]);
  const firstWins = numericValue(rows[0], "wins");
  const firstLosses = numericValue(rows[0], "losses");

  if (firstRecord && firstWins !== null && firstLosses !== null) {
    if (firstWins > firstLosses) {
      return `The ${first} lead the ${second} ${firstRecord} in their playoff history.`;
    }
    if (firstWins < firstLosses) {
      return `The ${second} lead the ${first} ${firstLosses}-${firstWins} in their playoff history.`;
    }
    return `The ${first} and ${second} are tied ${firstRecord} in their playoff history.`;
  }

  return `The ${first} and ${second} have playoff matchup history.`;
}

function historyColumns(
  rows: SectionRow[],
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [
    textColumn("season", "Season"),
    {
      key: "round",
      sourceKeys: ["round_reached", "deepest_round", "playoff_round", "round"],
      header: "Round",
      render: (row) => roundCell(row),
    },
    {
      key: "record",
      sourceKeys: ["wins", "losses", "games", "games_played", "series"],
      header: "Record",
      align: "center",
      render: (row) => recordText(row) ?? gameCount(row) ?? EMPTY_CELL,
    },
  ];

  if (rows.some((row) => hasValue(row.result))) {
    columns.push({
      key: "result",
      sourceKeys: ["result"],
      header: "Result",
      render: (row) => playoffResultValue(row),
    });
  }
  columns.push({
    key: "opponent",
    sourceKeys: ["opponent", "opponent_team_name", "opponent_team_abbr"],
    header: "Opponent",
    render: opponentValue,
  });

  addNumericIfPresent(columns, rows, "win_pct", "Win Pct");
  addNumericIfPresent(columns, rows, "games", "Games");

  return columns.filter((column) =>
    column.key === "opponent" ? rows.some((row) => hasOpponent(row)) : true,
  );
}

function roundRecordColumns(
  rows: SectionRow[],
  metadata: ResultMetadata | undefined,
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [
    {
      key: "rank",
      sourceKeys: ["rank"],
      header: "#",
      align: "center",
      render: (row, index) => rankValue(row, index),
    },
    {
      key: "team",
      sourceKeys: ["team", "team_name", "team_abbr", "team_id"],
      header: "Team",
      render: (row) => teamIdentity(teamDisplay(metadata, row)),
    },
    {
      key: "round",
      sourceKeys: ["round", "playoff_round", "round_reached", "deepest_round"],
      header: "Round",
      render: (row) => roundLabel(metadata, row) ?? ROUND_UNAVAILABLE,
    },
    {
      key: "record",
      sourceKeys: ["wins", "losses"],
      header: "Record",
      align: "center",
      render: (row) => recordText(row) ?? EMPTY_CELL,
    },
  ];

  addIfPresent(columns, rows, "seasons", "Seasons");
  addNumericIfPresent(columns, rows, "games_played", "Games");
  addNumericIfPresent(columns, rows, "win_pct", "Win Pct");
  addNumericIfPresent(columns, rows, "series", "Series");

  return columns;
}

function matchupColumns(
  rows: SectionRow[],
  teams: TeamDisplay[],
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [];

  if (rows.some((row) => hasValue(row.season))) {
    columns.push(textColumn("season", "Season"));
  }

  if (rows.some((row) => hasValue(row.round) || hasValue(row.playoff_round))) {
    columns.push({
      key: "round",
      sourceKeys: ["round", "playoff_round", "round_reached", "deepest_round"],
      header: "Round",
      render: (row) => roundCell(row),
    });
  }

  if (rows.some((row) => hasWinner(row))) {
    columns.push({
      key: "winner",
      sourceKeys: ["winner", "winner_team_name", "winner_team_abbr"],
      header: "Winner",
      render: winnerValue,
    });
  }

  if (rows.some((row) => hasValue(row.result) || hasValue(row.series_result))) {
    columns.push({
      key: "result",
      sourceKeys: ["series_result", "result"],
      header: "Result",
      render: (row) => playoffResultValue(row),
    });
  }

  for (const team of teams) {
    if (!team.teamAbbr) continue;
    const winsKey = `${team.teamAbbr}_wins`;
    const lossesKey = `${team.teamAbbr}_losses`;
    if (
      !rows.some((row) => hasValue(row[winsKey]) || hasValue(row[lossesKey]))
    ) {
      continue;
    }
    columns.push({
      key: `${team.teamAbbr}_record`,
      sourceKeys: [winsKey, lossesKey],
      header: team.teamAbbr,
      align: "center",
      render: (row) => recordText(row, winsKey, lossesKey) ?? EMPTY_CELL,
    });
  }

  if (columns.length === 0) {
    return [
      {
        key: "team",
        sourceKeys: ["team", "team_name", "team_abbr", "team_id"],
        header: "Team",
        render: (row, index) =>
          teamIdentity(teamDisplay(undefined, row, index)),
      },
      {
        key: "record",
        sourceKeys: ["wins", "losses"],
        header: "Record",
        align: "center",
        render: (row) => recordText(row) ?? EMPTY_CELL,
      },
    ];
  }

  addNumericIfPresent(columns, rows, "games", "Games");
  return columns;
}

function addIfPresent(
  columns: Array<ResultTableColumn<SectionRow>>,
  rows: SectionRow[],
  key: string,
  label: string,
) {
  if (!rows.some((row) => hasValue(row[key]))) return;
  columns.push(textColumn(key, label));
}

function addNumericIfPresent(
  columns: Array<ResultTableColumn<SectionRow>>,
  rows: SectionRow[],
  key: string,
  label: string,
) {
  if (!rows.some((row) => hasValue(row[key]))) return;
  columns.push({
    key,
    sourceKeys: [key],
    header: label,
    numeric: true,
    render: (row) => formatValue(row[key], key),
  });
}

function textColumn(key: string, label: string): ResultTableColumn<SectionRow> {
  return {
    key,
    sourceKeys: [key],
    header: label,
    render: (row) => textValue(row, key) ?? EMPTY_CELL,
  };
}

function detailToggles(
  sections: Record<string, SectionRow[]>,
  titles: Record<string, string>,
  visibleKeysBySection: Record<string, Iterable<string>> = {},
) {
  return Object.keys(sections)
    .filter((key) => sections[key]?.length > 0)
    .map((key) => {
      const visibleKeys = visibleKeysBySection[key];
      if (
        visibleKeys &&
        !rowsHaveAdditionalDetailFields(sections[key], visibleKeys)
      ) {
        return null;
      }
      const isAdditionalColumns = Boolean(visibleKeys);
      return (
        <RawDetailToggle
          key={key}
          title={titles[key] ?? `${formatColHeader(key)} Detail`}
          rows={sections[key]}
          highlight={key !== "summary"}
          collapsedLabel={
            isAdditionalColumns ? "Show additional columns" : undefined
          }
          expandedLabel={
            isAdditionalColumns ? "Hide additional columns" : undefined
          }
        />
      );
    });
}

function MatchupIdentity({ teams }: { teams: TeamDisplay[] }) {
  if (teams.length === 0) return null;

  return (
    <span className={styles.matchupIdentity}>
      {teamIdentity(teams[0])}
      {teams[1] && (
        <Badge variant="neutral" size="sm" uppercase>
          vs
        </Badge>
      )}
      {teams[1] && teamIdentity(teams[1])}
    </span>
  );
}

function teamIdentity(team: TeamDisplay): ReactNode {
  return (
    <EntityIdentity
      kind="team"
      teamId={team.id}
      teamAbbr={team.teamAbbr}
      teamName={team.name}
      size="md"
    />
  );
}

function matchupTeams(
  metadata: ResultMetadata | undefined,
  rows: SectionRow[],
): TeamDisplay[] {
  const teams = metadata?.teams_context?.map((team) => ({
    id: team.team_id,
    name: team.team_name,
    teamAbbr: team.team_abbr,
  }));

  if (teams && teams.length > 0) return teams;
  return rows
    .slice(0, 2)
    .map((row, index) => teamDisplay(metadata, row, index));
}

function teamDisplay(
  metadata: ResultMetadata | undefined,
  row: SectionRow,
  index = 0,
): TeamDisplay {
  const context =
    metadata?.teams_context?.[index] ??
    (index === 0 ? metadata?.team_context : undefined) ??
    (index === 1 ? metadata?.opponent_context : undefined);

  const teamAbbr =
    context?.team_abbr ??
    textValue(row, "team_abbr") ??
    textValue(row, "team") ??
    textValue(row, "abbr");
  const name =
    context?.team_name ??
    (index === 0 ? metadataText(metadata, "team") : null) ??
    (index === 1 ? metadataText(metadata, "opponent") : null) ??
    textValue(row, "team_name") ??
    textValue(row, "team") ??
    textValue(row, "name") ??
    teamAbbr ??
    `Team ${index + 1}`;

  return {
    id: context?.team_id ?? identityId(row.team_id),
    name,
    teamAbbr,
  };
}

function modeFromRoute(route: string | null | undefined): PlayoffMode {
  if (route === "playoff_round_record") return "round_record";
  if (route === "playoff_matchup_history") return "matchup";
  return "history";
}

function seasonRange(
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
): string | null {
  const direct =
    textValue(row, "season") ??
    textValue(row, "seasons") ??
    metadataText(metadata, "season");
  if (direct) return direct;

  const start =
    textValue(row, "season_start") ?? metadataText(metadata, "start_season");
  const end =
    textValue(row, "season_end") ?? metadataText(metadata, "end_season");
  if (start && end && start !== end) return `${start} to ${end}`;
  return start ?? end;
}

function roundLabel(
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
): string | null {
  const label =
    textValue(row, "playoff_round") ??
    textValue(row, "round") ??
    textValue(row, "round_reached") ??
    textValue(row, "deepest_round") ??
    metadataText(metadata, "playoff_round") ??
    metadataText(metadata, "round");
  return cleanRoundLabel(label);
}

function roundCell(row: SectionRow): string {
  return (
    cleanRoundLabel(
      textValue(row, "round_reached") ??
        textValue(row, "deepest_round") ??
        textValue(row, "playoff_round") ??
        textValue(row, "round"),
    ) ?? ROUND_UNAVAILABLE
  );
}

function cleanRoundLabel(label: string | null): string | null {
  if (!label) return null;
  const normalized = label.trim().toLowerCase();
  if (
    normalized === "unknown" ||
    normalized === "unknown round" ||
    normalized === "unavailable" ||
    normalized === "not available" ||
    normalized === "n/a"
  ) {
    return null;
  }
  return label;
}

function playoffResultValue(row: SectionRow): string {
  const value = textValue(row, "series_result") ?? textValue(row, "result");
  if (!value) return RESULT_UNAVAILABLE;
  const normalized = value.trim().toLowerCase();
  if (
    normalized === "unknown" ||
    normalized === "unavailable" ||
    normalized === "not available" ||
    normalized === "n/a"
  ) {
    return RESULT_UNAVAILABLE;
  }
  return value;
}

function roundRecordMetricKey(rows: SectionRow[]): string | undefined {
  return ["win_pct", "wins", "series", "games_played"].find((key) =>
    rows.some((row) => hasValue(row[key])),
  );
}

function opponentValue(row: SectionRow): string {
  return (
    textValue(row, "opponent") ??
    textValue(row, "opponent_team_name") ??
    textValue(row, "opponent_team_abbr") ??
    EMPTY_CELL
  );
}

function winnerValue(row: SectionRow): string {
  return (
    textValue(row, "winner") ??
    textValue(row, "winner_team_name") ??
    textValue(row, "winner_team_abbr") ??
    EMPTY_CELL
  );
}

function hasOpponent(row: SectionRow): boolean {
  return Boolean(
    textValue(row, "opponent") ??
    textValue(row, "opponent_team_name") ??
    textValue(row, "opponent_team_abbr"),
  );
}

function hasWinner(row: SectionRow): boolean {
  return Boolean(
    textValue(row, "winner") ??
    textValue(row, "winner_team_name") ??
    textValue(row, "winner_team_abbr"),
  );
}

function gameCount(row: SectionRow): string | null {
  const games =
    numericValue(row, "games") ??
    numericValue(row, "games_played") ??
    numericValue(row, "series");
  if (games === null) return null;
  return formatValue(games, "games");
}

function rankValue(row: SectionRow, index: number): number | string {
  return typeof row.rank === "number" || typeof row.rank === "string"
    ? row.rank
    : index + 1;
}

function recordText(
  row: SectionRow | undefined,
  winsKey = "wins",
  lossesKey = "losses",
): string | null {
  const wins = numericValue(row, winsKey);
  const losses = numericValue(row, lossesKey);
  if (wins === null || losses === null) return null;
  return `${formatValue(wins, winsKey)}-${formatValue(losses, lossesKey)}`;
}

function rowKey(row: SectionRow, index: number): string {
  return [
    textValue(row, "season"),
    textValue(row, "round"),
    textValue(row, "team_name"),
    textValue(row, "winner"),
    index,
  ]
    .filter(Boolean)
    .join("-");
}

function numericValue(row: SectionRow | undefined, key: string): number | null {
  const value = row?.[key];
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
