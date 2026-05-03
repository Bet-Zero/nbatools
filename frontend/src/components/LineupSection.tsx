import type { CSSProperties } from "react";
import type { ResultMetadata, SectionRow } from "../api/types";
import {
  Avatar,
  Card,
  SectionHeader,
  StatBlock,
  TeamBadge,
  type StatProps,
} from "../design-system";
import { resolvePlayerIdentity, resolveTeamIdentity } from "../lib/identity";
import RawDetailToggle from "./RawDetailToggle";
import { formatColHeader, formatValue } from "./tableFormatting";
import styles from "./LineupSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
  metadata?: ResultMetadata;
  mode: "summary" | "leaderboard";
}

const SUMMARY_STATS: Array<{
  key: string;
  label: string;
  signed?: boolean;
}> = [
  { key: "games", label: "Games" },
  { key: "gp", label: "GP" },
  { key: "minutes", label: "MIN" },
  { key: "possessions", label: "Poss" },
  { key: "off_rating", label: "ORtg" },
  { key: "def_rating", label: "DRtg" },
  { key: "net_rating", label: "Net", signed: true },
  { key: "pace", label: "Pace" },
  { key: "plus_minus", label: "+/-", signed: true },
  { key: "ts_pct", label: "TS%" },
  { key: "efg_pct", label: "eFG%" },
  { key: "oreb_pct", label: "OREB%" },
  { key: "dreb_pct", label: "DREB%" },
  { key: "reb_pct", label: "REB%" },
];

const METRIC_LABELS: Record<string, string> = {
  def_rating: "Def rating",
  efg_pct: "eFG%",
  minutes: "Minutes",
  net_rating: "Net rating",
  off_rating: "Off rating",
  pace: "Pace",
  plus_minus: "Plus-minus",
  possessions: "Possessions",
  ts_pct: "TS%",
};

const SIGNED_METRICS = new Set(["net_rating", "plus_minus"]);

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

function splitList(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value
      .map((item) => String(item).trim())
      .filter((item) => Boolean(item));
  }
  if (typeof value !== "string") return [];

  const trimmed = value.trim();
  if (!trimmed) return [];
  const separator = trimmed.includes("|")
    ? "|"
    : trimmed.includes(" - ")
      ? " - "
      : trimmed.includes(",")
        ? ","
        : null;

  return separator
    ? trimmed
        .split(separator)
        .map((item) => item.trim())
        .filter((item) => Boolean(item))
    : [trimmed];
}

function lineupMembers(
  row: SectionRow | undefined,
  metadata: ResultMetadata | undefined,
): string[] {
  const rowMembers =
    splitList(row?.player_names).length > 0
      ? splitList(row?.player_names)
      : splitList(row?.lineup_members).length > 0
        ? splitList(row?.lineup_members)
        : splitList(row?.members).length > 0
          ? splitList(row?.members)
          : splitList(row?.lineup_name);
  if (rowMembers.length > 0) return rowMembers;
  return splitList(metadata?.lineup_members);
}

function lineupPlayerIds(row: SectionRow | undefined): Array<string | null> {
  return splitList(row?.player_ids).map((value) => value || null);
}

function lineupName(
  row: SectionRow | undefined,
  metadata: ResultMetadata | undefined,
): string {
  const members = lineupMembers(row, metadata);
  if (members.length > 0) return members.join(" / ");
  return textValue(row, "lineup_name") ?? textValue(row, "lineup") ?? "Lineup";
}

function teamIdentity(
  row: SectionRow | undefined,
  metadata: ResultMetadata | undefined,
) {
  const teamAbbr =
    metadata?.team_context?.team_abbr ??
    textValue(row, "team_abbr") ??
    textValue(row, "team");
  const teamName =
    metadata?.team_context?.team_name ??
    metadata?.team ??
    textValue(row, "team_name") ??
    teamAbbr ??
    "Team";

  return resolveTeamIdentity({
    teamId: metadata?.team_context?.team_id ?? identityId(row?.team_id),
    teamAbbr,
    teamName,
  });
}

function seasonLabel(
  row: SectionRow | undefined,
  metadata: ResultMetadata | undefined,
): string | null {
  if (metadata?.season) return metadata.season;
  const start = metadata?.start_season ?? textValue(row, "season") ?? null;
  const end = metadata?.end_season ?? null;
  if (start && end && start !== end) return `${start} to ${end}`;
  return start ?? end;
}

