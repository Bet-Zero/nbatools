interface Props {
  reason?: string | null;
  status: string;
}

export default function NoResultDisplay({ reason, status }: Props) {
  const isError = status === "error";
  const icon = isError ? "⚠" : "∅";
  const title = isError ? "Query Error" : "No Results";
  const message =
    reason ?? (isError ? "Something went wrong." : "No matching data found.");

  return (
    <div className={`no-result-display ${isError ? "no-result-error" : ""}`}>
      <div className="no-result-icon">{icon}</div>
      <div className="no-result-title">{title}</div>
      <div className="no-result-message">{message}</div>
    </div>
  );
}
