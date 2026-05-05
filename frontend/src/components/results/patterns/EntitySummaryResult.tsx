import type { ReactNode } from "react";
import type {
  QueryResponse,
  ResultMetadata,
  SectionRow,
} from "../../../api/types";
import { formatValue } from "../../tableFormatting";
import EntityIdentity from "../primitives/EntityIdentity";
import ResultHero from "../primitives/ResultHero";
import styles from "./EntitySummaryResult.module.css";

interface Props {
  data: QueryResponse;
  sectionKey?: string;
}

export default function EntitySummaryResult({
  data,
  sectionKey = "summary",
}: Props) {
  const row = data.result?.sections?.[sectionKey]?.[0];
  if (!row) return null;

  return (
    <section className={styles.pattern} aria-label="Player summary result">
      <ResultHero
        sentence={summarySentence(row, data.result?.metadata, data.query)}
        subjectIllustration={heroIdentity(row, data.result?.metadata)}
        disambiguationNote={disambiguationNote(data.result?.metadata)}
        tone="accent"
      />
    </section>
  );
}

function summarySentence(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
  query: string,
): string {
  const name = playerName(row, metadata);
  const averages = averagePhrase(row);
  const context = summaryContext(row, metadata, query);

  if (!averages) {
    return `${name} has a summary available${context}.`;
  }

  return `${name} has averaged ${averages}${context}.`;
}

function averagePhrase(row: SectionRow): string | null {
  const parts = [
    statPhrase(row, "pts_avg", "points"),
    statPhrase(row, "reb_avg", "rebounds"),
    statPhrase(row, "ast_avg", "assists"),
  ].filter((part): part is string => Boolean(part));

  if (parts.length === 0) return null;
  if (parts.length === 1) return parts[0];
  if (parts.length === 2) return `${parts[0]} and ${parts[1]}`;
  return `${parts.slice(0, -1).join(", ")} and ${parts[parts.length - 1]}`;
}

function statPhrase(
  row: SectionRow,
  key: string,
  label: string,
): string | null {
  if (!hasValue(row[key])) return null;
  return `${formatValue(row[key], key)} ${label}`;
}

function summaryContext(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
  query: string,
): string {
  const lastN = lastNWindow(query, metadata);
  if (lastN) return ` in his last ${lastN} games`;

  if (/\bthis season\b/i.test(query)) return " this season";
  if (/\bcareer\b/i.test(query)) return " in his career";

  const seasonStart =
    textValue(row, "season_start") ?? metadataText(metadata, "season");
  const seasonEnd = textValue(row, "season_end");
  const seasonType =
    textValue(row, "season_type") ?? metadataText(metadata, "season_type");

  if (seasonStart && seasonEnd && seasonStart !== seasonEnd) {
    return ` from ${seasonStart} to ${seasonEnd}`;
  }

  if (seasonStart) {
    return ` in the ${seasonStart}${seasonType ? ` ${seasonType.toLowerCase()}` : ""}`;
  }

  const games = row.games;
  if (typeof games === "number" && Number.isFinite(games)) {
    return ` in ${formatValue(games, "games")} games`;
  }

  return "";
}

function heroIdentity(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
): ReactNode {
  return (
    <EntityIdentity
      kind="player"
      playerId={metadata?.player_context?.player_id ?? identityId(row.player_id)}
      playerName={playerName(row, metadata)}
    />
  );
}

function playerName(
  row: SectionRow,
  metadata: ResultMetadata | undefined,
): string {
  return (
    metadata?.player_context?.player_name ??
    metadataText(metadata, "player") ??
    textValue(row, "player_name") ??
    textValue(row, "player") ??
    "Player"
  );
}

function disambiguationNote(
  metadata: ResultMetadata | undefined,
): string | null {
  for (const key of ["disambiguation_note", "interpreted_as", "interpretation"]) {
    const value = metadata?.[key];
    if (typeof value !== "string") continue;
    const trimmed = value.trim();
    if (!trimmed) continue;
    return trimmed.toLowerCase().startsWith("interpreted as:")
      ? trimmed
      : `Interpreted as: ${trimmed}`;
  }
  return null;
}

function lastNWindow(
  query: string,
  metadata: ResultMetadata | undefined,
): number | null {
  const windowSize = metadata?.window_size;
  if (typeof windowSize === "number" && Number.isFinite(windowSize)) {
    return windowSize;
  }

  const queryText = `${query} ${metadata?.query_text ?? ""}`;
  const match = queryText.match(/\blast\s+(\d+)\s*(?:games?|gms?)?\b/i);
  return match ? Number(match[1]) : null;
}

function textValue(row: SectionRow, key: string): string | null {
  const value = row[key];
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

function identityId(value: unknown): number | string | null {
  return typeof value === "number" || typeof value === "string" ? value : null;
}

function hasValue(value: unknown): boolean {
  return value !== null && value !== undefined && value !== "";
}
