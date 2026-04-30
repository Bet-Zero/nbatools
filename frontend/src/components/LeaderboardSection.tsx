import { type CSSProperties } from "react";
import type { SectionRow } from "../api/types";
import { Avatar, SectionHeader, TeamBadge } from "../design-system";
import { resolvePlayerIdentity, resolveTeamIdentity } from "../lib/identity";
import DataTable from "./DataTable";
import { formatColHeader, formatValue } from "./tableFormatting";
import styles from "./LeaderboardSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
}

const SYSTEM_COLUMNS = new Set([
  "rank",
  "player_id",
  "team_id",
  "player_name",
  "team_name",
  "team_abbr",
  "season",
  "seasons",
  "season_type",
  "game_id",
  "game_date",
  "is_home",
  "is_away",
  "wl",
  "opponent_team_id",
  "opponent_team_abbr",
  "opponent_team_name",
]);

const ENTITY_COLUMNS = [
  "player_name",
  "team_name",
  "team_abbr",
  "lineup",
  "lineup_members",
  "members",
  "entity",
  "name",
];

type RowIdentity =
  | {
      kind: "player";
      label: string;
      player: ReturnType<typeof resolvePlayerIdentity>;
    }
  | {
      kind: "team";
      label: string;
      team: ReturnType<typeof resolveTeamIdentity>;
    };

function textValue(row: SectionRow, key: string): string | null {
  const value = row[key];
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function identityId(value: unknown): number | string | null {
  if (typeof value === "number" || typeof value === "string") return value;
  return null;
}

function hasValue(value: unknown): boolean {
  return value !== null && value !== undefined && value !== "";
}

function rankLabel(row: SectionRow, index: number): string {
  const rank = row.rank;
  if (typeof rank === "number" || typeof rank === "string") {
    return `#${rank}`;
  }
  return `#${index + 1}`;
}

function entityLabel(row: SectionRow): string {
  for (const key of ENTITY_COLUMNS) {
    const value = row[key];
    if (Array.isArray(value) && value.length > 0) {
      return value.map(String).join(" / ");
    }
    const text = textValue(row, key);
    if (text) return text;
  }
  return "Leaderboard Entry";
}

function rowIdentity(row: SectionRow): RowIdentity | null {
  const playerName = textValue(row, "player_name") ?? textValue(row, "player");
  if (playerName) {
    const player = resolvePlayerIdentity({
      playerId: identityId(row.player_id),
      playerName,
    });
    return {
      kind: "player",
      label: player.playerName ?? playerName,
      player,
    };
  }

  const teamName = textValue(row, "team_name") ?? textValue(row, "team");
  const teamAbbr = textValue(row, "team_abbr");
  if (teamName || teamAbbr) {
    const team = resolveTeamIdentity({
      teamId: identityId(row.team_id),
      teamAbbr,
      teamName,
    });
    return {
      kind: "team",
      label: team.teamName ?? team.teamAbbr ?? teamName ?? teamAbbr ?? "Team",
      team,
    };
  }

  return null;
}

function metricColumn(row: SectionRow): string | null {
  const columns = Object.keys(row);
  const metricCandidates = columns.filter(
    (key) =>
      !SYSTEM_COLUMNS.has(key) &&
      !ENTITY_COLUMNS.includes(key) &&
      key !== "games_played",
  );

  return (
    metricCandidates.find((key) => typeof row[key] === "number") ??
    metricCandidates.find((key) => hasValue(row[key])) ??
    (hasValue(row.games_played) ? "games_played" : null)
  );
}

function contextItems(row: SectionRow): string[] {
  const items: string[] = [];

  if (hasValue(row.games_played)) {
    items.push(`${formatValue(row.games_played, "games_played")} games`);
  }

  const season = textValue(row, "seasons") ?? textValue(row, "season");
  if (season) items.push(season);

  const seasonType = textValue(row, "season_type");
  if (seasonType) items.push(seasonType);

  const team = textValue(row, "team_abbr");
  if (team && textValue(row, "team_name")) items.push(team);

  const gameDate = textValue(row, "game_date");
  if (gameDate) items.push(gameDate);

  const opponent = textValue(row, "opponent_team_abbr");
  if (opponent) items.push(`vs ${opponent}`);

  return items;
}

function rowKey(row: SectionRow, index: number): string {
  return `${rankLabel(row, index)}-${entityLabel(row)}-${index}`;
}

function IdentityMark({ identity }: { identity: RowIdentity }) {
  if (identity.kind === "player") {
    return (
      <Avatar
        className={styles.identityMark}
        name={identity.player.playerName ?? identity.label}
        imageUrl={identity.player.headshotUrl}
        size="md"
      />
    );
  }

  return (
    <TeamBadge
      className={styles.identityMark}
      abbreviation={identity.team.teamAbbr ?? undefined}
      name={identity.team.teamName ?? identity.team.teamAbbr ?? identity.label}
      logoUrl={identity.team.logoUrl}
      size="md"
      showName={false}
      style={(identity.team.styleVars ?? undefined) as
        | CSSProperties
        | undefined}
    />
  );
}

export default function LeaderboardSection({ sections }: Props) {
  const leaderboard = sections.leaderboard;
  if (!leaderboard || leaderboard.length === 0) return null;

  return (
    <div className={styles.section}>
      <SectionHeader
        title="Leaderboard"
        count={`${leaderboard.length} entries`}
      />
      <div className={styles.rankedList} aria-label="Ranked leaderboard">
        {leaderboard.map((row, index) => {
          const metric = metricColumn(row);
          const context = contextItems(row);
          const isTopRank = index === 0;
          const identity = rowIdentity(row);

          return (
            <article
              className={`${styles.rankedRow} ${
                isTopRank ? styles.topRankedRow : ""
              }`}
              key={rowKey(row, index)}
            >
              <div className={styles.rank}>{rankLabel(row, index)}</div>
              <div className={styles.entityBlock}>
                <div className={styles.entityContent}>
                  {identity && <IdentityMark identity={identity} />}
                  <div className={styles.entityText}>
                    <div className={styles.entityName}>
                      {identity?.label ?? entityLabel(row)}
                    </div>
                    {context.length > 0 && (
                      <div className={styles.context}>
                        {context.join(" / ")}
                      </div>
                    )}
                  </div>
                </div>
              </div>
              {metric && (
                <div className={styles.metricBlock}>
                  <div className={styles.metricValue}>
                    {formatValue(row[metric], metric)}
                  </div>
                  <div className={styles.metricLabel}>
                    {formatColHeader(metric)}
                  </div>
                </div>
              )}
            </article>
          );
        })}
      </div>
      <div className={styles.detailSection}>
        <SectionHeader title="Full Leaderboard" />
        <DataTable rows={leaderboard} highlight />
      </div>
    </div>
  );
}
