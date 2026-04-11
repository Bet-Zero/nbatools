import { useCallback, useState } from "react";
import type { SavedQuery, SavedQueryInput } from "../api/savedQueryTypes";
import {
  addSavedQuery,
  clearAllSavedQueries,
  deleteSavedQuery,
  exportSavedQueries,
  importSavedQueries,
  loadSavedQueries,
  togglePin,
  updateSavedQuery,
} from "../storage/savedQueryStorage";

/**
 * React hook for managing saved queries.
 *
 * Keeps React state in sync with localStorage. Every mutation writes
 * through to storage and refreshes the local state snapshot.
 */
export default function useSavedQueries() {
  const [queries, setQueries] = useState<SavedQuery[]>(loadSavedQueries);

  const refresh = useCallback(() => setQueries(loadSavedQueries()), []);

  const add = useCallback(
    (input: SavedQueryInput): SavedQuery => {
      const entry = addSavedQuery(input);
      refresh();
      return entry;
    },
    [refresh],
  );

  const update = useCallback(
    (id: string, updates: Partial<SavedQueryInput>): SavedQuery | null => {
      const result = updateSavedQuery(id, updates);
      refresh();
      return result;
    },
    [refresh],
  );

  const remove = useCallback(
    (id: string) => {
      deleteSavedQuery(id);
      refresh();
    },
    [refresh],
  );

  const pin = useCallback(
    (id: string) => {
      togglePin(id);
      refresh();
    },
    [refresh],
  );

  const clearAll = useCallback(() => {
    clearAllSavedQueries();
    refresh();
  }, [refresh]);

  const doExport = useCallback((): string => {
    return exportSavedQueries();
  }, []);

  const doImport = useCallback(
    (json: string) => {
      importSavedQueries(json);
      refresh();
    },
    [refresh],
  );

  /** Sorted: pinned first, then by updatedAt descending. */
  const sorted = [...queries].sort((a, b) => {
    if (a.pinned !== b.pinned) return a.pinned ? -1 : 1;
    return b.updatedAt - a.updatedAt;
  });

  return {
    queries: sorted,
    add,
    update,
    remove,
    pin,
    clearAll,
    exportJSON: doExport,
    importJSON: doImport,
  } as const;
}
