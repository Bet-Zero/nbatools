import type { QueryHistoryEntry } from "../api/types";
import { Badge, Button, Card, SectionHeader } from "../design-system";
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

function statusLabel(status: string): string {
  if (status === "ok") return "Successful query";
  if (status === "no_result") return "No-result query";
  return "Failed query";
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
    <Card className={styles.queryHistory} depth="card" padding="md">
      <SectionHeader
        eyebrow="Session"
        title="History"
        count={`${entries.length} ${entries.length === 1 ? "query" : "queries"}`}
        actions={
          <Button type="button" onClick={onClear} size="sm" variant="ghost">
            Clear
          </Button>
        }
      />
      <div className={styles.list}>
        {entries.map((entry) => (
          <div key={entry.id} className={styles.item}>
            <span
              className={[styles.dot, statusDot(entry.result_status)].join(
                " ",
              )}
              role="img"
              aria-label={statusLabel(entry.result_status)}
            />
            <span
              className={styles.query}
              aria-label={`Run history query from label: ${entry.query}`}
              onClick={() => onSelect(entry.query)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelect(entry.query);
                }
              }}
              title="Run history query"
            >
              {entry.query}
            </span>
            <span className={styles.meta}>
              {entry.query_class && (
                <Badge variant="neutral" size="sm">
                  {entry.query_class}
                </Badge>
              )}
              {entry.route && (
                <Badge variant="accent" size="sm">
                  {entry.route}
                </Badge>
              )}
              <span className={styles.time}>{timeAgo(entry.timestamp)}</span>
            </span>
            <span className={styles.actions}>
              <Button
                type="button"
                className={styles.actionButton}
                onClick={() => onSelect(entry.query)}
                aria-label={`Run history query: ${entry.query}`}
                title="Run history query"
                size="sm"
                variant="ghost"
              >
                Run
              </Button>
              <Button
                type="button"
                className={styles.actionButton}
                onClick={() => onEdit(entry.query)}
                aria-label={`Edit history query: ${entry.query}`}
                title="Edit history query"
                size="sm"
                variant="ghost"
              >
                Edit
              </Button>
              {onSave && (
                <Button
                  type="button"
                  className={styles.actionButton}
                  onClick={() => onSave(entry.query)}
                  aria-label={`Save history query: ${entry.query}`}
                  title="Save history query"
                  size="sm"
                  variant="ghost"
                >
                  Save
                </Button>
              )}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}
