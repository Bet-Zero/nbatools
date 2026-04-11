import { useEffect, useRef, useState, type FormEvent } from "react";
import type { SavedQuery, SavedQueryInput } from "../api/savedQueryTypes";

interface Props {
  /** If set, we are editing an existing query. */
  editing?: SavedQuery | null;
  /** Pre-filled query text for new saves. */
  defaultQuery?: string;
  /** Pre-filled route for structured saves. */
  defaultRoute?: string | null;
  /** Pre-filled kwargs for structured saves. */
  defaultKwargs?: string | null;
  onSave: (input: SavedQueryInput) => void;
  onUpdate?: (id: string, input: Partial<SavedQueryInput>) => void;
  onCancel: () => void;
}

export default function SaveQueryDialog({
  editing,
  defaultQuery = "",
  defaultRoute = null,
  defaultKwargs = null,
  onSave,
  onUpdate,
  onCancel,
}: Props) {
  const [label, setLabel] = useState(editing?.label ?? "");
  const [query, setQuery] = useState(editing?.query ?? defaultQuery);
  const [tagsStr, setTagsStr] = useState(editing?.tags.join(", ") ?? "");
  const [pinned, setPinned] = useState(editing?.pinned ?? false);
  const labelRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    labelRef.current?.focus();
  }, []);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmedLabel = label.trim();
    const trimmedQuery = query.trim();
    if (!trimmedLabel || !trimmedQuery) return;

    const tags = tagsStr
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    if (editing && onUpdate) {
      onUpdate(editing.id, {
        label: trimmedLabel,
        query: trimmedQuery,
        tags,
        pinned,
      });
    } else {
      onSave({
        label: trimmedLabel,
        query: trimmedQuery,
        route: defaultRoute,
        kwargs: defaultKwargs,
        tags,
        pinned,
      });
    }
  }

  return (
    <div className="save-dialog-overlay" onClick={onCancel}>
      <form
        className="save-dialog"
        onSubmit={handleSubmit}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="save-dialog-title">
          {editing ? "Edit Saved Query" : "Save Query"}
        </h3>

        <label className="save-dialog-label" htmlFor="sq-label">
          Label
        </label>
        <input
          ref={labelRef}
          id="sq-label"
          className="save-dialog-input"
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="e.g. Jokic recent stats"
          autoComplete="off"
          maxLength={120}
        />

        <label className="save-dialog-label" htmlFor="sq-query">
          Query
        </label>
        <input
          id="sq-query"
          className="save-dialog-input"
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Natural language query"
          autoComplete="off"
        />

        <label className="save-dialog-label" htmlFor="sq-tags">
          Tags{" "}
          <span className="save-dialog-hint">(comma-separated, optional)</span>
        </label>
        <input
          id="sq-tags"
          className="save-dialog-input"
          type="text"
          value={tagsStr}
          onChange={(e) => setTagsStr(e.target.value)}
          placeholder="e.g. player, season, favorites"
          autoComplete="off"
        />

        <label className="save-dialog-checkbox">
          <input
            type="checkbox"
            checked={pinned}
            onChange={(e) => setPinned(e.target.checked)}
          />
          Pin to top
        </label>

        <div className="save-dialog-actions">
          <button
            type="button"
            className="save-dialog-cancel"
            onClick={onCancel}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="save-dialog-submit"
            disabled={!label.trim() || !query.trim()}
          >
            {editing ? "Update" : "Save"}
          </button>
        </div>
      </form>
    </div>
  );
}
