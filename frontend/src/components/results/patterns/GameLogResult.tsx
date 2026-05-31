import type { ReactNode } from "react";
import type {
  QueryResponse,
  ResultMetadata,
  SectionRow,
} from "../../../api/types";
import { Stat } from "../../../design-system";
import type { DisplayMode } from "../../../displayMode";
import {
  formatAverageValue,
  formatCompactDate,
  formatValue,
  trimProseTrailingZeroes,
} from "../../tableFormatting";
import EntityIdentity from "../primitives/EntityIdentity";
import RawDetailToggle from "../primitives/RawDetailToggle";
import ResultHero from "../primitives/ResultHero";
import ResultTable, {
  type ResultTableColumn,
  type ResultTableFooterRow,
} from "../primitives/ResultTable";
import {
  resultTableSourceKeys,
  rowsHaveAdditionalDetailFields,
} from "../primitives/detailTables";
import { hasPinnedEntity } from "./entityBinding";
import styles from "./GameLogResult.module.css";

type GameLogMode = "auto" | "player" | "team";

interface Props {
  data: QueryResponse;
  sectionKey?: string;
  summaryKey?: string;
  fallbackSectionKey?: string;
  mode?: GameLogMode;
  metricKey?: string;
  preserveOrder?: boolean;
  showSummaryStrip?: boolean;
  rawDetailTitle?: string;
  detailSectionKeys?: string[];
  collapseToDetail?: boolean;
  displayMode?: DisplayMode;
  afterHero?: ReactNode;
}

interface SummaryItem {
  key: string;
  label: string;
  value: string;
}

const PLAYER_STAT_COLUMNS = [
  "minutes",
  "pts",
  "reb",
  "ast",
  "fg",
  "fg3",
  "ft",
  "stl",
  "blk",
  "tov",
  "plus_minus",
  "ts_pct",
  "efg_pct",
];

const TEAM_STAT_COLUMNS = [
  "pts",
  "opponent_pts",
  "margin",
  "reb",
  "ast",
  "fg3m",
  "fg",
  "fg3",
  "ft",
  "tov",
  "stl",
  "blk",
  "oreb",
  "dreb",
];

const FOOTER_STAT_COLUMNS = new Set([
  ...PLAYER_STAT_COLUMNS,
  ...TEAM_STAT_COLUMNS,
]);

const TABLE_LABELS: Record<string, string> = {
  ast: "AST",
  blk: "BLK",
  date: "Date",
  dreb: "DRB",
  efg_pct: "eFG%",
  fg: "FG",
  fg3m: "3PM",
  fg3: "3P",
  ft: "FT",
  location: "",
  margin: "Margin",
  minutes: "MIN",
  oreb: "ORB",
  opponent: "Opp",
  plus_minus: "+/-",
  pts: "PTS",
  opponent_pts: "Opp PTS",
  reb: "REB",
  score: "Score",
  stl: "STL",
  team: "TM",
  tov: "TOV",
  ts_pct: "TS%",
  wl: "W/L",
};

const COMPOSITE_STATS: Record<
  string,
  { made: string; attempt: string; pct: string }
> = {
  fg: { made: "fgm", attempt: "fga", pct: "fg_pct" },
  fg3: { made: "fg3m", attempt: "fg3a", pct: "fg3_pct" },
  ft: { made: "ftm", attempt: "fta", pct: "ft_pct" },
};

