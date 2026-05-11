import { useState, type ReactNode } from "react";
import type {
  QueryResponse,
  ResultMetadata,
  SectionRow,
} from "../../../api/types";
import { Badge, Button, type StatSemantic } from "../../../design-system";
import {
  formatColHeader,
  formatLongDateRange,
  formatProseValue,
  formatValue,
} from "../../tableFormatting";
import EntityIdentity from "../primitives/EntityIdentity";
import RawDetailToggle from "../primitives/RawDetailToggle";
import ResultHero from "../primitives/ResultHero";
import ResultTable, { type ResultTableColumn } from "../primitives/ResultTable";
import {
  resultTableSourceKeys,
  rowsHaveAdditionalDetailFields,
} from "../primitives/detailTables";
import styles from "./ComparisonResult.module.css";

type SubjectKind = "player" | "team";

interface Props {
  data: QueryResponse;
  subject?: SubjectKind;
  headToHead?: boolean;
}

type EntityDisplay = {
  id: number | string | null;
  kind: SubjectKind;
  name: string;
  teamAbbr: string | null;
};

type StatChip = {
  label: string;
  value: ReactNode;
  context?: string | null;
  semantic?: StatSemantic;
};

type LeaderInfo =
  | { type: "leader"; column: string; delta: number; metric: string }
  | { type: "tie" };

type MetricDirection = "higher" | "lower" | "neutral";

const METRIC_DIRECTIONS: Record<string, MetricDirection> = {
  ast_avg: "higher",
  ast_pct_avg: "higher",
  ast_sum: "higher",
  blk_avg: "higher",
  efg_pct_avg: "higher",
  fg3m_avg: "higher",
  fg3_pct_avg: "higher",
  ft_pct_avg: "higher",
  games: "neutral",
  losses: "lower",
  minutes_avg: "neutral",
  plus_minus_avg: "higher",
  pts_avg: "higher",
  pts_sum: "higher",
  reb_avg: "higher",
  reb_pct_avg: "higher",
  reb_sum: "higher",
  stl_avg: "higher",
  tov_avg: "lower",
  ts_pct_avg: "higher",
  usg_pct_avg: "neutral",
  win_pct: "higher",
  wins: "higher",
};

const PRIMARY_COMPARISON_METRICS = [
  "games",
  "record",
  "pts_avg",
  "reb_avg",
  "ast_avg",
  "minutes_avg",
  "fg_pct_avg",
  "fg3_pct_avg",
  "ft_pct_avg",
  "stl_avg",
  "blk_avg",
  "tov_avg",
  "plus_minus_avg",
  "ts_pct_avg",
  "efg_pct_avg",
];

const PRIMARY_METRIC_LIMIT = 12;

const METRIC_LABEL_OVERRIDES: Record<string, string> = {
  ast_avg: "AST Avg",
  ast_pct_avg: "AST% Avg",
  ast_sum: "AST Total",
  blk_avg: "BLK Avg",
  efg_pct_avg: "eFG% Avg",
  fg_pct_avg: "FG% Avg",
  fg3m_avg: "3PM Avg",
  fg3_pct_avg: "3P% Avg",
  ft_pct_avg: "FT% Avg",
  losses: "Losses",
  minutes_avg: "MIN Avg",
  plus_minus_avg: "+/- Avg",
  pts_avg: "PTS Avg",
  pts_sum: "PTS Total",
  reb_avg: "REB Avg",
  reb_pct_avg: "REB% Avg",
  reb_sum: "REB Total",
  record: "Record",
  stl_avg: "STL Avg",
  tov_avg: "TOV Avg",
  ts_pct_avg: "TS% Avg",
  usg_pct_avg: "USG% Avg",
  win_pct: "Win Pct",
  wins: "Wins",
};

