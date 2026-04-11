import { useRef, useState } from "react";
import type { SavedQuery, SavedQueryInput } from "../api/savedQueryTypes";
import SaveQueryDialog from "./SaveQueryDialog";

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
    <div className="saved-queries">
      <div className="saved-header">
        <span className="saved-label">
          Saved Queries
          <span className="section-count" style={{ marginLeft: 6 }}>
            {queries.length} {queries.length === 1 ? "query" : "queries"}
          </span>
        </span>
        <span className="saved-header-actions">
          <button
            type="button"
            className="saved-action-sm"
            onClick={handleImportClick}
            title="Import saved queries from JSON"
          >
            Import
          </button>
          <input
            ref={importRef}
            type="file"
            accept=".json"
            style={{ display: "none" }}
            onChange={handleImportFile}
          />
          {queries.length > 0 && (
            <>
              <button
                type="button"
                className="saved-action-sm"
                onClick={handleExport}
                title="Export saved queries as JSON"
              >
                Export
              </button>
              <button
                type="button"
                className="saved-action-sm saved-action-danger"
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
        <div className="saved-tags-bar">
          <button
            type="button"
            className={`saved-tag-filter ${filterTag === null ? "active" : ""}`}
            onClick={() => setFilterTag(null)}
          >
            All
          </button>
          {allTags.map((tag) => (
            <button
              key={tag}
              type="button"
              className={`saved-tag-filter ${filterTag === tag ? "active" : ""}`}
              onClick={() => setFilterTag(filterTag === tag ? null : tag)}
            >
              {tag}
            </button>
          ))}
        </div>
      )}

      {/* Empty state */}
      {queries.length === 0 && (
        <div className="saved-empty">
          <div className="saved-empty-icon">📌</div>
          <div className="saved-empty-text">No saved queries yet</div>
          <div className="saved-empty-hint">
            Save queries you use often for quick access.
          </div>
        </div>
      )}

      {/* Query list */}
      {visible.length > 0 && (
        <div className="saved-list">
          {visible.map((sq) => (
            <div
              key={sq.id}
              className={`saved-item ${sq.pinned ? "saved-item-pinned" : ""}`}
            >
              <div className="saved-item-main">
                {sq.pinned && (
                  <span className="saved-pin-icon" title="Pinned">
                    📌
                  </span>
                )}
                <div className="saved-item-info">
                  <span
                    className="saved-item-label"
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
                  <span className="saved-item-query">{sq.query}</span>
                </div>
              </div>

              <div className="saved-item-meta">
                {sq.tags.map((tag) => (
                  <span key={tag} className="saved-tag">
                    {tag}
                  </span>
                ))}
                {sq.route && <span className="saved-route">{sq.route}</span>}
                <span className="saved-date">{timeLabel(sq.updatedAt)}</span>
              </div>

              <div className="saved-item-actions">
                <button
                  type="button"
                  className="history-action-btn"
                  onClick={() => onRun(sq.query)}
                  title="Run query"
                >
                  Run
                </button>
                <button
                  type="button"
                  className="history-action-btn"
                  onClick={() => onEdit(sq.query)}
                  title="Load into query bar"
                >
                  Load
                </button>
                <button
                  type="button"
                  className="history-action-btn"
                  onClick={() => onPin(sq.id)}
                  title={sq.pinned ? "Unpin" : "Pin"}
                >
                  {sq.pinned ? "Unpin" : "Pin"}
                </button>
                <button
                  type="button"
                  className="history-action-btn"
                  onClick={() => setEditingId(sq.id)}
                  title="Edit saved query"
                >
                  Edit
                </button>
                <button
                  type="button"
                  className="history-action-btn saved-delete-btn"
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
        <div className="saved-empty">
          <div className="saved-empty-text">
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
