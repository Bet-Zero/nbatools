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

  it("shows the shared loading preview for pending natural queries", async () => {
    let resolveQuery: (data: QueryResponse) => void = () => {};
    vi.mocked(postQuery).mockReturnValueOnce(
      new Promise<QueryResponse>((resolve) => {
        resolveQuery = resolve;
      }),
    );

    render(<App />);

    fireEvent.change(screen.getByLabelText("Search NBA performance"), {
      target: { value: "Jokic last 10 games" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Query" }));

    expect(screen.getByRole("status")).toHaveTextContent(
      "Searching NBA data",
    );
    expect(screen.getByLabelText("Loading result preview")).toBeInTheDocument();

    resolveQuery(makeResponse("Jokic last 10 games"));
    await waitFor(() =>
      expect(screen.getByText("Query output")).toBeInTheDocument(),
    );
  });

  it("shows the shared loading preview for pending structured queries", async () => {
    let resolveStructured: (data: QueryResponse) => void = () => {};
    vi.mocked(fetchRoutes).mockResolvedValueOnce({
      routes: ["season_leaders"],
    });
    vi.mocked(postStructuredQuery).mockReturnValueOnce(
      new Promise<QueryResponse>((resolve) => {
        resolveStructured = resolve;
      }),
    );

    render(<App />);

    fireEvent.click(screen.getByText(/Dev Tools/));
    await waitFor(() =>
      expect(
        screen.getByRole("option", { name: "season_leaders" }),
      ).toBeInTheDocument(),
    );
    fireEvent.change(screen.getByLabelText("Route"), {
      target: { value: "season_leaders" },
    });
    fireEvent.change(screen.getByLabelText("kwargs (JSON)"), {
      target: { value: '{"stat":"pts"}' },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Run Structured Query" }),
    );

    expect(postStructuredQuery).toHaveBeenCalledWith("season_leaders", {
      stat: "pts",
    });
    expect(screen.getByRole("status")).toHaveTextContent(
      "Searching NBA data",
    );
    expect(screen.getByLabelText("Loading result preview")).toBeInTheDocument();

    resolveStructured(makeResponse("structured query"));
    await waitFor(() =>
      expect(screen.getByText("Query output")).toBeInTheDocument(),
    );
  });

  it("retries a failed natural query through the existing query path", async () => {
    vi.mocked(postQuery)
      .mockRejectedValueOnce(new Error("Network request failed\nstack line"))
      .mockResolvedValueOnce(makeResponse("Jokic last 10 games"));

    render(<App />);

    fireEvent.change(screen.getByLabelText("Search NBA performance"), {
      target: { value: "Jokic last 10 games" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Query" }));

    await waitFor(() =>
      expect(screen.getByText("Request failed")).toBeInTheDocument(),
    );
    expect(screen.getByText("Network request failed")).toBeInTheDocument();
    expect(screen.queryByText("stack line")).not.toBeInTheDocument();
    expect(new URLSearchParams(window.location.search).get("q")).toBe(
      "Jokic last 10 games",
    );

    fireEvent.click(screen.getByRole("button", { name: "Retry query" }));

    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(2));
    await waitFor(() =>
      expect(screen.getByText("Query output")).toBeInTheDocument(),
    );
    expect(new URLSearchParams(window.location.search).get("q")).toBe(
      "Jokic last 10 games",
    );
  });

  it("retries a failed structured query through the existing structured path", async () => {
    vi.mocked(fetchRoutes).mockResolvedValueOnce({
      routes: ["season_leaders"],
    });
    vi.mocked(postStructuredQuery)
      .mockRejectedValueOnce(new Error("Structured API timeout"))
      .mockResolvedValueOnce(makeResponse("structured query"));

    render(<App />);

    fireEvent.click(screen.getByText(/Dev Tools/));
    await waitFor(() =>
      expect(
        screen.getByRole("option", { name: "season_leaders" }),
      ).toBeInTheDocument(),
    );
    fireEvent.change(screen.getByLabelText("Route"), {
      target: { value: "season_leaders" },
    });
    fireEvent.change(screen.getByLabelText("kwargs (JSON)"), {
      target: { value: '{"stat":"pts"}' },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Run Structured Query" }),
    );

    await waitFor(() =>
      expect(screen.getByText("Structured API timeout")).toBeInTheDocument(),
    );
    expect(new URLSearchParams(window.location.search).get("route")).toBe(
      "season_leaders",
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Retry structured query" }),
    );

    await waitFor(() => expect(postStructuredQuery).toHaveBeenCalledTimes(2));
    expect(postStructuredQuery).toHaveBeenLastCalledWith("season_leaders", {
      stat: "pts",
    });
    await waitFor(() =>
      expect(screen.getByText("Query output")).toBeInTheDocument(),
    );
    expect(new URLSearchParams(window.location.search).get("route")).toBe(
      "season_leaders",
    );
  });

  it("keeps API-offline failures distinct from no-result responses", async () => {
    vi.mocked(fetchHealth).mockRejectedValueOnce(new Error("offline"));
    vi.mocked(postQuery).mockRejectedValueOnce(new Error("Failed to fetch"));

    render(<App />);

    await waitFor(() =>
      expect(screen.getByText("unreachable")).toBeInTheDocument(),
    );
    fireEvent.change(screen.getByLabelText("Search NBA performance"), {
      target: { value: "Celtics record 2024-25" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Query" }));

    await waitFor(() =>
      expect(screen.getAllByText("API offline").length).toBeGreaterThan(1),
    );
    expect(screen.getByLabelText("Failure details")).toHaveTextContent(
      "Failed to fetch",
    );
    expect(screen.queryByText("No Matching Results")).not.toBeInTheDocument();
  });
});