const EDGE_LABEL_OVERRIDES: Record<string, string> = {
  ast_avg: "AST",
  ast_sum: "AST",
  blk_avg: "BLK",
  efg_pct_avg: "eFG%",
  fg_pct_avg: "FG%",
  fg3m_avg: "3PM",
  fg3_pct_avg: "3P%",
  ft_pct_avg: "FT%",
  games: "games",
  losses: "losses",
  minutes_avg: "MIN",
  plus_minus_avg: "+/-",
  pts_avg: "PTS",
  pts_sum: "PTS",
  reb_avg: "REB",
  reb_sum: "REB",
  stl_avg: "STL",
  tov_avg: "TOV",
  ts_pct_avg: "TS%",
  win_pct: "win pct",
  wins: "Wins",
};

const STAT_CANDIDATES: Array<{
  key: string;
  label: string;
  semantic?: StatChip["semantic"];
}> = [
  { key: "games", label: "Games" },
  { key: "pts_avg", label: "PTS", semantic: "accent" },
  { key: "reb_avg", label: "REB" },
  { key: "ast_avg", label: "AST" },
  { key: "minutes_avg", label: "MIN" },
  { key: "fg3m_avg", label: "3PM" },
  { key: "plus_minus_avg", label: "+/-" },
  { key: "win_pct", label: "Win Pct" },
  { key: "ts_pct_avg", label: "TS%" },
  { key: "efg_pct_avg", label: "eFG%" },
];

export default function ComparisonResult({ data, subject, headToHead }: Props) {
  const sections = data.result?.sections ?? {};
  const summary = sections.summary ?? [];
  const comparison = comparisonDisplayRows(summary, sections.comparison ?? []);
  const kind = subject ?? subjectKind(data);
  const isHeadToHead = headToHead ?? isHeadToHeadResult(data);
  const entities = summary.map((row, index) =>
    entityDisplay(kind, data.result?.metadata, row, index),
  );
  const primaryComparison = primaryMetricRows(comparison);
  const secondaryComparison = comparison.filter(
    (row) => !primaryComparison.includes(row),
  );
  const [showMoreMetrics, setShowMoreMetrics] = useState(false);
  const visibleComparison =
    showMoreMetrics || secondaryComparison.length === 0
      ? [...primaryComparison, ...secondaryComparison]
      : primaryComparison;
  const comparisonColumns = metricColumns(visibleComparison, entities);
  const teamAccentAbbr =
    kind === "team" && entities.length === 1 ? entities[0]?.teamAbbr : null;

  if (summary.length === 0 && comparison.length === 0) return null;

  return (
    <section className={styles.pattern} aria-label="Comparison result">
      <ResultHero
        sentence={heroSentence(data, entities, comparison, isHeadToHead)}
        subjectIllustration={<MatchupIdentity entities={entities} />}
        tone={
          kind === "team" ? (teamAccentAbbr ? "team" : "neutral") : "accent"
        }
        teamAccentAbbr={teamAccentAbbr}
      />
      {summary.length > 0 && (
        <div
          className={styles.subjectGrid}
          aria-label={subjectGridLabel(kind, isHeadToHead)}
        >
          {summary.map((row, index) => (
            <SubjectPanel
              entity={entities[index]}
              key={subjectKey(entities[index], index)}
              row={row}
            />
          ))}
        </div>
      )}
      {comparison.length > 0 && (
        <>
          <ResultTable
            rows={visibleComparison}
            columns={comparisonColumns}
            ariaLabel="Comparison metrics"
            getRowKey={metricRowKey}
          />
          {secondaryComparison.length > 0 && (
            <Button
              type="button"
              className={styles.showMoreButton}
              variant="secondary"
              size="sm"
              onClick={() => setShowMoreMetrics((current) => !current)}
            >
              {showMoreMetrics ? "Show fewer metrics" : "Show more metrics"}
            </Button>
          )}
        </>
      )}
      {detailToggles(sections, kind, isHeadToHead, {
        summary: subjectPanelSourceKeys(summary, kind),
        comparison: resultTableSourceKeys(comparisonColumns),
      })}
    </section>
  );
}

