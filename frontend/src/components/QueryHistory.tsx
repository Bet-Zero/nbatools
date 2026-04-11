import type { QueryHistoryEntry } from "../api/types";

interface Props {
  entries: QueryHistoryEntry[];
  onSelect: (query: string) => void;
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

export default function QueryHistory({ entries, onSelect, onClear }: Props) {
  if (entries.length === 0) return null;

  return (
    <div className="query-history">
      <div className="history-header">
        <span className="history-label">History</span>
        <button type="button" className="history-clear" onClick={onClear}>
          Clear
        </button>
      </div>
      <div className="history-list">
        {entries.map((entry) => (
          <button
            key={entry.id}
            type="button"
            className="history-item"
            onClick={() => onSelect(entry.query)}
            title={`${entry.route ?? "unrouted"} · ${entry.result_status}`}
          >
            <span className={`history-dot ${statusDot(entry.result_status)}`} />
            <span className="history-query">{entry.query}</span>
            <span className="history-meta">
              {entry.route && (
                <span className="history-route">{entry.route}</span>
              )}
              <span className="history-time">{timeAgo(entry.timestamp)}</span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
