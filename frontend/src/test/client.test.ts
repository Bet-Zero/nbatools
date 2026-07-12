import { describe, expect, it, vi, beforeEach } from "vitest";

// Mock fetch globally
const mockFetch = vi.fn();
globalThis.fetch = mockFetch as unknown as typeof fetch;

// Import after mock is set up
const {
  fetchDevFixtures,
  fetchHealth,
  fetchRoutes,
  postQuery,
  postQueryFeedback,
  postStructuredQuery,
  fetchFreshness,
  fetchAdminFeedbackGroups,
  fetchAdminFeedbackGroupDetail,
  fetchAdminFeedbackTriage,
  saveAdminFeedbackTriage,
} = await import("../api/client");

beforeEach(() => {
  mockFetch.mockReset();
  window.history.replaceState(null, "", "/");
});

function jsonResponse(
  data: unknown,
  options: { ok?: boolean; status?: number } = {},
) {
  return {
    ok: options.ok ?? true,
    status: options.status ?? 200,
    text: () => Promise.resolve(JSON.stringify(data)),
  };
}

function textResponse(
  body: string,
  options: { ok?: boolean; status?: number } = {},
) {
  return {
    ok: options.ok ?? true,
    status: options.status ?? 200,
    text: () => Promise.resolve(body),
  };
}

describe("fetchHealth", () => {
  it("returns health response", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ status: "ok", version: "0.5.0" }));
    const result = await fetchHealth();
    expect(result.status).toBe("ok");
    expect(result.version).toBe("0.5.0");
    expect(mockFetch).toHaveBeenCalledWith("/health", undefined);
  });

  it("throws on HTTP error", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ error: "internal", detail: "boom" }, { ok: false, status: 500 }),
    );
    await expect(fetchHealth()).rejects.toThrow("boom");
  });

  it("throws a diagnostic error for empty HTTP error responses", async () => {
    mockFetch.mockResolvedValueOnce(textResponse("", { ok: false, status: 502 }));

    await expect(fetchHealth()).rejects.toThrow("HTTP 502: empty response body");
  });

  it("throws a diagnostic error for non-JSON responses", async () => {
    mockFetch.mockResolvedValueOnce(
      textResponse("<html>bad gateway</html>", { ok: false, status: 502 }),
    );

    await expect(fetchHealth()).rejects.toThrow(
      "HTTP 502 returned non-JSON response: <html>bad gateway</html>",
    );
  });
});

describe("fetchRoutes", () => {
  it("returns routes list", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ routes: ["player_game_finder", "season_leaders"] }),
    );
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
    mockFetch.mockResolvedValueOnce(jsonResponse(mockResponse));

    const result = await postQuery("Jokic last 10");
    expect(result.query).toBe("Jokic last 10");
    expect(mockFetch).toHaveBeenCalledWith("/query", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-NBATools-Source-Page": "/",
      },
      body: JSON.stringify({ query: "Jokic last 10" }),
    });
  });

  it("sends the current source page header", async () => {
    window.history.replaceState(null, "", "/visual-qa");
    mockFetch.mockResolvedValueOnce(
      jsonResponse({
        ok: true,
        query: "Visual QA query",
        route: null,
        result_status: "no_result",
        result_reason: "unsupported",
        current_through: null,
        notes: [],
        caveats: [],
        result: {
          query_class: "unknown",
          result_status: "no_result",
          metadata: {},
          notes: [],
          caveats: [],
          sections: {},
        },
      }),
    );

    await postQuery("Visual QA query");
    expect(mockFetch).toHaveBeenCalledWith(
      "/query",
      expect.objectContaining({
        headers: expect.objectContaining({
          "X-NBATools-Source-Page": "/visual-qa",
        }),
      }),
    );
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
    mockFetch.mockResolvedValueOnce(jsonResponse(mockResponse));

    const result = await postStructuredQuery("season_leaders", {
      stat: "pts",
    });
    expect(result.route).toBe("season_leaders");
    expect(mockFetch).toHaveBeenCalledWith("/structured-query", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-NBATools-Source-Page": "/",
      },
      body: JSON.stringify({
        route: "season_leaders",
        kwargs: { stat: "pts" },
      }),
    });
  });
});

describe("postQueryFeedback", () => {
  it("submits feedback to the same-origin endpoint", async () => {
    window.history.replaceState(null, "", "/");
    mockFetch.mockResolvedValueOnce(
      jsonResponse({
        ok: true,
        feedback_id: "qfb_test",
        stored: true,
        disabled: false,
      }),
    );

    const result = await postQueryFeedback({
      query: "Jokic last 10",
      feedback_source: "user_submitted",
      feedback_type: "wrong_answer",
      route: "player_game_summary",
      status: "ok",
      reason: null,
    });

    expect(result.feedback_id).toBe("qfb_test");
    expect(mockFetch).toHaveBeenCalledWith("/query-feedback", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-NBATools-Source-Page": "/",
      },
      body: JSON.stringify({
        query: "Jokic last 10",
        feedback_source: "user_submitted",
        feedback_type: "wrong_answer",
        route: "player_game_summary",
        status: "ok",
        reason: null,
        source_page: "/",
      }),
    });
  });

  it("throws useful errors for non-JSON feedback responses", async () => {
    mockFetch.mockResolvedValueOnce(
      textResponse("<html>bad gateway</html>", { ok: false, status: 502 }),
    );

    await expect(
      postQueryFeedback({
        query: "Jokic last 10",
        feedback_source: "user_submitted",
        feedback_type: "wrong_answer",
      }),
    ).rejects.toThrow(
      "HTTP 502 returned non-JSON response: <html>bad gateway</html>",
    );
  });

  it("throws useful errors for empty feedback responses", async () => {
    mockFetch.mockResolvedValueOnce(textResponse("", { ok: true, status: 204 }));

    await expect(
      postQueryFeedback({
        query: "Jokic last 10",
        feedback_source: "user_submitted",
        feedback_type: "wrong_answer",
      }),
    ).rejects.toThrow("HTTP 204: empty response body");
  });
});