function unitSize(
  row: SectionRow | undefined,
  metadata: ResultMetadata | undefined,
): number | null {
  return numericValue(row, "unit_size") ?? metadataNumber(metadata, "unit_size");
}

function minuteMinimum(
  row: SectionRow | undefined,
  metadata: ResultMetadata | undefined,
): number | null {
  return (
    numericValue(row, "minute_minimum") ??
    metadataNumber(metadata, "minute_minimum")
  );
}

function formatMinuteMinimum(value: number | null): string | null {
  if (value === null) return null;
  if (value <= 0) return "No minute minimum";
  return `Min ${formatValue(value, "minute_minimum")} minutes`;
}

function contextItems(
  row: SectionRow | undefined,
  metadata: ResultMetadata | undefined,
): string[] {
  const size = unitSize(row, metadata);
  const minimum = minuteMinimum(row, metadata);

  return [
    size !== null ? `${formatValue(size, "unit_size")}-man` : null,
    seasonLabel(row, metadata),
    metadata?.season_type ?? textValue(row, "season_type"),
    formatMinuteMinimum(minimum),
  ].filter((item): item is string => Boolean(item));
}

function formatSignedValue(value: number, key: string): string {
  const formatted = formatValue(value, key);
  return value > 0 ? `+${formatted}` : formatted;
}

function displayValue(value: unknown, key: string): string {
  if (typeof value === "number" && SIGNED_METRICS.has(key)) {
    return formatSignedValue(value, key);
  }
  return formatValue(value, key);
}

