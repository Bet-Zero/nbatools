import { Badge, Card, type BadgeVariant } from "../design-system";
import type { DisambiguationCandidate, ResultMetadata } from "../api/types";
import {
  buildNoResultDetails,
  buildNoResultGuidance,
  isColumnUnavailableReason,
  isMetricUnavailableNoResult,
  readableNoResultMessage,
} from "./noResultDisplayUtils";
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
}

function stateProfile(
  reason: string | null | undefined,
  status: string,
  metricUnavailable = false,
): StateProfile {
  if (status === "error" || reason === "error") {
    return {
      variant: "error",
      title: "Query Error",
      label: "Result error",
      message: "An error occurred while processing the query.",
      badgeVariant: "danger",
    };
  }

  if (metricUnavailable || isColumnUnavailableReason(reason)) {
    return {
      variant: "unsupported",
      title: "Unavailable Metric",
      label: "Metric unavailable",
      message: "The requested metric is not available in the current dataset.",
      badgeVariant: "warning",
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
      };
    case "no_data":
      return {
        variant: "recoverable",
        title: "Data Not Available",
        label: "Unavailable scope",
        message: "Data is not available for the requested scope.",
        badgeVariant: "neutral",
      };
    case "unrouted":
      return {
        variant: "unsupported",
        title: "Unsupported Query",
        label: "Not routed",
        message: "This query type is not yet supported by the engine.",
        badgeVariant: "warning",
      };
    case "ambiguous":
      return {
        variant: "ambiguous",
        title: "Ambiguous Query",
        label: "Needs specificity",
        message:
          "The query matched multiple possible entities. Add more specific player, team, season, or matchup details.",
        badgeVariant: "warning",
      };
    case "unsupported":
      return {
        variant: "unsupported",
        title: "Unsupported Query",
        label: "Unsupported combination",
        message: "This query combination is not supported by the engine.",
        badgeVariant: "warning",
      };
    case "filter_not_supported":
      return {
        variant: "unsupported",
        title: "Unavailable Filter",
        label: "Filter unavailable",
        message:
          "The requested filter or metric is not available in the current dataset.",
        badgeVariant: "warning",
      };
    case "empty_sections":
      return {
        variant: "empty",
        title: "No Displayable Rows",
        label: "Completed without rows",
        message:
          "The query completed, but the response did not include rows this view can display.",
        badgeVariant: "info",
      };
    default:
      return {
        variant: "recoverable",
        title: "No Results",
        label: "No matching data",
        message: reason ?? "No matching data found.",
        badgeVariant: "neutral",
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
  const candidateLine = candidateSuggestionLine(metadata?.candidates);
  const details = buildNoResultDetails(notes, caveats, metadata);
  const detailTexts = details.map((detail) => detail.text);
  const profile = stateProfile(
    reason,
    status,
    isMetricUnavailableNoResult(reason, metadata, detailTexts),
  );
  const message = readableNoResultMessage(
    profile.message,
    reason,
    metadata,
    detailTexts,
  );
  const guidance = buildNoResultGuidance(reason, status, metadata, detailTexts);

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
      <div className={styles.message}>{message}</div>
      {candidateLine && (
        <div
          className={styles.recovery}
          aria-label="Disambiguation suggestions"
        >
          <span className={styles.recoveryLead}>Did you mean:</span>{" "}
          <span>{candidateLine}?</span>
        </div>
      )}
      {guidance.querySuggestions.length > 0 && (
        <div className={styles.recovery} aria-label="Suggested queries">
          <div className={styles.recoveryLead}>Try one of these:</div>
          <div className={styles.querySuggestions}>
            {guidance.querySuggestions.map((query) => (
              <code key={query} className={styles.querySuggestion}>
                {query}
              </code>
            ))}
          </div>
        </div>
      )}
      {details.length > 0 && (
        <div className={styles.details} aria-label="Result details">
          <div className={styles.sectionTitle}>Why this happened</div>
          {details.map((detail, i) => (
            <div key={`${detail.kind}-${i}`} className={styles.detailItem}>
              <span className={styles.detailKind}>{detail.kind}</span>
              <span className={styles.detailText}>{detail.text}</span>
            </div>
          ))}
        </div>
      )}
      {guidance.nextSteps.length > 0 && (
        <div className={styles.suggestions} aria-label="Suggested next steps">
          <div className={styles.sectionTitle}>Suggested next steps</div>
          <div className={styles.suggestionGrid}>
            {guidance.nextSteps.map((suggestion) => (
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
