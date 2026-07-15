import { type CSSProperties, type ReactNode, useState } from "react";
import type { QueryResponse } from "../api/types";
import {
  Avatar,
  Badge,
  Button,
  ResultEnvelopeShell,
  TeamBadge,
  type BadgeVariant,
} from "../design-system";
import { normalizeDisplayMode, type DisplayModeInput } from "../displayMode";
import { resolvePlayerIdentity, resolveTeamIdentity } from "../lib/identity";
import CopyButton from "./CopyButton";
import {
  formatReadableDateRange,
  productFacingNotice,
} from "./noResultDisplayUtils";
import RawJsonToggle from "./RawJsonToggle";
import { formatLongDateRange } from "./tableFormatting";
import styles from "./ResultEnvelope.module.css";

interface Props {
  data: QueryResponse;
  onAlternateSelect?: (description: string) => void;
  className?: string;
  displayMode?: DisplayModeInput;
}

function statusLabel(status: string): string {
  switch (status) {
    case "ok":
      return "Success";
    case "no_result":
      return "No Result";
    case "error":
      return "Error";
    default:
      return status;
  }
}

function reasonLabel(reason: string | null): string | null {
  if (!reason) return null;
  switch (reason) {
    case "no_match":
      return "no match";
    case "no_data":
      return "data unavailable";
    case "unrouted":
      return "unrecognized query";
    case "ambiguous":
      return "ambiguous entity";
    case "unsupported":
      return "unsupported";
    case "filter_not_supported":
      return "filter not supported";
    case "error":
      return "error";
    default:
      return reason;
  }
}

function routeLabel(route: string): string {
  return route.replace(/_/g, " ");
}

function isTeamAbbreviation(value: string): boolean {
  return /^[A-Z]{2,4}$/.test(value);
}

const STATUS_VARIANTS: Record<string, BadgeVariant> = {
  ok: "success",
  no_result: "warning",
  error: "danger",
};

type ContextItem = {
  key: string;
  label: string;
  value: string;
};

const BASE_SCOPE_CHIP_KEYS: ReadonlySet<string> = new Set([
  "player",
  "players",
  "team",
  "teams",
  "season",
  "opponent",
  "split",
]);

type ContextChip = {
  key: string;
  label: string;
  value: string;
  variant?: BadgeVariant;
  identity?: "player" | "team";
  imageUrl?: string | null;
  identityName?: string | null;
  abbreviation?: string | null;
  styleVars?: CSSProperties;
};

interface ResultContextSummaryProps {
  data: QueryResponse;
  className?: string;
}

