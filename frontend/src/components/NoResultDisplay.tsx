interface Props {
  reason?: string | null;
  status: string;
}

function friendlyReason(reason: string | null | undefined): string {
  switch (reason) {
    case "no_match":
      return "No games or records matched your query filters.";
    case "no_data":
      return "Data is not available for the requested scope.";
    case "unrouted":
      return "This query type is not yet supported.";
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

export default function NoResultDisplay({ reason, status }: Props) {
  const isError = status === "error";
  const icon = isError ? "⚠" : "∅";
  const title = isError ? "Query Error" : "No Results";

  return (
    <div className={`no-result-display ${isError ? "no-result-error" : ""}`}>
      <div className="no-result-icon">{icon}</div>
      <div className="no-result-title">{title}</div>
      <div className="no-result-message">{friendlyReason(reason)}</div>
      {!isError && (
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
