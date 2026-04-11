import type { QueryResponse } from "../api/types";

interface Props {
  data: QueryResponse;
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

function routeLabel(route: string): string {
  return route.replace(/_/g, " ");
}

export default function ResultEnvelope({ data }: Props) {
  const metadata = data.result?.metadata;
  const queryClass = data.result?.query_class;

  // Build context chips from metadata
  const contextChips: { label: string; value: string }[] = [];
  if (metadata) {
    if (typeof metadata.player === "string")
      contextChips.push({ label: "Player", value: metadata.player });
    if (Array.isArray(metadata.players) && metadata.players.length)
      contextChips.push({
        label: "Players",
        value: metadata.players.join(", "),
      });
    if (typeof metadata.team === "string")
      contextChips.push({ label: "Team", value: metadata.team });
    if (Array.isArray(metadata.teams) && metadata.teams.length)
      contextChips.push({
        label: "Teams",
        value: metadata.teams.join(", "),
      });
    if (typeof metadata.season === "string")
      contextChips.push({ label: "Season", value: metadata.season });
    if (typeof metadata.opponent === "string")
      contextChips.push({ label: "vs", value: metadata.opponent });
    if (typeof metadata.split_type === "string")
      contextChips.push({ label: "Split", value: metadata.split_type });
  }

  return (
    <div className="envelope">
      {/* Status + Route + Freshness row */}
      <div className="envelope-top">
        <span className={`status-badge status-badge-${data.result_status}`}>
          {statusLabel(data.result_status)}
        </span>
        {data.route && <span className="pill">{routeLabel(data.route)}</span>}
        {queryClass && queryClass !== data.route && (
          <span className="pill">{queryClass}</span>
        )}
        {data.result_reason && (
          <span className="muted" style={{ fontSize: "0.78rem" }}>
            {data.result_reason}
          </span>
        )}
        {data.current_through && (
          <>
            <span className="envelope-separator" />
            <span className="freshness">
              Data through <strong>{data.current_through}</strong>
            </span>
          </>
        )}
      </div>

      {/* Query text */}
      <div className="envelope-query-text">&ldquo;{data.query}&rdquo;</div>

      {/* Context chips */}
      {contextChips.length > 0 && (
        <div className="envelope-context">
          {contextChips.map((chip, i) => (
            <span key={i} className="context-chip">
              <span className="context-chip-label">{chip.label}</span>
              {chip.value}
            </span>
          ))}
        </div>
      )}

      {/* Notes */}
      {data.notes.length > 0 && (
        <div className="info-block notes-block">
          <div className="info-block-label">Notes</div>
          <ul>
            {data.notes.map((note, i) => (
              <li key={i}>{note}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Caveats */}
      {data.caveats.length > 0 && (
        <div className="info-block caveats-block">
          <div className="info-block-label">Caveats</div>
          <ul>
            {data.caveats.map((caveat, i) => (
              <li key={i}>{caveat}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
