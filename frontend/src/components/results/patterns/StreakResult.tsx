import type { ReactNode } from "react";
import type {
  QueryResponse,
  ResultMetadata,
  SectionRow,
} from "../../../api/types";
import { Badge } from "../../../design-system";
import { formatColHeader, formatValue } from "../../tableFormatting";
import EntityIdentity from "../primitives/EntityIdentity";
import RawDetailToggle from "../primitives/RawDetailToggle";
import ResultHero from "../primitives/ResultHero";
import ResultTable, {
  type ResultTableColumn,
} from "../primitives/ResultTable";
import styles from "./StreakResult.module.css";

type EntityKind = "player" | "team";

interface Props {
  data: QueryResponse;
  sectionKey?: string;
}

const TABLE_LABELS: Record<string, string> = {
  ast_avg: "AST",
  efg_pct_avg: "eFG%",
  fg3m_avg: "3PM",
  minutes_avg: "MIN",
  plus_minus_avg: "+/-",
  pts_avg: "PTS",
  reb_avg: "REB",
  ts_pct_avg: "TS%",
};

const AVERAGE_COLUMNS = [
  "pts_avg",
  "reb_avg",
  "ast_avg",
  "minutes_avg",
  "ts_pct_avg",
  "efg_pct_avg",
  "fg3m_avg",
  "plus_minus_avg",
];

export default function StreakResult({ data, sectionKey = "streak" }: Props) {
  const rows = data.result?.sections?.[sectionKey] ?? [];
  if (rows.length === 0) return null;

  const firstRow = rows[0];
  const kind = entityKind(data, firstRow);
  const entity = entityDisplay(kind, data.result?.metadata, firstRow);

  return (
    <section className={styles.pattern} aria-label="Streak result">
      <ResultHero
        sentence={heroSentence(firstRow, entity.name)}
        subjectIllustration={heroIdentity(kind, entity)}
        tone={kind === "team" ? "team" : "accent"}
        teamAccentAbbr={kind === "team" ? entity.teamAbbr : null}
      />
      <ResultTable
        rows={rows}
        columns={tableColumns(rows, data, kind)}
        ariaLabel="Streaks"
        getRowKey={rowKey}
      />
      <RawDetailToggle title="Full Streak Detail" rows={rows} highlight />
    </section>
  );
}

function tableColumns(
  rows: SectionRow[],
  data: QueryResponse,
  kind: EntityKind,
): Array<ResultTableColumn<SectionRow>> {
  const columns: Array<ResultTableColumn<SectionRow>> = [
    {
      key: "rank",
      header: "#",
      align: "center",
      render: (_row, index) => index + 1,
    },
    {
      key: "entity",
      header: kind === "team" ? "Team" : "Player",
      render: (row) => {
        const entity = entityDisplay(kind, data.result?.metadata, row);
        return heroIdentity(kind, entity);
      },
    },
    {
      key: "condition",
      header: "Streak",
      render: conditionLabel,
    },
    {
      key: "length",
      header: "Length",
      numeric: true,
      render: lengthValue,
    },
  ];

  if (rows.some((row) => hasValue(row.is_active))) {
    columns.push({
      key: "status",
      header: "Status",
      align: "center",
      render: statusCell,
    });
  }

  if (rows.some((row) => hasValue(row.start_date))) {
    columns.push({
      key: "start_date",
      header: "Start",
      render: (row) => textValue(row, "start_date") ?? "—",
    });
  }

  if (rows.some((row) => hasValue(row.end_date))) {
    columns.push({
      key: "end_date",
      header: "End",
      render: (row) => textValue(row, "end_date") ?? "—",
    });
  }

  if (rows.some((row) => hasValue(row.games))) {
    columns.push({
      key: "games",
      header: "Games",
      numeric: true,
      render: (row) => formatValue(row.games, "games"),
    });
  }

  if (rows.some((row) => hasValue(row.wins) || hasValue(row.losses))) {
    columns.push({
      key: "record",
      header: "Record",
      align: "center",
      render: recordValue,
    });
  }

  for (const key of AVERAGE_COLUMNS) {
    if (!rows.some((row) => hasValue(row[key]))) continue;
    columns.push({
      key,
      header: TABLE_LABELS[key] ?? formatColHeader(key),
      numeric: true,
      render: (row) => signedValue(row[key], key),
    });
  }

  return columns;
}