function SubjectPanel({
  entity,
  row,
}: {
  entity: EntityDisplay;
  row: SectionRow;
}) {
  const stats = subjectStats(row);

  return (
    <article className={styles.subjectCard}>
      <div className={styles.subjectHeader}>
        {entityIdentity(entity)}
      </div>
      {stats.length > 0 && (
        <dl className={styles.statGrid} aria-label={`${entity.name} stats`}>
          {stats.map((stat) => (
            <div
              className={[
                styles.statChip,
                stat.semantic ? styles[`stat-${stat.semantic}`] : "",
              ].join(" ")}
              key={stat.label}
            >
              <dt>{stat.label}</dt>
              <dd>{stat.value}</dd>
              {stat.context && <span>{stat.context}</span>}
            </div>
          ))}
        </dl>
      )}
    </article>
  );
}

function MatchupIdentity({ entities }: { entities: EntityDisplay[] }) {
  if (entities.length === 0) return null;

  return (
    <span className={styles.matchupIdentity}>
      {entityIdentity(entities[0])}
      {entities[1] && (
        <Badge variant="neutral" size="sm" uppercase>
          vs
        </Badge>
      )}
      {entities[1] && entityIdentity(entities[1])}
    </span>
  );
}

function heroSentence(
  data: QueryResponse,
  entities: EntityDisplay[],
  comparison: SectionRow[],
  headToHead: boolean,
): string {
  const title = comparisonTitle(entities);
  const first = entities[0]?.name ?? "Subject 1";
  const second = entities[1]?.name ?? "Subject 2";
  const summary = data.result?.sections?.summary ?? [];

  const recentSentence = recentFormSentence(data, entities, summary);
  if (recentSentence && !headToHead) return recentSentence;

  if (headToHead && summary.length >= 2) {
    const firstWins = numericValue(summary[0], "wins");
    const firstLosses = numericValue(summary[0], "losses");
    const secondRecord = recordText(summary[1]);
    const firstRecord = recordText(summary[0]);

    if (firstWins !== null && firstLosses !== null && firstRecord) {
      if (firstWins > firstLosses) {
        return `${first} ${leadVerb(entities[0])} ${second} ${firstRecord} in this head-to-head sample.`;
      }
      if (firstWins < firstLosses && secondRecord) {
        return `${second} ${leadVerb(entities[1])} ${first} ${secondRecord} in this head-to-head sample.`;
      }
      return `${first} and ${second} are tied ${firstRecord} in this head-to-head sample.`;
    }
  }

  const winsSentence = comparisonWinsSentence(data, entities, summary);
  if (winsSentence) return winsSentence;

  const edge = comparison
    .map((row) => {
      const columns = comparisonValueColumns(row);
      const leader = leaderInfo(row, columns);
      return leader?.type === "leader"
        ? edgeSentence(data, entities, leader, columns)
        : null;
    })
    .find((value): value is string => Boolean(value));

  if (edge) return edge;

  const context = contextLabel(data.result?.metadata);
  return `${title}${context ? ` for ${context}` : ""}.`;
}

function comparisonWinsSentence(
  data: QueryResponse,
  entities: EntityDisplay[],
  summary: SectionRow[],
): string | null {
  if (entities.length < 2 || summary.length < 2) return null;

  const firstWins = numericValue(summary[0], "wins");
  const secondWins = numericValue(summary[1], "wins");
  if (firstWins === null || secondWins === null) return null;

  const context = comparisonContextPhrase(data.result?.metadata, data.query);
  const [first, second] = entities;

  if (Math.abs(firstWins - secondWins) < 1e-9) {
    return withComparisonContext(
      `${sentenceSubject(first)} and ${sentenceObject(second)} each have ${formatProseValue(
        firstWins,
        "wins",
      )} wins`,
      context,
    );
  }

  const leader = firstWins > secondWins ? first : second;
  const trailer = firstWins > secondWins ? second : first;
  const leaderWins = Math.max(firstWins, secondWins);
  const trailerWins = Math.min(firstWins, secondWins);

  return withComparisonContext(
    `${sentenceSubject(leader)} ${hasVerb(leader)} ${formatProseValue(
      leaderWins,
      "wins",
    )} wins to ${possessiveSubject(trailer)} ${formatProseValue(
      trailerWins,
      "wins",
    )}`,
    context,
  );
}