describe("fetchFreshness", () => {
  it("returns freshness response", async () => {
    const mockResponse = {
      status: "fresh",
      current_through: "2026-04-13",
      checked_at: "2026-04-14T10:00:00",
      seasons: [
        {
          season: "2025-26",
          season_type: "Regular Season",
          status: "fresh",
          current_through: "2026-04-13",
          raw_complete: true,
          processed_complete: true,
          loaded_at: "2026-04-14T09:00:00",
          validation_state: "passed",
          generation_id: "generation-test",
          validation_errors: [],
        },
      ],
      last_refresh_ok: true,
      last_refresh_at: "2026-04-14T09:00:00",
      last_refresh_error: null,
    };
    mockFetch.mockResolvedValueOnce(jsonResponse(mockResponse));

    const result = await fetchFreshness();
    expect(result.status).toBe("fresh");
    expect(result.current_through).toBe("2026-04-13");
    expect(result.seasons).toHaveLength(1);
    expect(mockFetch).toHaveBeenCalledWith("/freshness", undefined);
  });

  it("throws on HTTP error", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse(
        { error: "internal", detail: "server error" },
        { ok: false, status: 500 },
      ),
    );
    await expect(fetchFreshness()).rejects.toThrow("server error");
  });
});

describe("fetchDevFixtures", () => {
  it("returns the parser example fixture list", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({
        source_path: "docs/architecture/parser/examples.md",
        fixtures: [{ case_id: "S2_2_1_01", query: "First query" }],
      }),
    );

    const result = await fetchDevFixtures();
    expect(result.source_path).toBe("docs/architecture/parser/examples.md");
    expect(result.fixtures).toEqual([
      { case_id: "S2_2_1_01", query: "First query" },
    ]);
    expect(mockFetch).toHaveBeenCalledWith("/api/dev/fixtures", undefined);
  });
});

describe("admin feedback client", () => {
  it("lists feedback groups with filters and admin token header", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({
        ok: true,
        source_mode: "r2",
        bucket: "nbatools-data",
        prefix: "query_feedback/preview",
        total_found: 1,
        total_exported: 1,
        excluded_smoke_count: 0,
        group_count: 1,
        groups: [],
      }),
    );

    const result = await fetchAdminFeedbackGroups(
      {
        review_status: "deferred",
        triage_decision: "needs_more_data",
        feedback_source: "user_submitted",
        route: "season_leaders",
        status: "no_result",
        reason: "filter_not_supported",
      },
      { adminToken: "secret" },
    );

    expect(result.group_count).toBe(1);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/admin/feedback/groups?review_status=deferred&triage_decision=needs_more_data&feedback_source=user_submitted&route=season_leaders&status=no_result&reason=filter_not_supported",
      {
        headers: {
          "X-NBATools-Admin-Token": "secret",
        },
      },
    );
  });

  it("reads group detail and triage overlay", async () => {
    mockFetch
      .mockResolvedValueOnce(
        jsonResponse({
          ok: true,
          group: { group_id: "qfg_123" },
          records: [],
          triage_overlay: { group_id: "qfg_123", review_status: "new" },
          handoff_summary: "Group: qfg_123",
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          ok: true,
          triage_overlay: { group_id: "qfg_123", review_status: "new" },
        }),
      );

    await fetchAdminFeedbackGroupDetail("qfg_123", { adminToken: "secret" });
    await fetchAdminFeedbackTriage("qfg_123", { adminToken: "secret" });

    expect(mockFetch).toHaveBeenNthCalledWith(
      1,
      "/api/admin/feedback/groups/qfg_123",
      {
        headers: {
          "X-NBATools-Admin-Token": "secret",
        },
      },
    );
    expect(mockFetch).toHaveBeenNthCalledWith(
      2,
      "/api/admin/feedback/groups/qfg_123/triage",
      {
        headers: {
          "X-NBATools-Admin-Token": "secret",
        },
      },
    );
  });

  it("saves triage overlay without source-page headers", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({
        ok: true,
        triage_overlay: {
          group_id: "qfg_123",
          review_status: "reviewed",
          triage_decision: "bug",
        },
      }),
    );

    await saveAdminFeedbackTriage(
      "qfg_123",
      {
        review_status: "reviewed",
        triage_decision: "bug",
        review_notes: "Needs regression coverage.",
        linked_case_or_issue: "RAW-123",
        reviewer_source: "admin_feedback_console",
      },
      { adminToken: "secret" },
    );

    expect(mockFetch).toHaveBeenCalledWith(
      "/api/admin/feedback/groups/qfg_123/triage",
      {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "X-NBATools-Admin-Token": "secret",
        },
        body: JSON.stringify({
          review_status: "reviewed",
          triage_decision: "bug",
          review_notes: "Needs regression coverage.",
          linked_case_or_issue: "RAW-123",
          reviewer_source: "admin_feedback_console",
        }),
      },
    );
  });
});