function heroSentence(row: SectionRow, entityName: string): ReactNode {
  const condition = conditionLabel(row);
  const length = lengthValue(row);
  const status = statusText(row);
  const span = dateRange(row);
  const statusTextPart = status ? `${status.toLowerCase()} ` : "";

  return (
    <>
      <span className={styles.heroValue}>{length}</span>{" "}
      {possessive(entityName)} {statusTextPart}
      {condition.toLowerCase()} streak{span ? ` from ${span}` : ""}.
    </>
  );
}

function heroIdentity(
  kind: EntityKind,
  entity: ReturnType<typeof entityDisplay>,
): ReactNode {
  return kind === "team" ? (
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

function entityKind(data: QueryResponse, row: SectionRow): EntityKind {
  const route = data.route ?? data.result?.metadata?.route;
  if (route === "team_streak_finder") return "team";
  if (route === "player_streak_finder") return "player";
  return textValue(row, "team_name") || textValue(row, "team_abbr")
    ? "team"
    : "player";
}

function entityDisplay(
  kind: EntityKind,
  metadata: ResultMetadata | undefined,
  row: SectionRow,
) {
  if (kind === "team") {
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

function conditionLabel(row: SectionRow): string {
  const raw = textValue(row, "condition");
  if (!raw) return "Streak";

  if (raw === "triple_double") return "Triple-double";
  if (raw === "made_three") return "Made three";
  if (raw === "wins") return "Wins";
  if (raw === "losses") return "Losses";

  const minimumMatch = raw.match(/^([a-z0-9_]+)>=(\d+(?:\.\d+)?)$/i);
  if (minimumMatch) {
    const [, stat, value] = minimumMatch;
    return `${formatValue(Number(value), stat)}+ ${compactStatLabel(stat)}`;
  }

  const maximumMatch = raw.match(/^([a-z0-9_]+)<=(\d+(?:\.\d+)?)$/i);
  if (maximumMatch) {
    const [, stat, value] = maximumMatch;
    return `<= ${formatValue(Number(value), stat)} ${compactStatLabel(stat)}`;
  }

  const rangeMatch = raw.match(
    /^([a-z0-9_]+):(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)$/i,
  );
  if (rangeMatch) {
    const [, stat, min, max] = rangeMatch;
    return `${formatValue(Number(min), stat)}-${formatValue(
      Number(max),
      stat,
    )} ${compactStatLabel(stat)}`;
  }

  return formatColHeader(raw);
}

function compactStatLabel(stat: string): string {
  const known: Record<string, string> = {
    ast: "AST",
    blk: "BLK",
    efg_pct: "eFG%",
    fg3m: "3PM",
    plus_minus: "+/-",
    pts: "PTS",
    reb: "REB",
    stl: "STL",
    tov: "TOV",
    ts_pct: "TS%",
  };
  return known[stat.toLowerCase()] ?? formatColHeader(stat);
}

function lengthValue(row: SectionRow): string {
  const length = numericValue(row, "streak_length") ?? numericValue(row, "games");
  if (length === null) return "—";
  return `${formatValue(length, "streak_length")} ${length === 1 ? "game" : "games"}`;
}

function statusCell(row: SectionRow): ReactNode {
  const status = statusText(row);
  if (!status) return "—";
  return (
    <Badge
      variant={status === "Active" ? "success" : "neutral"}
      size="sm"
      uppercase
    >
      {status}
    </Badge>
  );
}

function statusText(row: SectionRow): string | null {
  const value = row.is_active;
  if (value === true || value === 1 || value === "1" || value === "true") {
    return "Active";
  }
  if (value === false || value === 0 || value === "0" || value === "false") {
    return "Completed";
  }
  return null;
}

function dateRange(row: SectionRow): string | null {
  const start = textValue(row, "start_date");
  const end = textValue(row, "end_date");
  if (start && end) return `${start} to ${end}`;
  return start ?? end;
}

function recordValue(row: SectionRow): string {
  if (!hasValue(row.wins) && !hasValue(row.losses)) return "—";
  return `${formatValue(row.wins, "wins")}-${formatValue(row.losses, "losses")}`;
}

function signedValue(value: unknown, key: string): string {
  if (
    typeof value === "number" &&
    key === "plus_minus_avg" &&
    Number.isFinite(value)
  ) {
    const formatted = formatValue(value, key);
    return value > 0 ? `+${formatted}` : formatted;
  }
  return formatValue(value, key);
}

function possessive(name: string): string {
  return name.endsWith("s") ? `${name}'` : `${name}'s`;
}

function rowKey(row: SectionRow, index: number): string {
  return [
    row.player_id,
    row.team_id,
    row.condition,
    row.start_date,
    row.end_date,
    index,
  ]
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
