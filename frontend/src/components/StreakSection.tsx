import type { CSSProperties, ReactNode } from "react";
import type { ResultMetadata, SectionRow } from "../api/types";
import {
  Avatar,
  Badge,
  Card,
  SectionHeader,
  Stat,
  StatBlock,
  TeamBadge,
  type StatProps,
} from "../design-system";
import {
  resolvePlayerIdentity,
  resolveTeamIdentity,
} from "../lib/identity";
import DataTable from "./DataTable";
import { formatValue } from "./tableFormatting";
import styles from "./StreakSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
  metadata?: ResultMetadata;
  route?: string | null;
}

type EntityKind = "player" | "team";

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

function entityKind(route: string | null | undefined, row: SectionRow): EntityKind {
  if (route === "team_streak_finder") return "team";
  if (route === "player_streak_finder") return "player";
  if (textValue(row, "team_name") || textValue(row, "team_abbr")) return "team";
  return "player";
}

function entityName(
  kind: EntityKind,
  metadata: ResultMetadata | undefined,
  row: SectionRow,
): string {
  if (kind === "team") {
    return (
      metadata?.team_context?.team_name ??
      metadata?.team ??
      textValue(row, "team_name") ??
      textValue(row, "team") ??
      textValue(row, "team_abbr") ??
      "Team"
    );
  }

  return (
    metadata?.player_context?.player_name ??
    metadata?.player ??
    textValue(row, "player_name") ??
    textValue(row, "player") ??
    "Player"
  );
}

function entityMark(
  kind: EntityKind,
  metadata: ResultMetadata | undefined,
  row: SectionRow,
  name: string,
): ReactNode {
  if (kind === "team") {
    const team = resolveTeamIdentity({
      teamId:
        metadata?.team_context?.team_id ?? identityId(row.team_id),
      teamAbbr:
        metadata?.team_context?.team_abbr ??
        textValue(row, "team_abbr") ??
        textValue(row, "team"),
      teamName: name,
    });
    return (
      <TeamBadge
        abbreviation={team.teamAbbr ?? undefined}
        name={team.teamName ?? name}
        logoUrl={team.logoUrl}
        size="md"
        className={styles.teamBadge}
        style={(team.styleVars ?? undefined) as CSSProperties | undefined}
      />
    );
  }

  const player = resolvePlayerIdentity({
    playerId:
      metadata?.player_context?.player_id ?? identityId(row.player_id),
    playerName: name,
  });
  return (
    <Avatar
      name={player.playerName ?? name}
      imageUrl={player.headshotUrl}
      size="md"
      className={styles.avatar}
    />
  );
}

function conditionLabel(row: SectionRow): string {
  return textValue(row, "condition") ?? "Streak";
}

function pluralizeGames(value: number): string {
  return `${formatValue(value, "games")} ${value === 1 ? "game" : "games"}`;
}

function streakLengthStat(row: SectionRow): StatProps {
  const length = numericValue(row, "streak_length");
  const games = numericValue(row, "games");
  const value = length ?? games;

  return {
    label: "Streak",
    value: value !== null ? formatValue(value, "streak_length") : "Streak",
    context: value !== null ? (value === 1 ? "game" : "games") : undefined,
    semantic: "accent",
    size: "hero",
  };
}

function activeBadge(row: SectionRow): ReactNode {
  const value = row.is_active;
  if (value === true || value === 1 || value === "1" || value === "true") {
    return (
      <Badge variant="success" size="sm" uppercase>
        Active
      </Badge>
    );
  }
  if (value === false || value === 0 || value === "0" || value === "false") {
    return (
      <Badge variant="neutral" size="sm" uppercase>
        Completed
      </Badge>
    );
  }
  return null;
}

function recordStat(row: SectionRow): StatProps | null {
  const wins = numericValue(row, "wins");
  const losses = numericValue(row, "losses");
  if (wins === null || losses === null) return null;
  return {
    label: "Record",
    value: `${formatValue(wins, "wins")}-${formatValue(losses, "losses")}`,
    semantic: wins >= losses ? "win" : "loss",
  };
}