export function ResultContextSummary({
  data,
  className,
}: ResultContextSummaryProps) {
  const metadata = data.result?.metadata;
  const appliedFilters = appliedFilterLabels(metadata?.applied_filters);
  const rawNotes = uniqueStrings([
    ...data.notes,
    ...(data.result?.notes ?? []),
    ...metadataNotes(metadata?.notes),
  ]);
  const classifiedNotes = classifyNoticeItems(rawNotes);
  const classifiedCaveats = classifyNoticeItems(
    uniqueStrings([...data.caveats, ...(data.result?.caveats ?? [])]),
  );
  const contextItems = uniqueContextItems([
    ...buildContextItems(metadata, appliedFilters),
    ...classifiedNotes.context,
    ...classifiedCaveats.context,
  ]);
  const allContextChips = buildContextChips(
    metadata,
    appliedFilters,
    contextItems,
    true,
  );
  // The public answer hero already names player, team, season, opponent,
  // and split type. Drop those scope chips here so the public context
  // strip carries only non-obvious trust/scope information (applied
  // filters, date ranges, included opponents, "without X", etc.).
  const contextChips = allContextChips.filter(
    (chip) => !BASE_SCOPE_CHIP_KEYS.has(chip.key),
  );
  const caveatItems = classifiedCaveats.remaining.map(displayNoticeText);

  if (contextChips.length === 0 && caveatItems.length === 0) return null;

  return (
    <div className={[styles.publicContext, className].filter(Boolean).join(" ")}>
      {contextChips.length > 0 && (
        <div className={styles.publicContextChips} aria-label="Result context">
          {contextChips.map((chip) => (
            <ContextChipBadge chip={chip} key={chip.key} />
          ))}
        </div>
      )}
      {caveatItems.length > 0 && (
        <div className={[styles.infoBlock, styles.caveatsBlock].join(" ")}>
          <div className={styles.infoBlockLabel}>Caveats</div>
          <ul>
            {caveatItems.map((caveat, i) => (
              <li key={i}>{caveat}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function ResultEnvelope({
  data,
  onAlternateSelect,
  className,
  displayMode,
}: Props) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const normalizedDisplayMode = normalizeDisplayMode(displayMode);
  const isDebugMode = normalizedDisplayMode === "debug";
  const metadata = data.result?.metadata;
  const queryClass = data.result?.query_class;
  const appliedFilters = appliedFilterLabels(metadata?.applied_filters);
  const rawNotes = uniqueStrings([
    ...data.notes,
    ...(data.result?.notes ?? []),
    ...metadataNotes(metadata?.notes),
  ]);
  const classifiedNotes = classifyNoticeItems(rawNotes);
  const classifiedCaveats = classifyNoticeItems(
    uniqueStrings([...data.caveats, ...(data.result?.caveats ?? [])]),
  );
  const contextItems = uniqueContextItems([
    ...buildContextItems(metadata, appliedFilters),
    ...classifiedNotes.context,
    ...classifiedCaveats.context,
  ]);
  const noteItems =
    isDebugMode && data.result_status !== "no_result"
      ? classifiedNotes.remaining
      : [];
  const caveatItems = classifiedCaveats.remaining.map(displayNoticeText);
  const showContext = isDebugMode && contextItems.length > 0;
  const showNotes = noteItems.length > 0;
  const showCaveats = isDebugMode && caveatItems.length > 0;
  const rawCaveats = uniqueStrings([
    ...data.caveats,
    ...(data.result?.caveats ?? []),
  ]);
  const contextChips = buildContextChips(
    metadata,
    appliedFilters,
    contextItems,
    false,
  );
  const details = (
    <ResultDetails
      data={data}
      metadata={metadata}
      queryClass={queryClass}
      appliedFilters={appliedFilters}
      rawNotes={rawNotes}
      rawCaveats={rawCaveats}
    />
  );

  return (
    <ResultEnvelopeShell
      className={className}
      meta={
        isDebugMode ? (
          <>
            <Badge
              variant={STATUS_VARIANTS[data.result_status] ?? "danger"}
              uppercase
            >
              {statusLabel(data.result_status)}
            </Badge>
            {data.route && (
              <Badge className={styles.routeBadge} variant="neutral" size="sm">
                {routeLabel(data.route)}
              </Badge>
            )}
            {queryClass && queryClass !== data.route && (
              <Badge className={styles.routeBadge} variant="neutral" size="sm">
                {queryClass}
              </Badge>
            )}
            {data.result_reason && (
              <span className={[styles.muted, styles.resultReason].join(" ")}>
                {reasonLabel(data.result_reason)}
              </span>
            )}
            {data.current_through && (
              <>
                <span className={styles.separator} />
                <span className={styles.freshness}>
                  Data through <strong>{data.current_through}</strong>
                </span>
              </>
            )}
          </>
        ) : null
      }
      query={isDebugMode ? <>&ldquo;{data.query}&rdquo;</> : null}
      context={
        isDebugMode && contextChips.length > 0 ? (
          <>
            {contextChips.map((chip) => (
              <ContextChipBadge chip={chip} key={chip.key} />
            ))}
          </>
        ) : null
      }
      notices={
        showContext || showNotes || showCaveats ? (
          <>
            {showContext && (
              <div
                className={[styles.infoBlock, styles.contextBlock].join(" ")}
              >
                <div className={styles.infoBlockLabel}>Context</div>
                <ul>
                  {contextItems.map((item) => (
                    <li key={item.key}>
                      <span className={styles.noticeItemLabel}>
                        {item.label}:
                      </span>{" "}
                      {item.value}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {showNotes && (
              <div className={[styles.infoBlock, styles.notesBlock].join(" ")}>
                <div className={styles.infoBlockLabel}>Notes</div>
                <ul>
                  {noteItems.map((note, i) => (
                    <li key={i}>{note}</li>
                  ))}
                </ul>
              </div>
            )}
            {showCaveats && (
              <div
                className={[styles.infoBlock, styles.caveatsBlock].join(" ")}
              >
                <div className={styles.infoBlockLabel}>Caveats</div>
                <ul>
                  {caveatItems.map((caveat, i) => (
                    <li key={i}>{caveat}</li>
                  ))}
                </ul>
              </div>
            )}
          </>
        ) : null
      }
      alternates={
        data.alternates.length > 0 && onAlternateSelect ? (
          <>
            <span className={styles.alternatesLabel}>Did you mean: </span>
            {data.alternates.map((alt, i) => (
              <Button
                key={i}
                type="button"
                className={styles.alternateChip}
                onClick={() => onAlternateSelect(alt.description)}
                size="sm"
                variant="secondary"
              >
                {alt.description}
              </Button>
            ))}
          </>
        ) : null
      }
    >
      <details
        className={styles.detailsDisclosure}
        data-shortcut-scope="ignore"
        open={detailsOpen}
      >
        <summary
          className={styles.detailsSummary}
          onClick={(event) => {
            event.preventDefault();
            setDetailsOpen((open) => !open);
          }}
        >
          Details
        </summary>
        {detailsOpen && details}
      </details>
    </ResultEnvelopeShell>
  );
}

interface ResultDetailsProps {
  data: QueryResponse;
  metadata: QueryResponse["result"]["metadata"] | undefined;
  queryClass: string | undefined;
  appliedFilters: Array<{ key: string; label: string; value: string }>;
  rawNotes: string[];
  rawCaveats: string[];
}

function ResultDetails({
  data,
  metadata,
  queryClass,
  appliedFilters,
  rawNotes,
  rawCaveats,
}: ResultDetailsProps) {
  const resolvedEntities = resolvedEntityLines(metadata);
  const unsupportedFilters = metadataStringList(metadata?.unsupported_filters);
  const metadataKeys = metadata ? Object.keys(metadata).sort() : [];

  return (
    <div className={styles.detailsBody} aria-label="Result details">
      <div className={styles.detailsActions}>
        <CopyButton text={data.query} label="Copy Query" />
        <CopyButton text={JSON.stringify(data, null, 2)} label="Copy JSON" />
      </div>
      <div className={styles.detailsGrid}>
        <DetailItem label="Route" value={data.route ?? "unrouted"} />
        <DetailItem label="Result status" value={data.result_status} />
        <DetailItem
          label="Result reason"
          value={data.result_reason ?? "none"}
        />
        <DetailItem label="Query class" value={queryClass ?? "unknown"} />
        <DetailItem
          label="Current through"
          value={
            data.current_through ??
            metadataText(metadata, "current_through") ??
            "unknown"
          }
        />
        <DetailItem label="Full query" value={data.query} />
        <DetailList
          label="Applied filters"
          values={appliedFilters.map(
            (filter) => `${filter.label}: ${filter.value}`,
          )}
        />
        <DetailList label="Resolved entities" values={resolvedEntities} />
        <DetailList
          label="Unsupported filters"
          values={unsupportedFilters}
        />
        <DetailList label="Notes" values={rawNotes} />
        <DetailList label="Caveats" values={rawCaveats} />
        <DetailList label="Metadata keys" values={metadataKeys} />
      </div>
      {metadata && (
        <div className={styles.metadataSummary}>
          <div className={styles.detailsLabel}>Raw metadata summary</div>
          <pre>{JSON.stringify(metadata, null, 2)}</pre>
        </div>
      )}
      <RawJsonToggle data={data} variant="inline" />
    </div>
  );
}

function DetailItem({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className={styles.detailItem}>
      <span className={styles.detailsLabel}>{label}</span>
      <span className={styles.detailsValue}>{value}</span>
    </div>
  );
}

function DetailList({ label, values }: { label: string; values: string[] }) {
  if (values.length === 0) return null;
  return (
    <div className={styles.detailItem}>
      <span className={styles.detailsLabel}>{label}</span>
      <ul className={styles.detailsList}>
        {values.map((value, index) => (
          <li key={`${label}-${index}`}>{value}</li>
        ))}
      </ul>
    </div>
  );
}

function ContextChipBadge({ chip }: { chip: ContextChip }) {
  return (
    <Badge
      className={styles.contextChip}
      variant={chip.variant ?? "neutral"}
      size="sm"
    >
      {chip.identity === "player" && (
        <Avatar
          name={chip.identityName ?? chip.value}
          imageUrl={chip.imageUrl}
          size="sm"
        />
      )}
      {chip.identity === "team" && (
        <TeamBadge
          abbreviation={
            chip.abbreviation ??
            (isTeamAbbreviation(chip.value) ? chip.value : undefined)
          }
          name={chip.identityName ?? chip.value}
          logoUrl={chip.imageUrl}
          size="sm"
          showName={false}
          style={chip.styleVars}
        />
      )}
      <span className={styles.contextChipLabel}>{chip.label}</span>
      {chip.value}
    </Badge>
  );
}

function buildContextChips(
  metadata: QueryResponse["result"]["metadata"] | undefined,
  appliedFilters: Array<{ key: string; label: string; value: string }>,
  contextItems: ContextItem[],
  includeDerivedContext: boolean,
): ContextChip[] {
  const chips: ContextChip[] = [];

  if (metadata) {
    const booleanFilterMode = metadata.boolean_filter_mode;
    if (booleanFilterMode === "any") {
      chips.push({
        key: "boolean-logic",
        label: "Logic",
        value: "Any filter (OR)",
        variant: "accent",
      });
    } else if (booleanFilterMode === "all") {
      chips.push({
        key: "boolean-logic",
        label: "Logic",
        value: "All filters (AND)",
        variant: "accent",
      });
    } else if (booleanFilterMode === "grouped") {
      chips.push({
        key: "boolean-logic",
        label: "Logic",
        value: "Grouped AND/OR",
        variant: "accent",
      });
    }

    if (typeof metadata.player === "string") {
      const playerIdentity = resolvePlayerIdentity({
        playerId: metadata.player_context?.player_id,
        playerName: metadata.player_context?.player_name ?? metadata.player,
      });
      chips.push({
        key: "player",
        label: "Player",
        value: metadata.player,
        identity: "player",
        imageUrl: playerIdentity.headshotUrl,
        identityName: playerIdentity.playerName,
      });
    }
    if (Array.isArray(metadata.players) && metadata.players.length) {
      chips.push({
        key: "players",
        label: "Players",
        value: metadata.players.join(", "),
      });
    }
    if (typeof metadata.team === "string") {
      const teamIdentity = resolveTeamIdentity({
        teamId: metadata.team_context?.team_id,
        teamAbbr: metadata.team_context?.team_abbr,
        teamName: metadata.team_context?.team_name ?? metadata.team,
      });
      chips.push({
        key: "team",
        label: "Team",
        value: metadata.team,
        identity: "team",
        imageUrl: teamIdentity.logoUrl,
        identityName: teamIdentity.teamName,
        abbreviation: teamIdentity.teamAbbr,
        styleVars: (teamIdentity.styleVars ?? undefined) as
          | CSSProperties
          | undefined,
      });
    }
    if (Array.isArray(metadata.teams) && metadata.teams.length) {
      chips.push({
        key: "teams",
        label: "Teams",
        value: metadata.teams.join(", "),
      });
    }
    if (typeof metadata.season === "string") {
      chips.push({ key: "season", label: "Season", value: metadata.season });
    }
    if (typeof metadata.opponent === "string") {
      const opponentIdentity = resolveTeamIdentity({
        teamId: metadata.opponent_context?.team_id,
        teamAbbr: metadata.opponent_context?.team_abbr,
        teamName: metadata.opponent_context?.team_name ?? metadata.opponent,
      });
      chips.push({
        key: "opponent",
        label: "vs",
        value: metadata.opponent,
        identity: "team",
        imageUrl: opponentIdentity.logoUrl,
        identityName: opponentIdentity.teamName,
        abbreviation: opponentIdentity.teamAbbr,
        styleVars: (opponentIdentity.styleVars ?? undefined) as
          | CSSProperties
          | undefined,
      });
    }
    if (typeof metadata.split_type === "string") {
      chips.push({
        key: "split",
        label: "Split",
        value: splitContextLabel(metadata.split_type),
      });
    }
  }

  for (const filter of appliedFilters) {
    chips.push({
      key: `filter-${filter.key}`,
      label: filter.label,
      value: filter.value,
      variant: "accent",
    });
  }

  if (includeDerivedContext) {
    for (const item of contextItems) {
      chips.push({
        key: `context-${item.key}`,
        label: item.label,
        value: item.value,
        variant: "neutral",
      });
    }
  }

  return uniqueContextChips(chips);
}

function uniqueContextChips(chips: ContextChip[]): ContextChip[] {
  const seen = new Set<string>();
  return chips.filter((chip) => {
    const key = `${chip.label.toLowerCase()}-${normalizeChipValue(
      chip.value,
    )}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function normalizeChipValue(value: string): string {
  return value
    .toLowerCase()
    .replace(/\s+[\u2013-]\s+/g, " to ")
    .replace(/\s+/g, " ")
    .trim();
}

function splitContextLabel(value: string): string {
  const labels: Record<string, string> = {
    home_away: "Home/Away",
    on_off: "On/Off",
    wins_losses: "Wins/Losses",
  };
  return labels[value] ?? titleCase(value.replace(/_/g, " "));
}

function buildContextItems(
  metadata: QueryResponse["result"]["metadata"] | undefined,
  appliedFilters: Array<{ key: string; label: string; value: string }>,
): ContextItem[] {
  if (!metadata) return [];
  const items: ContextItem[] = [];

  const interpretedAs =
    metadataText(metadata, "interpreted_as") ??
    metadataText(metadata, "interpretation") ??
    metadataText(metadata, "disambiguation_note");
  if (interpretedAs) {
    addContextItem(
      items,
      "Interpreted as",
      stripInterpretedPrefix(interpretedAs),
    );
  }

  const dateRange = formatLongDateRange(
    metadataText(metadata, "start_date"),
    metadataText(metadata, "end_date"),
  );
  if (dateRange) addContextItem(items, "Date range", dateRange);

  const seasonRange = seasonRangeLabel(metadata);
  if (seasonRange) addContextItem(items, "Season range", seasonRange);

  const metric =
    metadataText(metadata, "stat") ??
    metadataText(metadata, "metric") ??
    metadataText(metadata, "target_stat") ??
    metadataText(metadata, "target_metric");
  if (metric) addContextItem(items, "Metric", contextMetricLabel(metric, metadata));

  for (const filter of appliedFilters) {
    if (
      (filter.label === "Date range" && dateRange) ||
      (filter.label === "Season range" && seasonRange)
    ) {
      continue;
    }
    if (filter.label === "Date range" || filter.label === "Season range") {
      addContextItem(items, filter.label, filter.value);
    } else if (filter.label === "Filter") {
      addContextItem(items, "Filter", filter.value);
    } else if (
      filter.label === "Window" ||
      filter.label === "Opponent group" ||
      filter.label === "Included opponents"
    ) {
      addContextItem(items, filter.label, filter.value);
    } else {
      addContextItem(items, "Filter", `${filter.label}: ${filter.value}`);
    }
  }

  return items;
}

function classifyNoticeItems(texts: string[]): {
  context: ContextItem[];
  remaining: string[];
} {
  const context: ContextItem[] = [];
  const remaining: string[] = [];
  for (const text of texts) {
    const displayText = productFacingNotice(text);
    if (displayText === null) continue;
    const item = contextItemFromNotice(displayText);
    if (item) {
      context.push(item);
    } else {
      remaining.push(displayText);
    }
  }
  return { context, remaining };
}

function contextItemFromNotice(text: string): ContextItem | null {
  const trimmed = text.trim();
  if (!trimmed) return null;
  if (isLimitationNotice(trimmed)) return null;

  const interpreted = trimmed.match(/^interpreted as:\s*(.+)$/i);
  if (interpreted) {
    return contextItem("Interpreted as", interpreted[1]);
  }

  const dateWindow = trimmed.match(/^date window:\s*(.+)$/i);
  if (dateWindow) {
    return contextItem("Date range", readableDateWindow(dateWindow[1]));
  }

  const filtered = trimmed.match(/^filtered to\s+(.+)$/i);
  if (filtered) {
    return contextItem("Filter", sentenceCase(filtered[1]));
  }

  const recordFiltered = trimmed.match(/^record filtered to games vs\s+(.+)$/i);
  if (recordFiltered) {
    return contextItem(
      "Included opponents",
      includedOpponentsLabel(recordFiltered[1]),
    );
  }

  const recordWithout = trimmed.match(/^record filtered to games without\s+(.+)$/i);
  if (recordWithout) {
    return contextItem("Filter", `Without ${recordWithout[1]}`);
  }

  const playoffGameFilter = trimmed.match(
    /^filtered to playoff games vs\s+(.+)$/i,
  );
  if (playoffGameFilter) {
    return contextItem("Filter", `Playoff games vs ${playoffGameFilter[1]}`);
  }

  if (/^playoff games only$/i.test(trimmed)) {
    return contextItem("Filter", "Playoff games only");
  }

  const scheduleFilter = trimmed.match(/^schedule-context filter:\s*(.+)$/i);
  if (scheduleFilter) {
    return contextItem("Filter", sentenceCase(scheduleFilter[1]));
  }

  const clutchFilter = trimmed.match(/^clutch filter:\s*(.+)$/i);
  if (clutchFilter) {
    return contextItem("Filter", `Clutch: ${sentenceCase(clutchFilter[1])}`);
  }

  const headToHead = trimmed.match(/^head-to-head:\s*(.+)$/i);
  if (headToHead) {
    return contextItem("Interpreted as", sentenceCase(headToHead[1]));
  }

  const aggregation = trimmed.match(
    /^multi-season (summary|comparison) aggregated from game logs across (.+)$/i,
  );
  if (aggregation) {
    return contextItem("Aggregation", `Game logs across ${aggregation[2]}`);
  }

  const recordByDecade = trimmed.match(
    /^record by decade aggregated across (.+)$/i,
  );
  if (recordByDecade) {
    return contextItem(
      "Aggregation",
      `Record by decade across ${recordByDecade[1]}`,
    );
  }

  const playoffHistoryAggregation = trimmed.match(
    /^playoff history aggregated across (.+)$/i,
  );
  if (playoffHistoryAggregation) {
    return contextItem(
      "Aggregation",
      `Playoff history across ${playoffHistoryAggregation[1]}`,
    );
  }

  const matchupHistory = trimmed.match(/^matchup history:\s*(.+)$/i);
  if (matchupHistory) {
    return contextItem(
      "Interpreted as",
      `Matchup history: ${matchupHistory[1]}`,
    );
  }

  const playoffMatchupHistory = trimmed.match(
    /^playoff matchup history(?: by round)?:\s*(.+)$/i,
  );
  if (playoffMatchupHistory) {
    return contextItem(
      "Interpreted as",
      `Playoff matchup history: ${playoffMatchupHistory[1]}`,
    );
  }

  const leaderboardContext = trimmed.match(
    /^(.+\bleaderboard)\s*\(([^)]+)\)$/i,
  );
  if (leaderboardContext) {
    return contextItem(
      "Interpreted as",
      `${sentenceCase(leaderboardContext[1])} (${statLabel(
        leaderboardContext[2],
      )})`,
    );
  }

  const acrossRange = trimmed.match(/^across\s+(.+)$/i);
  if (acrossRange) {
    return contextItem("Season range", acrossRange[1]);
  }

  if (/^games where\s+/i.test(trimmed)) {
    return contextItem("Filter", sentenceCase(trimmed));
  }

  return null;
}

function isLimitationNotice(text: string): boolean {
  return /\b(not available|unavailable|missing|excluded|partial|approx|degraded|unsupported)\b/i.test(
    text,
  );
}

function displayNoticeText(text: string): string {
  if (
    /^playoff round data not available(?: for seasons)? before 2001-02/i.test(
      text,
    )
  ) {
    return "Round-level data is unavailable before 2001-02, so those seasons are included in totals but not round breakdowns.";
  }
  return text;
}

function readableDateWindow(value: string): string {
  const start = value.match(/\bfrom\s+(\d{4}-\d{2}-\d{2})\b/i)?.[1] ?? null;
  const end = value.match(/\bto\s+(\d{4}-\d{2}-\d{2})\b/i)?.[1] ?? null;
  return formatLongDateRange(start, end) ?? value;
}

function contextItem(label: string, value: string): ContextItem {
  return {
    key: `${label}-${value}`,
    label,
    value,
  };
}

function addContextItem(items: ContextItem[], label: string, value: string) {
  const trimmed = value.trim();
  if (!trimmed) return;
  items.push(contextItem(label, trimmed));
}

function uniqueContextItems(items: ContextItem[]): ContextItem[] {
  const seen = new Set<string>();
  return items.filter((item) => {
    const key = `${item.label.toLowerCase()}-${item.value.toLowerCase()}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function uniqueStrings(values: string[]): string[] {
  const seen = new Set<string>();
  return values.filter((value) => {
    const trimmed = value.trim();
    if (!trimmed || seen.has(trimmed)) return false;
    seen.add(trimmed);
    return true;
  });
}

function metadataNotes(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

function seasonRangeLabel(
  metadata: QueryResponse["result"]["metadata"],
): string | null {
  if (metadata.season) return null;
  const start = metadataText(metadata, "start_season");
  const end = metadataText(metadata, "end_season");
  if (!start && !end) return null;
  if (start && end) return start === end ? start : `${start} to ${end}`;
  return start ? `Since ${start}` : `Through ${end}`;
}

function metadataText(
  metadata: QueryResponse["result"]["metadata"] | undefined,
  key: string,
): string | null {
  if (!metadata) return null;
  const value = metadata[key];
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function resolvedEntityLines(
  metadata: QueryResponse["result"]["metadata"] | undefined,
): string[] {
  if (!metadata) return [];
  const lines: string[] = [];

  if (metadata.player_context) {
    lines.push(
      `Player: ${metadata.player_context.player_name} (${metadata.player_context.player_id})`,
    );
  }
  for (const player of metadata.players_context ?? []) {
    lines.push(`Player: ${player.player_name} (${player.player_id})`);
  }
  if (metadata.team_context) {
    lines.push(
      `Team: ${metadata.team_context.team_name} (${metadata.team_context.team_abbr}, ${metadata.team_context.team_id})`,
    );
  }
  for (const team of metadata.teams_context ?? []) {
    lines.push(`Team: ${team.team_name} (${team.team_abbr}, ${team.team_id})`);
  }
  if (metadata.opponent_context) {
    lines.push(
      `Opponent: ${metadata.opponent_context.team_name} (${metadata.opponent_context.team_abbr}, ${metadata.opponent_context.team_id})`,
    );
  }

  return uniqueStrings(lines);
}

function metadataStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => stringValue(item))
    .filter((item): item is string => item !== null);
}

function stripInterpretedPrefix(value: string): string {
  return value.replace(/^interpreted as:\s*/i, "");
}

function sentenceCase(value: string): string {
  const trimmed = value.trim();
  return trimmed ? trimmed.charAt(0).toUpperCase() + trimmed.slice(1) : value;
}

function appliedFilterLabels(
  rawFilters: unknown,
): Array<{ key: string; label: string; value: string }> {
  if (!Array.isArray(rawFilters)) return [];

  return rawFilters
    .map((filter, index) => {
      if (!filter || typeof filter !== "object") return null;
      const row = filter as Record<string, unknown>;
      const label = stringValue(row.label);
      const value = stringValue(row.value);
      const kind = stringValue(row.kind);
      if (!label || !value) return null;

      const display = formatAppliedFilter(label, value, kind);
      return {
        key: `${display.label}-${display.value}-${index}`,
        label: display.label,
        value: display.value,
      };
    })
    .filter(
      (filter): filter is { key: string; label: string; value: string } =>
        filter !== null,
    );
}

function formatAppliedFilter(
  label: string,
  value: string,
  kind: string | null,
): { label: string; value: string } {
  if (kind === "quality") {
    return { label: "Opponent group", value: titleCase(value) };
  }

  if (kind === "threshold") {
    const threshold = thresholdFilterValue(label, value);
    if (threshold) {
      if (label.trim().toLowerCase().startsWith("opp pts ")) {
        return { label: "Filter", value: threshold };
      }
      return { label: "Filter", value: threshold };
    }
  }

  if (kind === "date") {
    const dateRange = dateFilterValue(value);
    if (dateRange) return { label, value: dateRange };
  }

  if (kind === "season" && label.toLowerCase() === "season range") {
    return { label: "Season range", value };
  }

  if (kind === "window" && label.toLowerCase() === "last n games") {
    return { label: "Window", value: `Last ${value} games` };
  }

  const normalizedValue =
    value.toLowerCase() === "true"
      ? "Yes"
      : value.toLowerCase() === "false"
        ? "No"
        : value;
  return { label, value: normalizedValue };
}

function dateFilterValue(value: string): string | null {
  const match = value.match(
    /(\d{4}-\d{2}-\d{2})(?:\s*(?:to|\u2013|-)\s*(\d{4}-\d{2}-\d{2}))?/,
  );
  if (!match) return null;
  return formatReadableDateRange(match[1], match[2] ?? match[1]);
}

function thresholdFilterValue(label: string, value: string): string | null {
  const match = label.match(/^(.+)\s+(min|max)$/i);
  if (!match) return null;

  const [, stat, direction] = match;
  const isExclusive = /\(exclusive\)/i.test(value);
  const threshold = compactThresholdValue(value);
  if (stat.trim().toLowerCase() === "opp pts") {
    if (direction.toLowerCase() === "min") {
      return isExclusive
        ? `Opp PTS > ${threshold}`
        : `Opp PTS >= ${threshold}`;
    }
    return isExclusive
      ? `Opp PTS < ${threshold}`
      : `Opp PTS <= ${threshold}`;
  }
  const suffix = statLabel(stat);
  if (direction.toLowerCase() === "min") {
    return isExclusive ? `> ${threshold} ${suffix}` : `${threshold}+ ${suffix}`;
  }
  return isExclusive ? `< ${threshold} ${suffix}` : `<= ${threshold} ${suffix}`;
}

function compactThresholdValue(value: string): string {
  const normalized = value.replace(/\s*\(exclusive\)\s*/gi, "").trim();
  const numeric = Number(normalized);
  if (!Number.isFinite(numeric)) return normalized;
  const rounded = Math.round(numeric);
  if (
    Math.abs(numeric - rounded) < 0.001 ||
    Math.abs(numeric - rounded - 0.0001) < 0.001
  ) {
    return String(rounded);
  }
  return Number(numeric.toFixed(1)).toString();
}

function statLabel(stat: string): string {
  const normalized = stat.trim().toLowerCase();
  const labels: Record<string, string> = {
    ast: "AST",
    ast_avg: "APG",
    ast_per_game: "APG",
    blk: "BLK",
    blk_avg: "BPG",
    blk_per_game: "BPG",
    fg3a: "3PA",
    fg3a_total: "3PA",
    fg3m: "3PM",
    fg3m_total: "3PM",
    fga: "FGA",
    fga_total: "FGA",
    fgm: "FGM",
    fgm_total: "FGM",
    fta: "FTA",
    fta_total: "FTA",
    ftm: "FTM",
    ftm_total: "FTM",
    minutes: "Minutes",
    minutes_total: "Minutes",
    pf: "PF",
    pf_total: "PF",
    pts: "PTS",
    pts_avg: "PPG",
    pts_per_game: "PPG",
    "opp pts": "Opponent points",
    opponent_pts: "Opponent points",
    reb: "REB",
    reb_avg: "RPG",
    reb_per_game: "RPG",
    stl: "STL",
    stl_avg: "SPG",
    stl_per_game: "SPG",
    tov: "TOV",
  };
  return labels[normalized] ?? normalized.replace(/_/g, " ").toUpperCase();
}

function contextMetricLabel(
  metric: string,
  metadata: QueryResponse["result"]["metadata"] | undefined,
): string {
  if (
    metadata?.route === "player_stretch_leaderboard" &&
    metric.trim().toLowerCase() === "pts"
  ) {
    return "PPG";
  }
  return statLabel(metric);
}

function includedOpponentsLabel(value: string): string {
  return value.replace(/^(\d+)\s+opponents\b/i, "$1 teams");
}

function titleCase(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function stringValue(value: unknown): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed ? trimmed : null;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return null;
}
