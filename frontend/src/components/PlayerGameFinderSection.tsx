import type { CSSProperties } from "react";
import type { SectionRow } from "../api/types";
import {
  Avatar,
  Badge,
  Card,
  SectionHeader,
  StatBlock,
  TeamBadge,
  type StatProps,
} from "../design-system";
import { resolvePlayerIdentity, resolveTeamIdentity } from "../lib/identity";
import DataTable from "./DataTable";
import { formatValue } from "./tableFormatting";
import styles from "./PlayerGameFinderSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
}

function numericValue(row: SectionRow, key: string): number | null {
  const value = row[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function textValue(row: SectionRow, key: string): string | null {
  const value = row[key];
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function identityId(value: unknown): number | string | null {
  return typeof value === "number" || typeof value === "string" ? value : null;
}

function boolValue(row: SectionRow, key: string): boolean {
  const value = row[key];
  return value === true || value === 1 || value === "1";
}

function playerIdentity(row: SectionRow, index: number) {
  return resolvePlayerIdentity({
    playerId: identityId(row.player_id),
    playerName:
      textValue(row, "player_name") ??
      textValue(row, "player") ??
      `Player ${index + 1}`,
  });
}

function teamIdentity(row: SectionRow, kind: "team" | "opponent") {
  const prefix = kind === "opponent" ? "opponent_team" : "team";
  const teamName =
    textValue(row, `${prefix}_name`) ??
    (kind === "team" ? textValue(row, "team") : textValue(row, "opponent"));
  const teamAbbr = textValue(row, `${prefix}_abbr`);
  const teamId = identityId(row[`${prefix}_id`]);
  const identity = resolveTeamIdentity({
    teamId,
    teamAbbr,
    teamName,
  });

  return identity.teamName || identity.teamAbbr ? identity : null;
}

function rowKey(row: SectionRow, index: number): string {
  const gameId = textValue(row, "game_id");
  const playerId = identityId(row.player_id);
  return [gameId, playerId, index].filter(Boolean).join("-") || `${index}`;
}

function rankLabel(row: SectionRow): string | null {
  const rank = numericValue(row, "rank");
  return rank === null ? null : `#${formatValue(rank, "rank")}`;
}

function gameDate(row: SectionRow): string | null {
  return textValue(row, "game_date");
}

function locationLabel(row: SectionRow, opponentLabel: string | null): string | null {
  if (!opponentLabel) return null;
  if (boolValue(row, "is_home")) return `vs ${opponentLabel}`;
  if (boolValue(row, "is_away")) return `at ${opponentLabel}`;
  return opponentLabel;
}

function resultVariant(wl: string): "win" | "loss" | "neutral" {
  const normalized = wl.trim().toUpperCase();
  if (normalized === "W") return "win";
  if (normalized === "L") return "loss";
  return "neutral";
}

function topLineStats(row: SectionRow): StatProps[] {
  const stats: StatProps[] = [];
  const candidates = [
    { key: "pts", label: "PTS", semantic: "accent" as const },
    { key: "reb", label: "REB", semantic: "neutral" as const },
    { key: "ast", label: "AST", semantic: "neutral" as const },
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

export default function PlayerGameFinderSection({ sections }: Props) {
  const finder = sections.finder;
  if (!finder || finder.length === 0) return null;

  return (
    <div className={styles.section}>
      <SectionHeader
        title="Player Games"
        count={`${finder.length} game${finder.length !== 1 ? "s" : ""}`}
      />
      <div className={styles.gameGrid} aria-label="Player game cards">
        {finder.map((row, index) => {
          const player = playerIdentity(row, index);
          const team = teamIdentity(row, "team");
          const opponent = teamIdentity(row, "opponent");
          const opponentLabel = opponent?.teamAbbr ?? opponent?.teamName ?? null;
          const location = locationLabel(row, opponentLabel);
          const result = textValue(row, "wl");
          const rank = rankLabel(row);
          const date = gameDate(row);
          const stats = topLineStats(row);

          return (
            <Card
              className={styles.gameCard}
              depth="card"
              key={rowKey(row, index)}
              padding="md"
            >
              <div className={styles.cardHeader}>
                <div className={styles.identityRow}>
                  <Avatar
                    className={styles.avatar}
                    name={player.playerName ?? `Player ${index + 1}`}
                    imageUrl={player.headshotUrl}
                    size="md"
                  />
                  <div className={styles.identityText}>
                    <div className={styles.eyebrow}>
                      {[rank, date].filter(Boolean).join(" / ") ||
                        `Game ${index + 1}`}
                    </div>
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

                {result && (
                  <Badge
                    className={styles.resultBadge}
                    size="sm"
                    uppercase
                    variant={resultVariant(result)}
                  >
                    {result}
                  </Badge>
                )}
              </div>

              {(opponent || location) && (
                <div className={styles.contextRow}>
                  {opponent && (
                    <TeamBadge
                      abbreviation={opponent.teamAbbr ?? undefined}
                      name={
                        opponent.teamName ?? opponent.teamAbbr ?? "Opponent"
                      }
                      logoUrl={opponent.logoUrl}
                      size="sm"
                      style={(opponent.styleVars ?? undefined) as
                        | CSSProperties
                        | undefined}
                    />
                  )}
                  {location && (
                    <span className={styles.locationLabel}>{location}</span>
                  )}
                </div>
              )}

              {stats.length > 0 && (
                <StatBlock
                  className={styles.statBlock}
                  columns={stats.length >= 3 ? 3 : 2}
                  stats={stats}
                />
              )}
            </Card>
          );
        })}
      </div>
      <Card className={styles.detailCard} depth="card" padding="md">
        <SectionHeader title="Player Game Detail" />
        <DataTable rows={finder} />
      </Card>
    </div>
  );
}
