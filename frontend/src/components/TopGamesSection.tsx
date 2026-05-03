import type { CSSProperties } from "react";
import type { ResultMetadata, SectionRow } from "../api/types";
import {
  Avatar,
  Badge,
  SectionHeader,
  StatBlock,
  TeamBadge,
  type BadgeVariant,
  type StatProps,
} from "../design-system";
import { resolvePlayerIdentity, resolveTeamIdentity } from "../lib/identity";
import RawDetailToggle from "./RawDetailToggle";
import { formatColHeader, formatValue } from "./tableFormatting";
import styles from "./TopGamesSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
  metadata?: ResultMetadata;
  mode: "player" | "team";
}

const METRIC_LABELS: Record<string, string> = {
  ast: "AST",
  blk: "BLK",
  dreb: "DREB",
  fg3a: "3PA",
  fg3m: "3PM",
  fga: "FGA",
  fgm: "FGM",
  fta: "FTA",
  ftm: "FTM",
  minutes: "MIN",
  oreb: "OREB",
  pf: "PF",
  plus_minus: "+/-",
  pts: "PTS",
  reb: "REB",
  stl: "STL",
  tov: "TOV",
};

const PLAYER_SUPPORT_STATS: Array<{ label: string; keys: string[] }> = [
  { label: "REB", keys: ["reb"] },
  { label: "AST", keys: ["ast"] },
  { label: "MIN", keys: ["minutes"] },
  { label: "FG", keys: ["fgm", "fga"] },
  { label: "3P", keys: ["fg3m", "fg3a"] },
  { label: "FT", keys: ["ftm", "fta"] },
  { label: "STL", keys: ["stl"] },
  { label: "BLK", keys: ["blk"] },
  { label: "TOV", keys: ["tov"] },
];

const TEAM_SUPPORT_STATS: Array<{ label: string; keys: string[] }> = [
  { label: "REB", keys: ["reb"] },
  { label: "AST", keys: ["ast"] },
  { label: "3P", keys: ["fg3m", "fg3a"] },
  { label: "FG", keys: ["fgm", "fga"] },
  { label: "FT", keys: ["ftm", "fta"] },
  { label: "STL", keys: ["stl"] },
  { label: "BLK", keys: ["blk"] },
  { label: "TOV", keys: ["tov"] },
  { label: "+/-", keys: ["plus_minus"] },
];

const SIGNED_METRICS = new Set(["plus_minus"]);

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

function rankLabel(row: SectionRow, index: number): string {
  const rank = row.rank;
  if (typeof rank === "number" || typeof rank === "string") return `#${rank}`;
  return `#${index + 1}`;
}

function metricKey(row: SectionRow, metadata: ResultMetadata | undefined): string | null {
  const requested = metadataText(metadata, "stat");
  if (requested && hasValue(row[requested])) return requested;

  for (const key of ["pts", "reb", "ast", "stl", "blk", "minutes", "plus_minus"]) {
    if (hasValue(row[key])) return key;
  }

  return null;
}

function metricLabel(key: string): string {
  return METRIC_LABELS[key] ?? formatColHeader(key);
}

function formatSigned(value: number, key: string): string {
  const formatted = formatValue(value, key);
  return value > 0 ? `+${formatted}` : formatted;
}

function displayValue(value: unknown, key: string): string {
  if (typeof value === "number" && SIGNED_METRICS.has(key)) {
    return formatSigned(value, key);
  }
  return formatValue(value, key);
}

function resultVariant(wl: string | null): BadgeVariant {
  if (wl?.toUpperCase() === "W") return "win";
  if (wl?.toUpperCase() === "L") return "loss";
  return "neutral";
}

function resultLabel(row: SectionRow): string | null {
  const wl = textValue(row, "wl");
  if (!wl) return null;
  const normalized = wl.toUpperCase();
  if (normalized === "W" || normalized === "L") return normalized;
  return wl;
}

function locationLabel(row: SectionRow): string | null {
  const opponent =
    textValue(row, "opponent_team_abbr") ??
    textValue(row, "opponent_team_name") ??
    textValue(row, "opponent");
  if (!opponent) return null;
  if (row.is_home === true || row.is_home === 1 || row.is_home === "1") {
    return `vs ${opponent}`;
  }
  if (row.is_away === true || row.is_away === 1 || row.is_away === "1") {
    return `at ${opponent}`;
  }
  return opponent;
}

