import { useRef, useState } from "react";
import type { SavedQuery, SavedQueryInput } from "../api/savedQueryTypes";
import { Badge, Button, Card, SectionHeader } from "../design-system";
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
    <Card className={styles.savedQueries} depth="card" padding="md">
      <SectionHeader
        eyebrow="Secondary"
        title="Saved Queries"
        count={`${queries.length} ${queries.length === 1 ? "query" : "queries"}`}
        actions={
          <span className={styles.headerActions}>
            <Button
              type="button"
              onClick={handleImportClick}
              title="Import saved queries from JSON"
              size="sm"
              variant="ghost"
            >
              Import
            </Button>
          <input
            ref={importRef}
            type="file"
            accept=".json"
            className={styles.importInput}
            onChange={handleImportFile}
          />
          {queries.length > 0 && (
            <>
              <Button
                type="button"
                onClick={handleExport}
                title="Export saved queries as JSON"
                size="sm"
                variant="ghost"
              >
                Export
              </Button>
              <Button
                type="button"
                onClick={handleClearAll}
                title="Delete all saved queries"
                size="sm"
                variant={confirmClear ? "danger" : "ghost"}
              >
                {confirmClear ? "Confirm?" : "Clear All"}
              </Button>
            </>
          )}
        </span>
        }
      />

      {/* Tag filter bar */}
      {allTags.length > 0 && (
        <div className={styles.tagsBar}>
          <Button
            type="button"
            className={[
              styles.tagFilter,
              filterTag === null ? styles.active : "",
            ]
              .filter(Boolean)
              .join(" ")}
            onClick={() => setFilterTag(null)}
            size="sm"
            variant="ghost"
          >
            All
          </Button>
          {allTags.map((tag) => (
            <Button
              key={tag}
              type="button"
              className={[
                styles.tagFilter,
                filterTag === tag ? styles.active : "",
              ]
                .filter(Boolean)
                .join(" ")}
              onClick={() => setFilterTag(filterTag === tag ? null : tag)}
              size="sm"
              variant="ghost"
            >
              {tag}
            </Button>
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
                {sq.route && (
                  <Badge variant="accent" size="sm">
                    {sq.route}
                  </Badge>
                )}
                <span className={styles.date}>{timeLabel(sq.updatedAt)}</span>
              </div>

              <div className={styles.itemActions}>
                <Button
                  type="button"
                  className={styles.itemActionButton}
                  onClick={() => onRun(sq.query)}
                  title="Run query"
                  size="sm"
                  variant="ghost"
                >
                  Run
                </Button>
                <Button
                  type="button"
                  className={styles.itemActionButton}
                  onClick={() => onEdit(sq.query)}
                  title="Load into query bar"
                  size="sm"
                  variant="ghost"
                >
                  Load
                </Button>
                <Button
                  type="button"
                  className={styles.itemActionButton}
                  onClick={() => onPin(sq.id)}
                  title={sq.pinned ? "Unpin" : "Pin"}
                  size="sm"
                  variant="ghost"
                >
                  {sq.pinned ? "Unpin" : "Pin"}
                </Button>
                <Button
                  type="button"
                  className={styles.itemActionButton}
                  onClick={() => setEditingId(sq.id)}
                  title="Edit saved query"
                  size="sm"
                  variant="ghost"
                >
                  Edit
                </Button>
                <Button
                  type="button"
                  className={styles.itemActionButton}
                  onClick={() => onDelete(sq.id)}
                  title="Delete saved query"
                  size="sm"
                  variant="danger"
                >
                  Delete
                </Button>
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
    </Card>
  );
}
