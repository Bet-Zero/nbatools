import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { QueryResponse, ResultMetadata } from "../api/types";

vi.mock("../api/client", () => ({
  fetchHealth: vi.fn(),
  fetchFreshness: vi.fn(),
  fetchRoutes: vi.fn(),
  postQuery: vi.fn(),
  postQueryFeedback: vi.fn(),
  postStructuredQuery: vi.fn(),
}));

import App from "../App";
import {
  fetchFreshness,
  fetchHealth,
  fetchRoutes,
  postQuery,
  postQueryFeedback,
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
  fireEvent.change(screen.getByLabelText("Ask an NBA question"), {
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
  vi.mocked(postQueryFeedback).mockResolvedValue({
    ok: true,
    feedback_id: "qfb_test",
    stored: true,
    disabled: false,
  });
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

    // Wait for the themed result surface itself rather than the
    // debug-only "Result" eyebrow: public mode is the default and does
    // not render that eyebrow. The data attribute is applied on the
    // result section regardless of display mode.
    await waitFor(() =>
      expect(container.querySelector('[data-team-theme="BOS"]')).not.toBeNull(),
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

    // Wait for the result section to mount via its stable data attribute
    // (rendered in both public and debug modes), then assert no team
    // theme was applied for the multi-team result.
    await waitFor(() =>
      expect(
        container.querySelector("[data-state-surface='result']"),
      ).not.toBeNull(),
    );

    expect(container.querySelector("[data-team-theme]")).toBeNull();
  });
});

const qualifiedEmptyMetadata: ResultMetadata = {
  team: "LAL",
  season: "2023-24",
  opponent: "BOS",
  player: null,
  with_player: "Jayson Tatum and Anthony Davis",
  last_n: 1,
  last_n_scope: "original_window",
  unsupported_filters: [],
  applied_filters: [
    { label: "Opponent", value: "BOS", kind: "team" },
    {
      label: "With player",
      value: "Jayson Tatum and Anthony Davis",
      kind: "player",
    },
    { label: "Last N games", value: "1", kind: "window" },
    {
      label: "Sample selection",
      value:
        "Select the last 1 original matchup game before checking both played predicates",
      kind: "window",
    },
  ],
};

function emptyResponse(
  reason: string,
  metadata = qualifiedEmptyMetadata,
): QueryResponse {
  const response = makeResponse(metadata);
  return {
    ...response,
    ok: false,
    route: "team_record",
    result_status: "no_result",
    result_reason: reason,
    result: {
      ...response.result,
      result_status: "no_result",
      result_reason: reason,
      sections: {},
    },
  };
}

describe("App qualified empty answer context", () => {
  it("shows the executed subject, both predicates and original sample without inventing a zero", async () => {
    vi.mocked(postQuery).mockResolvedValueOnce(emptyResponse("no_match"));
    render(<App />);
    submitQuery(
      "Lakers record against Celtics within their last game with Tatum playing while Davis plays in 2023-24",
    );
    const context = await screen.findByLabelText("Result context");
    expect(context).toHaveTextContent("LAL");
    expect(context).toHaveTextContent("BOS");
    expect(context).toHaveTextContent("2023-24");
    expect(context).toHaveTextContent("Jayson Tatum and Anthony Davis");
    expect((context.textContent?.match(/Jayson Tatum and Anthony Davis/g) ?? [])).toHaveLength(1);
    expect((context.textContent?.match(/before checking both played predicates/g) ?? [])).toHaveLength(1);
    expect(context).toHaveTextContent(
      "Select the last 1 original matchup game before checking both played predicates",
    );
    expect(screen.getByText("No Matching Results")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByText(/^0(?:[–-]0)?$/)).not.toBeInTheDocument();
  });

  it.each(["filter_not_supported", "no_data", "unrouted", "error"])(
    "does not present requested filters as executed for %s",
    async (reason) => {
      const response = emptyResponse(reason);
      if (reason === "error") {
        response.result_status = "error";
        response.result.result_status = "error";
      }
      vi.mocked(postQuery).mockResolvedValueOnce(response);
      render(<App />);
      submitQuery("test unavailable query");
      await waitFor(() =>
        expect(
          document.querySelector('[data-state-surface="result"]'),
        ).not.toBeNull(),
      );
      expect(screen.queryByLabelText("Result context")).not.toBeInTheDocument();
      expect(screen.queryByText(/^0(?:[–-]0)?$/)).not.toBeInTheDocument();
    },
  );

  it.each([
    { applied_filters: [] },
    { applied_filters: [{ label: " ", value: " ", kind: "window" }] },
    { unsupported_filters: ["unresolved_player_availability"] },
  ])(
    "requires usable applied filters and no blocked predicates: %j",
    async (damage) => {
      vi.mocked(postQuery).mockResolvedValueOnce(
        emptyResponse("no_match", { ...qualifiedEmptyMetadata, ...damage }),
      );
      render(<App />);
      submitQuery("unqualified empty response");
      await screen.findByText("No Matching Results");
      expect(screen.queryByLabelText("Result context")).not.toBeInTheDocument();
    },
  );
});
