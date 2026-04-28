import type { QueryHistoryEntry } from "../api/types";
import styles from "./QueryHistory.module.css";

interface Props {
  entries: QueryHistoryEntry[];
  onSelect: (query: string) => void;
  onEdit: (query: string) => void;
  onClear: () => void;
  onSave?: (query: string) => void;
}

function statusDot(status: string): string {
  if (status === "ok") return styles.okDot;
  if (status === "no_result") return styles.warnDot;
  return styles.errDot;
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
  onSave,
}: Props) {
  if (entries.length === 0) return null;

  return (
    <div className={styles.queryHistory}>
      <div className={styles.header}>
        <span className={styles.label}>
          History
          <span className={[styles.count, styles.countInline].join(" ")}>
            {entries.length} {entries.length === 1 ? "query" : "queries"}
          </span>
        </span>
        <button type="button" className={styles.clear} onClick={onClear}>
          Clear
        </button>
      </div>
      <div className={styles.list}>
        {entries.map((entry) => (
          <div key={entry.id} className={styles.item}>
            <span
              className={[styles.dot, statusDot(entry.result_status)].join(
                " ",
              )}
            />
            <span
              className={styles.query}
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
            <span className={styles.meta}>
              {entry.query_class && (
                <span className={styles.classBadge}>{entry.query_class}</span>
              )}
              {entry.route && (
                <span className={styles.route}>{entry.route}</span>
              )}
              <span className={styles.time}>{timeAgo(entry.timestamp)}</span>
            </span>
            <span className={styles.actions}>
              <button
                type="button"
                className={styles.actionButton}
                onClick={() => onEdit(entry.query)}
                title="Edit query"
              >
                Edit
              </button>
              <button
                type="button"
                className={styles.actionButton}
                onClick={() => onSelect(entry.query)}
                title="Rerun query"
              >
                Rerun
              </button>
              {onSave && (
                <button
                  type="button"
                  className={styles.actionButton}
                  onClick={() => onSave(entry.query)}
                  title="Save query"
                >
                  Save
                </button>
              )}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
