import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { QueryResponse, ResultMetadata } from "../api/types";

vi.mock("../api/client", () => ({
  fetchHealth: vi.fn(),
  fetchFreshness: vi.fn(),
  fetchRoutes: vi.fn(),
  postQuery: vi.fn(),
  postStructuredQuery: vi.fn(),
}));

import App from "../App";
import {
  fetchFreshness,
  fetchHealth,
  fetchRoutes,
  postQuery,
  postStructuredQuery,
} from "../api/client";

function makeResponse(
  metadata: ResultMetadata,
  queryClass = "summary",
): QueryResponse {
  return {
    ok: true,
    query: "test query",
    route: "game_summary",
    result_status: "ok",
    result_reason: null,
    current_through: "2026-04-28",
    confidence: null,
    intent: null,
    alternates: [],
    notes: [],
    caveats: [],
    result: {
      query_class: queryClass,
      result_status: "ok",
      metadata,
      notes: [],
      caveats: [],
      sections: {
        summary: [{ team_name: "Celtics", wins: 60 }],
      },
    },
  };
}

function submitQuery(query: string) {
  fireEvent.change(screen.getByLabelText("Search NBA performance"), {
    target: { value: query },
  });
  fireEvent.click(screen.getByRole("button", { name: "Query" }));
}

beforeEach(() => {
  vi.clearAllMocks();
  window.history.replaceState(null, "", "/");
  window.localStorage.clear();
  vi.mocked(fetchHealth).mockResolvedValue({
    status: "ok",
    version: "0.5.0",
  });
  vi.mocked(fetchFreshness).mockResolvedValue({
    status: "fresh",
    current_through: "2026-04-28",
    checked_at: "2026-04-29T10:00:00",
    seasons: [],
    last_refresh_ok: true,
    last_refresh_at: "2026-04-29T09:00:00",
    last_refresh_error: null,
  });
  vi.mocked(fetchRoutes).mockResolvedValue({ routes: [] });
  vi.mocked(postStructuredQuery).mockRejectedValue(
    new Error("structured query not used"),
  );
});

describe("App scoped team theming", () => {
  it("applies scoped team variables to single-team result surfaces", async () => {
    vi.mocked(postQuery).mockResolvedValueOnce(
      makeResponse({
        team: "BOS",
        team_context: {
          team_id: 1610612738,
          team_abbr: "BOS",
          team_name: "Celtics",
        },
      }),
    );

    const { container } = render(<App />);
    submitQuery("celtics record");

    await waitFor(() =>
      expect(screen.getByText("Query output")).toBeInTheDocument(),
    );

    const surface = container.querySelector('[data-team-theme="BOS"]');
    expect(surface).toHaveStyle("--team-primary: #007A33");
    expect(surface).toHaveStyle("--team-secondary: #BA9653");
  });

  it("keeps multi-team results neutral", async () => {
    vi.mocked(postQuery).mockResolvedValueOnce(
      makeResponse(
        {
          teams: ["BOS", "LAL"],
          teams_context: [
            {
              team_id: 1610612738,
              team_abbr: "BOS",
              team_name: "Celtics",
            },
            {
              team_id: 1610612747,
              team_abbr: "LAL",
              team_name: "Lakers",
            },
          ],
        },
        "comparison",
      ),
    );

    const { container } = render(<App />);
    submitQuery("celtics vs lakers");

    await waitFor(() =>
      expect(screen.getByText("Query output")).toBeInTheDocument(),
    );

    expect(container.querySelector("[data-team-theme]")).toBeNull();
  });
});
