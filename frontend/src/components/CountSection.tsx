import type { CSSProperties, ReactNode } from "react";
import type { ResultMetadata, SectionRow } from "../api/types";
import {
  Avatar,
  Card,
  SectionHeader,
  Stat,
  TeamBadge,
} from "../design-system";
import {
  resolvePlayerIdentity,
  resolveTeamIdentity,
} from "../lib/identity";
import DataTable from "./DataTable";
import { formatColHeader, formatValue } from "./tableFormatting";
import styles from "./CountSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
  metadata?: ResultMetadata;
  route?: string | null;
}

const DETAIL_LABELS: Record<string, string> = {
  finder: "Matching Games",
  leaderboard: "Leaderboard Detail",
  streak: "Streak Detail",
};

function sectionTitle(key: string): string {
  return DETAIL_LABELS[key] ?? formatColHeader(key);
}

function countValue(row: SectionRow | undefined): unknown {
  return row?.count ?? row?.value ?? null;
}

function textMetadata(metadata: ResultMetadata | undefined, key: string): string | null {
  const value = metadata?.[key];
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function sampleContext(metadata: ResultMetadata | undefined): string[] {
  const season =
    metadata?.season ??
    (metadata?.start_season && metadata?.end_season
      ? metadata.start_season === metadata.end_season
        ? metadata.start_season
        : `${metadata.start_season} to ${metadata.end_season}`
      : null);
  const dateRange =
    metadata?.start_date && metadata?.end_date
      ? `${metadata.start_date} to ${metadata.end_date}`
      : metadata?.start_date ?? metadata?.end_date ?? null;

  return [
    season,
    metadata?.season_type ?? null,
    dateRange,
    metadata?.opponent ? `vs ${metadata.opponent}` : null,
    textMetadata(metadata, "split_type"),
  ].filter((value): value is string => Boolean(value));
}

function entityName(metadata: ResultMetadata | undefined): string {
  return (
    metadata?.player_context?.player_name ??
    metadata?.team_context?.team_name ??
    metadata?.player ??
    metadata?.team ??
    "Matching results"
  );
}

function entityMark(metadata: ResultMetadata | undefined): ReactNode {
  if (metadata?.player_context || metadata?.player) {
    const name = metadata.player_context?.player_name ?? metadata.player ?? "Player";
    const player = resolvePlayerIdentity({
      playerId: metadata.player_context?.player_id,
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

  if (metadata?.team_context || metadata?.team) {
    const name = metadata.team_context?.team_name ?? metadata.team ?? "Team";
    const team = resolveTeamIdentity({
      teamId: metadata.team_context?.team_id,
      teamAbbr: metadata.team_context?.team_abbr ?? metadata.team,
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

  return null;
}

function detailKeys(sections: Record<string, SectionRow[]>): string[] {
  return Object.keys(sections).filter(
    (key) => key !== "count" && sections[key] && sections[key].length > 0,
  );
}

export default function CountSection({ sections, metadata, route }: Props) {
  const count = sections.count;
  const firstCount = count?.[0];
  const value = countValue(firstCount);
  const details = detailKeys(sections);
  const mark = entityMark(metadata);
  const context = sampleContext(metadata);
  const queryText = metadata?.query_text;
  const resolvedRoute = route ?? metadata?.route;

  return (
    <>
      {count && count.length > 0 && (
        <div className={styles.section}>
          <Card className={styles.countHero} depth="elevated" padding="lg">
            <div className={styles.heroHeader}>
              <div className={styles.identityRow}>
                {mark}
                <div className={styles.titleBlock}>
                  <div className={styles.eyebrow}>Count</div>
                  <h2 className={styles.entityName}>{entityName(metadata)}</h2>
                  {queryText && (
                    <div className={styles.queryText}>{queryText}</div>
                  )}
                </div>
              </div>
              {resolvedRoute && (
                <div className={styles.routeLabel}>
                  {formatColHeader(resolvedRoute)}
                </div>
              )}
            </div>

            <div className={styles.answerGrid}>
              <Stat
                label="Count"
                value={formatValue(value, "count")}
                size="hero"
                semantic="accent"
                animateValue
                className={styles.countStat}
              />
              {context.length > 0 && (
                <div className={styles.contextGrid} aria-label="Count context">
                  {context.map((item) => (
                    <span className={styles.contextItem} key={item}>
                      {item}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </Card>

          <div className={styles.detailSection}>
            <SectionHeader title="Count Detail" />
            <DataTable rows={count} />
          </div>
        </div>
      )}
      {details.map((key) => (
        <div className={styles.section} key={key}>
          <SectionHeader title={sectionTitle(key)} />
          <DataTable rows={sections[key]} />
        </div>
      ))}
    </>
  );
}