function madeAttemptValue(row: SectionRow, madeKey: string, attemptKey: string): string | null {
  if (!hasValue(row[madeKey]) || !hasValue(row[attemptKey])) return null;
  return `${formatValue(row[madeKey], madeKey)}/${formatValue(row[attemptKey], attemptKey)}`;
}

function supportStats(
  row: SectionRow,
  mode: "player" | "team",
  metric: string | null,
): StatProps[] {
  const candidates = mode === "player" ? PLAYER_SUPPORT_STATS : TEAM_SUPPORT_STATS;
  const stats: StatProps[] = [];

  for (const { label, keys } of candidates) {
    if (keys.length === 1 && keys[0] === metric) continue;

    const value =
      keys.length === 2
        ? madeAttemptValue(row, keys[0], keys[1])
        : hasValue(row[keys[0]])
          ? displayValue(row[keys[0]], keys[0])
          : null;
    if (!value) continue;
    const numeric = numericValue(row, keys[0]);

    stats.push({
      label,
      value,
      semantic:
        keys[0] === "plus_minus" && numeric !== null
          ? numeric >= 0
            ? "win"
            : "loss"
          : stats.length === 0
            ? "accent"
            : "neutral",
    });
  }

  return stats.slice(0, 9);
}

function statColumns(count: number): 1 | 2 | 3 | 4 {
  if (count >= 4) return 4;
  if (count === 3) return 3;
  if (count === 2) return 2;
  return 1;
}

function playerIdentity(row: SectionRow) {
  const name = textValue(row, "player_name") ?? "Player";
  return resolvePlayerIdentity({
    playerId: identityId(row.player_id),
    playerName: name,
  });
}

function teamIdentity(row: SectionRow, prefix = "team") {
  const name =
    textValue(row, `${prefix}_name`) ??
    (prefix === "team" ? textValue(row, "team") : textValue(row, "opponent"));
  const abbr = textValue(row, `${prefix}_abbr`);

  return resolveTeamIdentity({
    teamId: identityId(row[`${prefix}_id`]),
    teamAbbr: abbr,
    teamName: name ?? abbr,
  });
}

function teamScore(row: SectionRow): number | null {
  return numericValue(row, "team_score") ?? numericValue(row, "pts");
}

function opponentScore(row: SectionRow): number | null {
  const explicit =
    numericValue(row, "opponent_score") ??
    numericValue(row, "opponent_pts") ??
    numericValue(row, "opp_pts");
  if (explicit !== null) return explicit;

  const own = teamScore(row);
  const margin = numericValue(row, "plus_minus");
  if (own === null || margin === null) return null;
  return own - margin;
}

function scoreText(row: SectionRow): string | null {
  const own = teamScore(row);
  const opponent = opponentScore(row);
  if (own === null || opponent === null) return null;
  return `${formatValue(own, "pts")}-${formatValue(opponent, "pts")}`;
}

function rowKey(row: SectionRow, index: number, mode: "player" | "team"): string {
  const identity =
    mode === "player"
      ? textValue(row, "player_name")
      : textValue(row, "team_name") ?? textValue(row, "team_abbr");
  return `${rankLabel(row, index)}-${identity ?? "game"}-${textValue(row, "game_id") ?? index}`;
}

function ResultBadge({ row }: { row: SectionRow }) {
  const result = resultLabel(row);
  if (!result) return null;
  return (
    <Badge
      variant={resultVariant(result)}
      size="sm"
      uppercase
      aria-label={`Result ${result}`}
    >
      {result}
    </Badge>
  );
}

function PlayerGameRow({
  row,
  index,
  metadata,
}: {
  row: SectionRow;
  index: number;
  metadata?: ResultMetadata;
}) {
  const player = playerIdentity(row);
  const playerName = player.playerName ?? "Player";
  const team = teamIdentity(row);
  const metric = metricKey(row, metadata);
  const stats = supportStats(row, "player", metric);
  const date = textValue(row, "game_date");
  const location = locationLabel(row);
  const season = textValue(row, "season") ?? metadata?.season;

  return (
    <article
      className={`${styles.rankedRow} ${index === 0 ? styles.topRankedRow : ""}`}
      key={rowKey(row, index, "player")}
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
            <div className={styles.entityName}>{playerName}</div>
            <div className={styles.teamLine}>
              <TeamBadge
                abbreviation={team.teamAbbr ?? undefined}
                name={team.teamName ?? team.teamAbbr ?? "Team"}
                logoUrl={team.logoUrl}
                size="sm"
                className={styles.teamBadge}
                style={(team.styleVars ?? undefined) as CSSProperties | undefined}
              />
            </div>
            <div className={styles.context} aria-label={`${playerName} game context`}>
              {date && <span className={styles.contextChip}>{date}</span>}
              {location && <span className={styles.contextChip}>{location}</span>}
              {season && <span className={styles.contextChip}>{season}</span>}
              {metadata?.season_type && (
                <span className={styles.contextChip}>{metadata.season_type}</span>
              )}
            </div>
          </div>
        </div>
        {stats.length > 0 && (
          <StatBlock stats={stats} columns={statColumns(stats.length)} />
        )}
      </div>
      <div className={styles.metricBlock}>
        <ResultBadge row={row} />
        {metric && (
          <>
            <div className={styles.metricValue}>
              {displayValue(row[metric], metric)}
            </div>
            <div className={styles.metricLabel}>{metricLabel(metric)}</div>
          </>
        )}
      </div>
    </article>
  );
}

