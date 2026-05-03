import type { ReactNode } from "react";
import type {
  QueryResponse,
  ResultMetadata,
  SectionRow,
} from "../../../api/types";
import { formatColHeader, formatValue } from "../../tableFormatting";
import EntityIdentity from "../primitives/EntityIdentity";
import RawDetailToggle from "../primitives/RawDetailToggle";
import ResultHero from "../primitives/ResultHero";
import ResultTable, {
  type ResultTableColumn,
} from "../primitives/ResultTable";
import styles from "./SplitResult.module.css";

type SplitSubject = "player" | "team";

interface Props {
  data: QueryResponse;
  sectionKey?: string;
  summaryKey?: string | null;
  subject?: SplitSubject;
  bucketKey?: string;
  splitLabelOverride?: string;
  primaryDetailTitle?: string;
  summaryDetailTitle?: string | null;
}

type MetricOption = {
  key: string;
  label: string;
  edgeLabel: string;
  signed?: boolean;
};

type MetricCandidate = {
  options: MetricOption[];
};

const TABLE_METRICS: MetricCandidate[] = [
  { options: [{ key: "gp", label: "GP", edgeLabel: "GP" }] },
  { options: [{ key: "possessions", label: "Poss", edgeLabel: "poss" }] },
  { options: [{ key: "off_rating", label: "ORtg", edgeLabel: "off rating" }] },
  { options: [{ key: "def_rating", label: "DRtg", edgeLabel: "def rating" }] },
  {
    options: [
      { key: "net_rating", label: "Net", edgeLabel: "net rating", signed: true },
    ],
  },
  { options: [{ key: "pace", label: "Pace", edgeLabel: "pace" }] },
  {
    options: [
      { key: "pts_avg", label: "PTS", edgeLabel: "PPG" },
      { key: "pts", label: "PTS", edgeLabel: "PTS" },
    ],
  },
  {
    options: [
      { key: "reb_avg", label: "REB", edgeLabel: "REB" },
      { key: "reb", label: "REB", edgeLabel: "REB" },
    ],
  },
  {
    options: [
      { key: "ast_avg", label: "AST", edgeLabel: "AST" },
      { key: "ast", label: "AST", edgeLabel: "AST" },
    ],
  },
  {
    options: [
      { key: "minutes_avg", label: "MIN", edgeLabel: "MIN" },
      { key: "minutes", label: "MIN", edgeLabel: "MIN" },
    ],
  },
  {
    options: [
      { key: "fg3m_avg", label: "3PM", edgeLabel: "3PM" },
      { key: "fg3m", label: "3PM", edgeLabel: "3PM" },
    ],
  },
  {
    options: [
      { key: "ts_pct_avg", label: "TS%", edgeLabel: "TS%" },
      { key: "ts_pct", label: "TS%", edgeLabel: "TS%" },
    ],
  },
  {
    options: [
      { key: "efg_pct_avg", label: "eFG%", edgeLabel: "eFG%" },
      { key: "efg_pct", label: "eFG%", edgeLabel: "eFG%" },
    ],
  },
  {
    options: [
      { key: "fg3_pct_avg", label: "3P%", edgeLabel: "3P%" },
      { key: "fg3_pct", label: "3P%", edgeLabel: "3P%" },
    ],
  },
  {
    options: [
      {
        key: "plus_minus_avg",
        label: "+/-",
        edgeLabel: "+/-",
        signed: true,
      },
      { key: "plus_minus", label: "+/-", edgeLabel: "+/-", signed: true },
    ],
  },
];

const EDGE_METRICS: MetricCandidate[] = [
  TABLE_METRICS[6],
  TABLE_METRICS[8],
  TABLE_METRICS[4],
  TABLE_METRICS[14],
  TABLE_METRICS[11],
  TABLE_METRICS[12],
  TABLE_METRICS[13],
  TABLE_METRICS[7],
  TABLE_METRICS[9],
];