export default function GameLogResult({
  data,
  sectionKey = "game_log",
  summaryKey = "summary",
  fallbackSectionKey,
  mode = "auto",
  metricKey,
  preserveOrder = false,
  showSummaryStrip = true,
  rawDetailTitle,
  detailSectionKeys = [],
  collapseToDetail = false,
  displayMode = "public",
  afterHero,
}: Props) {
  const rawRows = sectionRows(data, sectionKey, fallbackSectionKey);
  const rows = orderedRows(rawRows, preserveOrder);
  const summary = data.result?.sections?.[summaryKey]?.[0];
  if (rows.length === 0 && !summary) return null;

  const resolvedMode = gameLogMode(rows, mode);
  const metrics = metricColumns(rows, data.result?.metadata, metricKey);
  const columns = tableColumns(rows, data, resolvedMode, metrics);
  const footerRows = summary ? tableFooters(rows, summary) : [];
  const displayedDetailKeys = resultTableSourceKeys(columns);
  if (
    resolvedMode === "player" &&
    hasPinnedEntity(data.result?.metadata, "player")
  ) {
    for (const key of ["player", "player_name", "player_id"]) {
      displayedDetailKeys.add(key);
    }
  }
  const hasAdditionalGameLogFields = rowsHaveAdditionalDetailFields(
    rows,
    displayedDetailKeys,
  );
  const items = summary
    ? summaryItems(summary, {
        hideMinutes:
          (data.route ?? data.result?.metadata?.route) === "game_summary" &&
          resolvedMode === "team",
      })
    : contextItems(data, rows);
  const countSentence = countHeadline(data.result?.metadata);
  const answerSentence = answerHeadline(data.result?.metadata);
  const finderSentence = finderCountHeadline(data, rows, resolvedMode);
  const heroSentence = proseHeadline(
    countSentence ?? answerSentence ?? finderSentence,
  );
  const showStrip = showSummaryStrip && !countSentence && items.length > 0;
  const showDetails = rows.length > 0;
  const collapseRowsToDetail =
    collapseToDetail && displayMode === "public" && rows.length > 0;

  return (
    <section className={styles.pattern} aria-label="Game log result">
      {heroSentence && <ResultHero sentence={heroSentence} tone="neutral" />}
      {afterHero}
      {showStrip && (
        <div className={styles.summaryStrip} aria-label="Game-log averages">
          {items.map((item) => (
            <Stat
              className={styles.summaryItem}
              key={item.key}
              label={item.label}
              value={item.value}
            />
          ))}
        </div>
      )}
      {rows.length > 0 && !collapseRowsToDetail && (
        <ResultTable
          rows={rows}
          columns={columns}
          highlightColumnKeys={metrics}
          footerRows={footerRows}
          ariaLabel="Game log"
          getRowKey={rowKey}
          rowLimit={displayMode === "public" ? 12 : undefined}
          rowNoun="games"
        />
      )}
      {showDetails && collapseRowsToDetail && (
        <RawDetailToggle
          title={rawDetailTitle ?? "Game Detail"}
          rows={rows}
          collapsedLabel="Show game detail"
          expandedLabel="Hide game detail"
        />
      )}
      {showDetails &&
        !collapseRowsToDetail &&
        rawDetailTitle &&
        hasAdditionalGameLogFields && (
        <RawDetailToggle
          title={rawDetailTitle}
          rows={rows}
          collapsedLabel="Show additional columns"
          expandedLabel="Hide additional columns"
        />
      )}
      {showDetails &&
        detailSectionKeys.map((key) => {
          const detailRows = data.result?.sections?.[key] ?? [];
          if (detailRows.length === 0) return null;
          const labels = detailToggleLabels(key);
          return (
            <RawDetailToggle
              key={key}
              title={detailTitle(key)}
              rows={detailRows}
              collapsedLabel={labels.collapsed}
              expandedLabel={labels.expanded}
            />
          );
        })}
    </section>
  );
}

function countHeadline(metadata: ResultMetadata | undefined): string | null {
  if (typeof metadata?.primary_count !== "number") return null;
  const phrase = metadata.count_phrase;
  return typeof phrase === "string" && phrase.trim() ? phrase.trim() : null;
}

function answerHeadline(metadata: ResultMetadata | undefined): string | null {
  const phrase = metadata?.answer_phrase;
  return typeof phrase === "string" && phrase.trim() ? phrase.trim() : null;
}

function finderCountHeadline(
  data: QueryResponse,
  rows: SectionRow[],
  mode: Exclude<GameLogMode, "auto">,
): string | null {
  if (mode !== "player") return null;
  if (data.result?.query_class !== "finder") return null;
  if (rows.length === 0) return null;

  const player = playerNameForRows(data.result?.metadata, rows[0]);
  const condition = thresholdPhraseFromQuery(data.query);
  const timeframe = finderTimeframe(data.query, rows[0], data.result?.metadata);
  const gameNoun = rows.length === 1 ? "game" : "games";
  const conditionPhrase = condition ? ` with ${condition}` : " matching";
  return `${player} had ${rows.length} ${gameNoun}${conditionPhrase}${timeframe}.`;
}

