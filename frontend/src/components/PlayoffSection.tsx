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
import { resolveTeamIdentity } from "../lib/identity";
import DataTable from "./DataTable";
import LeaderboardSection from "./LeaderboardSection";
import { formatColHeader, formatValue } from "./tableFormatting";
import styles from "./PlayoffSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
  metadata?: ResultMetadata;
  queryClass: string;
  route?: string | null;
}

type TeamIdentity = ReturnType<typeof resolveTeamIdentity>;

const DETAIL_LABELS: Record<string, string> = {
  summary: "Postseason Summary Detail",
  by_season: "Season Breakdown",
  comparison: "Series Detail",
  leaderboard: "Playoff Leaderboard Detail",
};

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

function routeName(route: string | null | undefined): string {
  return route ?? "";
}

function sectionTitle(route: string | null | undefined): string {
  if (routeName(route) === "playoff_appearances") {
    return "Playoff Appearances";
  }
  if (routeName(route) === "playoff_matchup_history") {
    return "Playoff Matchup";
  }
  return "Playoff History";
}

function sectionEyebrow(route: string | null | undefined): string {
  if (routeName(route) === "playoff_appearances") {
    return "Postseason Appearances";
  }
  if (routeName(route) === "playoff_matchup_history") {
    return "Postseason Matchup";
  }
  return "Postseason History";
}

function seasonRange(
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
): string | null {
  const direct =
    textValue(row, "season") ??
    textValue(row, "seasons") ??
    metadataText(metadata, "season");
  if (direct) return direct;

  const start =
    textValue(row, "season_start") ?? metadataText(metadata, "start_season");
  const end =
    textValue(row, "season_end") ?? metadataText(metadata, "end_season");
  if (start && end && start !== end) return `${start} to ${end}`;
  return start ?? end;
}

function roundLabel(
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
  fallbackRows: SectionRow[] = [],
): string | null {
  return (
    textValue(row, "playoff_round") ??
    textValue(row, "round") ??
    metadataText(metadata, "playoff_round") ??
    metadataText(metadata, "round") ??
    textValue(fallbackRows[0], "round")
  );
}

function contextItems(
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
  fallbackRows: SectionRow[] = [],
): string[] {
  const opponent = metadataText(metadata, "opponent");
  return [
    seasonRange(metadata, row),
    textValue(row, "season_type") ?? metadataText(metadata, "season_type"),
    roundLabel(metadata, row, fallbackRows),
    opponent ? `vs ${opponent}` : null,
  ].filter((item): item is string => Boolean(item));
}

function recordStat(
  row: SectionRow | undefined,
  size: StatProps["size"] = "md",
): StatProps | null {
  const wins = numericValue(row, "wins");
  const losses = numericValue(row, "losses");
  const games = numericValue(row, "games") ?? numericValue(row, "games_played");
  const winPct = numericValue(row, "win_pct");

  if (wins !== null && losses !== null) {
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
      semantic: wins > losses ? "win" : wins < losses ? "loss" : "neutral",
      size,
    };
  }

  if (games !== null) {
    return {
      label: "Sample",
      value: formatValue(games, "games"),
      context: games === 1 ? "game" : "games",
      semantic: "accent",
      size,
    };
  }

  return null;
}

function scalarStat(
  row: SectionRow | undefined,
  key: string,
  label: string,
  semantic: StatProps["semantic"] = "neutral",
  size: StatProps["size"] = "md",
): StatProps | null {
  const value = numericValue(row, key);
  if (value === null) return null;
  return {
    label,
    value: formatValue(value, key),
    semantic,
    size,
  };
}

function summaryStats(row: SectionRow | undefined): StatProps[] {
  const stats: StatProps[] = [];
  const primary =
    scalarStat(row, "appearances", "Appearances", "accent", "hero") ??
    scalarStat(row, "seasons_appeared", "Seasons", "accent", "hero");
  if (primary) stats.push(primary);

  const record = recordStat(row, primary ? "md" : "hero");
  if (record) stats.push(record);

  if (!record) {
    const games = scalarStat(
      row,
      "games",
      "Games",
      primary ? "neutral" : "accent",
      primary ? "md" : "hero",
    );
    if (games) stats.push(games);
  }

  const winPct = !record
    ? scalarStat(row, "win_pct", "Win Pct", "neutral")
    : null;
  if (winPct) stats.push(winPct);

  return stats.slice(0, 4);
}

function teamIdentity(
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
  index = 0,
): TeamIdentity {
  const context =
    metadata?.teams_context?.[index] ??
    (index === 0 ? metadata?.team_context : undefined);
  const name =
    context?.team_name ??
    (index === 0 ? metadataText(metadata, "team") : null) ??
    textValue(row, "team_name") ??
    textValue(row, "team") ??
    textValue(row, "team_abbr") ??
    `Team ${index + 1}`;

  return resolveTeamIdentity({
    teamId: context?.team_id ?? identityId(row?.team_id),
    teamAbbr:
      context?.team_abbr ??
      textValue(row, "team_abbr") ??
      textValue(row, "team"),
    teamName: name,
  });
}

function TeamIdentityMark({ team }: { team: TeamIdentity }) {
  return (
    <TeamBadge
      abbreviation={team.teamAbbr ?? undefined}
      name={team.teamName ?? team.teamAbbr ?? "Team"}
      logoUrl={team.logoUrl}
      size="md"
      showName={false}
      className={styles.teamBadge}
      style={(team.styleVars ?? undefined) as CSSProperties | undefined}
    />
  );
}

