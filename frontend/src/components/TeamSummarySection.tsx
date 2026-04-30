import type { CSSProperties } from "react";
import type { ResultMetadata, SectionRow } from "../api/types";
import {
  Card,
  SectionHeader,
  StatBlock,
  TeamBadge,
  type StatProps,
} from "../design-system";
import { resolveTeamIdentity } from "../lib/identity";
import DataTable from "./DataTable";
import { formatValue } from "./tableFormatting";
import styles from "./TeamSummarySection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
  metadata?: ResultMetadata;
  route?: string | null;
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

function sectionTitle(
  route: string | null | undefined,
  metadata: ResultMetadata | undefined,
): string {
  return (route ?? metadata?.route) === "team_record"
    ? "Team Record"
    : "Team Summary";
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

  const candidates: Array<{
    key: string;
    label: string;
    semantic?: StatProps["semantic"];
  }> = [
    { key: "pts_avg", label: "PTS", semantic: "accent" },
    { key: "reb_avg", label: "REB" },
    { key: "ast_avg", label: "AST" },
    { key: "plus_minus_avg", label: "+/-" },
  ];

  for (const { key, label, semantic } of candidates) {
    const value = numericValue(row, key);
    if (value === null) continue;
    stats.push({
      label,
      value: formatValue(value, key),
      semantic,
    });
  }

  return stats.slice(0, 4);
}

export default function TeamSummarySection({ sections, metadata, route }: Props) {
  const summary = sections.summary;
  const bySeason = sections.by_season;
  const summaryRow = summary?.[0];
  const name = teamName(metadata, summaryRow);
  const title = sectionTitle(route, metadata);
  const identity = resolveTeamIdentity({
    teamId:
      metadata?.team_context?.team_id ?? identityId(summaryRow?.team_id),
    teamAbbr:
      metadata?.team_context?.team_abbr ??
      textValue(summaryRow, "team_abbr") ??
      textValue(summaryRow, "team"),
    teamName: name,
  });
  const stats = summaryStats(summaryRow);

  return (
    <>
      {summary && summary.length > 0 && (
        <div className={styles.section}>
          <Card className={styles.ownerCard} depth="card" padding="md">
            <div className={styles.identityRow}>
              <TeamBadge
                abbreviation={identity.teamAbbr ?? undefined}
                name={identity.teamName ?? name}
                logoUrl={identity.logoUrl}
                size="md"
                style={(identity.styleVars ?? undefined) as
                  | CSSProperties
                  | undefined}
              />
              <div className={styles.identityText}>
                <div className={styles.eyebrow}>{title}</div>
                <h2 className={styles.teamName}>{name}</h2>
              </div>
            </div>
            {stats.length > 0 && (
              <StatBlock
                stats={stats}
                columns={stats.length >= 4 ? 4 : 2}
                className={styles.stats}
              />
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
          <SectionHeader title={title} />
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
