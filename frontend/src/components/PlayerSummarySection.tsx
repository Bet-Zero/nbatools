import type { ResultMetadata, SectionRow } from "../api/types";
import {
  Avatar,
  Card,
  SectionHeader,
  Stat,
  StatBlock,
  type StatProps,
} from "../design-system";
import { resolvePlayerIdentity } from "../lib/identity";
import DataTable from "./DataTable";
import { formatValue } from "./tableFormatting";
import styles from "./PlayerSummarySection.module.css";

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

function playerName(
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
) {
  return (
    metadata?.player_context?.player_name ??
    metadata?.player ??
    textValue(row, "player_name") ??
    textValue(row, "player") ??
    "Player"
  );
}

function heroStats(row: SectionRow | undefined): StatProps[] {
  const stats: StatProps[] = [];
  const candidates = [
    { key: "pts_avg", label: "PTS", semantic: "accent" as const },
    { key: "reb_avg", label: "REB", semantic: "neutral" as const },
    { key: "ast_avg", label: "AST", semantic: "neutral" as const },
  ];

  for (const { key, label, semantic } of candidates) {
    const value = numericValue(row, key);
    if (value === null) continue;
    stats.push({
      label,
      value: formatValue(value, key),
      semantic,
      size: "hero",
    });
  }

  return stats;
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

function secondaryStats(row: SectionRow | undefined): StatProps[] {
  const stats: StatProps[] = [];
  const candidates: Array<{ key: string; label: string }> = [
    { key: "minutes_avg", label: "MIN" },
    { key: "efg_pct_avg", label: "eFG%" },
    { key: "ts_pct_avg", label: "TS%" },
    { key: "fg3_pct_avg", label: "3P%" },
    { key: "plus_minus_avg", label: "+/-" },
  ];

  for (const { key, label } of candidates) {
    const value = numericValue(row, key);
    if (value === null) continue;
    stats.push({
      label,
      value: formatValue(value, key),
    });
  }

  return stats;
}

export default function PlayerSummarySection({ sections, metadata }: Props) {
  const summary = sections.summary;
  const bySeason = sections.by_season;
  const summaryRow = summary?.[0];
  const name = playerName(metadata, summaryRow);
  const identity = resolvePlayerIdentity({
    playerId:
      metadata?.player_context?.player_id ?? identityId(summaryRow?.player_id),
    playerName: name,
  });
  const primaryStats = heroStats(summaryRow);
  const record = recordStat(summaryRow);
  const supportingStats = secondaryStats(summaryRow);

  return (
    <>
      {summary && summary.length > 0 && (
        <div className={styles.section}>
          <Card className={styles.hero} depth="elevated" padding="lg">
            <div className={styles.identityRow}>
              <Avatar
                className={styles.avatar}
                name={identity.playerName ?? name}
                imageUrl={identity.headshotUrl}
                size="lg"
              />
              <div className={styles.identityText}>
                <div className={styles.eyebrow}>Player Summary</div>
                <h2 className={styles.playerName}>{name}</h2>
              </div>
            </div>

            {primaryStats.length > 0 && (
              <div className={styles.heroStats}>
                {primaryStats.map((stat, index) => (
                  <Stat key={index} {...stat} className={styles.heroStat} />
                ))}
              </div>
            )}

            {(record || supportingStats.length > 0) && (
              <div className={styles.supportingStats}>
                {record && <Stat {...record} />}
                <StatBlock
                  stats={supportingStats}
                  columns={supportingStats.length >= 4 ? 4 : 2}
                  className={styles.statBlock}
                />
              </div>
            )}
          </Card>

          <div className={styles.detailSection}>
            <SectionHeader title="Full Summary" />
            <DataTable rows={summary} />
          </div>
        </div>
      )}
      {(!summary || summary.length === 0) && (
        <div className={styles.section}>
          <SectionHeader title="Player Summary" />
        </div>
      )}
      {bySeason && bySeason.length > 0 && (
        <div className={styles.section}>
          <SectionHeader title="By Season" />
          <DataTable rows={bySeason} />
        </div>
      )}
    </>
  );
}
