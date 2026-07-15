import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { QueryResponse } from "../api/types";

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

interface Deferred<T> {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason: unknown) => void;
}

function deferred<T>(): Deferred<T> {
  let resolve: (value: T) => void = () => {};
  let reject: (reason: unknown) => void = () => {};
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });
  return { promise, resolve, reject };
}

function makeResponse(
  query: string,
  playerName: string,
  route = "player_game_summary",
): QueryResponse {
  return {
    ok: true,
    query,
    route,
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
        route,
        player: playerName,
        season: "2025-26",
        applied_filters: [
          { label: "Last N games", value: "5", kind: "window" },
        ],
      },
      notes: [],
      caveats: [],
      sections: {
        summary: [{ player_name: playerName, pts_avg: 30 }],
      },
    },
  };
}

function starterButton(query: string): HTMLElement {
  return screen.getByRole("button", {
    name: `Run starter query: ${query}`,
  });
}

async function openDevTools(routes: string[]): Promise<void> {
  fireEvent.click(screen.getByText(/Dev Tools/));
  await waitFor(() =>
    expect(screen.getByRole("option", { name: routes[0] })).toBeInTheDocument(),
  );
}

function runStructured(route: string, kwargs = "{}"): void {
  fireEvent.change(screen.getByLabelText("Route"), {
    target: { value: route },
  });
  fireEvent.change(screen.getByLabelText("kwargs (JSON)"), {
    target: { value: kwargs },
  });
  fireEvent.click(screen.getByRole("button", { name: "Run Structured Query" }));
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
  vi.mocked(postQueryFeedback).mockResolvedValue({
    ok: true,
    feedback_id: "qfb_test",
    stored: true,
    disabled: false,
  });
});

