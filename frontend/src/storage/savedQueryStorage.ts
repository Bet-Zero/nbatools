/**
 * Storage helper for saved queries.
 *
 * Wraps localStorage with a versioned key and typed CRUD operations.
 * All reads/writes are atomic over the full array.
 * This layer is intentionally thin so the persistence backend can be
 * swapped later (IndexedDB, API, etc.) without touching consumers.
 */

import type { SavedQuery, SavedQueryInput } from "../api/savedQueryTypes";

const STORAGE_KEY = "nbatools_saved_queries_v1";

// ---- helpers ----

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

// ---- read / write ----

export function loadSavedQueries(): SavedQuery[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed as SavedQuery[];
  } catch {
    return [];
  }
}

function persist(queries: SavedQuery[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(queries));
}

// ---- CRUD ----

export function addSavedQuery(input: SavedQueryInput): SavedQuery {
  const now = Date.now();
  const entry: SavedQuery = {
    id: generateId(),
    label: input.label,
    query: input.query,
    route: input.route ?? null,
    kwargs: input.kwargs ?? null,
    tags: input.tags ?? [],
    pinned: input.pinned ?? false,
    createdAt: now,
    updatedAt: now,
  };
  const queries = loadSavedQueries();
  queries.push(entry);
  persist(queries);
  return entry;
}

export function updateSavedQuery(
  id: string,
  updates: Partial<SavedQueryInput>,
): SavedQuery | null {
  const queries = loadSavedQueries();
  const idx = queries.findIndex((q) => q.id === id);
  if (idx === -1) return null;
  const existing = queries[idx];
  const updated: SavedQuery = {
    ...existing,
    label: updates.label ?? existing.label,
    query: updates.query ?? existing.query,
    route:
      updates.route !== undefined ? (updates.route ?? null) : existing.route,
    kwargs:
      updates.kwargs !== undefined ? (updates.kwargs ?? null) : existing.kwargs,
    tags: updates.tags ?? existing.tags,
    pinned: updates.pinned ?? existing.pinned,
    updatedAt: Date.now(),
  };
  queries[idx] = updated;
  persist(queries);
  return updated;
}

export function deleteSavedQuery(id: string): boolean {
  const queries = loadSavedQueries();
  const filtered = queries.filter((q) => q.id !== id);
  if (filtered.length === queries.length) return false;
  persist(filtered);
  return true;
}

export function togglePin(id: string): SavedQuery | null {
  const queries = loadSavedQueries();
  const entry = queries.find((q) => q.id === id);
  if (!entry) return null;
  entry.pinned = !entry.pinned;
  entry.updatedAt = Date.now();
  persist(queries);
  return entry;
}

export function clearAllSavedQueries(): void {
  localStorage.removeItem(STORAGE_KEY);
}

// ---- import / export ----

export function exportSavedQueries(): string {
  return JSON.stringify(loadSavedQueries(), null, 2);
}

export function importSavedQueries(json: string): SavedQuery[] {
  const incoming = JSON.parse(json);
  if (!Array.isArray(incoming)) throw new Error("Expected a JSON array");

  const existing = loadSavedQueries();
  const existingIds = new Set(existing.map((q) => q.id));

  // Merge: skip duplicates by id
  for (const item of incoming) {
    if (
      typeof item === "object" &&
      item !== null &&
      typeof item.id === "string" &&
      typeof item.label === "string" &&
      typeof item.query === "string" &&
      !existingIds.has(item.id)
    ) {
      existing.push(item as SavedQuery);
      existingIds.add(item.id);
    }
  }

  persist(existing);
  return existing;
}
