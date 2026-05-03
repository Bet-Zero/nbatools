import type { CSSProperties } from "react";
import type { ResultMetadata, SectionRow } from "../api/types";
import {
  Card,
  SectionHeader,
  StatBlock,
  TeamBadge,
  type StatProps,
} from "../design-system";
import {
  resolveScopedTeamTheme,
  resolveTeamIdentity,
} from "../lib/identity";
import RawDetailToggle from "./RawDetailToggle";
import TeamGameCards from "./TeamGameCards";
import { formatValue } from "./tableFormatting";
import styles from "./GameSummarySection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
  metadata?: ResultMetadata;
}

function numericValue(row: SectionRow | undefined, key: string): number | null {
  const value = row?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function textValue(row: SectionRow | undefined, key: string): string | null {
  const value = row?.[key];
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function identityId(value: unknown): number | string | null {
  return typeof value === "number" || typeof value === "string" ? value : null;
}

function teamName(
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
): string {
  return (
    metadata?.team_context?.team_name ??
    metadata?.team ??
    textValue(row, "team_name") ??
    textValue(row, "team") ??
    "Team"
  );
}

function teamIdentity(
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
) {
  const name = teamName(metadata, row);
  return resolveTeamIdentity({
    teamId:
      metadata?.team_context?.team_id ?? identityId(row?.team_id),
    teamAbbr:
      metadata?.team_context?.team_abbr ??
      textValue(row, "team_abbr") ??
      textValue(row, "team"),
    teamName: name,
  });
}

function opponentIdentity(metadata: ResultMetadata | undefined) {
  if (!metadata?.opponent_context && !metadata?.opponent) return null;
  return resolveTeamIdentity({
    teamId: metadata.opponent_context?.team_id,
    teamAbbr: metadata.opponent_context?.team_abbr ?? metadata.opponent,
    teamName: metadata.opponent_context?.team_name ?? metadata.opponent,
  });
}

function seasonLabel(
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
): string | null {
  const start =
    textValue(row, "season_start") ??
    metadata?.start_season ??
    metadata?.season ??
    null;
  const end =
    textValue(row, "season_end") ??
    metadata?.end_season ??
    metadata?.season ??
    null;

  if (start && end && start !== end) return `${start} to ${end}`;
  return start ?? end;
}

function dateLabel(metadata: ResultMetadata | undefined): string | null {
  const start = metadata?.start_date ?? null;
  const end = metadata?.end_date ?? null;
  if (start && end) return start === end ? start : `${start} to ${end}`;
  return start ?? end;
}

function contextText(
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
): string {
  const games = numericValue(row, "games");
  const parts = [
    dateLabel(metadata),
    seasonLabel(metadata, row),
    textValue(row, "season_type") ?? metadata?.season_type ?? null,
    metadata?.opponent ? `vs ${metadata.opponent}` : null,
    games !== null ? `${formatValue(games, "games")} games` : null,
  ];

  return parts.filter(Boolean).join(" / ");
}

function recordStat(row: SectionRow | undefined): StatProps | null {
  const wins = numericValue(row, "wins");
  const losses = numericValue(row, "losses");
  const games = numericValue(row, "games");
  const winPct = numericValue(row, "win_pct");
  if (wins === null || losses === null) return null;

  const context = [
    games !== null ? `${formatValue(games, "games")} games` : null,
    winPct !== null ? `${formatValue(winPct, "win_pct")} win pct` : null,
  ]
    .filter(Boolean)
    .join(" / ");

  return {
    label: "Record",
    value: `${formatValue(wins, "wins")}-${formatValue(losses, "losses")}`,
    context,
    semantic: wins >= losses ? "win" : "loss",
  };
}

function summaryStats(row: SectionRow | undefined): StatProps[] {
  const stats: StatProps[] = [];
  const record = recordStat(row);
  if (record) stats.push(record);

  const candidates: Array<{ key: string; label: string }> = [
    { key: "pts_avg", label: "PTS" },
    { key: "plus_minus_avg", label: "Margin" },
    { key: "reb_avg", label: "REB" },
    { key: "ast_avg", label: "AST" },
    { key: "fg3m_avg", label: "3PM" },
    { key: "tov_avg", label: "TOV" },
  ];

  for (const { key, label } of candidates) {
    const value = numericValue(row, key);
    if (value === null) continue;
    stats.push({
      label,
      value: formatValue(value, key),
      semantic:
        key === "plus_minus_avg"
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

function AggregateSummary({
  metadata,
  row,
}: {
  metadata?: ResultMetadata;
  row: SectionRow;
}) {
  const identity = teamIdentity(metadata, row);
  const opponent = opponentIdentity(metadata);
  const context = contextText(metadata, row);
  const stats = summaryStats(row);
  const scopedTheme = resolveScopedTeamTheme(metadata);
  const name = identity.teamName ?? teamName(metadata, row);

  return (
    <Card
      className={styles.heroCard}
      depth="elevated"
      padding="lg"
      style={(scopedTheme?.styleVars ?? undefined) as
        | CSSProperties
        | undefined}
    >
      <div className={styles.identityRow}>
        <TeamBadge
          abbreviation={identity.teamAbbr ?? undefined}
          name={name}
          logoUrl={identity.logoUrl}
          size="md"
          className={styles.teamBadge}
          style={(identity.styleVars ?? undefined) as
            | CSSProperties
            | undefined}
        />
        <div className={styles.identityText}>
          <div className={styles.eyebrow}>Game Summary</div>
          <h2 className={styles.teamName}>
            {opponent?.teamName || opponent?.teamAbbr
              ? `${name} vs ${opponent.teamName ?? opponent.teamAbbr}`
              : name}
          </h2>
          {context && <div className={styles.context}>{context}</div>}
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
}

export default function GameSummarySection({ sections, metadata }: Props) {
  const summary = sections.summary;
  const bySeason = sections.by_season;
  const gameLog = sections.game_log;
  const summaryRow = summary?.[0];

  return (
    <>
      <div className={styles.section}>
        <SectionHeader
          title="Game Summary"
          count={
            gameLog?.length
              ? `${gameLog.length} game${gameLog.length !== 1 ? "s" : ""}`
              : undefined
          }
        />
        {gameLog && gameLog.length > 0 ? (
          <TeamGameCards rows={gameLog} />
        ) : summaryRow ? (
          <AggregateSummary metadata={metadata} row={summaryRow} />
        ) : null}
      </div>

      {summary && summary.length > 0 && (
        <div className={styles.section}>
          <RawDetailToggle title="Summary Detail" rows={summary} />
        </div>
      )}
      {gameLog && gameLog.length > 0 && (
        <div className={styles.section}>
          <RawDetailToggle title="Game Detail" rows={gameLog} />
        </div>
      )}
      {bySeason && bySeason.length > 0 && (
        <div className={styles.section}>
          <RawDetailToggle title="By Season" rows={bySeason} />
        </div>
      )}
    </>
  );
}
