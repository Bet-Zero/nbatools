import type { CSSProperties } from "react";
import type { ResultMetadata, SectionRow } from "../api/types";
import {
  Card,
  SectionHeader,
  StatBlock,
  TeamBadge,
  type StatProps,
} from "../design-system";
import { resolveTeamIdentity } from "../lib/identity";
import RawDetailToggle from "./RawDetailToggle";
import { formatColHeader, formatValue } from "./tableFormatting";
import styles from "./TeamComparisonSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
  metadata?: ResultMetadata;
}

const LOWER_IS_BETTER = new Set(["losses", "tov_avg"]);

const TEAM_STATS: Array<{ key: string; label: string }> = [
  { key: "pts_avg", label: "PPG" },
  { key: "reb_avg", label: "REB" },
  { key: "ast_avg", label: "AST" },
  { key: "fg3m_avg", label: "3PM" },
  { key: "plus_minus_avg", label: "+/-" },
  { key: "efg_pct_avg", label: "eFG%" },
  { key: "ts_pct_avg", label: "TS%" },
];

function textValue(row: SectionRow | undefined, key: string): string | null {
  const value = row?.[key];
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function numericValue(row: SectionRow | undefined, key: string): number | null {
  const value = row?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function identityId(value: unknown): number | string | null {
  return typeof value === "number" || typeof value === "string" ? value : null;
}

function teamIdentity(
  metadata: ResultMetadata | undefined,
  row: SectionRow,
  index: number,
) {
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

  return resolveTeamIdentity({
    teamId: context?.team_id ?? identityId(row.team_id),
    teamAbbr:
      context?.team_abbr ??
      textValue(row, "team_abbr") ??
      textValue(row, "team"),
    teamName: context?.team_name ?? rowName ?? `Team ${index + 1}`,
  });
}

function comparisonTitle(
  metadata: ResultMetadata | undefined,
  summary: SectionRow[] | undefined,
): string {
  const names =
    metadata?.teams_context?.map((team) => team.team_name) ??
    summary?.map((row, index) => {
      const identity = teamIdentity(metadata, row, index);
      return identity.teamName ?? identity.teamAbbr ?? `Team ${index + 1}`;
    }) ??
    [];
  if (names.length >= 2) return `${names[0]} vs ${names[1]}`;
  return "Team Comparison";
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

function headerContext(metadata: ResultMetadata | undefined): string[] {
  return [
    seasonLabel(metadata),
    metadata?.season_type ?? null,
    dateLabel(metadata),
    metadata?.opponent ? `vs ${metadata.opponent}` : null,
  ].filter((item): item is string => Boolean(item));
}

function recordStat(row: SectionRow): StatProps | null {
  const wins = numericValue(row, "wins");
  const losses = numericValue(row, "losses");
  const games = numericValue(row, "games");
  const winPct = numericValue(row, "win_pct");
  if (wins === null || losses === null) return null;

  const context = [
    games !== null ? `${formatValue(games, "games")} games` : null,
    winPct !== null ? `${formatValue(winPct, "win_pct")} win pct` : null,
  ]
    .filter(Boolean)
    .join(" / ");

  return {
    label: "Record",
    value: `${formatValue(wins, "wins")}-${formatValue(losses, "losses")}`,
    context,
    semantic: wins >= losses ? "win" : "loss",
  };
}

function teamStats(row: SectionRow): StatProps[] {
  const stats: StatProps[] = [];
  const record = recordStat(row);
  if (record) stats.push(record);

  for (const { key, label } of TEAM_STATS) {
    const value = numericValue(row, key);
    if (value === null) continue;
    stats.push({
      label,
      value: formatValue(value, key),
      semantic:
        key === "plus_minus_avg"
          ? value >= 0
            ? "win"
            : "loss"
          : stats.length === 0
            ? "accent"
            : "neutral",
    });
  }

  return stats.slice(0, 8);
}

function statColumns(count: number): 1 | 2 | 3 | 4 {
  if (count >= 4) return 4;
  if (count === 3) return 3;
  if (count === 2) return 2;
  return 1;
}

function metricLabel(metric: string): string {
  const labels: Record<string, string> = {
    ast_avg: "AST",
    blk_avg: "BLK",
    efg_pct_avg: "eFG%",
    fg3m_avg: "3PM",
    games: "Games",
    losses: "Losses",
    plus_minus_avg: "+/-",
    pts_avg: "PPG",
    reb_avg: "REB",
    stl_avg: "STL",
    tov_avg: "TOV",
    ts_pct_avg: "TS%",
    win_pct: "Win Pct",
    wins: "Wins",
  };
  return labels[metric] ?? formatColHeader(metric);
}

function comparisonColumns(row: SectionRow): string[] {
  return Object.keys(row).filter((key) => key !== "metric");
}

type LeaderInfo =
  | { type: "leader"; column: string; delta: number; metric: string }
  | { type: "tie" };

function leaderInfo(row: SectionRow, columns: string[]): LeaderInfo | null {
  const metric = textValue(row, "metric") ?? "metric";
  if (columns.length < 2) return null;

  const values = columns
    .map((column) => ({ column, value: numericValue(row, column) }))
    .filter((item): item is { column: string; value: number } => item.value !== null);
  if (values.length < 2) return null;

  const sorted = [...values].sort((a, b) =>
    LOWER_IS_BETTER.has(metric) ? a.value - b.value : b.value - a.value,
  );
  const [first, second] = sorted;
  if (first.value === second.value) return { type: "tie" };

  return {
    type: "leader",
    column: first.column,
    delta: Math.abs(first.value - second.value),
    metric,
  };
}

function edgeLabel(leader: Extract<LeaderInfo, { type: "leader" }>): string {
  return `${leader.column} +${formatValue(leader.delta, leader.metric)}`;
}

export default function TeamComparisonSection({ sections, metadata }: Props) {
  const summary = sections.summary;
  const comparison = sections.comparison;
  const title = comparisonTitle(metadata, summary);
  const context = headerContext(metadata);

  return (
    <>
      {summary && summary.length > 0 && (
        <div className={styles.section}>
          <SectionHeader title={title} count={`${summary.length} teams`} />
          {context.length > 0 && (
            <div className={styles.context} aria-label="Comparison context">
              {context.map((item) => (
                <span className={styles.contextChip} key={item}>
                  {item}
                </span>
              ))}
            </div>
          )}
          <div className={styles.teamGrid} aria-label="Compared teams">
            {summary.map((row, index) => {
              const identity = teamIdentity(metadata, row, index);
              const name =
                identity.teamName ?? identity.teamAbbr ?? `Team ${index + 1}`;
              const stats = teamStats(row);

              return (
                <Card
                  className={styles.teamCard}
                  depth="card"
                  key={`${name}-${index}`}
                  padding="lg"
                >
                  <div className={styles.identityRow}>
                    <TeamBadge
                      abbreviation={identity.teamAbbr ?? undefined}
                      name={name}
                      logoUrl={identity.logoUrl}
                      size="md"
                      className={styles.teamBadge}
                      style={(identity.styleVars ?? undefined) as
                        | CSSProperties
                        | undefined}
                    />
                    <div className={styles.identityText}>
                      <div className={styles.eyebrow}>Team {index + 1}</div>
                      <h3 className={styles.teamName}>{name}</h3>
                    </div>
                  </div>
                  {stats.length > 0 && (
                    <StatBlock stats={stats} columns={statColumns(stats.length)} />
                  )}
                </Card>
              );
            })}
          </div>
          <RawDetailToggle title="Team Summary Detail" rows={summary} />
        </div>
      )}

      {comparison && comparison.length > 0 && (
        <div className={styles.section}>
          <SectionHeader title="Metric Comparison" />
          <div className={styles.metricGrid} aria-label="Team metric comparison">
            {comparison.map((row, index) => {
              const metric = textValue(row, "metric") ?? "metric";
              const columns = comparisonColumns(row);
              const leader = leaderInfo(row, columns);

              return (
                <Card
                  className={styles.metricCard}
                  depth="card"
                  key={`${metric}-${index}`}
                  padding="md"
                >
                  <div className={styles.metricHeader}>
                    <div className={styles.metricName}>{metricLabel(metric)}</div>
                    {leader?.type === "leader" && (
                      <div className={styles.leaderBadge}>{edgeLabel(leader)}</div>
                    )}
                    {leader?.type === "tie" && (
                      <div className={styles.tieBadge}>Tie</div>
                    )}
                  </div>
                  <div className={styles.metricValues}>
                    {columns.map((column) => {
                      const isLeader =
                        leader?.type === "leader" &&
                        leader.column === column;
                      return (
                        <div
                          className={`${styles.metricValue} ${
                            isLeader ? styles.leaderValue : ""
                          }`}
                          key={column}
                        >
                          <span className={styles.metricEntity}>{column}</span>
                          <span className={styles.metricNumber}>
                            {formatValue(row[column], metric)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </Card>
              );
            })}
          </div>
          <RawDetailToggle title="Full Metric Detail" rows={comparison} highlight />
        </div>
      )}
    </>
  );
}