export default function SplitResult({
  data,
  sectionKey = "split_comparison",
  summaryKey = "summary",
  subject,
  bucketKey = "bucket",
  splitLabelOverride,
  primaryDetailTitle = "Split Comparison Detail",
  summaryDetailTitle = "Split Summary Detail",
}: Props) {
  const rows = data.result?.sections?.[sectionKey] ?? [];
  if (rows.length === 0) return null;

  const summaryRows = summaryKey ? data.result?.sections?.[summaryKey] ?? [] : [];
  const summaryRow = summaryRows[0] ?? rows[0];
  const resolvedSubject = subject ?? subjectFromRoute(data);
  const splitName =
    splitLabelOverride ??
    splitLabel(textValue(summaryRow, "split") ?? metadataText(data.result?.metadata, "split_type"));
  const entity = entityDisplay(data.result?.metadata, summaryRow, resolvedSubject);
  const columns = tableColumns(rows, bucketKey);
  const edges = edgeRows(rows, bucketKey);

  return (
    <section className={styles.pattern} aria-label="Split result">
      <ResultHero
        sentence={heroSentence(entity.name, splitName, data.result?.metadata, summaryRow)}
        subjectIllustration={heroIdentity(entity, resolvedSubject)}
        tone={resolvedSubject === "team" ? "team" : "accent"}
      />
      <ResultTable
        rows={rows}
        columns={columns}
        ariaLabel="Split buckets"
        getRowKey={(row, index) => rowKey(row, bucketKey, index)}
      />
      {edges.length > 0 && (
        <div className={styles.edgeRow} aria-label="Split edges">
          <span className={styles.edgeTitle}>Edge</span>
          <div className={styles.edgeList}>
            {edges.map((edge) => (
              <span className={styles.edgeChip} key={edge}>
                {edge}
              </span>
            ))}
          </div>
        </div>
      )}
      {summaryDetailTitle && summaryRows.length > 0 && summaryKey !== sectionKey && (
        <RawDetailToggle title={summaryDetailTitle} rows={summaryRows} />
      )}
      {primaryDetailTitle && <RawDetailToggle title={primaryDetailTitle} rows={rows} />}
    </section>
  );
}

function tableColumns(
  rows: SectionRow[],
  bucketKey: string,
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [
    {
      key: "bucket",
      header: "Split",
      render: (row) => bucketLabel(row[bucketKey]),
    },
  ];

  if (rows.some((row) => numericValue(row, "games") !== null)) {
    columns.push(valueColumn("games", "GP"));
  } else if (rows.some((row) => numericValue(row, "gp") !== null)) {
    columns.push(valueColumn("gp", "GP"));
  }

  if (rows.some((row) => hasValue(row.wins) || hasValue(row.losses))) {
    columns.push({
      key: "record",
      header: "Record",
      align: "center",
      render: recordValue,
    });
  }

  for (const candidate of TABLE_METRICS) {
    const option = metricOption(rows, candidate);
    if (!option) continue;
    if (columns.some((column) => column.key === option.key)) continue;
    columns.push(valueColumn(option.key, option.label, option.signed));
  }

  return columns;
}

function valueColumn(
  key: string,
  label: string,
  signed = false,
): ResultTableColumn<SectionRow> {
  return {
    key,
    header: label,
    numeric: true,
    render: (row) => metricValue(row, key, signed),
  };
}

function metricOption(
  rows: SectionRow[],
  candidate: MetricCandidate,
): MetricOption | null {
  return (
    candidate.options.find((option) =>
      rows.some((row) => hasValue(row[option.key])),
    ) ?? null
  );
}

function metricValue(row: SectionRow, key: string, signed: boolean): string {
  const value = numericValue(row, key);
  if (value === null) return formatValue(row[key], key);
  const formatted = formatValue(value, key);
  return signed && value > 0 ? `+${formatted}` : formatted;
}

function recordValue(row: SectionRow): string {
  if (!hasValue(row.wins) && !hasValue(row.losses)) return "—";
  return `${formatValue(row.wins, "wins")}-${formatValue(row.losses, "losses")}`;
}

function edgeRows(rows: SectionRow[], bucketKey: string): string[] {
  if (rows.length !== 2) return [];
  const [first, second] = rows;
  const firstLabel = bucketLabel(first[bucketKey]);
  const secondLabel = bucketLabel(second[bucketKey]);
  const edges: string[] = [];

  for (const candidate of EDGE_METRICS) {
    const option = pairedMetricOption(first, second, candidate);
    if (!option) continue;

    const firstValue = numericValue(first, option.key);
    const secondValue = numericValue(second, option.key);
    if (firstValue === null || secondValue === null) continue;

    const delta = firstValue - secondValue;
    if (Math.abs(delta) < 0.05) continue;

    const leader = delta >= 0 ? firstLabel : secondLabel;
    const value = formatValue(Math.abs(delta), option.key);
    edges.push(`${leader} +${value} ${option.edgeLabel}`);
  }

  return edges.slice(0, 4);
}

