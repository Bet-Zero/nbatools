import type { CSSProperties } from "react";
import type { ResultMetadata, SectionRow } from "../api/types";
import {
  Avatar,
  SectionHeader,
  StatBlock,
  TeamBadge,
  type StatProps,
} from "../design-system";
import { resolvePlayerIdentity, resolveTeamIdentity } from "../lib/identity";
import RawDetailToggle from "./RawDetailToggle";
import { formatColHeader, formatValue } from "./tableFormatting";
import styles from "./PlayerStretchLeaderboardSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
  metadata?: ResultMetadata;
}

const METRIC_LABELS: Record<string, string> = {
  ast: "APG",
  blk: "BLK",
  efg_pct: "eFG%",
  fg3_pct: "3P%",
  fg3m: "3PM",
  fg_pct: "FG%",
  ft_pct: "FT%",
  game_score: "Game Score",
  minutes: "MIN",
  plus_minus: "+/-",
  pts: "PPG",
  reb: "RPG",
  stl: "STL",
  ts_pct: "TS%",
};

const SIGNED_METRICS = new Set(["plus_minus"]);

const SUPPORT_STATS: Array<{
  keys: string[];
  label: string;
}> = [
  { keys: ["reb_avg", "reb"], label: "REB" },
  { keys: ["ast_avg", "ast"], label: "AST" },
  { keys: ["ts_pct_avg", "ts_pct"], label: "TS%" },
  { keys: ["minutes_avg", "minutes"], label: "MIN" },
];

const OPTIONAL_GAME_SECTIONS = ["window_games", "game_log", "games"];

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

function hasValue(value: unknown): boolean {
  return value !== null && value !== undefined && value !== "";
}