function detailTitle(key: string): string {
  return DETAIL_LABELS[key] ?? formatColHeader(key);
}

function detailKeys(sections: Record<string, SectionRow[]>): string[] {
  return Object.keys(sections).filter(
    (key) => sections[key] && sections[key].length > 0,
  );
}

function Details({ sections }: { sections: Record<string, SectionRow[]> }) {
  return (
    <>
      {detailKeys(sections).map((key) => (
        <div className={styles.detailSection} key={key}>
          <SectionHeader title={detailTitle(key)} />
          <DataTable rows={sections[key]} highlight={key !== "summary"} />
        </div>
      ))}
    </>
  );
}

function PlayoffSummaryLayout({
  sections,
  metadata,
  route,
}: {
  sections: Record<string, SectionRow[]>;
  metadata?: ResultMetadata;
  route?: string | null;
}) {
  const summary = sections.summary ?? [];
  const row = summary[0];
  const team = teamIdentity(metadata, row);
  const stats = summaryStats(row);
  const context = contextItems(metadata, row, sections.by_season ?? []);

  return (
    <div className={styles.section}>
      {row && (
        <>
          <SectionHeader title={sectionTitle(route)} count="1 team" />
          <Card className={styles.heroCard} depth="elevated" padding="lg">
            <div className={styles.heroHeader}>
              <TeamIdentityMark team={team} />
              <div className={styles.titleBlock}>
                <div className={styles.eyebrow}>{sectionEyebrow(route)}</div>
                <h2 className={styles.title}>
                  {team.teamName ?? team.teamAbbr ?? "Team"}
                </h2>
              </div>
              {context.length > 0 && (
                <div
                  className={styles.contextList}
                  aria-label="Playoff context"
                >
                  {context.map((item) => (
                    <span className={styles.contextItem} key={item}>
                      {item}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {stats.length > 0 && (
              <div
                className={styles.statsPanel}
                aria-label="Postseason summary stats"
              >
                <StatBlock
                  stats={stats}
                  columns={stats.length >= 4 ? 4 : 2}
                />
              </div>
            )}
          </Card>
        </>
      )}

      <Details sections={sections} />
    </div>
  );
}

function matchupTitle(teams: TeamIdentity[]): string {
  if (teams.length >= 2) {
    return `${teams[0].teamName ?? teams[0].teamAbbr ?? "Team"} vs ${
      teams[1].teamName ?? teams[1].teamAbbr ?? "Team"
    }`;
  }
  return teams[0]?.teamName ?? teams[0]?.teamAbbr ?? "Playoff Matchup";
}

function PlayoffComparisonLayout({
  sections,
  metadata,
  route,
}: {
  sections: Record<string, SectionRow[]>;
  metadata?: ResultMetadata;
  route?: string | null;
}) {
  const summary = sections.summary ?? [];
  const teams = summary.map((row, index) => teamIdentity(metadata, row, index));
  const context = contextItems(metadata, summary[0], sections.comparison ?? []);

  return (
    <div className={styles.section}>
      {summary.length > 0 && (
        <>
          <SectionHeader
            title={sectionTitle(route)}
            count={`${summary.length} teams`}
          />
          <Card className={styles.heroCard} depth="elevated" padding="lg">
            <div className={styles.heroHeader}>
              <div className={styles.titleBlock}>
                <div className={styles.eyebrow}>{sectionEyebrow(route)}</div>
                <h2 className={styles.title}>{matchupTitle(teams)}</h2>
              </div>
              {context.length > 0 && (
                <div
                  className={styles.contextList}
                  aria-label="Playoff context"
                >
                  {context.map((item) => (
                    <span className={styles.contextItem} key={item}>
                      {item}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div
              className={styles.participantGrid}
              aria-label="Playoff matchup teams"
            >
              {summary.map((row, index) => {
                const team = teams[index];
                const record = recordStat(row, "hero");
                return (
                  <article className={styles.participantCard} key={index}>
                    <div className={styles.participantIdentity}>
                      <TeamIdentityMark team={team} />
                      <div className={styles.participantName}>
                        {team.teamName ?? team.teamAbbr ?? `Team ${index + 1}`}
                      </div>
                    </div>
                    {record && (
                      <Stat {...record} className={styles.participantRecord} />
                    )}
                  </article>
                );
              })}
            </div>
          </Card>
        </>
      )}

      <Details sections={sections} />
    </div>
  );
}

export default function PlayoffSection({
  sections,
  metadata,
  queryClass,
  route,
}: Props) {
  const resolvedRoute = route ?? metadata?.route;

  if (queryClass === "summary") {
    return (
      <div aria-label="Playoff result">
        <PlayoffSummaryLayout
          sections={sections}
          metadata={metadata}
          route={resolvedRoute}
        />
      </div>
    );
  }

  if (queryClass === "comparison") {
    return (
      <div aria-label="Playoff result">
        <PlayoffComparisonLayout
          sections={sections}
          metadata={metadata}
          route={resolvedRoute}
        />
      </div>
    );
  }

  if (queryClass === "leaderboard") {
    return (
      <div aria-label="Playoff result">
        <LeaderboardSection sections={sections} />
      </div>
    );
  }

  return (
    <div aria-label="Playoff result">
      <Details sections={sections} />
    </div>
  );
}
