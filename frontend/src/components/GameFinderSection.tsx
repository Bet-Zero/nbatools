import type { ResultMetadata, SectionRow } from "../api/types";
import { SectionHeader } from "../design-system";
import RawDetailToggle from "./RawDetailToggle";
import TeamGameCards from "./TeamGameCards";
import { formatColHeader, formatValue } from "./tableFormatting";
import styles from "./GameFinderSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
  metadata?: ResultMetadata;
}

function metadataNumber(
  metadata: ResultMetadata | undefined,
  key: string,
): number | null {
  const value = metadata?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
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
  if (start && end) return start === end ? start : `${start} to ${end}`;
  return start ?? end;
}

function conditionLabel(metadata: ResultMetadata | undefined): string | null {
  const stat = metadataText(metadata, "stat");
  const minValue = metadataNumber(metadata, "min_value");
  const maxValue = metadataNumber(metadata, "max_value");
  if (!stat || (minValue === null && maxValue === null)) return null;

  const label = formatColHeader(stat);
  if (minValue !== null && maxValue !== null) {
    return `${formatValue(minValue, stat)}-${formatValue(maxValue, stat)} ${label}`;
  }
  if (minValue !== null) return `${formatValue(minValue, stat)}+ ${label}`;
  return `<= ${formatValue(maxValue, stat)} ${label}`;
}

function contextItems(metadata: ResultMetadata | undefined): string[] {
  return [
    conditionLabel(metadata),
    seasonLabel(metadata),
    metadata?.season_type ?? null,
    dateLabel(metadata),
    metadata?.opponent ? `vs ${metadata.opponent}` : null,
  ].filter((item): item is string => Boolean(item));
}

export default function GameFinderSection({ sections, metadata }: Props) {
  const finder = sections.finder;
  if (!finder || finder.length === 0) return null;

  const context = contextItems(metadata);

  return (
    <div className={styles.section}>
      <SectionHeader
        title="Team Games"
        count={`${finder.length} game${finder.length !== 1 ? "s" : ""} found`}
      />
      {context.length > 0 && (
        <div className={styles.context} aria-label="Finder context">
          {context.map((item) => (
            <span className={styles.contextItem} key={item}>
              {item}
            </span>
          ))}
        </div>
      )}
      <TeamGameCards rows={finder} />
      <RawDetailToggle title="Game Detail" rows={finder} />
    </div>
  );
}
