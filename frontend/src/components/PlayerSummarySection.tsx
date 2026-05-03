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
import RawDetailToggle from "./RawDetailToggle";
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
      animateValue: true,
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

interface GameStat {
  key: string;
  label: string;
  value: string;
}

const RECENT_GAME_LIMIT = 30;

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

function hasDisplayValue(row: SectionRow, key: string): boolean {
  const value = row[key];
  if (value === null || value === undefined) return false;
  return typeof value !== "string" || value.trim().length > 0;
}

function madeAttemptStat(
  row: SectionRow,
  madeKey: string,
  attemptKey: string,
  pctKey: string,
): string | null {
  if (hasDisplayValue(row, madeKey) && hasDisplayValue(row, attemptKey)) {
    return `${formatValue(row[madeKey], madeKey)}-${formatValue(
      row[attemptKey],
      attemptKey,
    )}`;
  }
  if (hasDisplayValue(row, pctKey)) return formatValue(row[pctKey], pctKey);
  if (hasDisplayValue(row, madeKey)) return formatValue(row[madeKey], madeKey);
  return null;
}

function signedValue(value: number, key: string): string {
  const formatted = formatValue(value, key);
  return value > 0 ? `+${formatted}` : formatted;
}

function optionalStatValue(row: SectionRow, key: string): string | null {
  if (!hasDisplayValue(row, key)) return null;
  const value = row[key];
  if (key === "plus_minus" && typeof value === "number") {
    return signedValue(value, key);
  }
  return formatValue(value, key);
}

function statLine(row: SectionRow): GameStat[] {
  const stats: GameStat[] = [
    { key: "pts", label: "PTS", value: formatValue(row.pts, "pts") },
    { key: "reb", label: "REB", value: formatValue(row.reb, "reb") },
    { key: "ast", label: "AST", value: formatValue(row.ast, "ast") },
    {
      key: "minutes",
      label: "MIN",
      value: formatValue(row.minutes, "minutes"),
    },
  ];
  const optionalStats: Array<GameStat | null> = [
    statOrNull("fg", "FG", madeAttemptStat(row, "fgm", "fga", "fg_pct")),
    statOrNull("fg3", "3P", madeAttemptStat(row, "fg3m", "fg3a", "fg3_pct")),
    statOrNull("ft", "FT", madeAttemptStat(row, "ftm", "fta", "ft_pct")),
    statOrNull("stl", "STL", optionalStatValue(row, "stl")),
    statOrNull("blk", "BLK", optionalStatValue(row, "blk")),
    statOrNull("tov", "TOV", optionalStatValue(row, "tov")),
    statOrNull("plus_minus", "+/-", optionalStatValue(row, "plus_minus")),
  ];

  return stats.concat(
    optionalStats.filter((stat): stat is GameStat => stat !== null),
  );
}

function statOrNull(
  key: string,
  label: string,
  value: string | null,
): GameStat | null {
  return value === null ? null : { key, label, value };
}

function isTruthyFlag(value: unknown): boolean {
  if (value === true || value === 1) return true;
  if (typeof value === "string") {
    return ["1", "true", "yes", "y"].includes(value.trim().toLowerCase());
  }
  return false;
}

function matchupText(
  row: SectionRow,
  team: ReturnType<typeof opponentIdentity>,
): string | null {
  const opponent = team.teamAbbr ?? team.teamName;
  if (!opponent) return null;
  if (isTruthyFlag(row.is_away)) return `at ${opponent}`;
  if (isTruthyFlag(row.is_home)) return `vs ${opponent}`;
  return String(opponent);
}

function scorePair(
  row: SectionRow,
  firstKey: string,
  secondKey: string,
): string | null {
  if (!hasDisplayValue(row, firstKey) || !hasDisplayValue(row, secondKey)) {
    return null;
  }
  return `${formatValue(row[firstKey], firstKey)}-${formatValue(
    row[secondKey],
    secondKey,
  )}`;
}

