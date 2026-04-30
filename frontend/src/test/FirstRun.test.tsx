import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { QueryResponse } from "../api/types";

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

function makeResponse(query: string): QueryResponse {
  return {
    ok: true,
    query,
    route: "player_game_summary",
    result_status: "ok",
    result_reason: null,
    current_through: "2026-04-28",
    confidence: null,
    intent: null,
    alternates: [],
    notes: [],
    caveats: [],
    result: {
      query_class: "summary",
      result_status: "ok",
      metadata: {
        route: "player_game_summary",
      },
      notes: [],
      caveats: [],
      sections: {
        summary: [{ player_name: "Nikola Jokic", PTS: 30 }],
      },
    },
  };
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

describe("first-run starter queries", () => {
  it("keeps keyboard flow from query input to starter queries", async () => {
    const user = userEvent.setup();
    render(<App />);

    await waitFor(() =>
      expect(screen.getByText("Data freshness")).toBeInTheDocument(),
    );

    const input = screen.getByLabelText("Search NBA performance");
    input.focus();
    expect(input).toHaveFocus();

    await user.tab();

    expect(
      screen.getByRole("button", {
        name: "Run starter query: Jokic last 10 games",
      }),
    ).toHaveFocus();
  });

  it("runs a starter query through the natural-query path", async () => {
    vi.mocked(postQuery).mockResolvedValueOnce(
      makeResponse("Jokic last 10 games"),
    );

    render(<App />);

    await waitFor(() =>
      expect(screen.getByText("Data freshness")).toBeInTheDocument(),
    );
    expect(screen.getByText("Ready for a first query.")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Run starter query: Jokic last 10 games",
      }),
    );

    await waitFor(() =>
      expect(postQuery).toHaveBeenCalledWith("Jokic last 10 games"),
    );
    expect(new URLSearchParams(window.location.search).get("q")).toBe(
      "Jokic last 10 games",
    );
    expect(screen.getByLabelText("Search NBA performance")).toHaveValue(
      "Jokic last 10 games",
    );
    await waitFor(() =>
      expect(screen.getByText("Query output")).toBeInTheDocument(),
    );
  });
});
