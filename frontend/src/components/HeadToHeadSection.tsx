import type { CSSProperties, ReactNode } from "react";
import type { ResultMetadata, SectionRow } from "../api/types";
import {
  Avatar,
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
import { formatColHeader, formatValue } from "./tableFormatting";
import styles from "./HeadToHeadSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
  metadata?: ResultMetadata;
  route?: string | null;
}

type EntityKind = "player" | "team";

const DETAIL_LABELS: Record<string, string> = {
  summary: "Participant Detail",
  comparison: "Metric Detail",
  finder: "Matching Games",
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

function rowKind(route: string | null | undefined, row: SectionRow): EntityKind {
  if (route === "player_compare") return "player";
  if (textValue(row, "player_name") || textValue(row, "player")) return "player";
  return "team";
}

function entityName(
  kind: EntityKind,
  metadata: ResultMetadata | undefined,
  row: SectionRow,
  index: number,
): string {
  if (kind === "player") {
    const rowName =
      textValue(row, "player_name") ?? textValue(row, "player") ?? null;
    return (
      metadata?.players_context?.find(
        (context) => context.player_name === rowName,
      )?.player_name ??
      metadata?.players_context?.[index]?.player_name ??
      rowName ??
      `Player ${index + 1}`
    );
  }

  return (
    metadata?.teams_context?.[index]?.team_name ??
    textValue(row, "team_name") ??
    textValue(row, "team") ??
    textValue(row, "team_abbr") ??
    `Team ${index + 1}`
  );
}

function entityMark(
  kind: EntityKind,
  metadata: ResultMetadata | undefined,
  row: SectionRow,
  index: number,
  name: string,
): ReactNode {
  if (kind === "player") {
    const rowName =
      textValue(row, "player_name") ?? textValue(row, "player") ?? null;
    const context =
      metadata?.players_context?.find(
        (candidate) => candidate.player_name === rowName,
      ) ??
      metadata?.players_context?.[index] ??
      null;
    const player = resolvePlayerIdentity({
      playerId: context?.player_id ?? identityId(row.player_id),
      playerName: name,
    });

    return (
      <Avatar
        className={styles.identityMark}
        name={player.playerName ?? name}
        imageUrl={player.headshotUrl}
        size="md"
      />
    );
  }

  const context = metadata?.teams_context?.[index];
  const team = resolveTeamIdentity({
    teamId: context?.team_id ?? identityId(row.team_id),
    teamAbbr:
      context?.team_abbr ??
      textValue(row, "team_abbr") ??
      textValue(row, "team"),
    teamName: name,
  });

  return (
    <TeamBadge
      className={styles.identityMark}
      abbreviation={team.teamAbbr ?? undefined}
      name={team.teamName ?? team.teamAbbr ?? name}
      logoUrl={team.logoUrl}
      size="md"
      showName={false}
      style={(team.styleVars ?? undefined) as CSSProperties | undefined}
    />
  );
}

function recordStat(row: SectionRow): StatProps | null {
  const wins = numericValue(row, "wins");
  const losses = numericValue(row, "losses");
  const games = numericValue(row, "games");
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
      size: "hero",
    };
  }

  if (games !== null) {
    return {
      label: "Sample",
      value: formatValue(games, "games"),
      context: games === 1 ? "game" : "games",
      semantic: "accent",
      size: "hero",
    };
  }

  return null;
}

function secondaryStats(row: SectionRow): StatProps[] {
  const stats: StatProps[] = [];
  const candidates: Array<{ key: string; label: string }> = [
    { key: "pts_avg", label: "PTS" },
    { key: "reb_avg", label: "REB" },
    { key: "ast_avg", label: "AST" },
    { key: "minutes_avg", label: "MIN" },
    { key: "fg3m_avg", label: "3PM" },
    { key: "plus_minus_avg", label: "+/-" },
  ];

  for (const { key, label } of candidates) {
    const value = numericValue(row, key);
    if (value === null) continue;
    stats.push({ label, value: formatValue(value, key) });
  }

  return stats.slice(0, 4);
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

function seasonLabel(metadata: ResultMetadata | undefined): string | null {
  if (metadata?.season) return metadata.season;
  if (metadata?.start_season && metadata?.end_season) {
    return metadata.start_season === metadata.end_season
      ? metadata.start_season
      : `${metadata.start_season} to ${metadata.end_season}`;
  }
  return null;
}

function dateLabel(metadata: ResultMetadata | undefined): string | null {
  const start = metadataText(metadata, "start_date");
  const end = metadataText(metadata, "end_date");
  if (start && end) return `${start} to ${end}`;
  return start ?? end;
}

function contextItems(metadata: ResultMetadata | undefined): string[] {
  const opponent = metadataText(metadata, "opponent");
  return [
    seasonLabel(metadata),
    metadataText(metadata, "season_type"),
    dateLabel(metadata),
    metadata?.head_to_head_used ? "Head-to-head sample" : null,
    opponent ? `vs ${opponent}` : null,
  ].filter((item): item is string => Boolean(item));
}

function matchupTitle(names: string[]): string {
  if (names.length >= 2) return `${names[0]} vs ${names[1]}`;
  return names[0] ?? "Head-to-head";
}

function detailTitle(key: string): string {
  return DETAIL_LABELS[key] ?? formatColHeader(key);
}

function detailKeys(sections: Record<string, SectionRow[]>): string[] {
  return Object.keys(sections).filter(
    (key) => sections[key] && sections[key].length > 0,
  );
}

export default function HeadToHeadSection({
  sections,
  metadata,
  route,
}: Props) {
  const summary = sections.summary ?? [];
  const resolvedRoute = route ?? metadata?.route;
  const participants = summary.map((row, index) => {
    const kind = rowKind(resolvedRoute, row);
    const name = entityName(kind, metadata, row, index);
    return {
      kind,
      name,
      mark: entityMark(kind, metadata, row, index, name),
      record: recordStat(row),
      stats: secondaryStats(row),
      row,
    };
  });
  const context = contextItems(metadata);
  const details = detailKeys(sections);

  return (
    <div className={styles.section} aria-label="Head-to-head result">
      {participants.length > 0 && (
        <>
          <SectionHeader
            title="Head-to-Head"
            count={`${participants.length} participants`}
          />
          <Card className={styles.matchupCard} depth="elevated" padding="lg">
            <div className={styles.matchupHeader}>
              <div className={styles.titleBlock}>
                <div className={styles.eyebrow}>Matchup</div>
                <h2 className={styles.matchupTitle}>
                  {matchupTitle(
                    participants.map((participant) => participant.name),
                  )}
                </h2>
              </div>
              {context.length > 0 && (
                <div className={styles.contextList} aria-label="Matchup context">
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
              aria-label="Head-to-head participants"
            >
              {participants.map((participant, index) => (
                <article className={styles.participantCard} key={index}>
                  <div className={styles.participantIdentity}>
                    {participant.mark}
                    <div className={styles.participantName}>
                      {participant.name}
                    </div>
                  </div>
                  {participant.record && (
                    <Stat
                      {...participant.record}
                      className={styles.recordStat}
                    />
                  )}
                  {participant.stats.length > 0 && (
                    <StatBlock
                      stats={participant.stats}
                      columns={participant.stats.length >= 4 ? 4 : 2}
                      className={styles.statBlock}
                    />
                  )}
                </article>
              ))}
            </div>
          </Card>
        </>
      )}

      {details.map((key) => (
        <div className={styles.detailSection} key={key}>
          <SectionHeader title={detailTitle(key)} />
          <DataTable rows={sections[key]} highlight={key !== "summary"} />
        </div>
      ))}
    </div>
  );
}