function TeamGameRow({
  row,
  index,
  metadata,
}: {
  row: SectionRow;
  index: number;
  metadata?: ResultMetadata;
}) {
  const team = teamIdentity(row);
  const opponent = teamIdentity(row, "opponent_team");
  const teamName = team.teamName ?? team.teamAbbr ?? "Team";
  const metric = metricKey(row, metadata);
  const stats = supportStats(row, "team", metric);
  const date = textValue(row, "game_date");
  const location = locationLabel(row);
  const season = textValue(row, "season") ?? metadata?.season;
  const score = scoreText(row);

  return (
    <article
      className={`${styles.rankedRow} ${index === 0 ? styles.topRankedRow : ""}`}
      key={rowKey(row, index, "team")}
    >
      <div className={styles.rank}>{rankLabel(row, index)}</div>
      <div className={styles.identityBlock}>
        <div className={styles.teamMatchup}>
          <TeamBadge
            abbreviation={team.teamAbbr ?? undefined}
            name={teamName}
            logoUrl={team.logoUrl}
            size="md"
            className={styles.teamBadge}
            style={(team.styleVars ?? undefined) as CSSProperties | undefined}
          />
          <div className={styles.scoreBlock}>
            <div className={styles.scoreValue}>{score ?? "Game"}</div>
            {location && <div className={styles.locationText}>{location}</div>}
          </div>
          {(opponent.teamAbbr || opponent.teamName) && (
            <TeamBadge
              abbreviation={opponent.teamAbbr ?? undefined}
              name={opponent.teamName ?? opponent.teamAbbr ?? "Opponent"}
              logoUrl={opponent.logoUrl}
              size="md"
              className={styles.teamBadge}
              style={(opponent.styleVars ?? undefined) as CSSProperties | undefined}
            />
          )}
        </div>
        <div className={styles.context} aria-label={`${teamName} game context`}>
          {date && <span className={styles.contextChip}>{date}</span>}
          {season && <span className={styles.contextChip}>{season}</span>}
          {metadata?.season_type && (
            <span className={styles.contextChip}>{metadata.season_type}</span>
          )}
        </div>
        {stats.length > 0 && (
          <StatBlock stats={stats} columns={statColumns(stats.length)} />
        )}
      </div>
      <div className={styles.metricBlock}>
        <ResultBadge row={row} />
        {metric && (
          <>
            <div className={styles.metricValue}>
              {displayValue(row[metric], metric)}
            </div>
            <div className={styles.metricLabel}>{metricLabel(metric)}</div>
          </>
        )}
      </div>
    </article>
  );
}

export default function TopGamesSection({ sections, metadata, mode }: Props) {
  const leaderboard = sections.leaderboard;
  if (!leaderboard || leaderboard.length === 0) return null;

  const title = mode === "player" ? "Top Player Games" : "Top Team Games";
  const detailTitle =
    mode === "player" ? "Top Player Games Detail" : "Top Team Games Detail";

  return (
    <div className={styles.section}>
      <SectionHeader title={title} count={`${leaderboard.length} games`} />
      <div
        className={styles.rankedList}
        aria-label={mode === "player" ? "Ranked player games" : "Ranked team games"}
      >
        {leaderboard.map((row, index) =>
          mode === "player" ? (
            <PlayerGameRow
              row={row}
              index={index}
              metadata={metadata}
              key={rowKey(row, index, "player")}
            />
          ) : (
            <TeamGameRow
              row={row}
              index={index}
              metadata={metadata}
              key={rowKey(row, index, "team")}
            />
          ),
        )}
      </div>
      <RawDetailToggle title={detailTitle} rows={leaderboard} />
    </div>
  );
}
