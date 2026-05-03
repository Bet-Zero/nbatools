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
import {
  resolvePlayerIdentity,
  resolveTeamIdentity,
} from "../lib/identity";
import RawDetailToggle from "./RawDetailToggle";
import { formatValue } from "./tableFormatting";
import styles from "./PlayerOnOffSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
  metadata?: ResultMetadata;
}

type PresenceState = "on" | "off";

const ON_OFF_STATS: Array<{
  key: string;
  label: string;
  signed?: boolean;
}> = [
  { key: "gp", label: "GP" },
  { key: "minutes", label: "MIN" },
  { key: "possessions", label: "Poss" },
  { key: "off_rating", label: "ORtg" },
  { key: "def_rating", label: "DRtg" },
  { key: "net_rating", label: "Net", signed: true },
  { key: "pace", label: "Pace" },
  { key: "plus_minus", label: "+/-", signed: true },
  { key: "pts_avg", label: "PTS" },
  { key: "reb_avg", label: "REB" },
  { key: "ast_avg", label: "AST" },
  { key: "fg3m_avg", label: "3PM" },
  { key: "efg_pct_avg", label: "eFG%" },
  { key: "ts_pct_avg", label: "TS%" },
  { key: "pts", label: "PTS" },
  { key: "reb", label: "REB" },
  { key: "ast", label: "AST" },
  { key: "fg3m", label: "3PM" },
  { key: "efg_pct", label: "eFG%" },
  { key: "ts_pct", label: "TS%" },
];

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

function playerName(
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
): string {
  return (
    metadata?.player_context?.player_name ??
    metadata?.player ??
    textValue(row, "player_name") ??
    textValue(row, "player") ??
    "Player"
  );
}

function playerIdentity(
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
) {
  const name = playerName(metadata, row);
  return resolvePlayerIdentity({
    playerId: metadata?.player_context?.player_id ?? identityId(row?.player_id),
    playerName: name,
  });
}

function teamIdentity(
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
) {
  const name =
    metadata?.team_context?.team_name ??
    metadata?.team ??
    textValue(row, "team_name") ??
    textValue(row, "team") ??
    textValue(row, "team_abbr") ??
    "Team";

  return resolveTeamIdentity({
    teamId: metadata?.team_context?.team_id ?? identityId(row?.team_id),
    teamAbbr:
      metadata?.team_context?.team_abbr ??
      textValue(row, "team_abbr") ??
      textValue(row, "team"),
    teamName: name,
  });
}

function seasonLabel(
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
): string | null {
  if (metadata?.season) return metadata.season;
  const start = metadata?.start_season ?? textValue(row, "season") ?? null;
  const end = metadata?.end_season ?? null;
  if (start && end && start !== end) return `${start} to ${end}`;
  return start ?? end;
}

function contextItems(
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
): string[] {
  return [
    seasonLabel(metadata, row),
    metadata?.season_type ?? textValue(row, "season_type"),
    metadataText(metadata, "presence_state"),
  ].filter((item): item is string => Boolean(item));
}

function presenceState(row: SectionRow): PresenceState | null {
  const state = textValue(row, "presence_state")?.toLowerCase();
  if (state === "on" || state === "off") return state;
  return null;
}

function formatSignedValue(value: number, key: string): string {
  const formatted = formatValue(value, key);
  return value > 0 ? `+${formatted}` : formatted;
}

function statValue(row: SectionRow, key: string, signed: boolean): string {
  const value = numericValue(row, key);
  if (value === null) return formatValue(row[key], key);
  return signed ? formatSignedValue(value, key) : formatValue(value, key);
}

