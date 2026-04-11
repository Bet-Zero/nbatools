/**
 * Tests for the saved query storage layer.
 *
 * Uses a mock localStorage to validate CRUD, import/export, and edge cases.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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

// Mock localStorage
const storage: Record<string, string> = {};

beforeEach(() => {
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => storage[key] ?? null,
    setItem: (key: string, value: string) => {
      storage[key] = value;
    },
    removeItem: (key: string) => {
      delete storage[key];
    },
  });
});

afterEach(() => {
  for (const key of Object.keys(storage)) delete storage[key];
  vi.restoreAllMocks();
});

describe("loadSavedQueries", () => {
  it("returns empty array when localStorage is empty", () => {
    expect(loadSavedQueries()).toEqual([]);
  });

  it("returns empty array for invalid JSON", () => {
    storage["nbatools_saved_queries_v1"] = "not json";
    expect(loadSavedQueries()).toEqual([]);
  });

  it("returns empty array if stored value is not an array", () => {
    storage["nbatools_saved_queries_v1"] = '{"foo": 1}';
    expect(loadSavedQueries()).toEqual([]);
  });
});

describe("addSavedQuery", () => {
  it("creates a new saved query with defaults", () => {
    const entry = addSavedQuery({
      label: "My Query",
      query: "Jokic last 10 games",
    });
    expect(entry.id).toBeTruthy();
    expect(entry.label).toBe("My Query");
    expect(entry.query).toBe("Jokic last 10 games");
    expect(entry.route).toBeNull();
    expect(entry.kwargs).toBeNull();
    expect(entry.tags).toEqual([]);
    expect(entry.pinned).toBe(false);
    expect(entry.createdAt).toBeGreaterThan(0);
    expect(entry.updatedAt).toBe(entry.createdAt);
  });

  it("persists to localStorage", () => {
    addSavedQuery({ label: "Test", query: "test query" });
    const loaded = loadSavedQueries();
    expect(loaded).toHaveLength(1);
    expect(loaded[0].label).toBe("Test");
  });

  it("preserves existing entries", () => {
    addSavedQuery({ label: "First", query: "q1" });
    addSavedQuery({ label: "Second", query: "q2" });
    const loaded = loadSavedQueries();
    expect(loaded).toHaveLength(2);
    expect(loaded[0].label).toBe("First");
    expect(loaded[1].label).toBe("Second");
  });

  it("stores route, kwargs, tags, and pinned when provided", () => {
    const entry = addSavedQuery({
      label: "Structured",
      query: "player stats",
      route: "player_game_summary",
      kwargs: '{"season":"2024-25"}',
      tags: ["player", "season"],
      pinned: true,
    });
    expect(entry.route).toBe("player_game_summary");
    expect(entry.kwargs).toBe('{"season":"2024-25"}');
    expect(entry.tags).toEqual(["player", "season"]);
    expect(entry.pinned).toBe(true);
  });
});

describe("updateSavedQuery", () => {
  it("updates label and query", () => {
    const entry = addSavedQuery({ label: "Old", query: "old query" });
    const updated = updateSavedQuery(entry.id, {
      label: "New",
      query: "new query",
    });
    expect(updated).not.toBeNull();
    expect(updated!.label).toBe("New");
    expect(updated!.query).toBe("new query");
    expect(updated!.updatedAt).toBeGreaterThanOrEqual(entry.updatedAt);
  });

  it("returns null for unknown id", () => {
    expect(updateSavedQuery("nonexistent", { label: "X" })).toBeNull();
  });

  it("preserves unchanged fields", () => {
    const entry = addSavedQuery({
      label: "Keep",
      query: "keep query",
      tags: ["tag1"],
      pinned: true,
    });
    const updated = updateSavedQuery(entry.id, { label: "Changed" });
    expect(updated!.query).toBe("keep query");
    expect(updated!.tags).toEqual(["tag1"]);
    expect(updated!.pinned).toBe(true);
  });
});

describe("deleteSavedQuery", () => {
  it("removes a query by id", () => {
    const entry = addSavedQuery({ label: "Doomed", query: "q" });
    expect(deleteSavedQuery(entry.id)).toBe(true);
    expect(loadSavedQueries()).toHaveLength(0);
  });

  it("returns false for unknown id", () => {
    expect(deleteSavedQuery("nonexistent")).toBe(false);
  });

  it("does not remove other entries", () => {
    const a = addSavedQuery({ label: "A", query: "q1" });
    addSavedQuery({ label: "B", query: "q2" });
    deleteSavedQuery(a.id);
    const remaining = loadSavedQueries();
    expect(remaining).toHaveLength(1);
    expect(remaining[0].label).toBe("B");
  });
});

describe("togglePin", () => {
  it("toggles pinned state", () => {
    const entry = addSavedQuery({ label: "Pin me", query: "q" });
    expect(entry.pinned).toBe(false);

    const pinned = togglePin(entry.id);
    expect(pinned!.pinned).toBe(true);

    const unpinned = togglePin(entry.id);
    expect(unpinned!.pinned).toBe(false);
  });

  it("returns null for unknown id", () => {
    expect(togglePin("nonexistent")).toBeNull();
  });
});

describe("clearAllSavedQueries", () => {
  it("removes all saved queries", () => {
    addSavedQuery({ label: "A", query: "q1" });
    addSavedQuery({ label: "B", query: "q2" });
    clearAllSavedQueries();
    expect(loadSavedQueries()).toEqual([]);
  });
});

describe("exportSavedQueries", () => {
  it("returns valid JSON of all queries", () => {
    addSavedQuery({ label: "Export me", query: "q" });
    const json = exportSavedQueries();
    const parsed = JSON.parse(json);
    expect(parsed).toHaveLength(1);
    expect(parsed[0].label).toBe("Export me");
  });
});

describe("importSavedQueries", () => {
  it("imports queries from JSON", () => {
    const data = [
      {
        id: "import-1",
        label: "Imported",
        query: "imported query",
        route: null,
        kwargs: null,
        tags: [],
        pinned: false,
        createdAt: 1000,
        updatedAt: 1000,
      },
    ];
    const result = importSavedQueries(JSON.stringify(data));
    expect(result).toHaveLength(1);
    expect(result[0].label).toBe("Imported");
  });

  it("merges with existing queries, skipping duplicate ids", () => {
    const existing = addSavedQuery({ label: "Existing", query: "q1" });
    const data = [
      {
        id: existing.id,
        label: "Duplicate",
        query: "dup",
        route: null,
        kwargs: null,
        tags: [],
        pinned: false,
        createdAt: 1000,
        updatedAt: 1000,
      },
      {
        id: "new-1",
        label: "New",
        query: "new query",
        route: null,
        kwargs: null,
        tags: [],
        pinned: false,
        createdAt: 1000,
        updatedAt: 1000,
      },
    ];
    const result = importSavedQueries(JSON.stringify(data));
    expect(result).toHaveLength(2);
    expect(result[0].label).toBe("Existing"); // not overwritten
  });

  it("throws on non-array JSON", () => {
    expect(() => importSavedQueries('{"not": "array"}')).toThrow(
      "Expected a JSON array",
    );
  });

  it("skips entries missing required fields", () => {
    const data = [
      { id: "bad-1" }, // missing label and query
      { id: "good-1", label: "Good", query: "valid" },
    ];
    const result = importSavedQueries(JSON.stringify(data));
    expect(result).toHaveLength(1);
    expect(result[0].label).toBe("Good");
  });
});
