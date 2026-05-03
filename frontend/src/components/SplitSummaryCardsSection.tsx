import type { CSSProperties, ReactNode } from "react";
import type { ResultMetadata, SectionRow } from "../api/types";
import {
  Avatar,
  Card,
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
import { formatColHeader, formatValue } from "./tableFormatting";
import styles from "./SplitSummaryCardsSection.module.css";

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

function splitLabel(value: string | null): string {
  if (!value) return "Split";
  const known: Record<string, string> = {
    home_away: "Home/Away",
    wins_losses: "Wins/Losses",
  };
  return known[value] ?? formatColHeader(value);
}

function bucketLabel(value: unknown): string {
  const raw = typeof value === "string" ? value : String(value ?? "Bucket");
  const known: Record<string, string> = {
    home: "Home",
    away: "Away",
    wins: "Wins",
    losses: "Losses",
  };
  return known[raw] ?? formatColHeader(raw);
}

function pluralizeGames(count: number): string {
  return `${formatValue(count, "games")} ${count === 1 ? "game" : "games"}`;
}

function metadataText(
  metadata: ResultMetadata | undefined,
  key: string,
): string | null {
  const value = metadata?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function metadataNumber(
  metadata: ResultMetadata | undefined,
  key: string,
): number | null {
  const value = metadata?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function compactStatLabel(stat: string): string {
  const known: Record<string, string> = {
    ast: "AST",
    efg_pct: "eFG%",
    fg3_pct: "3P%",
    fg3m: "3PM",
    plus_minus: "+/-",
    pts: "PTS",
    reb: "REB",
    ts_pct: "TS%",
  };
  return known[stat.toLowerCase()] ?? formatColHeader(stat);
}

function statFilterContext(metadata: ResultMetadata | undefined): string | null {
  const stat = metadataText(metadata, "stat");
  if (!stat) return null;

  const label = compactStatLabel(stat);
  const min = metadataNumber(metadata, "min_value");
  const max = metadataNumber(metadata, "max_value");

  if (min !== null && max !== null) {
    return `${formatValue(min, stat)}-${formatValue(max, stat)} ${label}`;
  }
  if (min !== null) return `${formatValue(min, stat)}+ ${label}`;
  if (max !== null) return `<= ${formatValue(max, stat)} ${label}`;
  return label;
}

function filterContext(metadata: ResultMetadata | undefined): string | null {
  const parts = [
    metadataText(metadata, "team"),
    metadataText(metadata, "opponent")
      ? `vs ${metadataText(metadata, "opponent")}`
      : null,
    metadataNumber(metadata, "last_n") !== null
      ? `Last ${formatValue(metadataNumber(metadata, "last_n"), "last_n")} games`
      : null,
    statFilterContext(metadata),
  ];

  return parts.filter(Boolean).join(" / ") || null;
}

function sampleContext(row: SectionRow | undefined): string {
  const games = numericValue(row, "games_total") ?? numericValue(row, "games");
  const parts = [
    textValue(row, "season_start") && textValue(row, "season_end")
      ? textValue(row, "season_start") === textValue(row, "season_end")
        ? textValue(row, "season_start")
        : `${textValue(row, "season_start")} to ${textValue(row, "season_end")}`
      : textValue(row, "season"),
    textValue(row, "season_type"),
    games !== null ? pluralizeGames(games) : null,
  ];

  return parts.filter(Boolean).join(" / ");
}

function entityName(
  route: string | null | undefined,
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
): string {
  if (route === "team_split_summary") {
    return (
      metadata?.team_context?.team_name ??
      metadata?.team ??
      textValue(row, "team_name") ??
      textValue(row, "team") ??
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
  route: string | null | undefined,
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
  name: string,
): ReactNode {
  if (route === "team_split_summary") {
    const team = resolveTeamIdentity({
      teamId:
        metadata?.team_context?.team_id ?? identityId(row?.team_id),
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
      metadata?.player_context?.player_id ?? identityId(row?.player_id),
    playerName: name,
  });
  return (
    <Avatar
      name={player.playerName ?? name}
      imageUrl={player.headshotUrl}
      size="md"
      className={styles.entityAvatar}
    />
  );
}

function recordStat(row: SectionRow): StatProps | null {
  const wins = numericValue(row, "wins");
  const losses = numericValue(row, "losses");
  const games = numericValue(row, "games");
  const winPct = numericValue(row, "win_pct");

  if (wins === null || losses === null) return null;

  const context = [
    games !== null ? pluralizeGames(games) : null,
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

type MetricCandidate = {
  options: Array<{
    key: string;
    label: string;
    edgeLabel: string;
  }>;
};

const BUCKET_METRICS: MetricCandidate[] = [
  { options: [{ key: "pts_avg", label: "PTS", edgeLabel: "PPG" }] },
  { options: [{ key: "reb_avg", label: "REB", edgeLabel: "REB" }] },
  { options: [{ key: "ast_avg", label: "AST", edgeLabel: "AST" }] },
  { options: [{ key: "minutes_avg", label: "MIN", edgeLabel: "MIN" }] },
  {
    options: [
      { key: "ts_pct_avg", label: "TS%", edgeLabel: "TS%" },
      { key: "efg_pct_avg", label: "eFG%", edgeLabel: "eFG%" },
    ],
  },
  {
    options: [
      { key: "fg3_pct_avg", label: "3P%", edgeLabel: "3P%" },
      { key: "fg3_pct", label: "3P%", edgeLabel: "3P%" },
    ],
  },
  { options: [{ key: "fg3m_avg", label: "3PM", edgeLabel: "3PM" }] },
  { options: [{ key: "plus_minus_avg", label: "+/-", edgeLabel: "+/-" }] },
];
const EDGE_METRICS = [
  BUCKET_METRICS[0],
  BUCKET_METRICS[2],
  BUCKET_METRICS[7],
  BUCKET_METRICS[4],
  BUCKET_METRICS[5],
  BUCKET_METRICS[1],
  BUCKET_METRICS[3],
];

function metricValue(
  row: SectionRow,
  candidate: MetricCandidate,
): { key: string; value: number; label: string; edgeLabel: string } | null {
  for (const option of candidate.options) {
    const value = numericValue(row, option.key);
    if (value !== null) return { ...option, value };
  }
  return null;
}

function pairedMetricValues(
  first: SectionRow,
  second: SectionRow,
  candidate: MetricCandidate,
): {
  key: string;
  firstValue: number;
  secondValue: number;
  edgeLabel: string;
} | null {
  for (const option of candidate.options) {
    const firstValue = numericValue(first, option.key);
    const secondValue = numericValue(second, option.key);
    if (firstValue !== null && secondValue !== null) {
      return {
        key: option.key,
        firstValue,
        secondValue,
        edgeLabel: option.edgeLabel,
      };
    }
  }
  return null;
}

function bucketStats(row: SectionRow): StatProps[] {
  const stats: StatProps[] = [];
  const record = recordStat(row);
  if (record) stats.push(record);

  for (const candidate of BUCKET_METRICS) {
    const metric = metricValue(row, candidate);
    if (!metric) continue;
    stats.push({
      label: metric.label,
      value: formatValue(metric.value, metric.key),
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

function edgeRows(rows: SectionRow[]): string[] {
  if (rows.length !== 2) return [];
  const [first, second] = rows;
  const firstLabel = bucketLabel(first.bucket);
  const secondLabel = bucketLabel(second.bucket);
  const edges: string[] = [];

  for (const candidate of EDGE_METRICS) {
    const metric = pairedMetricValues(first, second, candidate);
    if (!metric) continue;

    const delta = metric.firstValue - metric.secondValue;
    if (Math.abs(delta) < 0.05) continue;

    const leader = delta >= 0 ? firstLabel : secondLabel;
    const value = formatValue(Math.abs(delta), metric.key);
    edges.push(`${leader} +${value} ${metric.edgeLabel}`);
  }

  return edges.slice(0, 4);
}

export default function SplitSummaryCardsSection({
  sections,
  metadata,
  route,
}: Props) {
  const summary = sections.summary;
  const splitComparison = sections.split_comparison;
  const summaryRow = summary?.[0];
  const resolvedRoute = route ?? metadata?.route;
  const name = entityName(resolvedRoute, metadata, summaryRow);
  const context = sampleContext(summaryRow);
  const filters = filterContext(metadata);
  const splitEdges = edgeRows(splitComparison ?? []);
  const scopedTheme = resolveScopedTeamTheme(metadata);
  const title =
    resolvedRoute === "team_split_summary"
      ? "Team Split Summary"
      : "Player Split Summary";
  const split = splitLabel(
    textValue(summaryRow, "split") ?? metadata?.split_type ?? null,
  );

  return (
    <>
      {summary && summary.length > 0 && (
        <div className={styles.section}>
          <Card
            className={styles.hero}
            depth="elevated"
            padding="lg"
            style={(scopedTheme?.styleVars ?? undefined) as
              | CSSProperties
              | undefined}
          >
            <div className={styles.identityRow}>
              {entityMark(resolvedRoute, metadata, summaryRow, name)}
              <div className={styles.titleBlock}>
                <div className={styles.eyebrow}>{title}</div>
                <h2 className={styles.entityName}>{name}</h2>
                <div className={styles.context}>
                  {[split, context, filters].filter(Boolean).join(" / ")}
                </div>
              </div>
            </div>
          </Card>
        </div>
      )}

      {splitComparison && splitComparison.length > 0 && (
        <div className={styles.section}>
          <div className={styles.bucketGrid} aria-label="Split buckets">
            {splitComparison.map((row, index) => {
              const stats = bucketStats(row);
              const games = numericValue(row, "games");
              return (
                <div className={styles.bucketCard} key={index}>
                  <div className={styles.bucketHeader}>
                    <h3 className={styles.bucketTitle}>
                      {bucketLabel(row.bucket)}
                    </h3>
                    {games !== null && (
                      <span className={styles.bucketCount}>
                        {pluralizeGames(games)}
                      </span>
                    )}
                  </div>
                  {stats.length > 0 && (
                    <StatBlock
                      stats={stats}
                      columns={statColumns(stats.length)}
                    />
                  )}
                </div>
              );
            })}
          </div>
          {splitEdges.length > 0 && (
            <div className={styles.edgeRow} aria-label="Split edges">
              <span className={styles.edgeTitle}>Edge</span>
              <div className={styles.edgeList}>
                {splitEdges.map((edge) => (
                  <span className={styles.edgeChip} key={edge}>
                    {edge}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {summary && summary.length > 0 && (
        <div className={styles.section}>
          <RawDetailToggle title="Split Summary Detail" rows={summary} />
        </div>
      )}
      {splitComparison && splitComparison.length > 0 && (
        <div className={styles.section}>
          <RawDetailToggle
            title="Split Comparison Detail"
            rows={splitComparison}
            highlight
          />
        </div>
      )}
    </>
  );
}