function playerNameForRows(
  metadata: ResultMetadata | undefined,
  row: SectionRow | undefined,
): string {
  return (
    metadata?.player_context?.player_name ??
    textValue(row, "player_name") ??
    textValue(row, "player") ??
    "This player"
  );
}

function thresholdPhraseFromQuery(query: string): string | null {
  const match = query.match(
    /\b(\d+)\s*\+\s*(threes?|3s|three[- ]pointers?|points?|pts|rebounds?|rebs?|assists?|asts?|steals?|blocks?|turnovers?)\b/i,
  );
  if (!match) return null;

  return `${match[1]}+ ${thresholdNoun(match[2])}`;
}

function thresholdNoun(value: string): string {
  const normalized = value.toLowerCase();
  if (normalized === "3s" || normalized.startsWith("three")) return "threes";
  if (normalized === "pts") return "points";
  if (normalized === "reb" || normalized === "rebs") return "rebounds";
  if (normalized === "ast" || normalized === "asts") return "assists";
  return normalized.endsWith("s") ? normalized : `${normalized}s`;
}

function finderTimeframe(
  query: string,
  row: SectionRow | undefined,
  metadata: ResultMetadata | undefined,
): string {
  if (/\bthis\s+(?:season|year)\b/i.test(query)) return " this season";
  const season = textValue(row, "season") ?? metadata?.season;
  return typeof season === "string" && season.trim() ? ` in ${season}` : "";
}

function proseHeadline(value: string | null): string | null {
  return value ? trimProseTrailingZeroes(value) : null;
}

function tableColumns(
  rows: SectionRow[],
  data: QueryResponse,
  mode: Exclude<GameLogMode, "auto">,
  primaryMetricKeys: string[] = [],
): Array<ResultTableColumn<SectionRow>> {
  const hidePinnedPlayerColumn =
    mode === "player" && hasPinnedEntity(data.result?.metadata, "player");
  const primaryMetrics = new Set(primaryMetricKeys);
  const columns: Array<ResultTableColumn<SectionRow>> = [
    {
      key: "rank",
      sourceKeys: ["rank"],
      header: "#",
      align: "center",
      mobilePriority: "secondary",
      render: (_row, index) => index + 1,
    },
  ];

  if (mode === "player") {
    if (!hidePinnedPlayerColumn) {
      columns.push({
        key: "player",
        sourceKeys: ["player_name", "player", "player_id", "team_abbr"],
        header: "Player",
        render: playerCell,
      });
    }
    columns.push(
      {
        key: "date",
        sourceKeys: ["game_date"],
        header: TABLE_LABELS.date,
        mobilePriority: "primary",
        render: (row) => formatCompactDate(textValue(row, "game_date")),
      },
      {
        key: "team",
        sourceKeys: ["team", "team_name", "team_abbr", "team_id"],
        header: TABLE_LABELS.team,
        mobilePriority: "primary",
        render: (row) => teamCell(row, data),
      },
    );
  } else {
    columns.push(
      {
        key: "date",
        sourceKeys: ["game_date"],
        header: TABLE_LABELS.date,
        mobilePriority: "primary",
        render: (row) => formatCompactDate(textValue(row, "game_date")),
      },
      {
        key: "team",
        sourceKeys: ["team", "team_name", "team_abbr", "team_id"],
        header: "Team",
        mobilePriority: "primary",
        render: (row) => teamCell(row, data),
      },
    );
  }

  columns.push(
    {
      key: "location",
      sourceKeys: ["is_home", "is_away", "location"],
      header: TABLE_LABELS.location,
      align: "center",
      mobilePriority: "secondary",
      render: locationCell,
    },
    {
      key: "opponent",
      sourceKeys: [
        "opponent",
        "opponent_team_name",
        "opponent_team_abbr",
        "opponent_team_id",
      ],
      header: TABLE_LABELS.opponent,
      mobilePriority: "primary",
      render: (row) => opponentCell(row, data),
    },
  );

  if (hasScoreColumn(rows, mode)) {
    columns.push({
      key: "score",
      sourceKeys: [
        "team_score",
        "pts_team",
        "team_pts",
        "pts",
        "opponent_score",
        "opponent_pts",
        "opp_pts",
      ],
      header: TABLE_LABELS.score,
      align: "center",
      mobilePriority: "primary",
      render: scoreCell,
    });
  }

  if (rows.some((row) => hasValue(row.wl))) {
    columns.push({
      key: "wl",
      sourceKeys: ["wl"],
      header: TABLE_LABELS.wl,
      align: "center",
      mobilePriority: "primary",
      render: (row) => textValue(row, "wl")?.toUpperCase() ?? "—",
    });
  }

  const statColumns =
    mode === "player" ? PLAYER_STAT_COLUMNS : TEAM_STAT_COLUMNS;
  for (const key of statColumns) {
    if (!hasStatColumn(rows, key)) continue;
    columns.push(statColumn(key, primaryMetrics.has(key)));
  }

  return columns;
}

