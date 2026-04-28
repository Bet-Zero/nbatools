import { useRef, useState } from "react";
import type { SavedQuery, SavedQueryInput } from "../api/savedQueryTypes";
import SaveQueryDialog from "./SaveQueryDialog";
import styles from "./SavedQueries.module.css";

interface Props {
  queries: SavedQuery[];
  onRun: (query: string) => void;
  onEdit: (query: string) => void;
  onSave: (input: SavedQueryInput) => void;
  onUpdate: (id: string, updates: Partial<SavedQueryInput>) => void;
  onDelete: (id: string) => void;
  onPin: (id: string) => void;
  onClearAll: () => void;
  onExport: () => string;
  onImport: (json: string) => void;
}

function timeLabel(ts: number): string {
  return new Date(ts).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function SavedQueries({
  queries,
  onRun,
  onEdit,
  onSave,
  onUpdate,
  onDelete,
  onPin,
  onClearAll,
  onExport,
  onImport,
}: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [filterTag, setFilterTag] = useState<string | null>(null);
  const [confirmClear, setConfirmClear] = useState(false);
  const importRef = useRef<HTMLInputElement>(null);

  // Collect all tags for the filter bar
  const allTags = Array.from(new Set(queries.flatMap((q) => q.tags))).sort();

  // Apply tag filter
  const visible = filterTag
    ? queries.filter((q) => q.tags.includes(filterTag))
    : queries;

  const editingQuery = editingId
    ? (queries.find((q) => q.id === editingId) ?? null)
    : null;

  function handleExport() {
    const json = onExport();
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "nbatools-saved-queries.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleImportClick() {
    importRef.current?.click();
  }

  function handleImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        onImport(reader.result as string);
      } catch {
        // silently ignore bad files
      }
    };
    reader.readAsText(file);
    // Reset so re-importing the same file works
    e.target.value = "";
  }

  function handleClearAll() {
    if (!confirmClear) {
      setConfirmClear(true);
      return;
    }
    onClearAll();
    setConfirmClear(false);
  }

  return (
    <div className={styles.savedQueries}>
      <div className={styles.header}>
        <span className={styles.label}>
          Saved Queries
          <span className={[styles.count, styles.countInline].join(" ")}>
            {queries.length} {queries.length === 1 ? "query" : "queries"}
          </span>
        </span>
        <span className={styles.headerActions}>
          <button
            type="button"
            className={styles.actionSmall}
            onClick={handleImportClick}
            title="Import saved queries from JSON"
          >
            Import
          </button>
          <input
            ref={importRef}
            type="file"
            accept=".json"
            className={styles.importInput}
            onChange={handleImportFile}
          />
          {queries.length > 0 && (
            <>
              <button
                type="button"
                className={styles.actionSmall}
                onClick={handleExport}
                title="Export saved queries as JSON"
              >
                Export
              </button>
              <button
                type="button"
                className={[
                  styles.actionSmall,
                  styles.actionDanger,
                ].join(" ")}
                onClick={handleClearAll}
                title="Delete all saved queries"
              >
                {confirmClear ? "Confirm?" : "Clear All"}
              </button>
            </>
          )}
        </span>
      </div>

      {/* Tag filter bar */}
      {allTags.length > 0 && (
        <div className={styles.tagsBar}>
          <button
            type="button"
            className={[
              styles.tagFilter,
              filterTag === null ? styles.active : "",
            ]
              .filter(Boolean)
              .join(" ")}
            onClick={() => setFilterTag(null)}
          >
            All
          </button>
          {allTags.map((tag) => (
            <button
              key={tag}
              type="button"
              className={[
                styles.tagFilter,
                filterTag === tag ? styles.active : "",
              ]
                .filter(Boolean)
                .join(" ")}
              onClick={() => setFilterTag(filterTag === tag ? null : tag)}
            >
              {tag}
            </button>
          ))}
        </div>
      )}

      {/* Empty state */}
      {queries.length === 0 && (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>📌</div>
          <div className={styles.emptyText}>No saved queries yet</div>
          <div className={styles.emptyHint}>
            Save queries you use often for quick access.
          </div>
        </div>
      )}

      {/* Query list */}
      {visible.length > 0 && (
        <div className={styles.list}>
          {visible.map((sq) => (
            <div
              key={sq.id}
              className={[styles.item, sq.pinned ? styles.pinnedItem : ""]
                .filter(Boolean)
                .join(" ")}
            >
              <div className={styles.itemMain}>
                {sq.pinned && (
                  <span className={styles.pinIcon} title="Pinned">
                    📌
                  </span>
                )}
                <div className={styles.itemInfo}>
                  <span
                    className={styles.itemLabel}
                    onClick={() => onRun(sq.query)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") onRun(sq.query);
                    }}
                    title="Click to run"
                  >
                    {sq.label}
                  </span>
                  <span className={styles.itemQuery}>{sq.query}</span>
                </div>
              </div>

              <div className={styles.itemMeta}>
                {sq.tags.map((tag) => (
                  <span key={tag} className={styles.tag}>
                    {tag}
                  </span>
                ))}
                {sq.route && <span className={styles.route}>{sq.route}</span>}
                <span className={styles.date}>{timeLabel(sq.updatedAt)}</span>
              </div>

              <div className={styles.itemActions}>
                <button
                  type="button"
                  className={styles.itemActionButton}
                  onClick={() => onRun(sq.query)}
                  title="Run query"
                >
                  Run
                </button>
                <button
                  type="button"
                  className={styles.itemActionButton}
                  onClick={() => onEdit(sq.query)}
                  title="Load into query bar"
                >
                  Load
                </button>
                <button
                  type="button"
                  className={styles.itemActionButton}
                  onClick={() => onPin(sq.id)}
                  title={sq.pinned ? "Unpin" : "Pin"}
                >
                  {sq.pinned ? "Unpin" : "Pin"}
                </button>
                <button
                  type="button"
                  className={styles.itemActionButton}
                  onClick={() => setEditingId(sq.id)}
                  title="Edit saved query"
                >
                  Edit
                </button>
                <button
                  type="button"
                  className={[
                    styles.itemActionButton,
                    styles.deleteButton,
                  ].join(" ")}
                  onClick={() => onDelete(sq.id)}
                  title="Delete saved query"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* No results for filter */}
      {queries.length > 0 && visible.length === 0 && filterTag && (
        <div className={styles.empty}>
          <div className={styles.emptyText}>
            No queries tagged "{filterTag}"
          </div>
        </div>
      )}

      {/* Edit dialog */}
      {editingQuery && (
        <SaveQueryDialog
          editing={editingQuery}
          onSave={onSave}
          onUpdate={(id, updates) => {
            onUpdate(id, updates);
            setEditingId(null);
          }}
          onCancel={() => setEditingId(null)}
        />
      )}
    </div>
  );
}
