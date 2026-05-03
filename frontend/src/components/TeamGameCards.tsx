import type { CSSProperties } from "react";
import type { SectionRow } from "../api/types";
import {
  Badge,
  Card,
  StatBlock,
  TeamBadge,
  type BadgeVariant,
  type StatProps,
} from "../design-system";
import { resolveTeamIdentity } from "../lib/identity";
import { formatColHeader, formatValue } from "./tableFormatting";
import styles from "./TeamGameCards.module.css";

interface Props {
  rows: SectionRow[];
}

type TeamKind = "team" | "opponent";

const STAT_LABELS: Record<string, string> = {
  ast: "AST",
  fg3m: "3PM",
  fg_pct: "FG%",
  fg3_pct: "3P%",
  ft_pct: "FT%",
  plus_minus: "Margin",
  pts: "PTS",
  reb: "REB",
  tov: "TOV",
};

const CARD_STATS = [
  "pts",
  "plus_minus",
  "reb",
  "ast",
  "fg3m",
  "fg_pct",
  "fg3_pct",
  "ft_pct",
  "tov",
];

function textValue(row: SectionRow, key: string): string | null {
  const value = row[key];
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function numericValue(row: SectionRow, key: string): number | null {
  const value = row[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function identityId(value: unknown): number | string | null {
  return typeof value === "number" || typeof value === "string" ? value : null;
}

function boolValue(row: SectionRow, key: string): boolean {
  const value = row[key];
  return value === true || value === 1 || value === "1";
}

function teamIdentity(row: SectionRow, kind: TeamKind) {
  const prefix = kind === "opponent" ? "opponent_team" : "team";
  const name =
    textValue(row, `${prefix}_name`) ??
    (kind === "team" ? textValue(row, "team") : textValue(row, "opponent"));
  const abbr = textValue(row, `${prefix}_abbr`);
  const id = identityId(row[`${prefix}_id`]);

  return resolveTeamIdentity({
    teamId: id,
    teamAbbr: abbr,
    teamName: name,
  });
}

function shortTeamLabel(row: SectionRow, kind: TeamKind): string | null {
  const identity = teamIdentity(row, kind);
  return identity.teamAbbr ?? identity.teamName ?? null;
}

function locationLabel(row: SectionRow): string | null {
  const opponent = shortTeamLabel(row, "opponent");
  if (!opponent) return null;
  if (boolValue(row, "is_home")) return `vs ${opponent}`;
  if (boolValue(row, "is_away")) return `at ${opponent}`;
  return opponent;
}

function resultVariant(wl: string | null): BadgeVariant {
  if (wl?.toUpperCase() === "W") return "win";
  if (wl?.toUpperCase() === "L") return "loss";
  return "neutral";
}

function resultLabel(wl: string | null): string | null {
  if (!wl) return null;
  const normalized = wl.toUpperCase();
  if (normalized === "W" || normalized === "L") return normalized;
  return wl;
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

function statLabel(key: string): string {
  return STAT_LABELS[key] ?? formatColHeader(key);
}

function statValue(row: SectionRow, key: string): number | null {
  if (key === "plus_minus") return numericValue(row, key);
  return numericValue(row, key);
}

function gameStats(row: SectionRow): StatProps[] {
  const stats: StatProps[] = [];

  for (const key of CARD_STATS) {
    const value = statValue(row, key);
    if (value === null) continue;
    stats.push({
      label: statLabel(key),
      value: formatValue(value, key),
      semantic:
        key === "plus_minus"
          ? value >= 0
            ? "win"
            : "loss"
          : stats.length === 0
            ? "accent"
            : "neutral",
    });
  }

  return stats.slice(0, 6);
}

function TeamMark({ row, kind }: { row: SectionRow; kind: TeamKind }) {
  const identity = teamIdentity(row, kind);
  const fallback = kind === "team" ? "Team" : "Opponent";
  const name = identity.teamName ?? identity.teamAbbr ?? fallback;

  return (
    <TeamBadge
      abbreviation={identity.teamAbbr ?? undefined}
      name={name}
      logoUrl={identity.logoUrl}
      size="md"
      className={styles.teamBadge}
      style={(identity.styleVars ?? undefined) as CSSProperties | undefined}
    />
  );
}

function rowKey(row: SectionRow, index: number): string {
  return (
    [textValue(row, "game_id"), textValue(row, "team_abbr"), index]
      .filter(Boolean)
      .join("-") || `${index}`
  );
}

export default function TeamGameCards({ rows }: Props) {
  if (!rows.length) return null;

  return (
    <div className={styles.cardList} aria-label="Team game cards">
      {rows.map((row, index) => {
        const date = textValue(row, "game_date");
        const location = locationLabel(row);
        const result = resultLabel(textValue(row, "wl"));
        const score = scoreText(row);
        const stats = gameStats(row);
        const margin = numericValue(row, "plus_minus");

        return (
          <Card
            as="article"
            className={styles.gameCard}
            depth={index === 0 ? "elevated" : "card"}
            padding="lg"
            key={rowKey(row, index)}
          >
            <div className={styles.metaRow}>
              <div className={styles.metaText}>
                {date && <span>{date}</span>}
                {location && <span>{location}</span>}
              </div>
              {result && (
                <Badge
                  variant={resultVariant(result)}
                  size="sm"
                  uppercase
                  aria-label={`Result ${result}`}
                >
                  {result}
                </Badge>
              )}
            </div>

            <div className={styles.matchupRow}>
              <div className={styles.teamSlot}>
                <TeamMark row={row} kind="team" />
              </div>
              <div className={styles.scoreBlock}>
                <div className={styles.scoreValue}>{score ?? "Game"}</div>
                {margin !== null && (
                  <div className={styles.margin}>
                    {formatValue(margin, "plus_minus")} margin
                  </div>
                )}
              </div>
              <div className={styles.teamSlot}>
                <TeamMark row={row} kind="opponent" />
              </div>
            </div>

            {stats.length > 0 && (
              <StatBlock
                stats={stats}
                columns={stats.length >= 4 ? 4 : stats.length >= 2 ? 2 : 1}
              />
            )}
          </Card>
        );
      })}
    </div>
  );
}
