import { type CSSProperties } from "react";
import type { SectionRow } from "../api/types";
import { Avatar, SectionHeader, TeamBadge } from "../design-system";
import { resolvePlayerIdentity, resolveTeamIdentity } from "../lib/identity";
import RawDetailToggle from "./RawDetailToggle";
import { formatColHeader, formatValue } from "./tableFormatting";
import styles from "./LeaderboardSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
  title?: string;
  detailTitle?: string;
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
  "team",
  "lineup",
  "lineup_members",
  "members",
  "entity",
  "name",
];

const CONTEXT_COLUMNS = new Set([
  ...SYSTEM_COLUMNS,
  ...ENTITY_COLUMNS,
  "games_played",
  "min_games",
  "min_value",
  "max_value",
  "qualifier",
  "qualification",
  "qualified",
  "sample_size",
  "threshold",
]);

const QUALIFIER_COLUMNS = [
  ["min_games", "Min games"],
  ["min_value", "Min"],
  ["max_value", "Max"],
  ["threshold", "Threshold"],
  ["qualifier", null],
  ["qualification", null],
  ["sample_size", "Sample"],
] as const;

const DIRECT_STAT_COLUMNS = new Set([
  "pts",
  "reb",
  "ast",
  "stl",
  "blk",
  "tov",
  "fgm",
  "fga",
  "fg3m",
  "fg3a",
  "ftm",
  "fta",
  "minutes",
  "wins",
  "losses",
  "off_rating",
  "def_rating",
  "net_rating",
  "pace",
]);

const STAT_LABELS: Record<string, string> = {
  ast: "AST",
  blk: "BLK",
  def: "DEF",
  fga: "FGA",
  fg3a: "FG3A",
  fg3m: "FG3M",
  fgm: "FGM",
  fta: "FTA",
  ftm: "FTM",
  off: "OFF",
  pts: "PTS",
  reb: "REB",
  stl: "STL",
  tov: "TOV",
};

interface ContextItem {
  key: string;
  text: string;
}

const PERCENTAGE_COMPANION_COLUMNS: Record<string, string[]> = {
  win_pct: ["wins", "losses"],
  fg_pct: ["fgm", "fga"],
  fg3_pct: ["fg3m", "fg3a"],
  ft_pct: ["ftm", "fta"],
};

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

function percentageCompanionColumns(metric: string, row: SectionRow): string[] {
  const lc = metric.toLowerCase();
  const explicitColumns = PERCENTAGE_COMPANION_COLUMNS[lc];
  if (explicitColumns) {
    return explicitColumns.filter((key) => hasValue(row[key]));
  }

  if (!lc.endsWith("_pct")) return [];

  const base = lc.slice(0, -4);
  const genericColumns = [`${base}m`, `${base}a`];
  return genericColumns.filter((key) => hasValue(row[key]));
}

function metricCompanionItems(
  row: SectionRow,
  metric: string | null,
): ContextItem[] {
  if (!metric) return [];

  const companionColumns = percentageCompanionColumns(metric, row);
  if (companionColumns.length === 0) return [];

  if (
    metric.toLowerCase() === "win_pct" &&
    companionColumns.includes("wins") &&
    companionColumns.includes("losses")
  ) {
    return [
      {
        key: "record",
        text: `${formatValue(row.wins, "wins")}-${formatValue(row.losses, "losses")}`,
      },
    ];
  }

  if (companionColumns.length === 2 && companionColumns[0].endsWith("m") && companionColumns[1].endsWith("a")) {
    return [
      {
        key: `${companionColumns[0]}_${companionColumns[1]}`,
        text: `${formatValue(row[companionColumns[0]], companionColumns[0])}/${formatValue(
          row[companionColumns[1]],
          companionColumns[1],
        )} ${formatColHeader(metric).replace(/\s*Pct$/i, "")}`,
      },
    ];
  }

  return companionColumns.map((key) => ({
    key,
    text: `${formatValue(row[key], key)} ${metricLabel(key)}`,
  }));
}

