import type { CSSProperties } from "react";
import type { ResultMetadata, SectionRow } from "../api/types";
import {
  Avatar,
  Badge,
  Card,
  SectionHeader,
  Stat,
  StatBlock,
  TeamBadge,
  type StatProps,
} from "../design-system";
import { resolvePlayerIdentity, resolveTeamIdentity } from "../lib/identity";
import DataTable from "./DataTable";
import { formatValue } from "./tableFormatting";
import styles from "./PlayerSummarySection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
  metadata?: ResultMetadata;
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

function identityId(value: unknown): number | string | null {
  return typeof value === "number" || typeof value === "string" ? value : null;
}

function playerName(
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
) {
  return (
    metadata?.player_context?.player_name ??
    metadata?.player ??
    textValue(row, "player_name") ??
    textValue(row, "player") ??
    "Player"
  );
}

function heroStats(row: SectionRow | undefined): StatProps[] {
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
      size: "hero",
    });
  }

  return stats;
}

function recordStat(row: SectionRow | undefined): StatProps | null {
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

function secondaryStats(row: SectionRow | undefined): StatProps[] {
  const stats: StatProps[] = [];
  const candidates: Array<{ key: string; label: string }> = [
    { key: "minutes_avg", label: "MIN" },
    { key: "efg_pct_avg", label: "eFG%" },
    { key: "ts_pct_avg", label: "TS%" },
    { key: "fg3_pct_avg", label: "3P%" },
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

interface GamePoint {
  key: string;
  pts: number;
}

function rowKey(row: SectionRow, index: number): string {
  return (
    textValue(row, "game_id") ??
    `${textValue(row, "game_date") ?? "game"}-${index}`
  );
}

function scoringPoints(rows: SectionRow[]): GamePoint[] {
  return rows
    .map((row, index) => {
      const pts = numericValue(row, "pts");
      if (pts === null) return null;
      return {
        key: rowKey(row, index),
        pts,
      };
    })
    .filter((point): point is GamePoint => point !== null);
}

function sparklineCoordinates(points: GamePoint[]): string {
  const width = 120;
  const height = 42;
  const padding = 4;
  const values = points.map((point) => point.pts);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const innerWidth = width - padding * 2;
  const innerHeight = height - padding * 2;

  return points
    .map((point, index) => {
      const x =
        points.length === 1
          ? width / 2
          : padding + (index / (points.length - 1)) * innerWidth;
      const y = height - padding - ((point.pts - min) / range) * innerHeight;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}

function ScoringSparkline({ points }: { points: GamePoint[] }) {
  if (points.length < 2) return null;

  const coordinates = sparklineCoordinates(points);
  const latest = points[points.length - 1];

  return (
    <div className={styles.sparklinePanel}>
      <div className={styles.sparklineMeta}>
        <span className={styles.sparklineLabel}>Scoring Trend</span>
        <span className={styles.sparklineLatest}>
          {formatValue(latest.pts, "pts")} PTS latest
        </span>
      </div>
      <svg
        className={styles.sparklineSvg}
        role="img"
        aria-label={`Points over ${points.length} games`}
        viewBox="0 0 120 42"
        preserveAspectRatio="none"
      >
        <line
          className={styles.sparklineBaseline}
          x1="4"
          x2="116"
          y1="38"
          y2="38"
        />
        <polyline className={styles.sparklineLine} points={coordinates} />
        {coordinates.split(" ").map((coord, index) => {
          const [cx, cy] = coord.split(",");
          const isLatest = index === points.length - 1;
          return (
            <circle
              key={points[index].key}
              className={
                isLatest
                  ? `${styles.sparklinePoint} ${styles.sparklinePointLatest}`
                  : styles.sparklinePoint
              }
              cx={cx}
              cy={cy}
              r={isLatest ? 3 : 2.25}
            />
          );
        })}
      </svg>
    </div>
  );
}

function opponentIdentity(row: SectionRow) {
  return resolveTeamIdentity({
    teamId: identityId(row.opponent_team_id),
    teamAbbr: textValue(row, "opponent_team_abbr"),
    teamName: textValue(row, "opponent_team_name"),
  });
}

function outcomeVariant(row: SectionRow): "win" | "loss" | "neutral" {
  const outcome = textValue(row, "wl")?.toUpperCase();
  if (outcome === "W") return "win";
  if (outcome === "L") return "loss";
  return "neutral";
}

function statLine(): Array<{ key: string; label: string }> {
  return [
    { key: "pts", label: "PTS" },
    { key: "reb", label: "REB" },
    { key: "ast", label: "AST" },
    { key: "minutes", label: "MIN" },
  ];
}

function RecentGames({ rows }: { rows: SectionRow[] }) {
  const visibleRows = rows.slice(-5).reverse();

  return (
    <div className={styles.recentList} aria-label="Recent games">
      {visibleRows.map((row, index) => {
        const team = opponentIdentity(row);
        const outcome = textValue(row, "wl")?.toUpperCase() ?? "—";
        const date = textValue(row, "game_date") ?? "Date TBD";

        return (
          <div className={styles.recentGame} key={rowKey(row, index)}>
            <div className={styles.recentGameHeader}>
              <span className={styles.gameDate}>{date}</span>
              <Badge
                variant={outcomeVariant(row)}
                size="sm"
                uppercase
                aria-label={`Result ${outcome}`}
              >
                {outcome}
              </Badge>
            </div>
            <TeamBadge
              abbreviation={team.teamAbbr ?? undefined}
              name={team.teamName ?? team.teamAbbr ?? "Opponent"}
              logoUrl={team.logoUrl}
              size="sm"
              showName={false}
              style={(team.styleVars ?? undefined) as
                | CSSProperties
                | undefined}
            />
            <div className={styles.gameStats}>
              {statLine().map(({ key, label }) => (
                <div className={styles.gameStat} key={key}>
                  <span className={styles.gameStatValue}>
                    {formatValue(row[key], key)}
                  </span>
                  <span className={styles.gameStatLabel}>{label}</span>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function pluralizeGames(count: number): string {
  return `${count} ${count === 1 ? "game" : "games"}`;
}

export default function PlayerSummarySection({ sections, metadata }: Props) {
  const summary = sections.summary;
  const bySeason = sections.by_season;
  const gameLog = sections.game_log ?? [];
  const summaryRow = summary?.[0];
  const name = playerName(metadata, summaryRow);
  const identity = resolvePlayerIdentity({
    playerId:
      metadata?.player_context?.player_id ?? identityId(summaryRow?.player_id),
    playerName: name,
  });
  const primaryStats = heroStats(summaryRow);
  const record = recordStat(summaryRow);
  const supportingStats = secondaryStats(summaryRow);
  const points = scoringPoints(gameLog);

  return (
    <>
      {summary && summary.length > 0 && (
        <div className={styles.section}>
          <Card className={styles.hero} depth="elevated" padding="lg">
            <div className={styles.identityRow}>
              <Avatar
                className={styles.avatar}
                name={identity.playerName ?? name}
                imageUrl={identity.headshotUrl}
                size="lg"
              />
              <div className={styles.identityText}>
                <div className={styles.eyebrow}>Player Summary</div>
                <h2 className={styles.playerName}>{name}</h2>
              </div>
            </div>

            {primaryStats.length > 0 && (
              <div className={styles.heroStats}>
                {primaryStats.map((stat, index) => (
                  <Stat key={index} {...stat} className={styles.heroStat} />
                ))}
              </div>
            )}

            {(record || supportingStats.length > 0) && (
              <div className={styles.supportingStats}>
                {record && <Stat {...record} />}
                <StatBlock
                  stats={supportingStats}
                  columns={supportingStats.length >= 4 ? 4 : 2}
                  className={styles.statBlock}
                />
              </div>
            )}
          </Card>

          {gameLog.length > 0 && (
            <Card className={styles.gameSeries} padding="md">
              <div className={styles.gameSeriesHeader}>
                <div>
                  <div className={styles.eyebrow}>Game Log</div>
                  <h3 className={styles.gameSeriesTitle}>Recent Games</h3>
                </div>
                <span className={styles.gameSeriesCount}>
                  {pluralizeGames(gameLog.length)}
                </span>
              </div>
              <ScoringSparkline points={points} />
              <RecentGames rows={gameLog} />
            </Card>
          )}

          <div className={styles.detailSection}>
            <SectionHeader title="Full Summary" />
            <DataTable rows={summary} />
          </div>
        </div>
      )}
      {(!summary || summary.length === 0) && (
        <div className={styles.section}>
          <SectionHeader title="Player Summary" />
        </div>
      )}
      {bySeason && bySeason.length > 0 && (
        <div className={styles.section}>
          <SectionHeader title="By Season" />
          <DataTable rows={bySeason} />
        </div>
      )}
    </>
  );
}