function recentFormSentence(
  data: QueryResponse,
  entities: EntityDisplay[],
  summary: SectionRow[],
): string | null {
  if (entities.length < 2 || summary.length < 2) return null;
  if (!isRecentFormQuery(data)) return null;

  const firstStats = pointsReboundsAssists(summary[0]);
  const secondStats = pointsReboundsAssists(summary[1]);
  if (!firstStats || !secondStats) return null;

  const context = comparisonContextPhrase(data.result?.metadata, data.query);
  const prefix = context?.startsWith("over ")
    ? `${capitalize(context)}, `
    : context
      ? `In ${context.replace(/^in\s+/i, "")}, `
      : "";

  return `${prefix}${entities[0].name} has averaged ${firstStats}, while ${entities[1].name} has averaged ${secondStats}.`;
}

function pointsReboundsAssists(row: SectionRow): string | null {
  const pts = numericValue(row, "pts_avg");
  const reb = numericValue(row, "reb_avg");
  const ast = numericValue(row, "ast_avg");
  if (pts === null && reb === null && ast === null) return null;
  return [
    pts !== null ? `${formatProseValue(pts, "pts_avg")} points` : null,
    reb !== null ? `${formatProseValue(reb, "reb_avg")} rebounds` : null,
    ast !== null ? `${formatProseValue(ast, "ast_avg")} assists` : null,
  ]
    .filter(Boolean)
    .join(", ")
    .replace(/, ([^,]*)$/, " and $1");
}

function isRecentFormQuery(data: QueryResponse): boolean {
  const query = `${data.query ?? ""} ${data.result?.metadata?.query_text ?? ""}`;
  if (/\b(recent form|last\s+\d+|past\s+\d+)\b/i.test(query)) return true;
  return lastNWindow(data.query, data.result?.metadata) !== null;
}

function edgeSentence(
  data: QueryResponse,
  entities: EntityDisplay[],
  leader: Extract<LeaderInfo, { type: "leader" }>,
  columns: string[],
): string {
  const otherColumn = columns.find((column) => column !== leader.column);
  const subject = sentenceSubject(entityFromColumn(leader.column, entities));
  const other = otherColumn
    ? sentenceObject(entityFromColumn(otherColumn, entities))
    : "the field";
  const delta = formatProseValue(leader.delta, leader.metric);
  const metric = proseMetricLabel(leader.metric);
  const context = comparisonContextPhrase(data.result?.metadata, data.query);
  const direction = metricDirection(leader.metric);
  const base =
    direction === "lower"
      ? `${subject} has ${delta} fewer ${metric} than ${other}`
      : direction === "neutral"
        ? `${subject} differs from ${other} by ${delta} ${metric}`
        : `${subject} leads ${other} by ${delta} ${metric}`;
  return withComparisonContext(base, context);
}

function withComparisonContext(
  sentence: string,
  context: string | null,
): string {
  if (!context) return `${sentence}.`;
  if (context.startsWith("over ")) {
    return `${capitalize(context)}, ${sentence}.`;
  }
  return `${sentence} ${context}.`;
}

function comparisonContextPhrase(
  metadata: ResultMetadata | undefined,
  query: string,
): string | null {
  const lastN = lastNWindow(query, metadata);
  if (lastN) return `over their last ${lastN} games`;

  const season = seasonLabel(metadata);
  const seasonType = metadataText(metadata, "season_type");
  if (season) {
    return `in the ${season}${seasonType ? ` ${seasonType.toLowerCase()}` : ""}`;
  }

  const date = dateLabel(metadata);
  return date ? `from ${date}` : null;
}

function lastNWindow(
  query: string,
  metadata: ResultMetadata | undefined,
): number | null {
  const windowSize = metadata?.window_size;
  if (typeof windowSize === "number" && Number.isFinite(windowSize)) {
    return windowSize;
  }
  const filterWindow = metadata?.applied_filters?.find(
    (filter) =>
      filter.kind === "window" ||
      filter.label.trim().toLowerCase() === "last n games",
  );
  if (filterWindow) {
    const value = Number(filterWindow.value);
    if (Number.isFinite(value)) return value;
  }
  const queryText = `${query} ${metadata?.query_text ?? ""}`;
  const match = queryText.match(/\blast\s+(\d+)\s*(?:games?|gms?)?\b/i);
  return match ? Number(match[1]) : null;
}