function scoreText(row: SectionRow): string | null {
  const directScore = textValue(row, "score");
  if (directScore) return directScore;

  const teamScore =
    scorePair(row, "team_score", "opponent_score") ??
    scorePair(row, "team_pts", "opponent_pts") ??
    scorePair(row, "pts_team", "pts_opponent");
  if (teamScore) return teamScore;

  if (
    !hasDisplayValue(row, "score_home") ||
    !hasDisplayValue(row, "score_away")
  ) {
    return null;
  }
  if (isTruthyFlag(row.is_away)) {
    return scorePair(row, "score_away", "score_home");
  }
  return scorePair(row, "score_home", "score_away");
}

function compareRecentRows(
  a: { row: SectionRow; index: number },
  b: { row: SectionRow; index: number },
): number {
  const aDate = textValue(a.row, "game_date");
  const bDate = textValue(b.row, "game_date");
  if (aDate && bDate && aDate !== bDate) return bDate.localeCompare(aDate);
  if (aDate && !bDate) return -1;
  if (!aDate && bDate) return 1;

  const aGameId = textValue(a.row, "game_id");
  const bGameId = textValue(b.row, "game_id");
  if (aGameId && bGameId && aGameId !== bGameId) {
    return bGameId.localeCompare(aGameId);
  }

  return b.index - a.index;
}

function recentGameRows(rows: SectionRow[]): SectionRow[] {
  return rows
    .map((row, index) => ({ row, index }))
    .sort(compareRecentRows)
    .slice(0, RECENT_GAME_LIMIT)
    .map(({ row }) => row);
}

function RecentGames({ rows }: { rows: SectionRow[] }) {
  return (
    <div className={styles.recentList} aria-label="Recent games">
      {rows.map((row, index) => {
        const team = opponentIdentity(row);
        const outcome = textValue(row, "wl")?.toUpperCase() ?? "—";
        const date = textValue(row, "game_date") ?? "Date TBD";
        const matchup = matchupText(row, team);
        const score = scoreText(row);
        const stats = statLine(row);

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
            <div className={styles.gameMeta}>
              <TeamBadge
                className={styles.opponentBadge}
                abbreviation={team.teamAbbr ?? undefined}
                name={team.teamName ?? team.teamAbbr ?? "Opponent"}
                logoUrl={team.logoUrl}
                size="sm"
                showName={false}
                style={(team.styleVars ?? undefined) as
                  | CSSProperties
                  | undefined}
              />
              {(matchup || score) && (
                <div className={styles.gameContext}>
                  {matchup && (
                    <span className={styles.matchupText}>{matchup}</span>
                  )}
                  {score && <span className={styles.scoreText}>{score}</span>}
                </div>
              )}
            </div>
            <div className={styles.gameStats}>
              {stats.map(({ key, label, value }) => (
                <div className={styles.gameStat} key={key}>
                  <span className={styles.gameStatValue}>{value}</span>
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
  const visibleGameLog = recentGameRows(gameLog);
  const sparklineRows = [...visibleGameLog].reverse();
  const points = scoringPoints(sparklineRows);
  const gameLogIsCapped = gameLog.length > visibleGameLog.length;

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
                <div className={styles.gameSeriesTitleBlock}>
                  <div className={styles.eyebrow}>Game Log</div>
                  <h3 className={styles.gameSeriesTitle}>
                    Recent Games ({visibleGameLog.length})
                  </h3>
                </div>
                <span className={styles.gameSeriesCount}>
                  {pluralizeGames(visibleGameLog.length)}
                </span>
              </div>
              {gameLogIsCapped && (
                <div className={styles.gameSeriesNote}>
                  showing {visibleGameLog.length} of {gameLog.length} games
                </div>
              )}
              <ScoringSparkline points={points} />
              <RecentGames rows={visibleGameLog} />
            </Card>
          )}

          <RawDetailToggle title="Full Summary" rows={summary} />
        </div>
      )}
      {(!summary || summary.length === 0) && (
        <div className={styles.section}>
          <SectionHeader title="Player Summary" />
        </div>
      )}
      {bySeason && bySeason.length > 0 && (
        <div className={styles.section}>
          <RawDetailToggle title="By Season" rows={bySeason} />
        </div>
      )}
    </>
  );
}
