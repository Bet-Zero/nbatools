import { Badge, Card } from "../design-system";
import styles from "./NoResultDisplay.module.css";

interface Props {
  reason?: string | null;
  status: string;
  notes?: string[];
}

function friendlyReason(reason: string | null | undefined): string {
  switch (reason) {
    case "no_match":
      return "No games or records matched your query filters.";
    case "no_data":
      return "Data is not available for the requested scope.";
    case "unrouted":
      return "This query type is not yet supported.";
    case "ambiguous":
      return "The query matched multiple possible entities. Try being more specific.";
    case "unsupported":
      return "This query combination is not supported by the engine.";
    case "error":
      return "An error occurred while processing the query.";
    default:
      return reason ?? "No matching data found.";
  }
}

const SUGGESTIONS = [
  "Check player/team spelling",
  "Try a different season or date range",
  "Broaden your stat filters",
  "Try one of the sample queries above",
];

export default function NoResultDisplay({ reason, status, notes }: Props) {
  const isError = status === "error";
  const isUnsupported = reason === "unsupported" || reason === "ambiguous";
  const icon = isError ? "⚠" : isUnsupported ? "⊘" : "∅";
  const title = isError
    ? "Query Error"
    : reason === "unsupported"
      ? "Unsupported Query"
      : reason === "ambiguous"
        ? "Ambiguous Query"
        : "No Results";
  const badgeVariant = isError
    ? "danger"
    : isUnsupported
      ? "warning"
      : "neutral";

  return (
    <Card
      className={[styles.display, isError ? styles.error : ""]
        .filter(Boolean)
        .join(" ")}
      depth="card"
      padding="lg"
    >
      <div className={styles.iconWrap}>
        <div className={styles.icon}>{icon}</div>
      </div>
      <Badge variant={badgeVariant} size="sm" uppercase>
        {status}
      </Badge>
      <div className={styles.title}>{title}</div>
      <div className={styles.message}>{friendlyReason(reason)}</div>
      {notes && notes.length > 0 && (
        <div className={styles.notes}>
          {notes.map((note, i) => (
            <div key={i} className={styles.note}>
              &bull; {note}
            </div>
          ))}
        </div>
      )}
      {!isError && !isUnsupported && (
        <div className={styles.suggestions}>
          <strong>Suggestions</strong>
          {SUGGESTIONS.map((s, i) => (
            <div key={i}>&bull; {s}</div>
          ))}
        </div>
      )}
    </Card>
  );
}
