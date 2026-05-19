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

type PlayoffMode = "history" | "round_record" | "matchup" | "appearances";

interface Props {
  data: QueryResponse;
  mode?: PlayoffMode;
  afterHero?: ReactNode;
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

export default function PlayoffHistoryResult({ data, mode, afterHero }: Props) {
  const route = data.route ?? data.result?.metadata?.route;
  const resolvedMode = mode ?? modeFromRoute(route);

  if (resolvedMode === "matchup") {
    return <PlayoffMatchupResult data={data} afterHero={afterHero} />;
  }

  if (resolvedMode === "round_record") {
    return <PlayoffRoundRecordResult data={data} afterHero={afterHero} />;
  }

  return (
    <PlayoffTeamHistoryResult
      data={data}
      variant={resolvedMode === "appearances" ? "appearances" : "history"}
      afterHero={afterHero}
    />
  );
}

function PlayoffTeamHistoryResult({
  data,
  variant = "history",
  afterHero,
}: {
  data: QueryResponse;
  variant?: "history" | "appearances";
  afterHero?: ReactNode;
}) {
  const sections = data.result?.sections ?? {};
  const summaryRows = sections.summary ?? [];
  const seasonRows = sections.by_season ?? [];
  const summary = summaryRows[0] ?? seasonRows[0];

  if (!summary) return null;

  const team = teamDisplay(data.result?.metadata, summary);
  const rows = seasonRows.length > 0 ? seasonRows : summaryRows;
  const columns =
    variant === "appearances" ? appearanceColumns(rows) : historyColumns(rows);
  const visibleDetailKeys: Record<string, Iterable<string>> = {};
  visibleDetailKeys[seasonRows.length > 0 ? "by_season" : "summary"] =
    resultTableSourceKeys(columns);

  return (
    <section className={styles.pattern} aria-label="Playoff history result">
      <ResultHero
        sentence={
          variant === "appearances"
            ? appearanceSentence(team.name, data.result?.metadata, summary)
            : historySentence(team.name, data.result?.metadata, summary)
        }
        subjectIllustration={teamIdentity(team)}
        tone="team"
        teamAccentAbbr={team.teamAbbr}
      />
      {afterHero}
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

function PlayoffRoundRecordResult({
  data,
  afterHero,
}: {
  data: QueryResponse;
  afterHero?: ReactNode;
}) {
  const rows =
    data.result?.sections?.leaderboard ??
    data.result?.sections?.summary ??
    data.result?.sections?.by_season ??
    [];

  if (rows.length === 0) return null;

  const leader = rows[0];
  const team = teamDisplay(data.result?.metadata, leader);
  const metric = roundRecordMetricKey(rows, data);
  const columns = roundRecordColumns(rows, data.result?.metadata, metric);
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
        sentence={roundRecordSentence(
          team.name,
          data.result?.metadata,
          leader,
          data,
        )}
        subjectIllustration={teamIdentity(team)}
        tone="team"
        teamAccentAbbr={team.teamAbbr}
      />
      {afterHero}
      <ResultTable
        rows={rows}
        columns={columns}
        ariaLabel="Playoff round records"
        getRowKey={rowKey}
        highlightColumnKey={metric}
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

function PlayoffMatchupResult({
  data,
  afterHero,
}: {
  data: QueryResponse;
  afterHero?: ReactNode;
}) {
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
        sentence={matchupSentence(teams, summaryRows, seriesRows)}
        subjectIllustration={<MatchupIdentity teams={teams} />}
        tone="neutral"
      />
      {afterHero}
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
  const rangePrefix = range ? `From ${range.replace(" to ", " through ")}, ` : "";
  const finalsClause =
    finals !== null && finals > 0
      ? ` They reached the Finals ${formatValue(finals, "finals")} ${
          finals === 1 ? "time" : "times"
        }${titleCount !== null ? ` and won ${titleCount} ${titleCount === 1 ? "title" : "titles"}` : ""}.`
      : titleCount !== null && titleCount > 0
        ? ` They won ${titleCount} ${titleCount === 1 ? "title" : "titles"}.`
        : "";

  return (
    <>
      {rangePrefix}the {teamName}{" "}
      {appearances !== null ? (
        <>
          made the playoffs{" "}
          <span className={styles.heroValue}>
            {formatValue(appearances, "appearances")}
          </span>{" "}
          {appearances === 1 ? "time" : "times"}
        </>
      ) : (
        "have playoff history"
      )}
      {record ? ` and went ${record}` : ""}.{finalsClause}
    </>
  );
}

function appearanceSentence(
  teamName: string,
  metadata: ResultMetadata | undefined,
  row: SectionRow,
): ReactNode {
  const appearances =
    numericValue(row, "appearances") ?? numericValue(row, "seasons_appeared");
  const round = roundLabel(metadata, row);
  const range = seasonRange(metadata, row);
  const rangePrefix = range ? `From ${range.replace(" to ", " through ")}, ` : "";
  const action = appearanceAction(round);

  return (
    <>
      {rangePrefix}the {teamName} {action}{" "}
      {appearances !== null ? (
        <>
          <span className={styles.heroValue}>
            {formatValue(appearances, "appearances")}
          </span>{" "}
          {appearances === 1 ? "time" : "times"}
        </>
      ) : (
        "in the available seasons"
      )}
      .
    </>
  );
}

function appearanceAction(round: string | null): string {
  if (!round) return "made the playoffs";
  const normalized = round.toLowerCase();
  if (normalized.includes("playoff")) return "made the playoffs";
  return `reached the ${round}`;
}

function roundRecordSentence(
  teamName: string,
  metadata: ResultMetadata | undefined,
  row: SectionRow,
  data: QueryResponse,
): ReactNode {
  const round = roundLabel(metadata, row);
  const record = recordText(row);
  const metricKey = roundRecordMetricKey([row], data);
  const context = roundRecordContext(metadata, row, data);
  const games =
    numericValue(row, "games_played") ??
    numericValue(row, "games") ??
    numericValue(row, "series");
  const winPctPhrase = hasValue(row.win_pct)
    ? `, a ${formatValue(row.win_pct, "win_pct")} win rate${
        games !== null ? "," : ""
      }`
    : "";

  if (metricKey === "win_pct" || !metricKey) {
    return (
      <>
        The {teamName} have the best{" "}
        {round ? `${round} record` : "playoff round record"}
        {context}
        {record ? `, going ${record}` : ""}
        {winPctPhrase}
        {games !== null ? ` across ${formatValue(games, "games")} games` : ""}.
      </>
    );
  }

  if (metricKey === "wins") {
    return (
      <>
        The {teamName} have the most{" "}
        {round ? `${round} wins` : "playoff round wins"}
        {context}, with{" "}
        <span className={styles.heroValue}>{formatValue(row.wins, "wins")}</span>{" "}
        wins
        {record ? ` (${record})` : ""}
        {games !== null ? ` across ${formatValue(games, "games")} games` : ""}.
      </>
    );
  }

  return (
    <>
      The {teamName} have played the most{" "}
      {round ? `${round} games` : "playoff round games"}
      {context}, with{" "}
      <span className={styles.heroValue}>{formatValue(row[metricKey], metricKey)}</span>{" "}
      games{record ? ` (${record})` : ""}.
    </>
  );
}

function matchupSentence(
  teams: TeamDisplay[],
  rows: SectionRow[],
  seriesRows: SectionRow[],
): string {
  const first = teams[0]?.name ?? "Team 1";
  const second = teams[1]?.name ?? "Team 2";
  const firstRecord = recordText(rows[0]);
  const firstWins = numericValue(rows[0], "wins");
  const firstLosses = numericValue(rows[0], "losses");
  const seriesRecord = playoffSeriesRecord(seriesRows, teams);
  const seriesClause = seriesRecord
    ? ` ${seriesRecord.sentence}.`
    : "";

  if (firstRecord && firstWins !== null && firstLosses !== null) {
    if (firstWins > firstLosses) {
      return `The ${first} lead the ${second} ${firstRecord} in playoff games.${seriesClause}`;
    }
    if (firstWins < firstLosses) {
      return `The ${second} lead the ${first} ${firstLosses}-${firstWins} in playoff games.${seriesClause}`;
    }
    return `The ${first} and ${second} are tied ${firstRecord} in playoff games.${seriesClause}`;
  }

  return `The ${first} and ${second} have playoff matchup history.${seriesClause}`;
}

function historyColumns(
  rows: SectionRow[],
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [
    textColumn("season", "Season"),
    {
      key: "round",
      sourceKeys: ["round_reached", "deepest_round", "playoff_round", "round"],
      header: "Round Reached",
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

function appearanceColumns(
  rows: SectionRow[],
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [
    textColumn("season", "Season"),
    {
      key: "record",
      sourceKeys: ["wins", "losses"],
      header: "Record",
      align: "center",
      render: (row) => recordText(row) ?? EMPTY_CELL,
    },
  ];

  if (rows.some((row) => hasValue(row.games_played))) {
    addNumericIfPresent(columns, rows, "games_played", "Games");
  } else {
    addNumericIfPresent(columns, rows, "games", "Games");
  }
  addNumericIfPresent(columns, rows, "win_pct", "Win Pct");

  return columns;
}

function roundRecordColumns(
  rows: SectionRow[],
  metadata: ResultMetadata | undefined,
  metric: string | undefined,
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

  if (metric === "wins") {
    addNumericIfPresent(columns, rows, "wins", "Wins");
  }
  if (rows.some((row) => hasValue(row.games_played))) {
    addNumericIfPresent(columns, rows, "games_played", "Games");
  } else {
    addNumericIfPresent(columns, rows, "games", "Games");
  }
  addNumericIfPresent(columns, rows, "win_pct", "Win Pct");
  addIfPresent(columns, rows, "seasons", "Seasons");
  addNumericIfPresent(columns, rows, "series", "Series");

  return columns;
}

function matchupColumns(
  rows: SectionRow[],
  teams: TeamDisplay[],
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [];

  columns.push({
    ...textColumn("season", "Season"),
    minWidth: "4.25rem",
    width: "4.25rem",
    mobilePriority: "primary",
  });

  columns.push({
    key: "round",
    sourceKeys: ["round", "playoff_round", "round_reached", "deepest_round"],
    header: "Round",
    minWidth: "4.75rem",
    width: "4.75rem",
    nowrap: false,
    mobilePriority: "primary",
    render: (row) => roundCell(row),
  });

  columns.push({
    key: "winner",
    sourceKeys: ["winner", "winner_team_name", "winner_team_abbr"],
    header: "Winner",
    minWidth: "4.75rem",
    width: "4.75rem",
    nowrap: false,
    mobilePriority: "primary",
    render: (row) => winnerValue(row, teams),
  });

  columns.push({
    key: "result",
    sourceKeys: ["series_result", "result"],
    header: "Series Result",
    minWidth: "5.75rem",
    width: "5.75rem",
    nowrap: false,
    mobilePriority: "primary",
    render: (row) => playoffResultValue(row, teams),
  });

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
      mobilePriority: "secondary",
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

  if (rows.some((row) => hasValue(row.games)) || teams.length >= 2) {
    columns.push({
      key: "games",
      sourceKeys: ["games"],
      header: "Games",
      numeric: true,
      mobilePriority: "secondary",
      render: (row) => playoffSeriesGames(row, teams) ?? EMPTY_CELL,
    });
  }
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
      const labels = playoffDetailToggleLabels(key, titles[key]);
      return (
        <RawDetailToggle
          key={key}
          title={titles[key] ?? `${formatColHeader(key)} Detail`}
          rows={sections[key]}
          highlight={key !== "summary"}
          collapsedLabel={
            isAdditionalColumns ? "Show additional columns" : labels.collapsed
          }
          expandedLabel={
            isAdditionalColumns ? "Hide additional columns" : labels.expanded
          }
        />
      );
    });
}

function playoffDetailToggleLabels(
  key: string,
  title: string | undefined,
): { collapsed: string; expanded: string } {
  if (title === "Postseason Summary Detail" || key === "summary") {
    return {
      collapsed: "Show postseason summary",
      expanded: "Hide postseason summary",
    };
  }
  return {
    collapsed: "Show additional columns",
    expanded: "Hide additional columns",
  };
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
  if (route === "playoff_appearances") return "appearances";
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

function playoffResultValue(row: SectionRow, teams?: TeamDisplay[]): string {
  const value = textValue(row, "series_result") ?? textValue(row, "result");
  if (value) {
    const normalized = value.trim().toLowerCase();
    if (
      normalized !== "unknown" &&
      normalized !== "unavailable" &&
      normalized !== "not available" &&
      normalized !== "n/a"
    ) {
      return value;
    }
  }
  const derived = teams ? playoffSeriesResult(row, teams) : null;
  return derived ?? RESULT_UNAVAILABLE;
}

function roundRecordMetricKey(
  rows: SectionRow[],
  data?: QueryResponse,
): string | undefined {
  const query =
    `${data?.query ?? ""} ${data?.result?.metadata?.query_text ?? ""}`.toLowerCase();
  if (/\b(most wins|wins|won|winningest)\b/.test(query)) {
    return rows.some((row) => hasValue(row.wins)) ? "wins" : undefined;
  }
  if (/\b(most games|games played)\b/.test(query)) {
    if (rows.some((row) => hasValue(row.games_played))) return "games_played";
    if (rows.some((row) => hasValue(row.games))) return "games";
  }
  if (
    /\b(best record|win pct|winning percentage|winning pct|record)\b/.test(
      query,
    ) &&
    rows.some((row) => hasValue(row.win_pct))
  ) {
    return "win_pct";
  }
  return ["win_pct", "wins", "games_played", "games", "series"].find((key) =>
    rows.some((row) => hasValue(row[key])),
  );
}

function roundRecordContext(
  metadata: ResultMetadata | undefined,
  row: SectionRow,
  data: QueryResponse,
): string {
  const query = `${data.query ?? ""} ${metadata?.query_text ?? ""}`;
  const since = query.match(/\bsince\s+(\d{4})\b/i);
  if (since) return ` since ${since[1]}`;

  const range = seasonRange(metadata, row);
  return range ? ` from ${range}` : "";
}

function opponentValue(row: SectionRow): string {
  return (
    textValue(row, "opponent") ??
    textValue(row, "opponent_team_name") ??
    textValue(row, "opponent_team_abbr") ??
    EMPTY_CELL
  );
}

function winnerValue(row: SectionRow, teams?: TeamDisplay[]): string {
  const explicit =
    textValue(row, "winner") ??
    textValue(row, "winner_team_name") ??
    textValue(row, "winner_team_abbr");
  if (explicit) return explicit;
  const derived = teams ? playoffSeriesWinner(row, teams) : null;
  return derived?.name ?? EMPTY_CELL;
}

function playoffSeriesWinner(
  row: SectionRow,
  teams: TeamDisplay[],
): { team: TeamDisplay; wins: number; losses: number; name: string } | null {
  const records = teams
    .map((team) => {
      const prefix = team.teamAbbr;
      if (!prefix) return null;
      const wins = numericValue(row, `${prefix}_wins`);
      const losses = numericValue(row, `${prefix}_losses`);
      if (wins === null || losses === null) return null;
      return { team, wins, losses, name: team.name };
    })
    .filter(
      (
        record,
      ): record is {
        team: TeamDisplay;
        wins: number;
        losses: number;
        name: string;
      } => record !== null,
    );

  if (records.length < 2) return null;
  const sorted = [...records].sort((a, b) => b.wins - a.wins);
  if (Math.abs(sorted[0].wins - sorted[1].wins) < 1e-9) return null;
  return sorted[0];
}

function playoffSeriesResult(
  row: SectionRow,
  teams: TeamDisplay[],
): string | null {
  const winner = playoffSeriesWinner(row, teams);
  if (!winner) return null;
  return `${winner.name} won ${formatValue(winner.wins, "wins")}-${formatValue(
    winner.losses,
    "losses",
  )}`;
}

function playoffSeriesGames(
  row: SectionRow,
  teams: TeamDisplay[],
): string | null {
  if (hasValue(row.games)) return formatValue(row.games, "games");
  const winner = playoffSeriesWinner(row, teams);
  if (!winner) return null;
  return formatValue(winner.wins + winner.losses, "games");
}

function playoffSeriesRecord(
  rows: SectionRow[],
  teams: TeamDisplay[],
): { sentence: string } | null {
  if (rows.length === 0 || teams.length < 2) return null;
  const [first, second] = teams;
  if (!first.teamAbbr || !second.teamAbbr) return null;

  let firstSeriesWins = 0;
  let secondSeriesWins = 0;
  for (const row of rows) {
    const firstWins = numericValue(row, `${first.teamAbbr}_wins`);
    const secondWins = numericValue(row, `${second.teamAbbr}_wins`);
    if (firstWins === null || secondWins === null) continue;
    if (firstWins > secondWins) firstSeriesWins += 1;
    if (secondWins > firstWins) secondSeriesWins += 1;
  }

  if (firstSeriesWins === 0 && secondSeriesWins === 0) return null;
  const record = `${firstSeriesWins}-${secondSeriesWins}`;
  if (firstSeriesWins > secondSeriesWins) {
    return {
      sentence: `The ${first.name} lead ${record} in playoff series`,
    };
  }
  if (firstSeriesWins < secondSeriesWins) {
    return {
      sentence: `The ${second.name} lead ${secondSeriesWins}-${firstSeriesWins} in playoff series`,
    };
  }
  return { sentence: `Their playoff series record is tied ${record}` };
}

function hasOpponent(row: SectionRow): boolean {
  return Boolean(
    textValue(row, "opponent") ??
    textValue(row, "opponent_team_name") ??
    textValue(row, "opponent_team_abbr"),
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
