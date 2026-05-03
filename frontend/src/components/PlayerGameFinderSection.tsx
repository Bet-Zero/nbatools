import type { CSSProperties } from "react";
import type { ResultMetadata, SectionRow } from "../api/types";
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
import RawDetailToggle from "./RawDetailToggle";
import { formatColHeader, formatValue } from "./tableFormatting";
import styles from "./PlayerGameFinderSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
  metadata?: ResultMetadata;
}

const STAT_LABELS: Record<string, string> = {
  ast: "AST",
  blk: "BLK",
  efg: "eFG",
  fga: "FGA",
  fg3a: "3PA",
  fg3m: "3PM",
  fgm: "FGM",
  fta: "FTA",
  ftm: "FTM",
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
  "fgm",
  "fga",
  "fg3m",
  "fg3a",
  "ftm",
  "fta",
  "stl",
  "blk",
  "tov",
  "plus_minus",
  "clutch_events",
  "clutch_seconds",
]);

const STAT_ALIASES: Record<string, string> = {
  "3pm": "fg3m",
  "3p": "fg3m",
  assists: "ast",
  ast: "ast",
  blocks: "blk",
  blk: "blk",
  points: "pts",
  pts: "pts",
  rebounds: "reb",
  reb: "reb",
  scoring: "pts",
  steals: "stl",
  stl: "stl",
  threes: "fg3m",
  turnovers: "tov",
  tov: "tov",
};

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

