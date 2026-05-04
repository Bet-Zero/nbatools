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
import ResultTable, {
  type ResultTableColumn,
} from "../primitives/ResultTable";
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
  semantic?: "accent" | "positive" | "negative" | "neutral";
};

type LeaderInfo =
  | { type: "leader"; column: string; delta: number; metric: string }
  | { type: "tie" };

const LOWER_IS_BETTER = new Set(["losses", "tov_avg"]);

const METRIC_LABEL_OVERRIDES: Record<string, string> = {
  ast_avg: "AST Avg",
  ast_pct_avg: "AST% Avg",
  ast_sum: "AST Total",
  blk_avg: "BLK Avg",
  efg_pct_avg: "eFG% Avg",
  fg3m_avg: "3PM Avg",
  losses: "Losses",
  minutes_avg: "MIN Avg",
  plus_minus_avg: "+/- Avg",
  pts_avg: "PTS Avg",
  pts_sum: "PTS Total",
  reb_avg: "REB Avg",
  reb_pct_avg: "REB% Avg",
  reb_sum: "REB Total",
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
  fg3m_avg: "3PM",
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
  const comparison = sections.comparison ?? [];
  const kind = subject ?? subjectKind(data);
  const isHeadToHead = headToHead ?? isHeadToHeadResult(data);
  const entities = summary.map((row, index) =>
    entityDisplay(kind, data.result?.metadata, row, index),
  );

  if (summary.length === 0 && comparison.length === 0) return null;

  return (
    <section className={styles.pattern} aria-label="Comparison result">
      <ResultHero
        sentence={heroSentence(data, entities, comparison, isHeadToHead)}
        subjectIllustration={<MatchupIdentity entities={entities} />}
        tone={kind === "team" ? "team" : "accent"}
      />
      {summary.length > 0 && (
        <div className={styles.subjectGrid} aria-label={subjectGridLabel(kind, isHeadToHead)}>
          {summary.map((row, index) => (
            <SubjectPanel
              entity={entities[index]}
              index={index}
              key={subjectKey(entities[index], index)}
              row={row}
            />
          ))}
        </div>
      )}
      {comparison.length > 0 && (
        <ResultTable
          rows={comparison}
          columns={metricColumns(comparison)}
          ariaLabel="Comparison metrics"
          getRowKey={metricRowKey}
        />
      )}
      {detailToggles(sections, kind, isHeadToHead)}
    </section>
  );
}

