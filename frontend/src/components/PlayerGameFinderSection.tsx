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
import { formatColHeader, formatValue } from "./tableFormatting";
import styles from "./PlayerGameFinderSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
}

const STAT_LABELS: Record<string, string> = {
  ast: "AST",
  blk: "BLK",
  efg: "eFG",
  fg3a: "FG3A",
  fg3m: "FG3M",
  pts: "PTS",
  reb: "REB",
  stl: "STL",
  tov: "TOV",
  ts: "TS",
  usg: "USG",
};

const PROMOTED_STAT_CANDIDATES = [
  "pts",
  "reb",
  "ast",
  "fg3m",
  "stl",
  "blk",
  "tov",
  "fg3a",
];

const DETAIL_OR_CONTEXT_KEYS = new Set([
  "rank",
  "game_date",
  "game_id",
  "season",
  "season_type",
  "player_name",
  "player",
  "player_id",
  "team_name",
  "team",
  "team_abbr",
  "team_id",
  "opponent_team_name",
  "opponent_team_abbr",
  "opponent_team_id",
  "opponent",
  "is_home",
  "is_away",
  "wl",
  "minutes",
  "plus_minus",
  "clutch_events",
  "clutch_seconds",
]);

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

function statLabel(key: string): string {
  return formatColHeader(key).replace(
    /\b(ast|blk|efg|fg3a|fg3m|pts|reb|stl|tov|ts|usg)\b/gi,
    (stat) => STAT_LABELS[stat.toLowerCase()] ?? stat,
  );
}

function addStat(
  stats: StatProps[],
  row: SectionRow,
  key: string,
  semantic: StatProps["semantic"] = "neutral",
): boolean {
  const value = numericValue(row, key);
  if (value === null) return false;
  stats.push({
    label: statLabel(key),
    value: formatValue(value, key),
    semantic,
  });
  return true;
}

function topLineStats(row: SectionRow): StatProps[] {
  const stats: StatProps[] = [];
  const used = new Set<string>();

  for (const key of PROMOTED_STAT_CANDIDATES) {
    if (stats.length >= 4) break;
    if (addStat(stats, row, key, stats.length === 0 ? "accent" : "neutral")) {
      used.add(key);
    }
  }

  for (const key of Object.keys(row)) {
    if (stats.length >= 4) break;
    if (used.has(key) || DETAIL_OR_CONTEXT_KEYS.has(key)) continue;
    addStat(stats, row, key, stats.length === 0 ? "accent" : "neutral");
  }

  return stats;
}

function signedValue(value: number, key: string): string {
  const formatted = formatValue(value, key);
  return value > 0 ? `+${formatted}` : formatted;
}

function secondaryContext(row: SectionRow): string[] {
  const context = [
    textValue(row, "season"),
    textValue(row, "season_type"),
  ];
  const minutes = numericValue(row, "minutes");
  const plusMinus = numericValue(row, "plus_minus");
  const clutchEvents = numericValue(row, "clutch_events");
  const clutchSeconds = numericValue(row, "clutch_seconds");

  if (minutes !== null) context.push(`MIN ${formatValue(minutes, "minutes")}`);
  if (plusMinus !== null) {
    context.push(`+/- ${signedValue(plusMinus, "plus_minus")}`);
  }
  if (clutchEvents !== null) {
    context.push(`Clutch events ${formatValue(clutchEvents, "clutch_events")}`);
  }
  if (clutchSeconds !== null) {
    context.push(
      `Clutch seconds ${formatValue(clutchSeconds, "clutch_seconds")}`,
    );
  }

  return context.filter((item): item is string => Boolean(item));
}

function statColumns(count: number): 1 | 2 | 3 | 4 {
  if (count >= 4) return 4;
  if (count === 3) return 3;
  if (count === 2) return 2;
  return 1;
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
          const context = secondaryContext(row);

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

              {context.length > 0 && (
                <div className={styles.secondaryContext}>
                  {context.map((item) => (
                    <span className={styles.contextChip} key={item}>
                      {item}
                    </span>
                  ))}
                </div>
              )}

              {stats.length > 0 && (
                <StatBlock
                  className={styles.statBlock}
                  columns={statColumns(stats.length)}
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
