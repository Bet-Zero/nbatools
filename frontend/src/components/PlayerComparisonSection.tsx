import type { CSSProperties } from "react";
import type { ResultMetadata, SectionRow } from "../api/types";
import {
  Avatar,
  Card,
  SectionHeader,
  Stat,
  StatBlock,
  TeamBadge,
  type StatProps,
} from "../design-system";
import { resolvePlayerIdentity, resolveTeamIdentity } from "../lib/identity";
import RawDetailToggle from "./RawDetailToggle";
import { formatColHeader, formatValue } from "./tableFormatting";
import styles from "./PlayerComparisonSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
  metadata?: ResultMetadata;
}

const STAT_LABELS: Record<string, string> = {
  ast: "AST",
  blk: "BLK",
  efg: "eFG",
  fg3m: "FG3M",
  pts: "PTS",
  reb: "REB",
  stl: "STL",
  ts: "TS",
  usg: "USG",
};

const METRIC_LABEL_OVERRIDES: Record<string, string> = {
  ast_pct_avg: "AST% Avg",
  ast_sum: "AST Total",
  efg_pct_avg: "eFG% Avg",
  fg3m_avg: "3PM Avg",
  minutes_avg: "MIN Avg",
  plus_minus_avg: "+/- Avg",
  pts_sum: "PTS Total",
  reb_pct_avg: "REB% Avg",
  reb_sum: "REB Total",
  ts_pct_avg: "TS% Avg",
  usg_pct_avg: "USG% Avg",
};

const LEADER_ELIGIBLE_METRICS = new Set([
  "games",
  "wins",
  "losses",
  "win_pct",
  "minutes_avg",
  "pts_avg",
  "reb_avg",
  "ast_avg",
  "stl_avg",
  "blk_avg",
  "tov_avg",
  "fg3m_avg",
  "plus_minus_avg",
  "efg_pct_avg",
  "ts_pct_avg",
  "usg_pct_avg",
  "ast_pct_avg",
  "reb_pct_avg",
  "pts_sum",
  "reb_sum",
  "ast_sum",
]);

const LOWER_IS_BETTER_METRICS = new Set(["losses", "tov_avg"]);

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

function identityId(value: unknown): number | string | null {
  return typeof value === "number" || typeof value === "string" ? value : null;
}

function playerContext(
  metadata: ResultMetadata | undefined,
  row: SectionRow,
  index: number,
) {
  const rowName = textValue(row, "player_name") ?? textValue(row, "player");
  return (
    metadata?.players_context?.find(
      (context) => context.player_name === rowName,
    ) ??
    metadata?.players_context?.[index] ??
    null
  );
}

function playerIdentity(
  metadata: ResultMetadata | undefined,
  row: SectionRow,
  index: number,
) {
  const context = playerContext(metadata, row, index);
  const rowName =
    textValue(row, "player_name") ?? textValue(row, "player") ?? null;
  return resolvePlayerIdentity({
    playerId: context?.player_id ?? identityId(row.player_id),
    playerName: context?.player_name ?? rowName ?? `Player ${index + 1}`,
  });
}

function teamIdentity(row: SectionRow) {
  const teamName = textValue(row, "team_name") ?? textValue(row, "team");
  const teamAbbr = textValue(row, "team_abbr");
  const identity = resolveTeamIdentity({
    teamId: identityId(row.team_id),
    teamAbbr,
    teamName,
  });

  return identity.teamName || identity.teamAbbr ? identity : null;
}

function heroStats(row: SectionRow): StatProps[] {
  const stats: StatProps[] = [];
  const candidates = [
    { key: "pts_avg", label: "PTS", semantic: "accent" as const },
    { key: "reb_avg", label: "REB", semantic: "neutral" as const },
    { key: "ast_avg", label: "AST", semantic: "neutral" as const },
  ];

  for (const { key, label, semantic } of candidates) {
    const value = numericValue(row, key);
    if (value === null) continue;
    stats.push({
      label,
      value: formatValue(value, key),
      semantic,
    });
  }

  return stats;
}

function sampleStats(row: SectionRow): string[] {
  const games = numericValue(row, "games");
  return games !== null ? [`${formatValue(games, "games")} games`] : [];
}

