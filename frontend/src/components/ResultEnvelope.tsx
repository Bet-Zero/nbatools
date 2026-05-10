import { type CSSProperties } from "react";
import type { QueryResponse } from "../api/types";
import {
  Avatar,
  Badge,
  Button,
  ResultEnvelopeShell,
  TeamBadge,
  type BadgeVariant,
} from "../design-system";
import { resolvePlayerIdentity, resolveTeamIdentity } from "../lib/identity";
import { formatLongDateRange } from "./tableFormatting";
import styles from "./ResultEnvelope.module.css";

interface Props {
  data: QueryResponse;
  onAlternateSelect?: (description: string) => void;
  className?: string;
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

export default function ResultEnvelope({
  data,
  onAlternateSelect,
  className,
}: Props) {
  const metadata = data.result?.metadata;
  const queryClass = data.result?.query_class;
  const appliedFilters = appliedFilterLabels(metadata?.applied_filters);
  const rawNotes = uniqueStrings([
    ...data.notes,
    ...metadataNotes(metadata?.notes),
  ]);
  const classifiedNotes = classifyNoticeItems(rawNotes);
  const classifiedCaveats = classifyNoticeItems(data.caveats);
  const contextItems = uniqueContextItems([
    ...buildContextItems(metadata, appliedFilters),
    ...classifiedNotes.context,
    ...classifiedCaveats.context,
  ]);
  const noteItems =
    data.result_status !== "no_result" ? classifiedNotes.remaining : [];
  const caveatItems = classifiedCaveats.remaining;
  const showContext = contextItems.length > 0;
  const showNotes = noteItems.length > 0;
  const showCaveats = caveatItems.length > 0;

  // Build context chips from metadata
  const contextChips: {
    label: string;
    value: string;
    identity?: "player" | "team";
    imageUrl?: string | null;
    identityName?: string | null;
    abbreviation?: string | null;
    styleVars?: CSSProperties;
  }[] = [];
  if (metadata) {
    if (typeof metadata.player === "string") {
      const playerIdentity = resolvePlayerIdentity({
        playerId: metadata.player_context?.player_id,
        playerName: metadata.player_context?.player_name ?? metadata.player,
      });
      contextChips.push({
        label: "Player",
        value: metadata.player,
        identity: "player",
        imageUrl: playerIdentity.headshotUrl,
        identityName: playerIdentity.playerName,
      });
    }
    if (Array.isArray(metadata.players) && metadata.players.length)
      contextChips.push({
        label: "Players",
        value: metadata.players.join(", "),
      });
    if (typeof metadata.team === "string") {
      const teamIdentity = resolveTeamIdentity({
        teamId: metadata.team_context?.team_id,
        teamAbbr: metadata.team_context?.team_abbr,
        teamName: metadata.team_context?.team_name ?? metadata.team,
      });
      contextChips.push({
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
    if (Array.isArray(metadata.teams) && metadata.teams.length)
      contextChips.push({
        label: "Teams",
        value: metadata.teams.join(", "),
      });
    if (typeof metadata.season === "string")
      contextChips.push({ label: "Season", value: metadata.season });
    if (typeof metadata.opponent === "string") {
      const opponentIdentity = resolveTeamIdentity({
        teamId: metadata.opponent_context?.team_id,
        teamAbbr: metadata.opponent_context?.team_abbr,
        teamName: metadata.opponent_context?.team_name ?? metadata.opponent,
      });
      contextChips.push({
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
    if (typeof metadata.split_type === "string")
      contextChips.push({ label: "Split", value: metadata.split_type });
  }

  return (
    <ResultEnvelopeShell
      className={className}
      meta={
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
      }
      query={<>&ldquo;{data.query}&rdquo;</>}
      context={
        contextChips.length > 0 || appliedFilters.length > 0 ? (
          <>
            {contextChips.map((chip, i) => (
              <Badge
                key={i}
                className={styles.contextChip}
                variant="neutral"
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
            ))}
            {appliedFilters.map((filter) => (
              <Badge
                key={filter.key}
                className={styles.contextChip}
                variant="accent"
                size="sm"
              >
                <span className={styles.contextChipLabel}>{filter.label}</span>
                {filter.value}
              </Badge>
            ))}
          </>
        ) : null
      }
      notices={
        showContext || showNotes || showCaveats ? (
          <>
            {showContext && (
              <div className={[styles.infoBlock, styles.contextBlock].join(" ")}>
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
    />
  );
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
    addContextItem(items, "Interpreted as", stripInterpretedPrefix(interpretedAs));
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
  if (metric) addContextItem(items, "Metric", statLabel(metric));

  for (const filter of appliedFilters) {
    addContextItem(items, "Filter", `${filter.label}: ${filter.value}`);
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
    const item = contextItemFromNotice(text);
    if (item) {
      context.push(item);
    } else {
      remaining.push(text);
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

  const leaderboardContext = trimmed.match(/^(.+\bleaderboard)\s*\(([^)]+)\)$/i);
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
  metadata: QueryResponse["result"]["metadata"],
  key: string,
): string | null {
  const value = metadata[key];
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
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
    return { label: "VS", value: opponentQualityChipValue(value) };
  }

  if (kind === "threshold") {
    const threshold = thresholdFilterValue(label, value);
    if (threshold) {
      if (label.trim().toLowerCase().startsWith("opp pts ")) {
        return { label: "OPP", value: threshold.replace(/^<=\s+/, "<= ") };
      }
      return { label: "Stat", value: threshold };
    }
  }

  const normalizedValue =
    value.toLowerCase() === "true"
      ? "Yes"
      : value.toLowerCase() === "false"
        ? "No"
        : value;
  return { label, value: normalizedValue };
}

function opponentQualityChipValue(value: string): string {
  const normalized = value.trim().toLowerCase();
  const labels: Record<string, string> = {
    contenders: "CONTENDERS",
    "good teams": "GOOD TEAMS",
    "playoff teams": "PLAYOFF TEAMS",
    "teams over .500": "WINNING TEAMS",
    "top teams": "TOP TEAMS",
    "top-10 defenses": "TOP-10 DEFENSES",
    "winning teams": "WINNING TEAMS",
  };
  return labels[normalized] ?? normalized.toUpperCase();
}

function thresholdFilterValue(label: string, value: string): string | null {
  const match = label.match(/^(.+)\s+(min|max)$/i);
  if (!match) return null;

  const [, stat, direction] = match;
  const threshold = compactThresholdValue(value);
  const suffix = statLabel(stat);
  return direction.toLowerCase() === "min"
    ? `${threshold}+ ${suffix}`
    : `<= ${threshold} ${suffix}`;
}

function compactThresholdValue(value: string): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return value;
  const rounded = Math.round(numeric);
  if (Math.abs(numeric - rounded) < 0.001 || Math.abs(numeric - rounded - 0.0001) < 0.001) {
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
    fg3m: "3PM",
    pts: "PTS",
    pts_avg: "PPG",
    pts_per_game: "PPG",
    "opp pts": "PTS",
    opponent_pts: "PTS",
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
