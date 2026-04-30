import type { CSSProperties } from "react";
import type { ResultMetadata, SectionRow } from "../api/types";
import {
  Card,
  SectionHeader,
  Stat,
  StatBlock,
  TeamBadge,
  type StatProps,
} from "../design-system";
import {
  resolveScopedTeamTheme,
  resolveTeamIdentity,
  type ResolvedTeamIdentity,
} from "../lib/identity";
import DataTable from "./DataTable";
import { formatValue } from "./tableFormatting";
import styles from "./TeamRecordSection.module.css";

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

function recordStat(
  row: SectionRow | undefined,
  size: StatProps["size"] = "md",
): StatProps | null {
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
    size,
  };
}

function secondaryStats(row: SectionRow | undefined): StatProps[] {
  const stats: StatProps[] = [];
  const candidates: Array<{ key: string; label: string }> = [
    { key: "pts_avg", label: "PTS" },
    { key: "reb_avg", label: "REB" },
    { key: "ast_avg", label: "AST" },
    { key: "fg3m_avg", label: "3PM" },
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

  return stats.slice(0, 4);
}

function seasonText(
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

function sampleContext(
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
): string {
  const games = numericValue(row, "games");
  const parts = [
    seasonText(metadata, row),
    textValue(row, "season_type") ?? metadata?.season_type ?? null,
    games !== null ? `${formatValue(games, "games")} games` : null,
  ];

  return parts.filter(Boolean).join(" / ");
}

function primaryTeam(
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
): ResolvedTeamIdentity {
  const name =
    metadata?.team_context?.team_name ??
    metadata?.team ??
    textValue(row, "team_name") ??
    textValue(row, "team") ??
    "Team";

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

function opponentTeam(
  metadata: ResultMetadata | undefined,
): ResolvedTeamIdentity | null {
  const name =
    metadata?.opponent_context?.team_name ?? metadata?.opponent ?? null;
  const abbr =
    metadata?.opponent_context?.team_abbr ?? metadata?.opponent ?? null;
  const id = metadata?.opponent_context?.team_id;

  if (!name && !abbr && !id) return null;

  return resolveTeamIdentity({
    teamId: id,
    teamAbbr: abbr,
    teamName: name,
  });
}

function matchupTeam(
  metadata: ResultMetadata | undefined,
  row: SectionRow,
  index: number,
): ResolvedTeamIdentity {
  const context = metadata?.teams_context?.[index];
  const name =
    context?.team_name ??
    textValue(row, "team_name") ??
    textValue(row, "team") ??
    `Team ${index + 1}`;

  return resolveTeamIdentity({
    teamId: context?.team_id ?? identityId(row.team_id),
    teamAbbr:
      context?.team_abbr ??
      textValue(row, "team_abbr") ??
      textValue(row, "team"),
    teamName: name,
  });
}

function TeamBadgeMark({ team }: { team: ResolvedTeamIdentity }) {
  return (
    <TeamBadge
      abbreviation={team.teamAbbr ?? undefined}
      name={team.teamName ?? team.teamAbbr ?? "Team"}
      logoUrl={team.logoUrl}
      size="md"
      style={(team.styleVars ?? undefined) as CSSProperties | undefined}
    />
  );
}

function SingleTeamRecord({
  sections,
  metadata,
}: {
  sections: Record<string, SectionRow[]>;
  metadata?: ResultMetadata;
}) {
  const summary = sections.summary;
  const bySeason = sections.by_season;
  const summaryRow = summary?.[0];
  const team = primaryTeam(metadata, summaryRow);
  const opponent = opponentTeam(metadata);
  const scopedTheme = resolveScopedTeamTheme(metadata);
  const record = recordStat(summaryRow, "hero");
  const stats = secondaryStats(summaryRow);
  const context = sampleContext(metadata, summaryRow);

  return (
    <>
      {summary && summary.length > 0 && (
        <div className={styles.section}>
          <Card
            className={styles.recordHero}
            depth="elevated"
            padding="lg"
            style={(scopedTheme?.styleVars ?? undefined) as
              | CSSProperties
              | undefined}
          >
            <div className={styles.recordHeader}>
              <div className={styles.identityStack}>
                <TeamBadgeMark team={team} />
                {opponent && (
                  <>
                    <span className={styles.versus}>vs</span>
                    <TeamBadgeMark team={opponent} />
                  </>
                )}
              </div>
              <div className={styles.titleBlock}>
                <div className={styles.eyebrow}>Team Record</div>
                <h2 className={styles.teamName}>
                  {team.teamName ?? team.teamAbbr ?? "Team"}
                </h2>
                {context && <div className={styles.context}>{context}</div>}
              </div>
            </div>

            <div className={styles.recordStats}>
              {record && <Stat {...record} className={styles.primaryRecord} />}
              {stats.length > 0 && (
                <StatBlock
                  stats={stats}
                  columns={stats.length >= 4 ? 4 : 2}
                  className={styles.secondaryStats}
                />
              )}
            </div>
          </Card>

          <div className={styles.detailSection}>
            <SectionHeader title="Record Detail" />
            <DataTable rows={summary} />
          </div>
        </div>
      )}
      {(!summary || summary.length === 0) && (
        <div className={styles.section}>
          <SectionHeader title="Team Record" />
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

function MatchupRecord({
  sections,
  metadata,
}: {
  sections: Record<string, SectionRow[]>;
  metadata?: ResultMetadata;
}) {
  const summary = sections.summary ?? [];
  const comparison = sections.comparison;
  const teams = summary.map((row, index) => matchupTeam(metadata, row, index));
  const title =
    teams.length >= 2
      ? `${teams[0].teamName ?? teams[0].teamAbbr ?? "Team"} vs ${
          teams[1].teamName ?? teams[1].teamAbbr ?? "Team"
        }`
      : "Team Matchup";

  return (
    <>
      {summary.length > 0 && (
        <div className={styles.section}>
          <Card className={styles.matchupHero} depth="elevated" padding="lg">
            <div className={styles.titleBlock}>
              <div className={styles.eyebrow}>Team Matchup Record</div>
              <h2 className={styles.teamName}>{title}</h2>
            </div>
            <div className={styles.matchupGrid} aria-label="Matchup records">
              {summary.map((row, index) => {
                const team = teams[index];
                const record = recordStat(row);
                const stats = secondaryStats(row);
                const context = sampleContext(metadata, row);
                return (
                  <div className={styles.matchupTeam} key={index}>
                    <TeamBadgeMark team={team} />
                    {record && <Stat {...record} />}
                    {context && (
                      <div className={styles.matchupContext}>{context}</div>
                    )}
                    {stats.length > 0 && (
                      <StatBlock
                        stats={stats}
                        columns={stats.length >= 4 ? 4 : 2}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </Card>

          <div className={styles.detailSection}>
            <SectionHeader title="Team Summary Detail" />
            <DataTable rows={summary} />
          </div>
        </div>
      )}
      {comparison && comparison.length > 0 && (
        <div className={styles.section}>
          <SectionHeader title="Metric Detail" />
          <DataTable rows={comparison} highlight />
        </div>
      )}
    </>
  );
}

export default function TeamRecordSection({
  sections,
  metadata,
  route,
}: Props) {
  const resolvedRoute = route ?? metadata?.route;
  if (resolvedRoute === "team_matchup_record") {
    return <MatchupRecord sections={sections} metadata={metadata} />;
  }
  return <SingleTeamRecord sections={sections} metadata={metadata} />;
}