function statColumn(
  key: string,
  isPrimaryMetric = false,
): ResultTableColumn<SectionRow> {
  return {
    key,
    sourceKeys: statSourceKeys(key),
    header: TABLE_LABELS[key] ?? key,
    numeric: true,
    mobilePriority: isPrimaryMetric ? "primary" : "secondary",
    render: (row) => statValue(row, key),
  };
}

function statSourceKeys(key: string): string[] {
  const composite = COMPOSITE_STATS[key];
  if (composite) return [composite.made, composite.attempt, composite.pct];
  if (key === "margin") {
    return ["margin", "plus_minus", "pts", "opponent_pts", "opp_pts"];
  }
  if (key === "opponent_pts") {
    return ["opponent_pts", "opp_pts", "opponent_score", "pts", "plus_minus"];
  }
  return [key];
}

function tableFooters(
  rows: SectionRow[],
  summary: SectionRow | undefined,
): Array<ResultTableFooterRow<SectionRow>> {
  return [
    {
      key: "average",
      label: "Average",
      getValue: (column) => footerValue("avg", column.key, rows, summary),
    },
    {
      key: "total",
      label: "Total",
      getValue: (column) => footerValue("sum", column.key, rows, summary),
    },
  ];
}

function footerValue(
  kind: "avg" | "sum",
  key: string,
  rows: SectionRow[],
  summary: SectionRow | undefined,
): ReactNode {
  if (COMPOSITE_STATS[key]) {
    return compositeFooterValue(kind, key, rows, summary);
  }
  if (!FOOTER_STAT_COLUMNS.has(key)) return null;

  const summaryKey = `${summaryPrefix(key)}_${kind}`;
  if (summary && hasValue(summary[summaryKey])) {
    return formatStatValue(summary[summaryKey], key, kind);
  }

  const values = rows
    .map((row) => numericStatValue(row, key))
    .filter((value): value is number => typeof value === "number");
  if (values.length === 0) return null;

  const total = values.reduce((sum, value) => sum + value, 0);
  const value = kind === "avg" ? total / values.length : total;
  return formatStatValue(value, key, kind);
}

function compositeFooterValue(
  kind: "avg" | "sum",
  key: string,
  rows: SectionRow[],
  summary: SectionRow | undefined,
): string | null {
  const config = COMPOSITE_STATS[key];
  const madeKey = `${config.made}_${kind}`;
  const attemptKey = `${config.attempt}_${kind}`;

  if (summary && hasValue(summary[madeKey]) && hasValue(summary[attemptKey])) {
    return `${formatValue(summary[madeKey], madeKey)}-${formatValue(
      summary[attemptKey],
      attemptKey,
    )}`;
  }

  const made = numericValues(rows, config.made);
  const attempts = numericValues(rows, config.attempt);
  if (made.length === 0 || attempts.length === 0) return null;

  const madeTotal = made.reduce((sum, value) => sum + value, 0);
  const attemptTotal = attempts.reduce((sum, value) => sum + value, 0);
  if (kind === "sum") {
    return `${formatValue(madeTotal, config.made)}-${formatValue(
      attemptTotal,
      config.attempt,
    )}`;
  }

  return `${formatAverageValue(madeTotal / made.length, config.made)}-${formatAverageValue(
    attemptTotal / attempts.length,
    config.attempt,
  )}`;
}

