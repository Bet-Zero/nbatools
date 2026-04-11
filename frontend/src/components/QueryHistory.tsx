import type { QueryHistoryEntry } from "../api/types";

interface Props {
  entries: QueryHistoryEntry[];
  onSelect: (query: string) => void;
  onEdit: (query: string) => void;
  onClear: () => void;
}

function statusDot(status: string): string {
  if (status === "ok") return "dot-ok";
  if (status === "no_result") return "dot-warn";
  return "dot-err";
}

function timeAgo(ts: number): string {
  const seconds = Math.floor((Date.now() - ts) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

export default function QueryHistory({
  entries,
  onSelect,
  onEdit,
  onClear,
}: Props) {
  if (entries.length === 0) return null;

  return (
    <div className="query-history">
      <div className="history-header">
        <span className="history-label">
          History
          <span className="section-count" style={{ marginLeft: 6 }}>
            {entries.length} {entries.length === 1 ? "query" : "queries"}
          </span>
        </span>
        <button type="button" className="history-clear" onClick={onClear}>
          Clear
        </button>
      </div>
      <div className="history-list">
        {entries.map((entry) => (
          <div key={entry.id} className="history-item">
            <span className={`history-dot ${statusDot(entry.result_status)}`} />
            <span
              className="history-query"
              onClick={() => onSelect(entry.query)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter") onSelect(entry.query);
              }}
              title="Click to rerun"
            >
              {entry.query}
            </span>
            <span className="history-meta">
              {entry.query_class && (
                <span className="history-class">{entry.query_class}</span>
              )}
              {entry.route && (
                <span className="history-route">{entry.route}</span>
              )}
              <span className="history-time">{timeAgo(entry.timestamp)}</span>
            </span>
            <span className="history-item-actions">
              <button
                type="button"
                className="history-action-btn"
                onClick={() => onEdit(entry.query)}
                title="Edit query"
              >
                Edit
              </button>
              <button
                type="button"
                className="history-action-btn"
                onClick={() => onSelect(entry.query)}
                title="Rerun query"
              >
                Rerun
              </button>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