function secondaryStats(row: SectionRow): StatProps[] {
  const stats: StatProps[] = [];
  const record = recordStat(row);
  if (record) stats.push(record);

  const candidates: Array<{ key: string; label: string }> = [
    { key: "pts_avg", label: "PTS" },
    { key: "reb_avg", label: "REB" },
    { key: "ast_avg", label: "AST" },
    { key: "minutes_avg", label: "MIN" },
    { key: "fg3m_avg", label: "3PM" },
    { key: "efg_pct_avg", label: "eFG%" },
    { key: "ts_pct_avg", label: "TS%" },
    { key: "plus_minus_avg", label: "+/-" },
  ];

  for (const { key, label } of candidates) {
    const value = numericValue(row, key);
    if (value === null) continue;
    stats.push({ label, value: formatValue(value, key) });
  }

  return stats.slice(0, 4);
}

function dateSpan(row: SectionRow): ReactNode {
  const start = textValue(row, "start_date");
  const end = textValue(row, "end_date");
  if (!start && !end) return null;
  return (
    <div className={styles.spanRow} aria-label="Streak span">
      {start && (
        <span className={styles.datePill}>
          <span className={styles.dateLabel}>Start</span>
          {start}
        </span>
      )}
      {end && (
        <span className={styles.datePill}>
          <span className={styles.dateLabel}>End</span>
          {end}
        </span>
      )}
    </div>
  );
}

function contextText(row: SectionRow): string {
  const games = numericValue(row, "games");
  return games !== null ? pluralizeGames(games) : "";
}

export default function StreakSection({ sections, metadata, route }: Props) {
  const streak = sections.streak;
  if (!streak || streak.length === 0) return null;

  return (
    <div className={styles.section}>
      <SectionHeader
        title="Streaks"
        count={`${streak.length} found`}
      />
      <div className={styles.cardList} aria-label="Streak results">
        {streak.map((row, index) => {
          const kind = entityKind(route ?? metadata?.route, row);
          const name = entityName(kind, metadata, row);
          const stats = secondaryStats(row);
          const status = activeBadge(row);
          const context = contextText(row);
          const span = dateSpan(row);
          const hasSpanContext = Boolean(context || span);
          return (
            <Card
              as="article"
              className={styles.streakCard}
              depth={index === 0 ? "elevated" : "card"}
              padding="lg"
              key={`${name}-${index}`}
            >
              <div className={styles.cardHeader}>
                <div className={styles.identityRow}>
                  {entityMark(kind, metadata, row, name)}
                  <div className={styles.titleBlock}>
                    <div className={styles.eyebrow}>
                      {kind === "team" ? "Team Streak" : "Player Streak"}
                    </div>
                    <h3 className={styles.entityName}>{name}</h3>
                    <div className={styles.condition}>
                      {conditionLabel(row)}
                    </div>
                  </div>
                </div>
                {status && <div className={styles.status}>{status}</div>}
              </div>

              <div
                className={`${styles.answerGrid} ${
                  hasSpanContext ? "" : styles.answerGridSingle
                }`}
              >
                <Stat {...streakLengthStat(row)} className={styles.heroStat} />
                {hasSpanContext && (
                  <div className={styles.spanBlock}>
                    {context && (
                      <div className={styles.context}>{context}</div>
                    )}
                    {span}
                  </div>
                )}
              </div>

              {stats.length > 0 && (
                <StatBlock
                  stats={stats}
                  columns={stats.length >= 4 ? 4 : 2}
                  className={styles.statBlock}
                />
              )}
            </Card>
          );
        })}
      </div>

      <div className={styles.detailSection}>
        <SectionHeader title="Full Streak Detail" />
        <DataTable rows={streak} highlight />
      </div>
    </div>
  );
}