function summaryItems(
  summary: SectionRow | undefined,
  options?: { hideMinutes?: boolean },
): SummaryItem[] {
  if (!summary) return [];
  const items: SummaryItem[] = [];
  addSummaryItem(items, summary, "games", "GP");
  addRecordSummaryItem(items, summary);
  addSummaryItem(items, summary, "pts_avg", "PPG");
  addSummaryItem(items, summary, "reb_avg", "RPG");
  addSummaryItem(items, summary, "ast_avg", "APG");
  if (!options?.hideMinutes) {
    addSummaryItem(items, summary, "minutes_avg", "MIN");
  }
  return items;
}

function addRecordSummaryItem(items: SummaryItem[], row: SectionRow) {
  if (!hasValue(row.wins) && !hasValue(row.losses)) return;
  items.push({
    key: "record",
    label: "Record",
    value: `${formatValue(row.wins, "wins")}-${formatValue(row.losses, "losses")}`,
  });
}

function addSummaryItem(
  items: SummaryItem[],
  row: SectionRow,
  key: string,
  label: string,
) {
  if (!hasValue(row[key])) return;
  items.push({ key, label, value: formatValue(row[key], key) });
}

function sectionRows(
  data: QueryResponse,
  sectionKey: string,
  fallbackSectionKey: string | undefined,
): SectionRow[] {
  const rows = data.result?.sections?.[sectionKey] ?? [];
  if (rows.length > 0 || !fallbackSectionKey) return rows;
  return data.result?.sections?.[fallbackSectionKey] ?? [];
}

function orderedRows(rows: SectionRow[], preserveOrder: boolean): SectionRow[] {
  if (preserveOrder) return [...rows];
  return [...rows].sort((a, b) => {
    const aDate = textValue(a, "game_date");
    const bDate = textValue(b, "game_date");
    if (aDate && bDate && aDate !== bDate) return bDate.localeCompare(aDate);
    return 0;
  });
}

function gameLogMode(
  rows: SectionRow[],
  mode: GameLogMode,
): Exclude<GameLogMode, "auto"> {
  if (mode !== "auto") return mode;
  return rows.some(
    (row) =>
      hasValue(row.player_name) ||
      hasValue(row.player) ||
      hasValue(row.player_id),
  )
    ? "player"
    : "team";
}

function metricColumns(
  rows: SectionRow[],
  metadata: ResultMetadata | undefined,
  explicitMetric: string | undefined,
): string[] {
  const metrics: string[] = [];
  addMetricColumn(metrics, rows, explicitMetric);

  const stat = metadataText(metadata, "stat");
  addMetricColumn(metrics, rows, stat);

  for (const condition of metadataConditions(metadata)) {
    addMetricColumn(metrics, rows, condition.stat);
  }

  const occurrence = metadata?.occurrence_event;
  if (
    occurrence &&
    typeof occurrence === "object" &&
    !Array.isArray(occurrence)
  ) {
    const event = occurrence as Record<string, unknown>;
    if (event.special_event === "triple_double") {
      for (const key of ["pts", "reb", "ast"]) addMetricColumn(metrics, rows, key);
    } else if (typeof event.stat === "string") {
      addMetricColumn(metrics, rows, event.stat);
    }
  }

  return Array.from(new Set(metrics));
}

function addMetricColumn(
  metrics: string[],
  rows: SectionRow[],
  key: string | null | undefined,
) {
  const mapped = metricColumnKey(key);
  if (!mapped) return;
  if (rows.some((row) => hasStatColumn([row], mapped))) metrics.push(mapped);
}

