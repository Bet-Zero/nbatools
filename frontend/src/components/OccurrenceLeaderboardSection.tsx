import type { CSSProperties } from "react";
import type { ResultMetadata, SectionRow } from "../api/types";
import { Avatar, SectionHeader, TeamBadge } from "../design-system";
import { resolvePlayerIdentity, resolveTeamIdentity } from "../lib/identity";
import DataTable from "./DataTable";
import { formatColHeader, formatValue } from "./tableFormatting";
import styles from "./OccurrenceLeaderboardSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
  metadata?: ResultMetadata;
}

const SYSTEM_COLUMNS = new Set([
  "rank",
  "player_id",
  "team_id",
  "player_name",
  "player",
  "team_name",
  "team_abbr",
  "team",
  "entity",
  "name",
  "lineup",
  "lineup_members",
  "members",
  "season",
  "seasons",
  "season_type",
  "games_played",
  "game_id",
  "game_date",
  "start_date",
  "end_date",
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

const CONTEXT_COLUMNS = new Set([
  ...SYSTEM_COLUMNS,
  ...QUALIFIER_COLUMNS.map(([key]) => key),
  "qualified",
]);

const ENTITY_COLUMNS = [
  "player_name",
  "player",
  "team_name",
  "team_abbr",
  "team",
  "entity",
  "name",
  "lineup",
  "lineup_members",
  "members",
];

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

function addContextItem(items: ContextItem[], key: string, text: string | null) {
  if (!text) return;
  if (items.some((item) => item.text === text)) return;
  items.push({ key, text });
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

function seasonLabel(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
): string | null {
  return (
    textValue(row, "seasons") ??
    textValue(row, "season") ??
    metadataText(metadata, "season") ??
    (metadata?.start_season && metadata?.end_season
      ? metadata.start_season === metadata.end_season
        ? metadata.start_season
        : `${metadata.start_season} to ${metadata.end_season}`
      : null)
  );
}

function dateLabel(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
): string | null {
  const start = textValue(row, "start_date") ?? metadataText(metadata, "start_date");
  const end = textValue(row, "end_date") ?? metadataText(metadata, "end_date");
  if (start && end) return `${start} to ${end}`;
  return start ?? end;
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
  return "Occurrence Entry";
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

function rankLabel(row: SectionRow, index: number): string {
  const rank = row.rank;
  if (typeof rank === "number" || typeof rank === "string") {
    return `#${rank}`;
  }
  return `#${index + 1}`;
}

function occurrenceMetricPriority(row: SectionRow, key: string): number {
  if (CONTEXT_COLUMNS.has(key) || !hasValue(row[key])) return -1;

  const lc = key.toLowerCase();
  if (lc.startsWith("games_") && lc !== "games_played") return 100;
  if (lc === "qualifying_games") return 98;
  if (lc.includes("double")) return 96;
  if (lc.includes("occurrence") || lc.includes("count")) return 94;
  if (typeof row[key] === "number") return 80;
  return 10;
}

function occurrenceMetricColumn(row: SectionRow): string | null {
  const metricCandidates = Object.keys(row)
    .map((key, index) => ({
      key,
      index,
      priority: occurrenceMetricPriority(row, key),
    }))
    .filter((candidate) => candidate.priority >= 0)
    .sort((a, b) => b.priority - a.priority || a.index - b.index);

  return metricCandidates[0]?.key ?? null;
}

function occurrenceMetricLabel(metric: string): string {
  return formatColHeader(metric).replace(
    /\b(ast|blk|def|fga|fg3a|fg3m|fgm|fta|ftm|off|pts|reb|stl|tov)\b/gi,
    (stat) => STAT_LABELS[stat.toLowerCase()] ?? stat,
  );
}

function contextItems(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
): ContextItem[] {
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

  addContextItem(items, "season", seasonLabel(row, metadata));
  addContextItem(
    items,
    "season_type",
    textValue(row, "season_type") ?? metadataText(metadata, "season_type"),
  );
  addContextItem(items, "date", dateLabel(row, metadata));

  const team = textValue(row, "team_abbr");
  if (team && hasPlayerIdentity) {
    addContextItem(items, "team_abbr", team);
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

export default function OccurrenceLeaderboardSection({
  sections,
  metadata,
}: Props) {
  const leaderboard = sections.leaderboard;
  if (!leaderboard || leaderboard.length === 0) return null;

  return (
    <div className={styles.section}>
      <SectionHeader
        title="Occurrence Leaderboard"
        count={`${leaderboard.length} entries`}
      />
      <div
        className={styles.rankedList}
        aria-label="Occurrence leaderboard rankings"
      >
        {leaderboard.map((row, index) => {
          const metric = occurrenceMetricColumn(row);
          const identity = rowIdentity(row);
          const context = contextItems(row, metadata);
          const label = identity?.label ?? entityLabel(row);
          const isTopRank = index === 0;

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
                    <div className={styles.entityName}>{label}</div>
                    {context.length > 0 && (
                      <div
                        className={styles.context}
                        aria-label={`${label} occurrence context`}
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
                  <div className={styles.metricEyebrow}>Event Count</div>
                  <div className={styles.metricValue}>
                    {formatValue(row[metric], metric)}
                  </div>
                  <div className={styles.metricLabel}>
                    {occurrenceMetricLabel(metric)}
                  </div>
                </div>
              )}
            </article>
          );
        })}
      </div>
      <div className={styles.detailSection}>
        <SectionHeader title="Full Occurrence Detail" />
        <DataTable rows={leaderboard} highlight hiddenColumns={SYSTEM_COLUMNS} />
      </div>
    </div>
  );
}
