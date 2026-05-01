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
  const [importStatus, setImportStatus] = useState<{
    kind: "success" | "error";
    message: string;
  } | null>(null);
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
    setImportStatus(null);
    importRef.current?.click();
  }

  function handleImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        onImport(reader.result as string);
        setFilterTag(null);
        setImportStatus({
          kind: "success",
          message: "Imported saved queries.",
        });
      } catch {
        setImportStatus({
          kind: "error",
          message: "Import failed. Choose a valid saved-query JSON export.",
        });
      }
    };
    reader.onerror = () => {
      setImportStatus({
        kind: "error",
        message: "Import failed. Choose a readable JSON file.",
      });
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
    setImportStatus(null);
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
              aria-label="Import saved queries from JSON"
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
              aria-label="Saved query JSON file"
              className={styles.importInput}
              onChange={handleImportFile}
            />
            {queries.length > 0 && (
              <>
                <Button
                  type="button"
                  onClick={handleExport}
                  aria-label={`Export ${queries.length} saved ${
                    queries.length === 1 ? "query" : "queries"
                  } as JSON`}
                  title="Export saved queries as JSON"
                  size="sm"
                  variant="ghost"
                >
                  Export
                </Button>
                <Button
                  type="button"
                  onClick={handleClearAll}
                  aria-label={
                    confirmClear
                      ? "Confirm delete all saved queries"
                      : "Delete all saved queries"
                  }
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

      {importStatus && (
        <div
          className={[
            styles.importStatus,
            importStatus.kind === "error" ? styles.importError : "",
          ]
            .filter(Boolean)
            .join(" ")}
          role={importStatus.kind === "error" ? "alert" : "status"}
        >
          {importStatus.message}
        </div>
      )}

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
            aria-label="Show all saved queries"
            aria-pressed={filterTag === null}
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
              aria-label={`Filter saved queries by tag: ${tag}`}
              aria-pressed={filterTag === tag}
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
                  <span
                    className={styles.pinIcon}
                    role="img"
                    aria-label="Pinned query"
                    title="Pinned"
                  >
                    📌
                  </span>
                )}
                <div className={styles.itemInfo}>
                  <span
                    className={styles.itemLabel}
                    aria-label={`Run saved query from label: ${sq.label}`}
                    onClick={() => onRun(sq.query)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onRun(sq.query);
                      }
                    }}
                    title="Run saved query"
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
                  aria-label={`Run saved query: ${sq.label}`}
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
                  aria-label={`Load saved query into query bar: ${sq.label}`}
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
                  aria-label={`${
                    sq.pinned ? "Unpin" : "Pin"
                  } saved query: ${sq.label}`}
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
                  aria-label={`Edit saved query: ${sq.label}`}
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
                  aria-label={`Delete saved query: ${sq.label}`}
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
          <Button
            type="button"
            className={styles.showAllButton}
            onClick={() => setFilterTag(null)}
            size="sm"
            variant="ghost"
          >
            Show All
          </Button>
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