function metricColumnKey(key: string | null | undefined): string | null {
  if (!key) return null;
  const normalized = key.trim().toLowerCase();
  const aliases: Record<string, string> = {
    fg3a: "fg3",
    fg3m: "fg3m",
    fga: "fg",
    fgm: "fg",
    fta: "ft",
    ftm: "ft",
    opp_pts: "opponent_pts",
  };
  return aliases[normalized] ?? normalized;
}

function metadataConditions(
  metadata: ResultMetadata | undefined,
): Array<{ stat: string }> {
  const conditions: Array<{ stat: string }> = [];
  for (const key of ["threshold_conditions", "extra_conditions"]) {
    const raw = metadata?.[key];
    if (!Array.isArray(raw)) continue;
    for (const condition of raw) {
      if (!condition || typeof condition !== "object") continue;
      const conditionRow = condition as Record<string, unknown>;
      if (typeof conditionRow.stat === "string") {
        conditions.push({ stat: conditionRow.stat });
      }
    }
  }
  return conditions;
}

function playerCell(row: SectionRow): ReactNode {
  return (
    <EntityIdentity
      kind="player"
      playerId={identityId(row.player_id)}
      playerName={textValue(row, "player_name") ?? textValue(row, "player")}
      teamAbbr={textValue(row, "team_abbr")}
      size="sm"
    />
  );
}

function teamCell(row: SectionRow, data: QueryResponse): ReactNode {
  const teamContext = data.result?.metadata?.team_context;
  return (
    <span className={styles.teamCell}>
      <EntityIdentity
        kind="team"
        teamId={identityId(row.team_id) ?? teamContext?.team_id}
        teamAbbr={textValue(row, "team_abbr") ?? teamContext?.team_abbr}
        teamName={
          textValue(row, "team_name") ??
          textValue(row, "team") ??
          teamContext?.team_name
        }
        size="sm"
      />
    </span>
  );
}

function opponentCell(row: SectionRow, data: QueryResponse): ReactNode {
  const opponentContext = data.result?.metadata?.opponent_context;
  return (
    <span className={styles.teamCell}>
      <EntityIdentity
        kind="team"
        teamId={identityId(row.opponent_team_id) ?? opponentContext?.team_id}
        teamAbbr={
          textValue(row, "opponent_team_abbr") ??
          textValue(row, "opponent") ??
          opponentContext?.team_abbr
        }
        teamName={
          textValue(row, "opponent_team_name") ??
          textValue(row, "opponent") ??
          opponentContext?.team_name
        }
        size="sm"
      />
    </span>
  );
}

function hasScoreColumn(
  rows: SectionRow[],
  mode: Exclude<GameLogMode, "auto">,
): boolean {
  return rows.some((row) => {
    if (hasValue(row.team_score) && hasValue(row.opponent_score)) return true;
    if (
      mode === "team" &&
      teamScoreValue(row) !== null &&
      opponentScoreValue(row) !== null
    ) {
      return true;
    }
    return false;
  });
}

function scoreCell(row: SectionRow): string {
  const teamScore = teamScoreValue(row);
  const opponentScore = opponentScoreValue(row);

  if (teamScore === null || opponentScore === null) return "—";
  return `${formatValue(teamScore, "team_score")}-${formatValue(
    opponentScore,
    "opponent_score",
  )}`;
}

function locationCell(row: SectionRow): string {
  if (isTruthyFlag(row.is_away)) return "@";
  if (isTruthyFlag(row.is_home)) return "vs";
  return "—";
}

function hasStatColumn(rows: SectionRow[], key: string): boolean {
  const config = COMPOSITE_STATS[key];
  if (config) {
    return rows.some(
      (row) =>
        hasValue(row[config.made]) ||
        hasValue(row[config.attempt]) ||
        hasValue(row[config.pct]),
    );
  }
  if (key === "margin" || key === "opponent_pts") {
    return rows.some((row) => numericStatValue(row, key) !== null);
  }
  return rows.some((row) => hasValue(row[key]));
}

function statValue(row: SectionRow, key: string): ReactNode {
  const config = COMPOSITE_STATS[key];
  if (config) {
    return madeAttemptStat(row, config.made, config.attempt, config.pct);
  }
  if (key === "margin" || key === "opponent_pts") {
    return formatStatValue(numericStatValue(row, key), key);
  }
  return formatStatValue(row[key], key);
}

