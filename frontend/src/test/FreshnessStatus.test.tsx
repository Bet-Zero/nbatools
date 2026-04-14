import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import FreshnessStatus from "../components/FreshnessStatus";
import type { FreshnessResponse } from "../api/types";

// Mock the fetch-based client
const mockFetchFreshness = vi.fn<() => Promise<FreshnessResponse>>();

vi.mock("../api/client", () => ({
  fetchFreshness: (...args: unknown[]) => mockFetchFreshness(...(args as [])),
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
    vi.restoreAllMocks();
  });

  it("renders nothing while loading", () => {
    // Never resolves
    mockFetchFreshness.mockReturnValue(new Promise(() => {}));
    const { container } = render(<FreshnessStatus pollInterval={0} />);
    expect(container.querySelector(".freshness-panel")).toBeNull();
  });

  it("renders nothing when API is offline", async () => {
    mockFetchFreshness.mockRejectedValue(new Error("offline"));
    const { container } = render(<FreshnessStatus pollInterval={0} />);
    // Wait a tick
    await new Promise((r) => setTimeout(r, 50));
    expect(container.querySelector(".freshness-panel")).toBeNull();
  });

  it("shows fresh status with current_through date", async () => {
    mockFetchFreshness.mockResolvedValue(makeFreshnessData());
    render(<FreshnessStatus pollInterval={0} />);
    await waitFor(() => {
      expect(screen.getByText(/Data through 2026-04-13/)).toBeInTheDocument();
    });
    expect(screen.getByText("fresh")).toBeInTheDocument();
  });

  it("shows stale status", async () => {
    mockFetchFreshness.mockResolvedValue(
      makeFreshnessData({ status: "stale", current_through: "2026-04-01" }),
    );
    render(<FreshnessStatus pollInterval={0} />);
    await waitFor(() => {
      expect(screen.getByText("stale")).toBeInTheDocument();
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
      expect(screen.getByText("failed")).toBeInTheDocument();
    });
  });

  it("expands to show season details on click", async () => {
    mockFetchFreshness.mockResolvedValue(makeFreshnessData());
    render(<FreshnessStatus pollInterval={0} />);
    await waitFor(() => {
      expect(screen.getByText(/Data through/)).toBeInTheDocument();
    });

    const button = screen.getByRole("button");
    await userEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText("2025-26 Regular Season")).toBeInTheDocument();
    });
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
      expect(screen.getByText(/Data through/)).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(screen.getByText(/Last refresh/)).toBeInTheDocument();
      expect(screen.getByText(/pull_games failed/)).toBeInTheDocument();
    });
  });
});