function SubjectPanel({
  entity,
  index,
  row,
}: {
  entity: EntityDisplay;
  index: number;
  row: SectionRow;
}) {
  const stats = subjectStats(row);

  return (
    <article className={styles.subjectCard}>
      <div className={styles.subjectHeader}>
        {entityIdentity(entity)}
        <span className={styles.subjectIndex}>
          {entity.kind === "player" ? "Player" : "Team"} {index + 1}
        </span>
      </div>
      {stats.length > 0 && (
        <div className={styles.statGrid} aria-label={`${entity.name} stats`}>
          {stats.map((stat) => (
            <span
              className={`${styles.statChip} ${styles[`stat_${stat.semantic ?? "neutral"}`]}`}
              key={stat.label}
            >
              <span className={styles.statValue}>{stat.value}</span>
              <span className={styles.statLabel}>{stat.label}</span>
              {stat.context && (
                <span className={styles.statContext}>{stat.context}</span>
              )}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}

function MatchupIdentity({ entities }: { entities: EntityDisplay[] }) {
  if (entities.length === 0) return null;

  return (
    <span className={styles.matchupIdentity}>
      {entityIdentity(entities[0])}
      {entities[1] && <span className={styles.vsBadge}>vs</span>}
      {entities[1] && entityIdentity(entities[1])}
    </span>
  );
}

function heroSentence(
  data: QueryResponse,
  entities: EntityDisplay[],
  comparison: SectionRow[],
  headToHead: boolean,
): ReactNode {
  const title = comparisonTitle(entities);
  const first = entities[0]?.name ?? "Subject 1";
  const second = entities[1]?.name ?? "Subject 2";
  const summary = data.result?.sections?.summary ?? [];

  if (headToHead && summary.length >= 2) {
    const firstWins = numericValue(summary[0], "wins");
    const firstLosses = numericValue(summary[0], "losses");
    const secondRecord = recordText(summary[1]);
    const firstRecord = recordText(summary[0]);

    if (firstWins !== null && firstLosses !== null && firstRecord) {
      if (firstWins > firstLosses) {
        return (
          <>
            {first} leads {second}{" "}
            <span className={styles.heroValue}>{firstRecord}</span> in this
            head-to-head sample.
          </>
        );
      }
      if (firstWins < firstLosses && secondRecord) {
        return (
          <>
            {second} leads {first}{" "}
            <span className={styles.heroValue}>{secondRecord}</span> in this
            head-to-head sample.
          </>
        );
      }
      return (
        <>
          {first} and {second} are tied{" "}
          <span className={styles.heroValue}>{firstRecord}</span> in this
          head-to-head sample.
        </>
      );
    }
  }

  const edge = comparison
    .map((row) => {
      const columns = comparisonValueColumns(row);
      const leader = leaderInfo(row, columns);
      return leader?.type === "leader" ? edgeLabel(leader) : null;
    })
    .find((value): value is string => Boolean(value));

  if (edge) {
    return (
      <>
        {title}: <span className={styles.heroValue}>{edge}</span>.
      </>
    );
  }

  const context = contextLabel(data.result?.metadata);
  return (
    <>
      {title}
      {context ? ` for ${context}` : ""}.
    </>
  );
}

function metricColumns(
  rows: SectionRow[],
): Array<ResultTableColumn<SectionRow>> {
  const valueColumns = allMetricValueColumns(rows);
  const columns: Array<ResultTableColumn<SectionRow>> = [
    {
      key: "metric",
      header: "Metric",
      render: (row) => metricLabel(metricKey(row)),
    },
  ];

  for (const key of valueColumns) {
    columns.push({
      key,
      header: key,
      numeric: rows.some((row) => numericValue(row, key) !== null),
      render: (row) => metricValue(row, key),
    });
  }

  columns.push({
    key: "edge",
    header: "Edge",
    render: (row) => {
      const leader = leaderInfo(row, valueColumns);
      if (leader?.type === "tie") return "Tie";
      return leader?.type === "leader" ? edgeLabel(leader) : "-";
    },
  });

  return columns;
}

function detailToggles(
  sections: Record<string, SectionRow[]>,
  kind: SubjectKind,
  headToHead: boolean,
) {
  return Object.keys(sections)
    .filter((key) => sections[key]?.length > 0)
    .map((key) => (
      <RawDetailToggle
        key={key}
        title={detailTitle(key, kind, headToHead)}
        rows={sections[key]}
        highlight={key !== "summary"}
      />
    ));
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
            ? "positive"
            : "negative"
          : candidate.semantic,
    });
  }

  return stats.slice(0, 8);
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
        winPct !== null ? `${formatValue(winPct, "win_pct")} win pct` : null,
      ]
        .filter(Boolean)
        .join(" / "),
      semantic: wins > losses ? "positive" : wins < losses ? "negative" : "neutral",
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
  return route === "team_matchup_record" || data.result?.metadata?.head_to_head_used === true;
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
    metricLabel(metric).replace(/\s+Avg$/i, "").replace(/\s+Total$/i, "")
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
  return Object.keys(row).filter((key) => key !== "metric");
}

function leaderInfo(row: SectionRow, columns: string[]): LeaderInfo | null {
  const metric = metricKey(row);
  const values = columns
    .map((column) => ({ column, value: numericValue(row, column) }))
    .filter((item): item is { column: string; value: number } => item.value !== null);

  if (values.length < 2) return null;

  const sorted = [...values].sort((a, b) =>
    LOWER_IS_BETTER.has(metric) ? a.value - b.value : b.value - a.value,
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

function edgeLabel(leader: Extract<LeaderInfo, { type: "leader" }>): string {
  return `${leader.column} +${formatEdgeDelta(leader.delta, leader.metric)} ${edgeMetricLabel(
    leader.metric,
  )}`;
}

function formatEdgeDelta(delta: number, metric: string): string {
  if (metric.endsWith("_avg") && !metric.includes("pct")) {
    return delta.toFixed(1);
  }
  return formatValue(delta, metric);
}

function metricValue(row: SectionRow, key: string): ReactNode {
  return hasValue(row[key]) ? formatValue(row[key], metricKey(row)) : "-";
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
  if (start && end) return start === end ? start : `${start} to ${end}`;
  return start ?? end;
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