function entityFromColumn(
  column: string,
  entities: EntityDisplay[],
): EntityDisplay | string {
  return (
    entities.find(
      (entity) =>
        entity.name === column ||
        entity.teamAbbr === column ||
        column.includes(entity.name),
    ) ?? column
  );
}

function sentenceSubject(entity: EntityDisplay | string): string {
  if (typeof entity === "string") return entity;
  if (entity.kind === "team" && !/^the\b/i.test(entity.name)) {
    return `The ${entity.name}`;
  }
  return entity.name;
}

function sentenceObject(entity: EntityDisplay | string): string {
  if (typeof entity === "string") return entity;
  if (entity.kind === "team" && !/^the\b/i.test(entity.name)) {
    return `the ${entity.name}`;
  }
  return entity.name;
}

function possessiveSubject(entity: EntityDisplay): string {
  const base =
    entity.kind === "team" && !/^the\b/i.test(entity.name)
      ? `the ${entity.name}`
      : entity.name;
  return base.endsWith("s") ? `${base}'` : `${base}'s`;
}

function leadVerb(entity: EntityDisplay | undefined): "lead" | "leads" {
  return entity?.kind === "team" ? "lead" : "leads";
}

function hasVerb(entity: EntityDisplay): "has" | "have" {
  return entity.kind === "team" ? "have" : "has";
}