function identityId(value: unknown): number | string | null {
  return typeof value === "number" || typeof value === "string" ? value : null;
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

function metadataNumber(
  metadata: ResultMetadata | undefined,
  key: string,
): number | null {
  const value = metadata?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function rankLabel(row: SectionRow, index: number): string {
  const rank = row.rank;
  if (typeof rank === "number" || typeof rank === "string") return `#${rank}`;
  return `#${index + 1}`;
}

function playerIdentity(row: SectionRow) {
  const name = textValue(row, "player_name") ?? "Player";
  return resolvePlayerIdentity({
    playerId: identityId(row.player_id),
    playerName: name,
  });
}

function teamIdentity(row: SectionRow) {
  const teamAbbr = textValue(row, "team_abbr") ?? textValue(row, "team");
  const teamName = textValue(row, "team_name") ?? teamAbbr ?? "Team";
  return resolveTeamIdentity({
    teamId: identityId(row.team_id),
    teamAbbr,
    teamName,
  });
}

function stretchMetric(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
): string {
  return (
    textValue(row, "stretch_metric") ??
    metadataText(metadata, "stretch_metric") ??
    metadataText(metadata, "stat") ??
    "stretch_value"
  );
}

function metricLabel(metric: string): string {
  return METRIC_LABELS[metric] ?? formatColHeader(metric);
}

function displayValue(value: unknown, metric: string): string {
  if (typeof value === "number" && SIGNED_METRICS.has(metric)) {
    const formatted = formatValue(value, metric);
    return value > 0 ? `+${formatted}` : formatted;
  }
  return formatValue(value, metric);
}

function dateRange(row: SectionRow): string | null {
  const start = textValue(row, "window_start_date");
  const end = textValue(row, "window_end_date");
  if (start && end) return start === end ? start : `${start} to ${end}`;
  return start ?? end;
}

function seasonRange(row: SectionRow, metadata: ResultMetadata | undefined): string | null {
  const start =
    textValue(row, "window_start_season") ??
    metadata?.start_season ??
    metadata?.season ??
    null;
  const end =
    textValue(row, "window_end_season") ??
    metadata?.end_season ??
    metadata?.season ??
    null;
  if (start && end && start !== end) return `${start} to ${end}`;
  return start ?? end;
}

function windowSize(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
): number | null {
  return numericValue(row, "window_size") ?? metadataNumber(metadata, "window_size");
}

function gamesInWindow(row: SectionRow): number | null {
  return numericValue(row, "games_in_window") ?? numericValue(row, "games");
}

function contextItems(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
): string[] {
  const size = windowSize(row, metadata);
  const games = gamesInWindow(row);
  return [
    size !== null ? `${formatValue(size, "window_size")}-game stretch` : null,
    dateRange(row),
    seasonRange(row, metadata),
    metadata?.season_type ?? textValue(row, "season_type"),
    games !== null ? `${formatValue(games, "games_in_window")} games` : null,
  ].filter((item): item is string => Boolean(item));
}

function supportStats(row: SectionRow): StatProps[] {
  const stats: StatProps[] = [];

  for (const { keys, label } of SUPPORT_STATS) {
    const key = keys.find((candidate) => hasValue(row[candidate]));
    if (!key) continue;
    stats.push({
      label,
      value: formatValue(row[key], key),
      semantic: stats.length === 0 ? "accent" : "neutral",
    });
  }

  return stats;
}

function statColumns(count: number): 1 | 2 | 3 | 4 {
  if (count >= 4) return 4;
  if (count === 3) return 3;
  if (count === 2) return 2;
  return 1;
}

function rowKey(row: SectionRow, index: number): string {
  return `${rankLabel(row, index)}-${textValue(row, "player_name") ?? "player"}-${index}`;
}

function optionalGameRows(sections: Record<string, SectionRow[]>): SectionRow[] {
  for (const key of OPTIONAL_GAME_SECTIONS) {
    const rows = sections[key];
    if (rows && rows.length > 0) return rows;
  }
  return [];
}

export default function PlayerStretchLeaderboardSection({
  sections,
  metadata,
}: Props) {
  const leaderboard = sections.leaderboard;
  if (!leaderboard || leaderboard.length === 0) return null;

  const gameRows = optionalGameRows(sections);

  return (
    <>
      <div className={styles.section}>
        <SectionHeader
          title="Stretch Leaderboard"
          count={`${leaderboard.length} stretches`}
        />
        <div className={styles.rankedList} aria-label="Ranked stretches">
          {leaderboard.map((row, index) => {
            const player = playerIdentity(row);
            const playerName = player.playerName ?? "Player";
            const team = teamIdentity(row);
            const teamName = team.teamName ?? team.teamAbbr ?? "Team";
            const metric = stretchMetric(row, metadata);
            const support = supportStats(row);
            const context = contextItems(row, metadata);

            return (
              <article
                className={`${styles.rankedRow} ${
                  index === 0 ? styles.topRankedRow : ""
                }`}
                key={rowKey(row, index)}
              >
                <div className={styles.rank}>{rankLabel(row, index)}</div>
                <div className={styles.identityBlock}>
                  <div className={styles.identityContent}>
                    <Avatar
                      className={styles.avatar}
                      name={playerName}
                      imageUrl={player.headshotUrl}
                      size="md"
                    />
                    <div className={styles.identityText}>
                      <div className={styles.playerName}>{playerName}</div>
                      <div className={styles.teamLine}>
                        <TeamBadge
                          abbreviation={team.teamAbbr ?? undefined}
                          name={teamName}
                          logoUrl={team.logoUrl}
                          size="sm"
                          className={styles.teamBadge}
                          style={(team.styleVars ?? undefined) as
                            | CSSProperties
                            | undefined}
                        />
                      </div>
                      {context.length > 0 && (
                        <div
                          className={styles.context}
                          aria-label={`${playerName} stretch context`}
                        >
                          {context.map((item) => (
                            <span className={styles.contextChip} key={item}>
                              {item}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                  {support.length > 0 && (
                    <StatBlock
                      stats={support}
                      columns={statColumns(support.length)}
                      className={styles.supportStats}
                    />
                  )}
                </div>
                <div className={styles.metricBlock}>
                  <div className={styles.metricValue}>
                    {displayValue(row.stretch_value, metric)}
                  </div>
                  <div className={styles.metricLabel}>{metricLabel(metric)}</div>
                </div>
              </article>
            );
          })}
        </div>
        <RawDetailToggle title="Stretch Leaderboard Detail" rows={leaderboard} />
      </div>

      {gameRows.length > 0 && (
        <div className={styles.section}>
          <RawDetailToggle title="Stretch Games" rows={gameRows} />
        </div>
      )}
    </>
  );
}