function headerPlayerIdentity(
  metadata: ResultMetadata | undefined,
  row: SectionRow,
) {
  return resolvePlayerIdentity({
    playerId:
      metadata?.player_context?.player_id ?? identityId(row.player_id),
    playerName:
      metadata?.player_context?.player_name ??
      textValue(row, "player_name") ??
      textValue(row, "player") ??
      "Player",
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
    /\b(ast|blk|efg|fga|fg3a|fg3m|fgm|fta|ftm|pts|reb|stl|tov|ts|usg)\b/gi,
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

function madeAttemptLabel(
  row: SectionRow,
  madeKey: string,
  attemptKey: string,
  label: string,
): string | null {
  const made = numericValue(row, madeKey);
  const attempts = numericValue(row, attemptKey);
  if (made === null || attempts === null) return null;
  return `${label} ${formatValue(made, madeKey)}/${formatValue(
    attempts,
    attemptKey,
  )}`;
}

function signedValue(value: number, key: string): string {
  const formatted = formatValue(value, key);
  return value > 0 ? `+${formatted}` : formatted;
}

function secondaryStats(row: SectionRow): string[] {
  const context: string[] = [];
  const minutes = numericValue(row, "minutes");
  const plusMinus = numericValue(row, "plus_minus");
  const fg = madeAttemptLabel(row, "fgm", "fga", "FG");
  const threes = madeAttemptLabel(row, "fg3m", "fg3a", "3P");
  const freeThrows = madeAttemptLabel(row, "ftm", "fta", "FT");

  if (minutes !== null) context.push(`MIN ${formatValue(minutes, "minutes")}`);
  for (const item of [fg, threes, freeThrows]) {
    if (item) context.push(item);
  }
  for (const key of ["stl", "blk", "tov"]) {
    const value = numericValue(row, key);
    if (value !== null) context.push(`${statLabel(key)} ${formatValue(value, key)}`);
  }
  if (plusMinus !== null) {
    context.push(`+/- ${signedValue(plusMinus, "plus_minus")}`);
  }

  return context;
}

function secondaryContext(row: SectionRow): string[] {
  const context = [
    textValue(row, "season"),
    textValue(row, "season_type"),
  ];
  const clutchEvents = numericValue(row, "clutch_events");
  const clutchSeconds = numericValue(row, "clutch_seconds");

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

function metadataText(
  metadata: ResultMetadata | undefined,
  key: string,
): string | null {
  const value = metadata?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function metadataNumber(
  metadata: ResultMetadata | undefined,
  key: string,
): number | null {
  const value = metadata?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function normalizeStatKey(value: string | null): string | null {
  if (!value) return null;
  const normalized = value.toLowerCase().replace(/[_\s-]+/g, " ").trim();
  return STAT_ALIASES[normalized] ?? value.toLowerCase();
}

function formatCondition(stat: string, min: number | null, max: number | null): string {
  const label = statLabel(normalizeStatKey(stat) ?? stat);
  if (min !== null && max !== null) {
    return `${formatValue(min, stat)}-${formatValue(max, stat)} ${label}`;
  }
  if (min !== null) return `${formatValue(min, stat)}+ ${label}`;
  if (max !== null) return `<= ${formatValue(max, stat)} ${label}`;
  return label;
}

function thresholdConditionsFromMetadata(
  metadata: ResultMetadata | undefined,
): string[] {
  const conditions: string[] = [];
  for (const key of ["threshold_conditions", "extra_conditions"]) {
    const raw = metadata?.[key];
    if (!Array.isArray(raw)) continue;
    for (const condition of raw) {
      if (!condition || typeof condition !== "object") continue;
      const statValue = (condition as Record<string, unknown>).stat;
      if (typeof statValue !== "string") continue;
      const minValue = (condition as Record<string, unknown>).min_value;
      const maxValue = (condition as Record<string, unknown>).max_value;
      conditions.push(
        formatCondition(
          statValue,
          typeof minValue === "number" ? minValue : null,
          typeof maxValue === "number" ? maxValue : null,
        ),
      );
    }
  }

  const occurrenceEvent = metadata?.occurrence_event;
  if (
    conditions.length === 0 &&
    occurrenceEvent &&
    typeof occurrenceEvent === "object" &&
    !Array.isArray(occurrenceEvent)
  ) {
    const event = occurrenceEvent as Record<string, unknown>;
    if (typeof event.stat === "string") {
      const minValue =
        typeof event.min_value === "number" ? event.min_value : null;
      if (event.stat === "pts" && minValue !== null) {
        conditions.push(`${formatValue(minValue, "pts")}-point games`);
      } else {
        conditions.push(
          formatCondition(
            event.stat,
            minValue,
            typeof event.max_value === "number" ? event.max_value : null,
          ),
        );
      }
    }
  }

  const stat = metadataText(metadata, "stat");
  if (stat && conditions.length === 0) {
    conditions.push(
      formatCondition(
        stat,
        metadataNumber(metadata, "min_value"),
        metadataNumber(metadata, "max_value"),
      ),
    );
  }

  return Array.from(new Set(conditions));
}

function finderCondition(metadata: ResultMetadata | undefined): string {
  const metadataConditions = thresholdConditionsFromMetadata(metadata);
  if (metadataConditions.length > 0) return metadataConditions.join(", ");
  return "Matching games";
}

function sortMetric(metadata: ResultMetadata | undefined): string | null {
  const metadataStat = normalizeStatKey(metadataText(metadata, "stat"));
  if (
    metadataText(metadata, "sort_by") === "stat" &&
    metadata?.ranked_intent === true &&
    metadataStat
  ) {
    return metadataStat;
  }
  return null;
}

function sortFinderRows(
  rows: SectionRow[],
  metadata: ResultMetadata | undefined,
): SectionRow[] {
  const metric = sortMetric(metadata);
  const copy = [...rows];
  if (metric) {
    return copy.sort((a, b) => {
      const aValue = numericValue(a, metric) ?? Number.NEGATIVE_INFINITY;
      const bValue = numericValue(b, metric) ?? Number.NEGATIVE_INFINITY;
      if (bValue !== aValue) return bValue - aValue;
      return String(gameDate(b) ?? "").localeCompare(String(gameDate(a) ?? ""));
    });
  }
  return copy.sort((a, b) => {
    const dateCompare = String(gameDate(b) ?? "").localeCompare(
      String(gameDate(a) ?? ""),
    );
    if (dateCompare !== 0) return dateCompare;
    return String(textValue(b, "game_id") ?? "").localeCompare(
      String(textValue(a, "game_id") ?? ""),
    );
  });
}

function scoreLabel(row: SectionRow): string | null {
  const teamScore =
    numericValue(row, "team_score") ??
    numericValue(row, "pts_team") ??
    numericValue(row, "team_pts");
  const opponentScore =
    numericValue(row, "opponent_score") ??
    numericValue(row, "opp_pts") ??
    numericValue(row, "opponent_pts");
  if (teamScore === null || opponentScore === null) return null;
  return `${formatValue(teamScore, "team_score")}-${formatValue(
    opponentScore,
    "opponent_score",
  )}`;
}

function statColumns(count: number): 1 | 2 | 3 | 4 {
  if (count >= 4) return 4;
  if (count === 3) return 3;
  if (count === 2) return 2;
  return 1;
}

export default function PlayerGameFinderSection({ sections, metadata }: Props) {
  const finder = sections.finder;
  if (!finder || finder.length === 0) return null;
  const displayRows = sortFinderRows(finder, metadata);
  const headerPlayer = headerPlayerIdentity(metadata, displayRows[0]);
  const condition = finderCondition(metadata);
  const countText = `${displayRows.length} game${displayRows.length !== 1 ? "s" : ""} found`;

  return (
    <div className={styles.section}>
      <SectionHeader
        title="Player Games"
        count={countText}
      />
      <Card className={styles.finderHeader} depth="card" padding="md">
        <Avatar
          className={styles.headerAvatar}
          name={headerPlayer.playerName ?? "Player"}
          imageUrl={headerPlayer.headshotUrl}
          size="md"
        />
        <div className={styles.finderHeaderText}>
          <div className={styles.eyebrow}>{condition}</div>
          <h2 className={styles.finderTitle}>
            {headerPlayer.playerName ?? "Player"}
          </h2>
          <div className={styles.headerMeta}>
            <span className={styles.contextChip}>{countText}</span>
          </div>
        </div>
      </Card>
      <div className={styles.gameGrid} aria-label="Player game cards">
        {displayRows.map((row, index) => {
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
          const secondary = secondaryStats(row);
          const score = scoreLabel(row);

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
                      className={styles.contextBadge}
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

              {score && <div className={styles.scoreLabel}>{score}</div>}

              {context.length > 0 && (
                <div className={styles.secondaryContext}>
                  {context.map((item) => (
                    <span className={styles.contextChip} key={item}>
                      {item}
                    </span>
                  ))}
                </div>
              )}

              {secondary.length > 0 && (
                <div
                  className={styles.secondaryStats}
                  aria-label={`${player.playerName ?? `Player ${index + 1}`} secondary stats`}
                >
                  {secondary.map((item) => (
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
      <RawDetailToggle title="Player Game Detail" rows={displayRows} />
    </div>
  );
}
