import { describe, expect, it, vi, beforeEach } from "vitest";

// Mock fetch globally
const mockFetch = vi.fn();
globalThis.fetch = mockFetch as unknown as typeof fetch;

// Import after mock is set up
const { fetchHealth, fetchRoutes, postQuery, postStructuredQuery } =
  await import("../api/client");

beforeEach(() => {
  mockFetch.mockReset();
});

describe("fetchHealth", () => {
  it("returns health response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: "ok", version: "0.5.0" }),
    });
    const result = await fetchHealth();
    expect(result.status).toBe("ok");
    expect(result.version).toBe("0.5.0");
    expect(mockFetch).toHaveBeenCalledWith("/health", undefined);
  });

  it("throws on HTTP error", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ error: "internal", detail: "boom" }),
    });
    await expect(fetchHealth()).rejects.toThrow("boom");
  });
});

describe("fetchRoutes", () => {
  it("returns routes list", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({ routes: ["player_game_finder", "season_leaders"] }),
    });
    const result = await fetchRoutes();
    expect(result.routes).toEqual(["player_game_finder", "season_leaders"]);
  });
});

describe("postQuery", () => {
  it("sends POST with query body", async () => {
    const mockResponse = {
      ok: true,
      query: "Jokic last 10",
      route: "player_game_finder",
      result_status: "ok",
      result_reason: null,
      current_through: "2025-04-01",
      notes: [],
      caveats: [],
      result: {
        query_class: "finder",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: { finder: [] },
      },
    };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const result = await postQuery("Jokic last 10");
    expect(result.query).toBe("Jokic last 10");
    expect(mockFetch).toHaveBeenCalledWith("/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "Jokic last 10" }),
    });
  });
});

describe("postStructuredQuery", () => {
  it("sends POST with route and kwargs", async () => {
    const mockResponse = {
      ok: true,
      query: "structured",
      route: "season_leaders",
      result_status: "ok",
      result_reason: null,
      current_through: null,
      notes: [],
      caveats: [],
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: { leaderboard: [] },
      },
    };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const result = await postStructuredQuery("season_leaders", {
      stat: "pts",
    });
    expect(result.route).toBe("season_leaders");
    expect(mockFetch).toHaveBeenCalledWith("/structured-query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        route: "season_leaders",
        kwargs: { stat: "pts" },
      }),
    });
  });
});