function addContextItem(items: ContextItem[], key: string, text: string | null) {
  if (!text) return;
  if (items.some((item) => item.text === text)) return;
  items.push({ key, text });
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

function metricPriority(row: SectionRow, key: string): number {
  if (!hasValue(row[key])) return -1;

  const lc = key.toLowerCase();
  if (lc.startsWith("games_") && lc !== "games_played") return 100;
  if (lc.endsWith("_per_game")) return 95;
  if (lc.endsWith("_pct") || lc.includes("pct")) return 90;
  if (DIRECT_STAT_COLUMNS.has(lc)) return 85;
  if (typeof row[key] === "number") return 80;
  return 10;
}

function metricColumn(row: SectionRow): string | null {
  const columns = Object.keys(row);
  const metricCandidates = columns
    .map((key, index) => ({
      key,
      index,
      priority: CONTEXT_COLUMNS.has(key) ? -1 : metricPriority(row, key),
    }))
    .filter((candidate) => candidate.priority >= 0)
    .sort(
      (a, b) => b.priority - a.priority || a.index - b.index,
    );

  return (
    metricCandidates[0]?.key ??
    (hasValue(row.games_played) ? "games_played" : null)
  );
}

function metricLabel(metric: string): string {
  return formatColHeader(metric).replace(
    /\b(ast|blk|def|fga|fg3a|fg3m|fgm|fta|ftm|off|pts|reb|stl|tov)\b/gi,
    (stat) => STAT_LABELS[stat.toLowerCase()] ?? stat,
  );
}

function contextItems(row: SectionRow, metric: string | null): ContextItem[] {
  const items: ContextItem[] = [];
  const hasPlayerIdentity = Boolean(
    textValue(row, "player_name") ?? textValue(row, "player"),
  );

  if (hasValue(row.games_played)) {
    addContextItem(
      items,
      "games_played",
      `${formatValue(row.games_played, "games_played")} games`,
    );
  }

  const season = textValue(row, "seasons") ?? textValue(row, "season");
  addContextItem(items, "season", season);

  const seasonType = textValue(row, "season_type");
  addContextItem(items, "season_type", seasonType);

  const team = textValue(row, "team_abbr");
  if (team && (hasPlayerIdentity || textValue(row, "team_name"))) {
    addContextItem(items, "team_abbr", team);
  }

  const gameDate = textValue(row, "game_date");
  addContextItem(items, "game_date", gameDate);

  const opponent =
    textValue(row, "opponent_team_abbr") ??
    textValue(row, "opponent_team_name");
  if (opponent) {
    const prefix = row.is_away === true ? "at" : "vs";
    addContextItem(items, "opponent", `${prefix} ${opponent}`);
  }

  const result = textValue(row, "wl");
  if (result) addContextItem(items, "wl", result.toUpperCase());

  for (const item of metricCompanionItems(row, metric)) {
    addContextItem(items, item.key, item.text);
  }

  for (const [key, label] of QUALIFIER_COLUMNS) {
    if (!hasValue(row[key])) continue;
    const formatted = formatValue(row[key], key);
    addContextItem(items, key, label ? `${label} ${formatted}` : formatted);
  }

  if (typeof row.qualified === "boolean") {
    addContextItem(items, "qualified", row.qualified ? "Qualified" : null);
  }

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

export default function LeaderboardSection({
  sections,
  title = "Leaderboard",
  detailTitle = "Full Leaderboard",
}: Props) {
  const leaderboard = sections.leaderboard;
  if (!leaderboard || leaderboard.length === 0) return null;

  return (
    <div className={styles.section}>
      <SectionHeader
        title={title}
        count={`${leaderboard.length} entries`}
      />
      <div className={styles.rankedList} aria-label="Ranked leaderboard">
        {leaderboard.map((row, index) => {
          const metric = metricColumn(row);
          const context = contextItems(row, metric);
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
                      <div
                        className={styles.context}
                        aria-label={`${identity?.label ?? entityLabel(row)} context`}
                      >
                        {context.map((item) => (
                          <span className={styles.contextItem} key={item.key}>
                            {item.text}
                          </span>
                        ))}
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
                    {metricLabel(metric)}
                  </div>
                </div>
              )}
            </article>
          );
        })}
      </div>
      <RawDetailToggle
        title={detailTitle}
        rows={leaderboard}
        highlight
        hiddenColumns={SYSTEM_COLUMNS}
      />
    </div>
  );
}