function summaryStats(row: SectionRow): StatProps[] {
  const seenLabels = new Set<string>();
  const stats: StatProps[] = [];

  for (const { key, label, signed = false } of SUMMARY_STATS) {
    if (!hasValue(row[key]) || seenLabels.has(label)) continue;
    seenLabels.add(label);
    const numeric = numericValue(row, key);

    stats.push({
      label,
      value:
        signed && numeric !== null
          ? formatSignedValue(numeric, key)
          : formatValue(row[key], key),
      semantic:
        numeric !== null && (key === "net_rating" || key === "plus_minus")
          ? numeric >= 0
            ? "win"
            : "loss"
          : stats.length === 0
            ? "accent"
            : "neutral",
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

function metricLabel(metric: string): string {
  return METRIC_LABELS[metric] ?? formatColHeader(metric);
}

function requestedMetric(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
): string | null {
  const requested = metadataText(metadata, "stat");
  if (requested && hasValue(row[requested])) return requested;

  for (const key of [
    "net_rating",
    "plus_minus",
    "off_rating",
    "def_rating",
    "minutes",
    "pace",
    "ts_pct",
  ]) {
    if (hasValue(row[key])) return key;
  }

  return null;
}

function sampleItems(row: SectionRow): string[] {
  return [
    hasValue(row.games) ? `${formatValue(row.games, "games")} games` : null,
    hasValue(row.gp) ? `${formatValue(row.gp, "gp")} GP` : null,
    hasValue(row.minutes) ? `${formatValue(row.minutes, "minutes")} minutes` : null,
    hasValue(row.possessions)
      ? `${formatValue(row.possessions, "possessions")} possessions`
      : null,
  ].filter((item): item is string => Boolean(item));
}

function rankLabel(row: SectionRow, index: number): string {
  const rank = row.rank;
  if (typeof rank === "number" || typeof rank === "string") return `#${rank}`;
  return `#${index + 1}`;
}

function rowKey(row: SectionRow, metadata: ResultMetadata | undefined, index: number) {
  return `${rankLabel(row, index)}-${lineupName(row, metadata)}-${index}`;
}

function MemberChips({
  members,
  playerIds,
}: {
  members: string[];
  playerIds?: Array<string | null>;
}) {
  if (members.length === 0) return null;

  return (
    <div className={styles.memberList} aria-label="Lineup members">
      {members.map((member, index) => {
        const player = resolvePlayerIdentity({
          playerId: playerIds?.[index] ?? null,
          playerName: member,
        });
        return (
          <span className={styles.memberChip} key={`${member}-${index}`}>
            <Avatar
              name={player.playerName ?? member}
              imageUrl={player.headshotUrl}
              size="sm"
              className={styles.memberAvatar}
            />
            <span className={styles.memberName}>{player.playerName ?? member}</span>
          </span>
        );
      })}
    </div>
  );
}

function SummaryDisplay({
  row,
  metadata,
}: {
  row: SectionRow;
  metadata?: ResultMetadata;
}) {
  const team = teamIdentity(row, metadata);
  const teamName = team.teamName ?? team.teamAbbr ?? "Team";
  const members = lineupMembers(row, metadata);
  const playerIds = lineupPlayerIds(row);
  const context = contextItems(row, metadata);
  const stats = summaryStats(row);

  return (
    <Card
      className={styles.heroCard}
      depth="elevated"
      padding="lg"
      style={(team.styleVars ?? undefined) as CSSProperties | undefined}
    >
      <div className={styles.heroHeader}>
        <TeamBadge
          abbreviation={team.teamAbbr ?? undefined}
          name={teamName}
          logoUrl={team.logoUrl}
          size="md"
          className={styles.teamBadge}
          style={(team.styleVars ?? undefined) as CSSProperties | undefined}
        />
        <div className={styles.heroText}>
          <div className={styles.eyebrow}>Lineup Summary</div>
          <h2 className={styles.lineupTitle}>{lineupName(row, metadata)}</h2>
          {context.length > 0 && (
            <div className={styles.context} aria-label="Lineup context">
              {context.map((item) => (
                <span className={styles.contextChip} key={item}>
                  {item}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
      <MemberChips members={members} playerIds={playerIds} />
      {stats.length > 0 && (
        <StatBlock stats={stats} columns={statColumns(stats.length)} />
      )}
    </Card>
  );
}

function LeaderboardDisplay({
  rows,
  metadata,
}: {
  rows: SectionRow[];
  metadata?: ResultMetadata;
}) {
  return (
    <div className={styles.rankedList} aria-label="Ranked lineups">
      {rows.map((row, index) => {
        const team = teamIdentity(row, metadata);
        const teamName = team.teamName ?? team.teamAbbr ?? "Team";
        const members = lineupMembers(row, metadata);
        const playerIds = lineupPlayerIds(row);
        const metric = requestedMetric(row, metadata);
        const context = [...contextItems(row, metadata), ...sampleItems(row)];

        return (
          <article
            className={`${styles.rankedRow} ${
              index === 0 ? styles.topRankedRow : ""
            }`}
            key={rowKey(row, metadata, index)}
          >
            <div className={styles.rank}>{rankLabel(row, index)}</div>
            <div className={styles.lineupBlock}>
              <div className={styles.lineupIdentity}>
                <TeamBadge
                  abbreviation={team.teamAbbr ?? undefined}
                  name={teamName}
                  logoUrl={team.logoUrl}
                  size="md"
                  showName={false}
                  className={styles.teamMark}
                  style={(team.styleVars ?? undefined) as
                    | CSSProperties
                    | undefined}
                />
                <div className={styles.lineupText}>
                  <div className={styles.lineupName}>
                    {lineupName(row, metadata)}
                  </div>
                  {context.length > 0 && (
                    <div
                      className={styles.context}
                      aria-label={`${lineupName(row, metadata)} context`}
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
              <MemberChips members={members} playerIds={playerIds} />
            </div>
            {metric && (
              <div className={styles.metricBlock}>
                <div className={styles.metricValue}>
                  {displayValue(row[metric], metric)}
                </div>
                <div className={styles.metricLabel}>{metricLabel(metric)}</div>
              </div>
            )}
          </article>
        );
      })}
    </div>
  );
}

export default function LineupSection({ sections, metadata, mode }: Props) {
  const summary = sections.summary;
  const leaderboard = sections.leaderboard;

  if (mode === "summary") {
    const row = summary?.[0];
    return (
      <>
        <div className={styles.section}>
          <SectionHeader title="Lineup Summary" />
          {row && <SummaryDisplay row={row} metadata={metadata} />}
        </div>
        {summary && summary.length > 0 && (
          <div className={styles.section}>
            <RawDetailToggle title="Lineup Detail" rows={summary} />
          </div>
        )}
      </>
    );
  }

  if (!leaderboard || leaderboard.length === 0) return null;

  return (
    <div className={styles.section}>
      <SectionHeader
        title="Lineup Leaderboard"
        count={`${leaderboard.length} lineups`}
      />
      <LeaderboardDisplay rows={leaderboard} metadata={metadata} />
      <RawDetailToggle title="Lineup Leaderboard Detail" rows={leaderboard} />
    </div>
  );
}