function madeAttemptStat(
  row: SectionRow,
  madeKey: string,
  attemptKey: string,
  pctKey: string,
): string {
  if (hasValue(row[madeKey]) && hasValue(row[attemptKey])) {
    return `${formatValue(row[madeKey], madeKey)}-${formatValue(
      row[attemptKey],
      attemptKey,
    )}`;
  }
  if (hasValue(row[pctKey])) return formatValue(row[pctKey], pctKey);
  if (hasValue(row[madeKey])) return formatValue(row[madeKey], madeKey);
  return "—";
}

function formatStatValue(
  value: unknown,
  key: string,
  kind: "avg" | "sum" = "sum",
): string {
  if ((key === "plus_minus" || key === "margin") && typeof value === "number") {
    const formatted =
      kind === "avg" ? formatAverageValue(value, key) : formatValue(value, key);
    return value > 0 ? `+${formatted}` : formatted;
  }
  return kind === "avg"
    ? formatAverageValue(value, key)
    : formatValue(value, key);
}

function summaryPrefix(key: string): string {
  return key === "minutes" ? "minutes" : key;
}

function numericValues(rows: SectionRow[], key: string): number[] {
  return rows
    .map((row) => row[key])
    .filter((value): value is number => typeof value === "number");
}

function numericStatValue(row: SectionRow, key: string): number | null {
  if (key === "margin") return marginValue(row);
  if (key === "opponent_pts") return opponentScoreValue(row);
  return numericValue(row, key);
}

function teamScoreValue(row: SectionRow): number | null {
  return (
    numericValue(row, "team_score") ??
    numericValue(row, "pts_team") ??
    numericValue(row, "team_pts") ??
    numericValue(row, "pts")
  );
}

function opponentScoreValue(row: SectionRow): number | null {
  const explicit =
    numericValue(row, "opponent_score") ??
    numericValue(row, "opponent_pts") ??
    numericValue(row, "opp_pts");
  if (explicit !== null) return explicit;

  const teamScore = teamScoreValue(row);
  const margin = marginValue(row, false);
  if (teamScore === null || margin === null) return null;
  return teamScore - margin;
}

function marginValue(row: SectionRow, allowDerived = true): number | null {
  const explicit =
    numericValue(row, "margin") ?? numericValue(row, "plus_minus");
  if (explicit !== null) return explicit;
  if (!allowDerived) return null;

  const teamScore = teamScoreValue(row);
  const opponentScore =
    numericValue(row, "opponent_score") ??
    numericValue(row, "opponent_pts") ??
    numericValue(row, "opp_pts");
  if (teamScore === null || opponentScore === null) return null;
  return teamScore - opponentScore;
}

