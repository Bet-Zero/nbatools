import { Badge, Card, type BadgeVariant } from "../design-system";
import type { DisambiguationCandidate, ResultMetadata } from "../api/types";
import styles from "./NoResultDisplay.module.css";

interface Props {
  reason?: string | null;
  status: string;
  metadata?: ResultMetadata | null;
  notes?: string[];
  caveats?: string[];
}

type StateVariant =
  | "recoverable"
  | "unsupported"
  | "ambiguous"
  | "error"
  | "empty";

interface StateProfile {
  variant: StateVariant;
  title: string;
  label: string;
  message: string;
  badgeVariant: BadgeVariant;
  suggestions: string[];
}

const RECOVERABLE_SUGGESTIONS = [
  "Check player or team spelling",
  "Try a different season or date range",
  "Broaden stat filters or split filters",
  "Start from a grouped starter query",
];

const NO_DATA_SUGGESTIONS = [
  "Try a season covered by the local data",
  "Broaden the date window",
  "Remove narrow split filters",
];

function stateProfile(
  reason: string | null | undefined,
  status: string,
): StateProfile {
  if (status === "error" || reason === "error") {
    return {
      variant: "error",
      title: "Query Error",
      label: "Result error",
      message: "An error occurred while processing the query.",
      badgeVariant: "danger",
      suggestions: [],
    };
  }

  switch (reason) {
    case "no_match":
      return {
        variant: "recoverable",
        title: "No Matching Results",
        label: "No matching rows",
        message: "No games or records matched the query filters.",
        badgeVariant: "neutral",
        suggestions: RECOVERABLE_SUGGESTIONS,
      };
    case "no_data":
      return {
        variant: "recoverable",
        title: "Data Not Available",
        label: "Unavailable scope",
        message: "Data is not available for the requested scope.",
        badgeVariant: "neutral",
        suggestions: NO_DATA_SUGGESTIONS,
      };
    case "unrouted":
      return {
        variant: "unsupported",
        title: "Unsupported Query",
        label: "Not routed",
        message: "This query type is not yet supported by the engine.",
        badgeVariant: "warning",
        suggestions: [],
      };
    case "ambiguous":
      return {
        variant: "ambiguous",
        title: "Ambiguous Query",
        label: "Needs specificity",
        message:
          "The query matched multiple possible entities. Add more specific player, team, season, or matchup details.",
        badgeVariant: "warning",
        suggestions: [],
      };
    case "unsupported":
      return {
        variant: "unsupported",
        title: "Unsupported Query",
        label: "Unsupported combination",
        message: "This query combination is not supported by the engine.",
        badgeVariant: "warning",
        suggestions: [],
      };
    case "empty_sections":
      return {
        variant: "empty",
        title: "No Displayable Rows",
        label: "Completed without rows",
        message:
          "The query completed, but the response did not include rows this view can display.",
        badgeVariant: "info",
        suggestions: [],
      };
    default:
      return {
        variant: "recoverable",
        title: "No Results",
        label: "No matching data",
        message: reason ?? "No matching data found.",
        badgeVariant: "neutral",
        suggestions: RECOVERABLE_SUGGESTIONS,
      };
  }
}

function formatStatus(status: string): string {
  return status.replace(/_/g, " ");
}

export default function NoResultDisplay({
  reason,
  status,
  metadata,
  notes = [],
  caveats = [],
}: Props) {
  const profile = stateProfile(reason, status);
  const candidateLine = candidateSuggestionLine(metadata?.candidates);
  const suggestedQueries = suggestedQueryLines(metadata?.suggested_queries);
  const details = [
    ...notes.map((text) => ({ kind: "Note", text })),
    ...caveats.map((text) => ({ kind: "Caveat", text })),
  ];

  return (
    <Card
      className={[styles.display, styles[profile.variant]]
        .filter(Boolean)
        .join(" ")}
      depth="card"
      padding="lg"
    >
      <div className={styles.header}>
        <div className={styles.titleGroup}>
          <span className={styles.stateLabel}>{profile.label}</span>
          <div className={styles.title}>{profile.title}</div>
        </div>
        <Badge variant={profile.badgeVariant} size="sm" uppercase>
          {formatStatus(status)}
        </Badge>
      </div>
      <div className={styles.message}>{profile.message}</div>
      {candidateLine && (
        <div className={styles.recovery} aria-label="Disambiguation suggestions">
          <span className={styles.recoveryLead}>Did you mean:</span>{" "}
          <span>{candidateLine}?</span>
        </div>
      )}
      {suggestedQueries.length > 0 && (
        <div className={styles.recovery} aria-label="Suggested queries">
          <div className={styles.recoveryLead}>Try one of these:</div>
          <div className={styles.querySuggestions}>
            {suggestedQueries.map((query) => (
              <code key={query} className={styles.querySuggestion}>
                {query}
              </code>
            ))}
          </div>
        </div>
      )}
      {details.length > 0 && (
        <div className={styles.details} aria-label="Result details">
          <div className={styles.sectionTitle}>Details</div>
          {details.map((detail, i) => (
            <div key={`${detail.kind}-${i}`} className={styles.detailItem}>
              <span className={styles.detailKind}>{detail.kind}</span>
              <span className={styles.detailText}>{detail.text}</span>
            </div>
          ))}
        </div>
      )}
      {profile.suggestions.length > 0 && (
        <div className={styles.suggestions} aria-label="Suggested next steps">
          <div className={styles.sectionTitle}>Suggested next steps</div>
          <div className={styles.suggestionGrid}>
            {profile.suggestions.map((suggestion) => (
              <div key={suggestion} className={styles.suggestion}>
                {suggestion}
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

function candidateSuggestionLine(
  candidates: DisambiguationCandidate[] | undefined,
): string | null {
  if (!Array.isArray(candidates) || candidates.length === 0) return null;
  const labels = candidates
    .map(candidateLabel)
    .filter((label): label is string => Boolean(label));
  if (labels.length === 0) return null;
  return joinHumanList(labels);
}

function candidateLabel(candidate: DisambiguationCandidate): string | null {
  const name = stringValue(candidate.display_name);
  if (!name) return null;
  const team = stringValue(candidate.team_abbr) ?? "free agent";
  return `${name} (${team})`;
}

function suggestedQueryLines(queries: string[] | undefined): string[] {
  if (!Array.isArray(queries)) return [];
  return queries
    .map(stringValue)
    .filter((query): query is string => Boolean(query));
}

function joinHumanList(values: string[]): string {
  if (values.length <= 1) return values[0] ?? "";
  if (values.length === 2) return `${values[0]} or ${values[1]}`;
  return `${values.slice(0, -1).join(", ")}, or ${values[values.length - 1]}`;
}

function stringValue(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}