function splitStats(row: SectionRow): StatProps[] {
  const seenLabels = new Set<string>();
  const stats: StatProps[] = [];

  for (const { key, label, signed = false } of ON_OFF_STATS) {
    const value = row[key];
    if (value === null || value === undefined || seenLabels.has(label)) continue;
    seenLabels.add(label);

    const numeric = numericValue(row, key);
    stats.push({
      label,
      value: statValue(row, key, signed),
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

function splitLabel(state: PresenceState): string {
  return state === "on" ? "On" : "Off";
}

function splitRow(
  rows: SectionRow[] | undefined,
  state: PresenceState,
): SectionRow | null {
  return rows?.find((row) => presenceState(row) === state) ?? null;
}

function impactMetric(
  onRow: SectionRow | null,
  offRow: SectionRow | null,
): { metric: string; label: string; diff: number } | null {
  if (!onRow || !offRow) return null;

  const netOn = numericValue(onRow, "net_rating");
  const netOff = numericValue(offRow, "net_rating");
  if (netOn !== null && netOff !== null) {
    return { metric: "net_rating", label: "net rating", diff: netOn - netOff };
  }

  const plusMinusOn = numericValue(onRow, "plus_minus");
  const plusMinusOff = numericValue(offRow, "plus_minus");
  if (plusMinusOn !== null && plusMinusOff !== null) {
    return {
      metric: "plus_minus",
      label: "plus-minus",
      diff: plusMinusOn - plusMinusOff,
    };
  }

  return null;
}

function impactLabel(
  onRow: SectionRow | null,
  offRow: SectionRow | null,
): string | null {
  const impact = impactMetric(onRow, offRow);
  if (!impact) return null;

  if (impact.diff === 0) return `Even ${impact.label}`;
  const side = impact.diff > 0 ? "On" : "Off";
  return `${side} +${formatValue(Math.abs(impact.diff), impact.metric)} ${impact.label}`;
}

function orderedRows(rows: SectionRow[] | undefined): SectionRow[] {
  if (!rows) return [];
  const onRow = splitRow(rows, "on");
  const offRow = splitRow(rows, "off");
  const known = [onRow, offRow].filter((row): row is SectionRow => Boolean(row));
  const unknown = rows.filter((row) => !presenceState(row));
  return [...known, ...unknown];
}

export default function PlayerOnOffSection({ sections, metadata }: Props) {
  const summary = sections.summary;
  const rows = orderedRows(summary);
  const primaryRow = rows[0] ?? summary?.[0];
  const player = playerIdentity(metadata, primaryRow);
  const team = teamIdentity(metadata, primaryRow);
  const playerDisplayName = player.playerName ?? playerName(metadata, primaryRow);
  const teamDisplayName = team.teamName ?? team.teamAbbr ?? "Team";
  const context = contextItems(metadata, primaryRow);
  const onRow = splitRow(summary, "on");
  const offRow = splitRow(summary, "off");
  const impact = impactLabel(onRow, offRow);

  return (
    <>
      <div className={styles.section}>
        <SectionHeader
          title="Player On/Off"
          count={summary?.length ? `${summary.length} split${summary.length === 1 ? "" : "s"}` : undefined}
        />
        <Card
          className={styles.heroCard}
          depth="elevated"
          padding="lg"
          style={(team.styleVars ?? undefined) as
            | CSSProperties
            | undefined}
        >
          <div className={styles.identityRow}>
            <Avatar
              name={playerDisplayName}
              imageUrl={player.headshotUrl}
              size="lg"
              className={styles.avatar}
            />
            <div className={styles.identityText}>
              <div className={styles.eyebrow}>On/Off Split</div>
              <h2 className={styles.playerName}>{playerDisplayName}</h2>
              <div className={styles.teamLine}>
                <TeamBadge
                  abbreviation={team.teamAbbr ?? undefined}
                  name={teamDisplayName}
                  logoUrl={team.logoUrl}
                  size="sm"
                  className={styles.teamBadge}
                  style={(team.styleVars ?? undefined) as
                    | CSSProperties
                    | undefined}
                />
              </div>
            </div>
          </div>
          {context.length > 0 && (
            <div className={styles.context} aria-label="On/off context">
              {context.map((item) => (
                <span className={styles.contextChip} key={item}>
                  {item}
                </span>
              ))}
            </div>
          )}
        </Card>
      </div>

      {rows.length > 0 && (
        <div className={styles.section}>
          <div className={styles.splitGrid} aria-label="On/off split cards">
            {rows.map((row, index) => {
              const state = presenceState(row);
              const title = state ? splitLabel(state) : `Split ${index + 1}`;
              const stats = splitStats(row);

              return (
                <Card
                  className={styles.splitCard}
                  depth="card"
                  key={`${title}-${index}`}
                  padding="lg"
                >
                  <div className={styles.splitHeader}>
                    <div>
                      <div className={styles.eyebrow}>Player {title}</div>
                      <h3 className={styles.splitTitle}>{title}</h3>
                    </div>
                    {state && (
                      <span
                        className={
                          state === "on" ? styles.onBadge : styles.offBadge
                        }
                      >
                        {state === "on" ? "On Court" : "Off Court"}
                      </span>
                    )}
                  </div>
                  {stats.length > 0 && (
                    <StatBlock stats={stats} columns={statColumns(stats.length)} />
                  )}
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {impact && (
        <div className={styles.section}>
          <Card className={styles.impactCard} depth="card" padding="md">
            <span className={styles.impactLabel}>Impact</span>
            <span className={styles.impactValue}>{impact}</span>
          </Card>
        </div>
      )}

      {summary && summary.length > 0 && (
        <div className={styles.section}>
          <RawDetailToggle title="On/Off Detail" rows={summary} />
        </div>
      )}
    </>
  );
}