function pairedMetricOption(
  first: SectionRow,
  second: SectionRow,
  candidate: MetricCandidate,
): MetricOption | null {
  return (
    candidate.options.find(
      (option) =>
        numericValue(first, option.key) !== null &&
        numericValue(second, option.key) !== null,
    ) ?? null
  );
}

function heroSentence(
  entityName: string,
  splitName: string,
  metadata: ResultMetadata | undefined,
  row: SectionRow,
): string {
  const context = [seasonLabel(metadata, row), metadataText(metadata, "season_type")]
    .filter(Boolean)
    .join(" ");
  return context
    ? `${possessive(entityName)} ${splitName.toLowerCase()} split for ${context}.`
    : `${possessive(entityName)} ${splitName.toLowerCase()} split.`;
}

function possessive(name: string): string {
  return name.endsWith("s") ? `${name}'` : `${name}'s`;
}

function heroIdentity(
  entity: ReturnType<typeof entityDisplay>,
  subject: SplitSubject,
): ReactNode {
  return subject === "team" ? (
    <EntityIdentity
      kind="team"
      teamId={entity.id}
      teamAbbr={entity.teamAbbr}
      teamName={entity.name}
      size="md"
    />
  ) : (
    <EntityIdentity
      kind="player"
      playerId={entity.id}
      playerName={entity.name}
      teamAbbr={entity.teamAbbr}
      size="md"
    />
  );
}

function entityDisplay(
  metadata: ResultMetadata | undefined,
  row: SectionRow,
  subject: SplitSubject,
) {
  if (subject === "team") {
    return {
      id: metadata?.team_context?.team_id ?? identityId(row.team_id),
      name:
        metadata?.team_context?.team_name ??
        metadataText(metadata, "team") ??
        textValue(row, "team_name") ??
        textValue(row, "team") ??
        textValue(row, "team_abbr") ??
        "Team",
      teamAbbr:
        metadata?.team_context?.team_abbr ??
        textValue(row, "team_abbr") ??
        textValue(row, "team"),
    };
  }

  return {
    id: metadata?.player_context?.player_id ?? identityId(row.player_id),
    name:
      metadata?.player_context?.player_name ??
      metadataText(metadata, "player") ??
      textValue(row, "player_name") ??
      textValue(row, "player") ??
      "Player",
    teamAbbr:
      metadata?.team_context?.team_abbr ??
      textValue(row, "team_abbr") ??
      textValue(row, "team"),
  };
}

function subjectFromRoute(data: QueryResponse): SplitSubject {
  const route = data.route ?? data.result?.metadata?.route;
  return route === "team_split_summary" ? "team" : "player";
}

function splitLabel(value: string | null): string {
  if (!value) return "Split";
  const labels: Record<string, string> = {
    home_away: "Home/Away",
    on_off: "On/Off",
    wins_losses: "Wins/Losses",
  };
  return labels[value] ?? formatColHeader(value);
}

function bucketLabel(value: unknown): string {
  const raw = typeof value === "string" ? value : String(value ?? "Bucket");
  const labels: Record<string, string> = {
    away: "Away",
    home: "Home",
    losses: "Losses",
    off: "Off",
    on: "On",
    wins: "Wins",
  };
  return labels[raw.toLowerCase()] ?? formatColHeader(raw);
}

function seasonLabel(
  metadata: ResultMetadata | undefined,
  row: SectionRow,
): string | null {
  const start =
    metadataText(metadata, "start_season") ??
    textValue(row, "season_start") ??
    textValue(row, "season");
  const end = metadataText(metadata, "end_season") ?? textValue(row, "season_end");
  if (start && end && start !== end) return `${start} to ${end}`;
  return metadataText(metadata, "season") ?? start ?? end;
}

function rowKey(row: SectionRow, bucketKey: string, index: number): string {
  return [row[bucketKey], row.player_id, row.team_id, index]
    .filter(hasValue)
    .join("-");
}

function textValue(row: SectionRow | undefined, key: string): string | null {
  const value = row?.[key];
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
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

function numericValue(row: SectionRow | undefined, key: string): number | null {
  const value = row?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function identityId(value: unknown): number | string | null {
  return typeof value === "number" || typeof value === "string" ? value : null;
}

function hasValue(value: unknown): boolean {
  return value !== null && value !== undefined && value !== "";
}
