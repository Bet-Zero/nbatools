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
  resolveScopedTeamTheme,
  resolveTeamIdentity,
} from "../lib/identity";
import RawDetailToggle from "./RawDetailToggle";
import TeamGameCards from "./TeamGameCards";
import { formatColHeader, formatValue } from "./tableFormatting";
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

function playerIdentity(row: SectionRow) {
  const name = textValue(row, "player_name") ?? "Player";
  return resolvePlayerIdentity({
    playerId: identityId(row.player_id),
    playerName: name,
  });
}

function performerTeamIdentity(row: SectionRow) {
  const abbr = textValue(row, "team_abbr") ?? textValue(row, "team");
  const name = textValue(row, "team_name") ?? abbr ?? "Team";
  return resolveTeamIdentity({
    teamId: identityId(row.team_id),
    teamAbbr: abbr,
    teamName: name,
  });
}

function statColumns(count: number): 1 | 2 | 3 | 4 {
  if (count >= 4) return 4;
  if (count === 3) return 3;
  if (count === 2) return 2;
  return 1;
}

function performerStats(row: SectionRow): StatProps[] {
  const leaderType = textValue(row, "leader_type");
  const stats: StatProps[] = [];
  const candidates = [
    { key: "pts", label: "PTS" },
    { key: "reb", label: "REB" },
    { key: "ast", label: "AST" },
    { key: "minutes", label: "MIN" },
  ];

  for (const { key, label } of candidates) {
    if (numericValue(row, key) === null) continue;
    stats.push({
      label,
      value: formatValue(row[key], key),
      semantic: leaderType === key ? "accent" : "neutral",
    });
  }

  return stats;
}

function performerContext(row: SectionRow): string[] {
  const opponent = textValue(row, "opponent_team_abbr");
  return [
    textValue(row, "game_date"),
    opponent ? `vs ${opponent}` : null,
    textValue(row, "wl"),
  ].filter((item): item is string => Boolean(item));
}

function performerKey(row: SectionRow, index: number): string {
  return `${textValue(row, "leader_type") ?? "leader"}-${textValue(row, "player_name") ?? "player"}-${index}`;
}

function TopPerformers({ rows }: { rows: SectionRow[] }) {
  return (
    <div className={styles.performerGrid} aria-label="Top player performers">
      {rows.map((row, index) => {
        const leaderType = textValue(row, "leader_type") ?? "value";
        const label =
          textValue(row, "leader_label") ?? formatColHeader(leaderType);
        const value = row.value ?? row[leaderType];
        const player = playerIdentity(row);
        const playerName = player.playerName ?? "Player";
        const team = performerTeamIdentity(row);
        const teamName = team.teamName ?? team.teamAbbr ?? "Team";
        const stats = performerStats(row);
        const context = performerContext(row);

        return (
          <article className={styles.performerCard} key={performerKey(row, index)}>
            <div className={styles.performerTopline}>
              <div className={styles.performerLabel}>{label}</div>
              <div className={styles.performerValue}>
                {formatValue(value, leaderType)}
              </div>
            </div>
            <div className={styles.performerIdentity}>
              <Avatar
                className={styles.performerAvatar}
                name={playerName}
                imageUrl={player.headshotUrl}
                size="md"
              />
              <div className={styles.performerText}>
                <div className={styles.performerName}>{playerName}</div>
                <div className={styles.performerTeam}>
                  <TeamBadge
                    abbreviation={team.teamAbbr ?? undefined}
                    name={teamName}
                    logoUrl={team.logoUrl}
                    size="sm"
                    className={styles.performerTeamBadge}
                    style={(team.styleVars ?? undefined) as
                      | CSSProperties
                      | undefined}
                  />
                </div>
                {context.length > 0 && (
                  <div className={styles.performerContext}>
                    {context.map((item) => (
                      <span className={styles.performerContextChip} key={item}>
                        {item}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
            {stats.length > 0 && (
              <StatBlock stats={stats} columns={statColumns(stats.length)} />
            )}
          </article>
        );
      })}
    </div>
  );
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
  const topPerformers = sections.top_performers;
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

      {topPerformers && topPerformers.length > 0 && (
        <div className={styles.section}>
          <SectionHeader
            title="Top Performers"
            count={`${topPerformers.length} leader${
              topPerformers.length !== 1 ? "s" : ""
            }`}
          />
          <TopPerformers rows={topPerformers} />
          <RawDetailToggle title="Top Performers Detail" rows={topPerformers} />
        </div>
      )}

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
