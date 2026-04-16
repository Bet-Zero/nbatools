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

  return (
    <div className={`no-result-display ${isError ? "no-result-error" : ""}`}>
      <div className="no-result-icon">{icon}</div>
      <div className="no-result-title">{title}</div>
      <div className="no-result-message">{friendlyReason(reason)}</div>
      {notes && notes.length > 0 && (
        <div className="no-result-notes">
          {notes.map((note, i) => (
            <div key={i} className="no-result-note">
              &bull; {note}
            </div>
          ))}
        </div>
      )}
      {!isError && !isUnsupported && (
        <div className="no-result-suggestions">
          <strong>Suggestions</strong>
          {SUGGESTIONS.map((s, i) => (
            <div key={i}>&bull; {s}</div>
          ))}
        </div>
      )}
    </div>
  );
}