describe("latest request ownership", () => {
  it("keeps the latest natural result, URL, input, and history after reversed completion", async () => {
    const first = deferred<QueryResponse>();
    const latest = deferred<QueryResponse>();
    vi.mocked(postQuery).mockImplementation((query) =>
      query === "Jokic last 10 games" ? first.promise : latest.promise,
    );

    const { container } = render(<App />);

    fireEvent.click(starterButton("Jokic last 10 games"));
    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(1));
    const firstSignal = vi.mocked(postQuery).mock.calls[0][1]?.signal;

    fireEvent.click(starterButton("Celtics record 2024-25"));
    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(2));
    expect(firstSignal?.aborted).toBe(true);

    await act(async () => {
      latest.resolve(makeResponse("Celtics record 2024-25", "Jayson Tatum"));
    });
    await waitFor(() =>
      expect(screen.getByText(/Jayson Tatum has averaged/)).toBeInTheDocument(),
    );

    await act(async () => {
      first.resolve(makeResponse("Jokic last 10 games", "Nikola Jokic"));
    });

    expect(screen.queryByText(/Nikola Jokic has averaged/)).toBeNull();
    expect(screen.getByLabelText("Ask an NBA question")).toHaveValue(
      "Celtics record 2024-25",
    );
    expect(new URLSearchParams(window.location.search).get("q")).toBe(
      "Celtics record 2024-25",
    );
    expect(
      screen.getByRole("button", {
        name: "Run history query: Celtics record 2024-25",
      }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: "Run history query: Jokic last 10 games",
      }),
    ).toBeNull();
    expect(container.querySelector("[data-app-state='result']")).not.toBeNull();
  });

  it("keeps the latest structured result and aborts the superseded structured request", async () => {
    const routes = ["player_game_summary"];
    const first = deferred<QueryResponse>();
    const latest = deferred<QueryResponse>();
    window.history.replaceState(null, "", "/?debug=1");
    vi.mocked(fetchRoutes).mockResolvedValue({ routes });
    vi.mocked(postStructuredQuery).mockImplementation((_route, kwargs) =>
      kwargs.season === "2024-25" ? first.promise : latest.promise,
    );

    render(<App />);
    await openDevTools(routes);

    runStructured(routes[0], '{"season":"2024-25"}');
    await waitFor(() => expect(postStructuredQuery).toHaveBeenCalledTimes(1));
    const firstSignal = vi.mocked(postStructuredQuery).mock.calls[0][2]?.signal;

    runStructured(routes[0], '{"season":"2025-26"}');
    await waitFor(() => expect(postStructuredQuery).toHaveBeenCalledTimes(2));
    expect(firstSignal?.aborted).toBe(true);

    await act(async () => {
      latest.resolve(
        makeResponse("latest structured", "Jayson Tatum", routes[0]),
      );
    });
    await waitFor(() =>
      expect(screen.getByText(/Jayson Tatum has averaged/)).toBeInTheDocument(),
    );

    await act(async () => {
      first.resolve(
        makeResponse("stale structured", "Nikola Jokic", routes[0]),
      );
    });

    expect(screen.queryByText(/Nikola Jokic has averaged/)).toBeNull();
    expect(new URLSearchParams(window.location.search).get("route")).toBe(
      routes[0],
    );
    expect(new URLSearchParams(window.location.search).get("kwargs")).toBe(
      '{"season":"2025-26"}',
    );
    expect(screen.getByLabelText("Ask an NBA question")).toHaveValue("");
    expect(
      screen.getByRole("button", {
        name: "Run history query: latest structured",
      }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: "Run history query: stale structured",
      }),
    ).toBeNull();
  });

  it("suppresses a stale natural error and preserves loading ownership for a newer structured request", async () => {
    const routes = ["player_game_summary"];
    const stale = deferred<QueryResponse>();
    const latest = deferred<QueryResponse>();
    window.history.replaceState(null, "", "/?debug=1");
    vi.mocked(fetchRoutes).mockResolvedValue({ routes });
    vi.mocked(postQuery).mockReturnValue(stale.promise);
    vi.mocked(postStructuredQuery).mockReturnValue(latest.promise);

    const { container } = render(<App />);
    await openDevTools(routes);

    fireEvent.click(starterButton("Jokic last 10 games"));
    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(1));
    runStructured(routes[0]);
    await waitFor(() => expect(postStructuredQuery).toHaveBeenCalledTimes(1));

    await act(async () => {
      stale.reject(new Error("stale request failed"));
    });

    expect(
      container.querySelector("[data-app-state='loading']"),
    ).not.toBeNull();
    expect(screen.getByRole("status")).toHaveTextContent("Searching NBA data");
    expect(screen.queryByText("stale request failed")).toBeNull();
    expect(postQueryFeedback).not.toHaveBeenCalled();

    await act(async () => {
      latest.resolve(
        makeResponse("latest structured", "Jayson Tatum", routes[0]),
      );
    });
    await waitFor(() =>
      expect(screen.getByText(/Jayson Tatum has averaged/)).toBeInTheDocument(),
    );
  });

  it("does not submit automatic feedback for the current query error", async () => {
    vi.mocked(postQuery).mockRejectedValueOnce(new Error("current request failed"));

    render(<App />);
    fireEvent.click(starterButton("Jokic last 10 games"));

    expect(await screen.findByText("current request failed")).toBeInTheDocument();
    expect(postQueryFeedback).not.toHaveBeenCalled();
  });

  it("prevents a superseded retry from replacing a newer starter-query result", async () => {
    const retry = deferred<QueryResponse>();
    const latest = deferred<QueryResponse>();
    vi.mocked(postQuery)
      .mockRejectedValueOnce(new Error("temporary failure"))
      .mockReturnValueOnce(retry.promise)
      .mockReturnValueOnce(latest.promise);

    render(<App />);

    fireEvent.click(starterButton("Jokic last 10 games"));
    await waitFor(() =>
      expect(screen.getByText("temporary failure")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole("button", { name: "Retry query" }));
    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(2));
    const retrySignal = vi.mocked(postQuery).mock.calls[1][1]?.signal;

    fireEvent.click(starterButton("Celtics record 2024-25"));
    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(3));
    expect(retrySignal?.aborted).toBe(true);

    await act(async () => {
      latest.resolve(makeResponse("Celtics record 2024-25", "Jayson Tatum"));
    });
    await waitFor(() =>
      expect(screen.getByText(/Jayson Tatum has averaged/)).toBeInTheDocument(),
    );

    await act(async () => {
      retry.resolve(makeResponse("Jokic last 10 games", "Nikola Jokic"));
    });

    expect(screen.queryByText(/Nikola Jokic has averaged/)).toBeNull();
    expect(new URLSearchParams(window.location.search).get("q")).toBe(
      "Celtics record 2024-25",
    );
    expect(
      screen.queryByRole("button", {
        name: "Run history query: Jokic last 10 games",
      }),
    ).toBeNull();
  });

  it("gives popstate navigation ownership over an in-flight request", async () => {
    const first = deferred<QueryResponse>();
    const navigated = deferred<QueryResponse>();
    vi.mocked(postQuery).mockImplementation((query) =>
      query === "Jokic last 10 games" ? first.promise : navigated.promise,
    );

    render(<App />);

    fireEvent.click(starterButton("Jokic last 10 games"));
    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(1));
    const firstSignal = vi.mocked(postQuery).mock.calls[0][1]?.signal;

    act(() => {
      window.history.pushState(null, "", "/?q=Celtics+record+2024-25");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(2));
    expect(firstSignal?.aborted).toBe(true);

    await act(async () => {
      navigated.resolve(makeResponse("Celtics record 2024-25", "Jayson Tatum"));
    });
    await act(async () => {
      first.resolve(makeResponse("Jokic last 10 games", "Nikola Jokic"));
    });

    await waitFor(() =>
      expect(screen.getByText(/Jayson Tatum has averaged/)).toBeInTheDocument(),
    );
    expect(screen.getByLabelText("Ask an NBA question")).toHaveValue(
      "Celtics record 2024-25",
    );
    expect(new URLSearchParams(window.location.search).get("q")).toBe(
      "Celtics record 2024-25",
    );
    expect(screen.queryByText(/Nikola Jokic has averaged/)).toBeNull();
  });

  it("routes query-history launches through the same latest-request owner", async () => {
    const pending = deferred<QueryResponse>();
    const recalled = deferred<QueryResponse>();
    vi.mocked(postQuery)
      .mockResolvedValueOnce(
        makeResponse("Jokic last 10 games", "Nikola Jokic"),
      )
      .mockReturnValueOnce(pending.promise)
      .mockReturnValueOnce(recalled.promise);

    render(<App />);

    fireEvent.click(starterButton("Jokic last 10 games"));
    await waitFor(() =>
      expect(
        screen.getByRole("button", {
          name: "Run history query: Jokic last 10 games",
        }),
      ).toBeInTheDocument(),
    );

    fireEvent.click(starterButton("Celtics record 2024-25"));
    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(2));
    const pendingSignal = vi.mocked(postQuery).mock.calls[1][1]?.signal;

    fireEvent.click(
      screen.getByRole("button", {
        name: "Run history query: Jokic last 10 games",
      }),
    );
    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(3));
    expect(pendingSignal?.aborted).toBe(true);

    await act(async () => {
      recalled.resolve(makeResponse("Jokic last 10 games", "Nikola Jokic"));
    });
    await act(async () => {
      pending.resolve(makeResponse("Celtics record 2024-25", "Jayson Tatum"));
    });

    await waitFor(() =>
      expect(screen.getByText(/Nikola Jokic has averaged/)).toBeInTheDocument(),
    );
    expect(screen.queryByText(/Jayson Tatum has averaged/)).toBeNull();
    expect(new URLSearchParams(window.location.search).get("q")).toBe(
      "Jokic last 10 games",
    );
  });

  it("aborts the active request on unmount and ignores its later failure", async () => {
    const pending = deferred<QueryResponse>();
    vi.mocked(postQuery).mockReturnValue(pending.promise);

    const { unmount } = render(<App />);
    fireEvent.click(starterButton("Jokic last 10 games"));
    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(1));
    const signal = vi.mocked(postQuery).mock.calls[0][1]?.signal;

    unmount();
    expect(signal?.aborted).toBe(true);

    await act(async () => {
      pending.reject(new Error("finished after unmount"));
    });
    expect(postQueryFeedback).not.toHaveBeenCalled();
  });
});