function recordStat(row: SectionRow): StatProps | null {
  const wins = numericValue(row, "wins");
  const losses = numericValue(row, "losses");
  const winPct = numericValue(row, "win_pct");

  if (wins === null || losses === null) return null;

  return {
    label: "Record",
    value: `${formatValue(wins, "wins")}-${formatValue(losses, "losses")}`,
    context:
      winPct !== null ? `${formatValue(winPct, "win_pct")} win pct` : null,
    semantic: wins >= losses ? "win" : "loss",
  };
}

function secondaryStats(row: SectionRow): StatProps[] {
  const stats: StatProps[] = [];
  const candidates: Array<{ key: string; label: string }> = [
    { key: "minutes_avg", label: "MIN" },
    { key: "ts_pct_avg", label: "TS%" },
    { key: "efg_pct_avg", label: "eFG%" },
    { key: "usg_pct_avg", label: "USG%" },
    { key: "plus_minus_avg", label: "+/-" },
  ];

  for (const { key, label } of candidates) {
    const value = numericValue(row, key);
    if (value === null) continue;
    stats.push({
      label,
      value: formatValue(value, key),
    });
  }

  return stats;
}

function rowKey(row: SectionRow, index: number): string {
  return textValue(row, "player_name") ?? textValue(row, "player") ?? `${index}`;
}

function metricKey(row: SectionRow): string {
  return textValue(row, "metric") ?? "metric";
}

function metricLabel(metric: string): string {
  const override = METRIC_LABEL_OVERRIDES[metric.toLowerCase()];
  if (override) return override;

  return formatColHeader(metric).replace(
    /\b(ast|blk|efg|fg3m|pts|reb|stl|ts|usg)\b/gi,
    (stat) => STAT_LABELS[stat.toLowerCase()] ?? stat,
  );
}

function edgeMetricLabel(metric: string): string {
  return metricLabel(metric)
    .replace(/\s+Avg$/i, "")
    .replace(/\s+Total$/i, "");
}

function formatEdgeDelta(delta: number, metric: string): string {
  if (metric.endsWith("_avg") && !metric.includes("pct")) {
    return delta.toFixed(1);
  }
  return formatValue(delta, metric);
}

function playerNameForTitle(
  metadata: ResultMetadata | undefined,
  summary: SectionRow[] | undefined,
  index: number,
): string {
  const row = summary?.[index];
  return (
    metadata?.players_context?.[index]?.player_name ??
    textValue(row, "player_name") ??
    textValue(row, "player") ??
    `Player ${index + 1}`
  );
}

function comparisonTitle(
  metadata: ResultMetadata | undefined,
  summary: SectionRow[] | undefined,
): string {
  return `${playerNameForTitle(metadata, summary, 0)} vs ${playerNameForTitle(
    metadata,
    summary,
    1,
  )}`;
}

function isCareerComparison(metadata: ResultMetadata | undefined): boolean {
  const query =
    typeof metadata?.query_text === "string" ? metadata.query_text : "";
  return /\b(career|all[- ]?time|lifetime)\b/i.test(query);
}

function seasonContext(metadata: ResultMetadata | undefined): string | null {
  const start = metadata?.start_season ?? metadata?.season ?? null;
  const end = metadata?.end_season ?? metadata?.season ?? null;
  if (start && end && start !== end) return `${start} to ${end}`;
  return start ?? end;
}

function headerContextItems(
  metadata: ResultMetadata | undefined,
  summary: SectionRow[] | undefined,
): string[] {
  const games = (summary ?? [])
    .map((row) => numericValue(row, "games"))
    .filter((value): value is number => value !== null);
  const parts = [
    isCareerComparison(metadata)
      ? "Career averages and totals"
      : seasonContext(metadata),
    metadata?.season_type ?? null,
    games.length >= 2
      ? `${formatValue(games[0], "games")} vs ${formatValue(
          games[1],
          "games",
        )} games`
      : null,
    metadata?.opponent ? `vs ${metadata.opponent}` : null,
  ];

  return parts.filter((part): part is string => Boolean(part));
}

function comparisonColumns(row: SectionRow): string[] {
  return Object.keys(row).filter((key) => key !== "metric");
}

