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

const LEADER_ELIGIBLE_METRICS = new Set([
  "games",
  "wins",
  "win_pct",
  "minutes_avg",
  "pts_avg",
  "reb_avg",
  "ast_avg",
  "stl_avg",
  "blk_avg",
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

function secondaryStats(row: SectionRow): StatProps[] {
  const stats: StatProps[] = [];
  const candidates: Array<{ key: string; label: string }> = [
    { key: "minutes_avg", label: "MIN" },
    { key: "efg_pct_avg", label: "eFG%" },
    { key: "ts_pct_avg", label: "TS%" },
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
  return formatColHeader(metric).replace(
    /\b(ast|blk|efg|fg3m|pts|reb|stl|ts|usg)\b/gi,
    (stat) => STAT_LABELS[stat.toLowerCase()] ?? stat,
  );
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

  const numericValues = columns
    .map((column) => ({
      column,
      value: comparisonValue(row, column),
    }))
    .filter(
      (item): item is { column: string; value: number } => item.value !== null,
    )
    .sort((a, b) => b.value - a.value);

  if (numericValues.length < 2) return null;

  const [first, second] = numericValues;
  if (Math.abs(first.value - second.value) < 1e-9) {
    return { type: "tie" as const };
  }

  return {
    type: "leader" as const,
    column: first.column,
    delta: first.value - second.value,
    metric,
  };
}

export default function PlayerComparisonSection({ sections, metadata }: Props) {
  const summary = sections.summary;
  const comparison = sections.comparison;

  return (
    <>
      {summary && summary.length > 0 && (
        <div className={styles.section}>
          <SectionHeader
            title="Player Comparison"
            count={`${summary.length} players`}
          />
          <div className={styles.playerGrid} aria-label="Compared players">
            {summary.map((row, index) => {
              const player = playerIdentity(metadata, row, index);
              const team = teamIdentity(row);
              const stats = heroStats(row);
              const record = recordStat(row);
              const secondary = secondaryStats(row);

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
                    </div>
                  </div>

                  {stats.length > 0 && (
                    <StatBlock
                      className={styles.heroStats}
                      columns={stats.length >= 3 ? 3 : 2}
                      stats={stats}
                    />
                  )}

                  {(record || secondary.length > 0) && (
                    <div className={styles.supportingStats}>
                      {record && <Stat {...record} />}
                      <StatBlock
                        className={styles.secondaryStats}
                        columns={secondary.length >= 4 ? 4 : 2}
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
                        {leader.column} leads by{" "}
                        {formatValue(leader.delta, leader.metric)}
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