function proseMetricLabel(metric: string): string {
  const labels: Record<string, string> = {
    ast_avg: "assists per game",
    ast_sum: "assists",
    blk_avg: "blocks per game",
    efg_pct_avg: "effective field-goal percentage",
    fg3m_avg: "threes per game",
    losses: "losses",
    minutes_avg: "minutes per game",
    plus_minus_avg: "plus-minus",
    pts_avg: "points per game",
    pts_sum: "points",
    reb_avg: "rebounds per game",
    reb_sum: "rebounds",
    record: "record",
    stl_avg: "steals per game",
    tov_avg: "turnovers per game",
    ts_pct_avg: "true-shooting percentage",
    win_pct: "win percentage",
    wins: "wins",
  };
  return labels[metric] ?? edgeMetricLabel(metric).toLowerCase();
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function metricColumns(
  rows: SectionRow[],
  entities: EntityDisplay[],
): Array<ResultTableColumn<SectionRow>> {
  const valueColumns = allMetricValueColumns(rows);
  const columns: Array<ResultTableColumn<SectionRow>> = [
    {
      key: "metric",
      sourceKeys: ["metric"],
      header: "Metric",
      render: (row) => metricLabel(metricKey(row)),
    },
  ];

  for (const key of valueColumns) {
    columns.push({
      key,
      sourceKeys: [key],
      header: key,
      numeric: rows.some((row) => numericValue(row, key) !== null),
      render: (row) => metricValue(row, key),
    });
  }

  columns.push({
    key: "edge",
    header: "Edge / Difference",
    render: (row) => {
      const explicit = textValue(row, "__edge_label");
      if (explicit) return explicit;
      const leader = leaderInfo(row, valueColumns);
      if (leader?.type === "tie") return "Tie";
      return leader?.type === "leader" ? edgeLabel(leader, entities) : "-";
    },
  });

  return columns;
}

function comparisonDisplayRows(
  summary: SectionRow[],
  comparison: SectionRow[],
): SectionRow[] {
  const rows = [...comparison];
  const record = comparisonRecordRow(summary);
  if (record && !rows.some((row) => metricKey(row) === "record")) {
    const insertAt = rows.findIndex((row) => metricKey(row) === "wins");
    rows.splice(insertAt >= 0 ? insertAt : 1, 0, record);
  }
  return rows;
}

function comparisonRecordRow(summary: SectionRow[]): SectionRow | null {
  if (summary.length < 2) return null;
  const firstName = textValue(summary[0], "player_name") ?? textValue(summary[0], "team_name");
  const secondName = textValue(summary[1], "player_name") ?? textValue(summary[1], "team_name");
  if (!firstName || !secondName) return null;
  const firstRecord = recordText(summary[0]);
  const secondRecord = recordText(summary[1]);
  if (!firstRecord || !secondRecord) return null;

  return {
    metric: "record",
    [firstName]: firstRecord,
    [secondName]: secondRecord,
    __edge_label: recordEdgeLabel(summary, firstName, secondName),
  };
}

function recordEdgeLabel(
  summary: SectionRow[],
  firstName: string,
  secondName: string,
): string {
  const firstWins = numericValue(summary[0], "wins");
  const secondWins = numericValue(summary[1], "wins");
  if (firstWins === null || secondWins === null) return "-";
  if (Math.abs(firstWins - secondWins) < 1e-9) return "Tie";
  const leader = firstWins > secondWins ? firstName : secondName;
  return `${leader} +${formatValue(Math.abs(firstWins - secondWins), "wins")} wins`;
}

function primaryMetricRows(rows: SectionRow[]): SectionRow[] {
  const primary: SectionRow[] = [];
  for (const metric of PRIMARY_COMPARISON_METRICS) {
    const row = rows.find((candidate) => metricKey(candidate) === metric);
    if (row) primary.push(row);
    if (primary.length >= PRIMARY_METRIC_LIMIT) break;
  }
  if (primary.length === 0) return rows.slice(0, PRIMARY_METRIC_LIMIT);
  return primary;
}

function detailToggles(
  sections: Record<string, SectionRow[]>,
  kind: SubjectKind,
  headToHead: boolean,
  visibleKeysBySection: Record<string, Iterable<string>>,
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
          title={detailTitle(key, kind, headToHead)}
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

function detailTitle(
  key: string,
  kind: SubjectKind,
  headToHead: boolean,
): string {
  if (key === "summary") {
    if (headToHead) return "Participant Detail";
    return kind === "player" ? "Player Summary Detail" : "Team Summary Detail";
  }
  if (key === "comparison") {
    return headToHead ? "Metric Detail" : "Full Metric Detail";
  }
  if (key === "finder") return "Matching Games";
  return `${formatColHeader(key)} Detail`;
}

function subjectStats(row: SectionRow): StatChip[] {
  const stats: StatChip[] = [];
  const record = recordStat(row);
  if (record) stats.push(record);

  for (const candidate of STAT_CANDIDATES) {
    if (candidate.key === "games" && record) continue;
    const value = numericValue(row, candidate.key);
    if (value === null) continue;
    stats.push({
      label: candidate.label,
      value: signedValue(value, candidate.key),
      semantic:
        candidate.key === "plus_minus_avg"
          ? value >= 0
            ? "success"
            : "danger"
          : candidate.semantic,
    });
  }

  return stats.slice(0, 5);
}

function subjectPanelSourceKeys(
  rows: SectionRow[],
  kind: SubjectKind,
): Set<string> {
  const keys = new Set<string>(
    kind === "player"
      ? ["player_name", "player", "player_id", "team_abbr"]
      : ["team_name", "team", "team_abbr", "team_id"],
  );

  for (const row of rows) {
    for (const key of visibleSubjectStatKeys(row)) {
      keys.add(key);
    }
  }
  return keys;
}

function visibleSubjectStatKeys(row: SectionRow): string[] {
  const keys: string[] = [];
  let visibleCount = 0;
  const record = recordStat(row);
  if (record) {
    visibleCount += 1;
    if (numericValue(row, "wins") !== null) keys.push("wins");
    if (numericValue(row, "losses") !== null) keys.push("losses");
    if (numericValue(row, "games") !== null) keys.push("games");
    if (numericValue(row, "win_pct") !== null) keys.push("win_pct");
  }

  for (const candidate of STAT_CANDIDATES) {
    if (candidate.key === "games" && record) continue;
    if (numericValue(row, candidate.key) === null) continue;
    if (visibleCount >= 5) break;
    keys.push(candidate.key);
    visibleCount += 1;
  }

  return keys;
}

function recordStat(row: SectionRow): StatChip | null {
  const wins = numericValue(row, "wins");
  const losses = numericValue(row, "losses");
  const games = numericValue(row, "games");
  const winPct = numericValue(row, "win_pct");

  if (wins !== null && losses !== null) {
    return {
      label: "Record",
      value: `${formatValue(wins, "wins")}-${formatValue(losses, "losses")}`,
      context: [
        games !== null ? `${formatValue(games, "games")} games` : null,
        winPct !== null ? `${formatValue(winPct, "win_pct")} win rate` : null,
      ]
        .filter(Boolean)
        .join(" / "),
      semantic:
        wins > losses ? "success" : wins < losses ? "danger" : "neutral",
    };
  }

  if (games !== null) {
    return {
      label: "Sample",
      value: formatValue(games, "games"),
      context: games === 1 ? "game" : "games",
      semantic: "accent",
    };
  }

  return null;
}

function entityIdentity(entity: EntityDisplay): ReactNode {
  return entity.kind === "player" ? (
    <EntityIdentity
      kind="player"
      playerId={entity.id}
      playerName={entity.name}
      teamAbbr={entity.teamAbbr}
      size="md"
    />
  ) : (
    <EntityIdentity
      kind="team"
      teamId={entity.id}
      teamAbbr={entity.teamAbbr}
      teamName={entity.name}
      size="md"
    />
  );
}

function entityDisplay(
  kind: SubjectKind,
  metadata: ResultMetadata | undefined,
  row: SectionRow,
  index: number,
): EntityDisplay {
  if (kind === "player") {
    const rowName =
      textValue(row, "player_name") ?? textValue(row, "player") ?? null;
    const context =
      metadata?.players_context?.find(
        (candidate) => candidate.player_name === rowName,
      ) ??
      metadata?.players_context?.[index] ??
      null;

    return {
      id: context?.player_id ?? identityId(row.player_id),
      kind,
      name: context?.player_name ?? rowName ?? `Player ${index + 1}`,
      teamAbbr: textValue(row, "team_abbr") ?? null,
    };
  }

  const rowName =
    textValue(row, "team_name") ??
    textValue(row, "team") ??
    textValue(row, "team_abbr");
  const context =
    metadata?.teams_context?.find(
      (candidate) =>
        candidate.team_name === rowName || candidate.team_abbr === rowName,
    ) ??
    metadata?.teams_context?.[index] ??
    null;

  return {
    id: context?.team_id ?? identityId(row.team_id),
    kind,
    name: context?.team_name ?? rowName ?? `Team ${index + 1}`,
    teamAbbr:
      context?.team_abbr ??
      textValue(row, "team_abbr") ??
      textValue(row, "team"),
  };
}

function comparisonTitle(entities: EntityDisplay[]): string {
  if (entities.length >= 2) return `${entities[0].name} vs ${entities[1].name}`;
  return entities[0]?.name ?? "Comparison";
}

function contextLabel(metadata: ResultMetadata | undefined): string | null {
  return [
    seasonLabel(metadata),
    metadataText(metadata, "season_type"),
    dateLabel(metadata),
  ]
    .filter(Boolean)
    .join(" ");
}

function subjectGridLabel(kind: SubjectKind, headToHead: boolean): string {
  if (headToHead) return "Head-to-head participants";
  return kind === "player" ? "Compared players" : "Compared teams";
}

function subjectKind(data: QueryResponse): SubjectKind {
  const route = data.route ?? data.result?.metadata?.route;
  if (route === "player_compare") return "player";
  return "team";
}

function isHeadToHeadResult(data: QueryResponse): boolean {
  const route = data.route ?? data.result?.metadata?.route;
  return (
    route === "team_matchup_record" ||
    data.result?.metadata?.head_to_head_used === true
  );
}

function metricRowKey(row: SectionRow, index: number): string {
  return `${metricKey(row)}-${index}`;
}

function metricKey(row: SectionRow): string {
  return textValue(row, "metric") ?? "metric";
}

function metricLabel(metric: string): string {
  return METRIC_LABEL_OVERRIDES[metric] ?? formatColHeader(metric);
}

function edgeMetricLabel(metric: string): string {
  return (
    EDGE_LABEL_OVERRIDES[metric] ??
    metricLabel(metric)
      .replace(/\s+Avg$/i, "")
      .replace(/\s+Total$/i, "")
  );
}

function allMetricValueColumns(rows: SectionRow[]): string[] {
  const keys: string[] = [];
  for (const row of rows) {
    for (const key of comparisonValueColumns(row)) {
      if (!keys.includes(key)) keys.push(key);
    }
  }
  return keys;
}

function comparisonValueColumns(row: SectionRow): string[] {
  return Object.keys(row).filter(
    (key) => key !== "metric" && !key.startsWith("__"),
  );
}

function leaderInfo(row: SectionRow, columns: string[]): LeaderInfo | null {
  const metric = metricKey(row);
  const values = columns
    .map((column) => ({ column, value: numericValue(row, column) }))
    .filter(
      (item): item is { column: string; value: number } => item.value !== null,
    );

  if (values.length < 2) return null;

  const sorted = [...values].sort((a, b) =>
    metricDirection(metric) === "lower"
      ? a.value - b.value
      : b.value - a.value,
  );
  const [first, second] = sorted;
  if (Math.abs(first.value - second.value) < 1e-9) return { type: "tie" };

  return {
    type: "leader",
    column: first.column,
    delta: Math.abs(first.value - second.value),
    metric,
  };
}

function edgeLabel(
  leader: Extract<LeaderInfo, { type: "leader" }>,
  entities: EntityDisplay[],
): string {
  const subject = entityLabel(entityFromColumn(leader.column, entities));
  const delta = formatEdgeDelta(leader.delta, leader.metric);
  const metric = edgeMetricLabel(leader.metric);
  const direction = metricDirection(leader.metric);
  if (direction === "lower") {
    return `${subject} ${delta} fewer ${metric}`;
  }
  if (direction === "neutral") {
    return `Difference ${delta} ${metric}`;
  }
  if (isPercentagePointMetric(leader.metric)) {
    return `${subject} +${delta}`;
  }
  return `${subject} +${delta} ${metric}`;
}

function formatEdgeDelta(delta: number, metric: string): string {
  if (isPercentagePointMetric(metric)) {
    const points = delta >= 0 && delta <= 1 ? delta * 100 : delta;
    return `${points.toFixed(1)} percentage points`;
  }
  return formatValue(delta, metric);
}

function metricValue(row: SectionRow, key: string): ReactNode {
  return hasValue(row[key])
    ? formatComparisonMetricValue(row[key], metricKey(row))
    : "-";
}

function metricDirection(metric: string): MetricDirection {
  return METRIC_DIRECTIONS[metric] ?? "higher";
}

function isPercentagePointMetric(metric: string): boolean {
  return metric === "win_pct" || metric.endsWith("_pct_avg");
}

function formatComparisonMetricValue(value: unknown, metric: string): string {
  if (
    typeof value === "number" &&
    Number.isFinite(value) &&
    isPercentagePointMetric(metric) &&
    value > 1
  ) {
    return `${value.toFixed(1)}%`;
  }
  return formatValue(value, metric);
}

function entityLabel(entity: EntityDisplay | string): string {
  return typeof entity === "string" ? entity : entity.name;
}

function signedValue(value: number, key: string): string {
  if (key === "plus_minus_avg" && value > 0) {
    return `+${formatValue(value, key)}`;
  }
  return formatValue(value, key);
}

function recordText(row: SectionRow | undefined): string | null {
  const wins = numericValue(row, "wins");
  const losses = numericValue(row, "losses");
  if (wins === null || losses === null) return null;
  return `${formatValue(wins, "wins")}-${formatValue(losses, "losses")}`;
}

function subjectKey(entity: EntityDisplay | undefined, index: number): string {
  return `${entity?.kind ?? "subject"}-${entity?.name ?? index}`;
}

function seasonLabel(metadata: ResultMetadata | undefined): string | null {
  if (metadata?.season) return metadata.season;
  if (metadata?.start_season && metadata?.end_season) {
    return metadata.start_season === metadata.end_season
      ? metadata.start_season
      : `${metadata.start_season} to ${metadata.end_season}`;
  }
  return null;
}

function dateLabel(metadata: ResultMetadata | undefined): string | null {
  const start = metadataText(metadata, "start_date");
  const end = metadataText(metadata, "end_date");
  return formatLongDateRange(start, end);
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