function comparisonValue(row: SectionRow, column: string): number | null {
  const value = row[column];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function leaderInfo(row: SectionRow, columns: string[]) {
  const metric = metricKey(row);
  if (!LEADER_ELIGIBLE_METRICS.has(metric)) return null;
  const lowerIsBetter = LOWER_IS_BETTER_METRICS.has(metric);

  const numericValues = columns
    .map((column) => ({
      column,
      value: comparisonValue(row, column),
    }))
    .filter(
      (item): item is { column: string; value: number } => item.value !== null,
    )
    .sort((a, b) => (lowerIsBetter ? a.value - b.value : b.value - a.value));

  if (numericValues.length < 2) return null;

  const [first, second] = numericValues;
  if (Math.abs(first.value - second.value) < 1e-9) {
    return { type: "tie" as const };
  }

  return {
    type: "leader" as const,
    column: first.column,
    delta: Math.abs(first.value - second.value),
    metric,
  };
}

function edgeLabel(
  leader: Extract<ReturnType<typeof leaderInfo>, { type: "leader" }>,
) {
  return `${leader.column} +${formatEdgeDelta(
    leader.delta,
    leader.metric,
  )} ${edgeMetricLabel(leader.metric)}`;
}

function statColumns(count: number): 1 | 2 | 3 | 4 {
  if (count <= 1) return 1;
  if (count === 2) return 2;
  if (count === 3) return 3;
  return 4;
}

export default function PlayerComparisonSection({ sections, metadata }: Props) {
  const summary = sections.summary;
  const comparison = sections.comparison;
  const title = comparisonTitle(metadata, summary);
  const headerContext = headerContextItems(metadata, summary);

  return (
    <>
      {summary && summary.length > 0 && (
        <div className={styles.section}>
          <SectionHeader
            title={title}
            count={`${summary.length} players`}
          />
          {headerContext.length > 0 && (
            <div
              className={styles.headerContext}
              aria-label="Comparison context"
            >
              {headerContext.map((item) => (
                <span className={styles.contextChip} key={item}>
                  {item}
                </span>
              ))}
            </div>
          )}
          <div className={styles.playerGrid} aria-label="Compared players">
            {summary.map((row, index) => {
              const player = playerIdentity(metadata, row, index);
              const team = teamIdentity(row);
              const stats = heroStats(row);
              const record = recordStat(row);
              const secondary = secondaryStats(row);
              const playerContext = sampleStats(row);

              return (
                <Card
                  className={styles.playerCard}
                  depth="card"
                  key={rowKey(row, index)}
                  padding="lg"
                >
                  <div className={styles.identityRow}>
                    <Avatar
                      className={styles.avatar}
                      name={player.playerName ?? `Player ${index + 1}`}
                      imageUrl={player.headshotUrl}
                      size="lg"
                    />
                    <div className={styles.identityText}>
                      <div className={styles.eyebrow}>Player {index + 1}</div>
                      <h3 className={styles.playerName}>
                        {player.playerName ?? `Player ${index + 1}`}
                      </h3>
                      {team && (
                        <TeamBadge
                          className={styles.teamBadge}
                          abbreviation={team.teamAbbr ?? undefined}
                          name={team.teamName ?? team.teamAbbr ?? "Team"}
                          logoUrl={team.logoUrl}
                          size="sm"
                          style={(team.styleVars ?? undefined) as
                            | CSSProperties
                            | undefined}
                        />
                      )}
                      {playerContext.length > 0 && (
                        <div
                          className={styles.playerContext}
                          aria-label={`${
                            player.playerName ?? `Player ${index + 1}`
                          } sample`}
                        >
                          {playerContext.map((item) => (
                            <span className={styles.contextChip} key={item}>
                              {item}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {stats.length > 0 && (
                    <StatBlock
                      className={styles.heroStats}
                      columns={statColumns(stats.length)}
                      stats={stats}
                    />
                  )}

                  {(record || secondary.length > 0) && (
                    <div className={styles.supportingStats}>
                      {record && <Stat {...record} />}
                      <StatBlock
                        className={styles.secondaryStats}
                        columns={statColumns(secondary.length)}
                        stats={secondary}
                      />
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
          <RawDetailToggle title="Player Summary Detail" rows={summary} />
        </div>
      )}
      {comparison && comparison.length > 0 && (
        <div className={styles.section}>
          <SectionHeader title="Metric Comparison" />
          <div
            className={styles.metricGrid}
            aria-label="Metric comparison cards"
          >
            {comparison.map((row, index) => {
              const metric = metricKey(row);
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
                    <div className={styles.metricName}>
                      {metricLabel(metric)}
                    </div>
                    {leader?.type === "leader" && (
                      <div className={styles.leaderBadge}>
                        {edgeLabel(leader)}
                      </div>
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
