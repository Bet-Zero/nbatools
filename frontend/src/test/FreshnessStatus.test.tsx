import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import FreshnessStatus from "../components/FreshnessStatus";
import type { FreshnessResponse, FreshnessStatusValue } from "../api/types";

// Mock the fetch-based client
const mockFetchFreshness = vi.fn<
  (options?: { signal?: AbortSignal }) => Promise<FreshnessResponse>
>();

vi.mock("../api/client", () => ({
  fetchFreshness: (options?: { signal?: AbortSignal }) =>
    mockFetchFreshness(options),
}));

function makeFreshnessData(
  overrides: Partial<FreshnessResponse> = {},
): FreshnessResponse {
  return {
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
    ...overrides,
  };
}

describe("FreshnessStatus", () => {
  beforeEach(() => {
    mockFetchFreshness.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("renders nothing while loading", () => {
    // Never resolves
    mockFetchFreshness.mockReturnValue(new Promise(() => {}));
    const { container } = render(<FreshnessStatus pollInterval={0} />);
    expect(container.firstChild).toBeNull();
  });

  it("shows an unverified state when the initial request fails", async () => {
    mockFetchFreshness.mockRejectedValue(new Error("offline"));
    render(<FreshnessStatus pollInterval={0} />);

    await waitFor(() => {
      expect(screen.getByText("Freshness check unavailable")).toBeInTheDocument();
    });
    expect(screen.getByText("unverified")).toBeInTheDocument();
    expect(
      screen.getByText("Current data freshness could not be verified. Try again soon."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("shows fresh status with current_through date", async () => {
    mockFetchFreshness.mockResolvedValue(makeFreshnessData());
    render(<FreshnessStatus pollInterval={0} />);
    await waitFor(() => {
      expect(
        screen.getByRole("button", {
          name: "Data freshness: Data through 2026-04-13",
        }),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("current")).toBeInTheDocument();
  });

  it("shows stale status", async () => {
    mockFetchFreshness.mockResolvedValue(
      makeFreshnessData({ status: "stale", current_through: "2026-04-01" }),
    );
    render(<FreshnessStatus pollInterval={0} />);
    await waitFor(() => {
      expect(screen.getByText("awaiting refresh")).toBeInTheDocument();
    });
  });

  it("shows unknown status when no current_through", async () => {
    mockFetchFreshness.mockResolvedValue(
      makeFreshnessData({ status: "unknown", current_through: null }),
    );
    render(<FreshnessStatus pollInterval={0} />);
    await waitFor(() => {
      expect(screen.getByText("unknown")).toBeInTheDocument();
      expect(screen.getByText("Freshness unknown")).toBeInTheDocument();
    });
  });

  it("shows failed status", async () => {
    mockFetchFreshness.mockResolvedValue(
      makeFreshnessData({
        status: "failed",
        last_refresh_ok: false,
        last_refresh_error: "API timeout",
      }),
    );
    render(<FreshnessStatus pollInterval={0} />);
    await waitFor(() => {
      expect(screen.getByText("refresh failed")).toBeInTheDocument();
    });
  });

  it("renders first-run banner presentation", async () => {
    mockFetchFreshness.mockResolvedValue(makeFreshnessData());
    render(<FreshnessStatus pollInterval={0} variant="banner" />);

    await waitFor(() => {
      expect(screen.getByText("Data freshness")).toBeInTheDocument();
      expect(screen.getByText("Ready for a first query.")).toBeInTheDocument();
    });
    expect(
      screen.getByRole("button", {
        name: "Data freshness: Data through 2026-04-13",
      }),
    ).toBeInTheDocument();
  });

  it.each<[FreshnessStatusValue, string, string]>([
    [
      "stale",
      "awaiting refresh",
      "Stats run through the date shown — new games arrive with the next refresh.",
    ],
    ["unknown", "unknown", "Freshness is not confirmed."],
    [
      "failed",
      "refresh failed",
      "Refresh needs attention before results are trusted.",
    ],
  ])("shows %s banner guidance", async (status, badgeLabel, message) => {
    mockFetchFreshness.mockResolvedValue(
      makeFreshnessData({
        status,
        current_through: status === "stale" ? "2026-04-01" : null,
        last_refresh_ok: status === "failed" ? false : null,
        last_refresh_error: status === "failed" ? "API timeout" : null,
      }),
    );
    render(<FreshnessStatus pollInterval={0} variant="banner" />);

    await waitFor(() => {
      expect(screen.getByText(badgeLabel)).toBeInTheDocument();
      expect(screen.getByText(message)).toBeInTheDocument();
    });
  });

  it("expands to show season details on click", async () => {
    mockFetchFreshness.mockResolvedValue(makeFreshnessData());
    render(<FreshnessStatus pollInterval={0} />);
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Data freshness: Data through/ }),
      ).toBeInTheDocument();
    });

    const disclosure = screen.getByRole("button");
    const detailsId = disclosure.getAttribute("aria-controls");
    expect(detailsId).toBeTruthy();
    fireEvent.click(disclosure);

    await waitFor(() => {
      expect(screen.getByText("2025-26 Regular Season")).toBeInTheDocument();
      expect(screen.getByText("validation passed · generati")).toBeInTheDocument();
    });
    expect(document.getElementById(detailsId!)).toBeInTheDocument();
  });

  it("shows last refresh info when expanded", async () => {
    mockFetchFreshness.mockResolvedValue(
      makeFreshnessData({
        last_refresh_ok: false,
        last_refresh_at: "2026-04-14T09:00:00",
        last_refresh_error: "pull_games failed",
      }),
    );
    render(<FreshnessStatus pollInterval={0} />);
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Data freshness: Data through/ }),
      ).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(screen.getByText(/Last refresh/)).toBeInTheDocument();
      expect(screen.getByText(/details withheld/)).toBeInTheDocument();
    });
    expect(screen.queryByText(/pull_games failed/)).not.toBeInTheDocument();
  });

  it("revokes a fresh verification immediately after a poll failure", async () => {
    vi.useFakeTimers();
    mockFetchFreshness
      .mockResolvedValueOnce(makeFreshnessData())
      .mockRejectedValueOnce(new Error("offline"));
    render(<FreshnessStatus pollInterval={1_000} variant="banner" />);

    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByText("Data through 2026-04-13")).toBeInTheDocument();
    expect(screen.getByText("current")).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });
    expect(
      screen.getByText("Last known data through 2026-04-13"),
    ).toBeInTheDocument();
    expect(screen.getByText("unverified")).toBeInTheDocument();
    expect(screen.queryByText("current")).not.toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: /Data freshness unverified/ }),
    );
    expect(screen.getByText("Last verified: 2026-04-14T10:00:00")).toBeInTheDocument();
    expect(screen.getByText("Last-known season coverage")).toBeInTheDocument();
    expect(screen.getByText("last known through 2026-04-13")).toBeInTheDocument();
  });

  it("labels stale data as last known after a poll failure", async () => {
    vi.useFakeTimers();
    mockFetchFreshness
      .mockResolvedValueOnce(
        makeFreshnessData({ status: "stale", current_through: "2026-04-01" }),
      )
      .mockRejectedValueOnce(new Error("offline"));
    render(<FreshnessStatus pollInterval={1_000} />);

    await act(async () => {
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(1_000);
    });

    expect(
      screen.getByText("Last known data through 2026-04-01"),
    ).toBeInTheDocument();
    expect(screen.getByText("unverified")).toBeInTheDocument();
  });

  it("stays unverified across repeated failures and recovers on success", async () => {
    vi.useFakeTimers();
    mockFetchFreshness
      .mockResolvedValueOnce(makeFreshnessData())
      .mockRejectedValueOnce(new Error("first failure"))
      .mockRejectedValueOnce(new Error("second failure"))
      .mockResolvedValueOnce(
        makeFreshnessData({ status: "stale", current_through: "2026-04-20" }),
      );
    render(<FreshnessStatus pollInterval={1_000} variant="banner" />);

    await act(async () => {
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(1_000);
    });
    expect(screen.getByText("unverified")).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });
    expect(screen.getByText("unverified")).toBeInTheDocument();
    expect(mockFetchFreshness).toHaveBeenCalledTimes(3);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });
    expect(screen.getByText("Data through 2026-04-20")).toBeInTheDocument();
    expect(screen.getByText("awaiting refresh")).toBeInTheDocument();
    expect(screen.queryByText("unverified")).not.toBeInTheDocument();
    expect(mockFetchFreshness).toHaveBeenCalledTimes(4);
  });

  it("does not overlap a slow request", async () => {
    vi.useFakeTimers();
    let resolveRequest: ((value: FreshnessResponse) => void) | undefined;
    mockFetchFreshness.mockReturnValue(
      new Promise((resolve) => {
        resolveRequest = resolve;
      }),
    );
    render(<FreshnessStatus pollInterval={100} />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(mockFetchFreshness).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolveRequest?.(makeFreshnessData());
      await Promise.resolve();
    });
    expect(screen.getByText("Data through 2026-04-13")).toBeInTheDocument();
  });

  it("skips hidden polling and refreshes immediately when visible", async () => {
    vi.useFakeTimers();
    let visibility: DocumentVisibilityState = "visible";
    vi.spyOn(document, "visibilityState", "get").mockImplementation(
      () => visibility,
    );
    mockFetchFreshness
      .mockResolvedValueOnce(makeFreshnessData())
      .mockResolvedValueOnce(
        makeFreshnessData({ current_through: "2026-04-20" }),
      );
    render(<FreshnessStatus pollInterval={1_000} />);

    await act(async () => {
      await Promise.resolve();
    });
    visibility = "hidden";
    act(() => document.dispatchEvent(new Event("visibilitychange")));
    expect(screen.getByText("unverified")).toBeInTheDocument();
    expect(screen.queryByText("current")).not.toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000);
    });
    expect(mockFetchFreshness).toHaveBeenCalledTimes(1);

    visibility = "visible";
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
      await Promise.resolve();
    });
    expect(mockFetchFreshness).toHaveBeenCalledTimes(2);
    expect(screen.getByText("Data through 2026-04-20")).toBeInTheDocument();
  });

  it("aborts hidden work and ignores its late resolution", async () => {
    let visibility: DocumentVisibilityState = "visible";
    vi.spyOn(document, "visibilityState", "get").mockImplementation(
      () => visibility,
    );
    let firstSignal: AbortSignal | undefined;
    let resolveFirst: ((value: FreshnessResponse) => void) | undefined;
    let resolveSecond: ((value: FreshnessResponse) => void) | undefined;
    mockFetchFreshness
      .mockImplementationOnce(
        (options) =>
          new Promise((resolve) => {
            firstSignal = options?.signal;
            resolveFirst = resolve;
          }),
      )
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveSecond = resolve;
          }),
      );
    render(<FreshnessStatus pollInterval={1_000} />);

    visibility = "hidden";
    act(() => document.dispatchEvent(new Event("visibilitychange")));
    expect(firstSignal?.aborted).toBe(true);

    visibility = "visible";
    act(() => document.dispatchEvent(new Event("visibilitychange")));
    expect(mockFetchFreshness).toHaveBeenCalledTimes(2);

    await act(async () => {
      resolveSecond?.(makeFreshnessData({ current_through: "2026-04-20" }));
      await Promise.resolve();
    });
    expect(screen.getByText("Data through 2026-04-20")).toBeInTheDocument();

    await act(async () => {
      resolveFirst?.(makeFreshnessData({ current_through: "2026-04-01" }));
      await Promise.resolve();
    });
    expect(screen.getByText("Data through 2026-04-20")).toBeInTheDocument();
    expect(screen.queryByText("Data through 2026-04-01")).not.toBeInTheDocument();
  });

  it("aborts an in-flight request on unmount", async () => {
    let signal: AbortSignal | undefined;
    mockFetchFreshness.mockImplementation(
      (options) =>
        new Promise((_resolve, reject) => {
          signal = options?.signal;
          signal?.addEventListener("abort", () => {
            reject(new DOMException("aborted", "AbortError"));
          });
        }),
    );
    const { unmount } = render(<FreshnessStatus pollInterval={1_000} />);

    expect(signal?.aborted).toBe(false);
    unmount();
    expect(signal?.aborted).toBe(true);
  });

  it("normalizes invalid runtime statuses to unknown", async () => {
    const invalid = makeFreshnessData({
      status: "unexpected" as FreshnessStatusValue,
      current_through: "2026-04-13",
      seasons: [
        {
          ...makeFreshnessData().seasons[0],
          status: "unexpected" as FreshnessStatusValue,
        },
      ],
    });
    mockFetchFreshness.mockResolvedValue(invalid);
    render(<FreshnessStatus pollInterval={0} />);

    await waitFor(() => {
      expect(screen.getByText("Freshness unknown")).toBeInTheDocument();
    });
    expect(screen.getByText("unknown")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getAllByText("unknown")).toHaveLength(2);
  });

  it("announces verification changes through a polite atomic status", async () => {
    mockFetchFreshness.mockRejectedValue(new Error("private provider failure"));
    render(<FreshnessStatus pollInterval={0} />);

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(
        "Data freshness unverified: Freshness check unavailable",
      );
    });
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
    expect(screen.getByRole("status")).toHaveAttribute("aria-atomic", "true");
    expect(screen.queryByText(/private provider failure/)).not.toBeInTheDocument();
  });

  it("announces panel recovery without first-query banner guidance", async () => {
    vi.useFakeTimers();
    mockFetchFreshness
      .mockResolvedValueOnce(makeFreshnessData())
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(
        makeFreshnessData({ current_through: "2026-04-20" }),
      );
    render(<FreshnessStatus pollInterval={1_000} />);

    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByRole("status")).toHaveTextContent(
      "Data freshness: Data through 2026-04-13",
    );
    expect(screen.getByRole("status")).not.toHaveTextContent(
      "Ready for a first query",
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });
    expect(screen.getByRole("status")).toHaveTextContent(
      "Data freshness unverified",
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });
    expect(screen.getByRole("status")).toHaveTextContent(
      "Data freshness: Data through 2026-04-20",
    );
    expect(screen.getByRole("status")).not.toHaveTextContent(
      "Ready for a first query",
    );
  });
});