function rowKey(row: SectionRow, index: number): string {
  return [row.game_id, row.player_id, row.team_id, row.game_date, index]
    .filter(hasValue)
    .join("-");
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

function numericValue(row: SectionRow, key: string): number | null {
  const value = row[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function isTruthyFlag(value: unknown): boolean {
  if (value === true || value === 1) return true;
  if (typeof value === "string") {
    return ["1", "true", "yes", "y"].includes(value.trim().toLowerCase());
  }
  return false;
}

function hasValue(value: unknown): boolean {
  return value !== null && value !== undefined && value !== "";
}

function contextItems(data: QueryResponse, rows: SectionRow[]): SummaryItem[] {
  const metadata = data.result?.metadata;
  const items: SummaryItem[] = [
    {
      key: "games",
      label: rows.length === 1 ? "Game" : "Games",
      value: formatValue(rows.length, "games"),
    },
  ];

  const condition = conditionText(metadata);
  if (condition) {
    items.push({ key: "condition", label: "Filter", value: condition });
  }

  const season = seasonText(metadata);
  if (season) items.push({ key: "season", label: "Season", value: season });

  const seasonType = metadataText(metadata, "season_type");
  if (seasonType) {
    items.push({ key: "season_type", label: "Type", value: seasonType });
  }

  return items;
}

function conditionText(metadata: ResultMetadata | undefined): string | null {
  const conditions: string[] = [];
  for (const key of ["threshold_conditions", "extra_conditions"]) {
    const raw = metadata?.[key];
    if (!Array.isArray(raw)) continue;
    for (const condition of raw) {
      if (!condition || typeof condition !== "object") continue;
      const conditionRow = condition as Record<string, unknown>;
      if (typeof conditionRow.stat !== "string") continue;
      conditions.push(
        formatCondition(
          conditionRow.stat,
          typeof conditionRow.min_value === "number"
            ? conditionRow.min_value
            : null,
          typeof conditionRow.max_value === "number"
            ? conditionRow.max_value
            : null,
        ),
      );
    }
  }

  if (conditions.length === 0) {
    const occurrenceEvent = metadata?.occurrence_event;
    if (
      occurrenceEvent &&
      typeof occurrenceEvent === "object" &&
      !Array.isArray(occurrenceEvent)
    ) {
      const event = occurrenceEvent as Record<string, unknown>;
      if (typeof event.stat === "string") {
        conditions.push(
          formatCondition(
            event.stat,
            typeof event.min_value === "number" ? event.min_value : null,
            typeof event.max_value === "number" ? event.max_value : null,
          ),
        );
      }
    }
  }

  if (conditions.length === 0) {
    const stat = metadataText(metadata, "stat");
    if (stat) {
      conditions.push(
        formatCondition(
          stat,
          metadataNumber(metadata, "min_value"),
          metadataNumber(metadata, "max_value"),
        ),
      );
    }
  }

  return conditions.length > 0
    ? Array.from(new Set(conditions)).join(", ")
    : null;
}

function formatCondition(
  stat: string,
  minValue: number | null,
  maxValue: number | null,
): string {
  if (stat === "opponent_pts") {
    const minDisplay =
      minValue !== null ? formatThresholdValue(minValue, stat) : null;
    const maxDisplay =
      maxValue !== null ? formatThresholdValue(maxValue, stat) : null;
    if (minDisplay !== null && maxDisplay !== null) {
      return `OPP ${minDisplay}-${maxDisplay} PTS`;
    }
    if (minDisplay !== null) return `OPP >= ${minDisplay} PTS`;
    if (maxDisplay !== null) return `OPP <= ${maxDisplay} PTS`;
    return "OPP PTS";
  }

  const label = TABLE_LABELS[stat] ?? stat.toUpperCase();
  if (minValue !== null && maxValue !== null) {
    return `${formatValue(minValue, stat)}-${formatValue(maxValue, stat)} ${label}`;
  }
  if (minValue !== null) return `${formatValue(minValue, stat)}+ ${label}`;
  if (maxValue !== null) return `<= ${formatValue(maxValue, stat)} ${label}`;
  return label;
}

function formatThresholdValue(value: number, stat: string): string {
  const rounded = Math.round(value);
  if (Math.abs(value + 0.0001 - rounded) < 0.001) {
    return formatValue(rounded, stat);
  }
  return formatValue(value, stat);
}

function seasonText(metadata: ResultMetadata | undefined): string | null {
  const start = metadataText(metadata, "start_season");
  const end = metadataText(metadata, "end_season");
  if (start && end) return start === end ? start : `${start} to ${end}`;
  return metadataText(metadata, "season") ?? start ?? end;
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

function metadataNumber(
  metadata: ResultMetadata | undefined,
  key: string,
): number | null {
  const value = metadata?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function detailTitle(key: string): string {
  const labels: Record<string, string> = {
    by_season: "By Season Detail",
    summary: "Summary Detail",
    top_performers: "Top Performers Detail",
  };
  return labels[key] ?? `${key.replace(/_/g, " ")} Detail`;
}

function detailToggleLabels(key: string): {
  collapsed: string;
  expanded: string;
} {
  const labels: Record<string, { collapsed: string; expanded: string }> = {
    top_performers: {
      collapsed: "Show top performer details",
      expanded: "Hide top performer details",
    },
  };
  return (
    labels[key] ?? {
      collapsed: "Show additional columns",
      expanded: "Hide additional columns",
    }
  );
}
