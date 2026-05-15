import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { isValidElement, type ReactElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { QueryResponse } from "../api/types";

vi.mock("../api/client", () => ({
  postQuery: vi.fn(),
}));

vi.mock("../lib/reviewScreenshots", () => ({
  downloadReviewScreenshots: vi.fn(),
}));

import VisualQaPage from "../VisualQaPage";
import { postQuery } from "../api/client";
import { downloadReviewScreenshots } from "../lib/reviewScreenshots";
import { resolveRootView } from "../main";
import { VISUAL_QA_CASES, VISUAL_QA_INTERNAL_ROUTE } from "../visualQaCases";

function deferred<T>() {
  let resolve: (value: T) => void = () => {};
  let reject: (reason?: unknown) => void = () => {};
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function makeNoResult(query: string): QueryResponse {
  return {
    ok: false,
    query,
    route: "season_leaders",
    result_status: "no_result",
    result_reason: "filter_not_supported",
    current_through: null,
    confidence: null,
    intent: "leaderboard",
    alternates: [],
    notes: [],
    caveats: [],
    result: {
      query_class: "leaderboard",
      result_status: "no_result",
      result_reason: "filter_not_supported",
      metadata: {},
      notes: [],
      caveats: [],
      sections: {},
    },
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(downloadReviewScreenshots).mockResolvedValue();
});

describe("VisualQaPage", () => {
  it("renders all 15 visual QA case ids and focus text from the manifest", async () => {
    vi.mocked(postQuery).mockImplementation((query) =>
      Promise.resolve(makeNoResult(query)),
    );

    render(<VisualQaPage />);

    expect(
      await screen.findByText("15 / 15 cases completed"),
    ).toBeInTheDocument();
    expect(document.querySelectorAll("[data-visual-case-id]").length).toBe(
      VISUAL_QA_CASES.length,
    );
    expect(
      screen.getByText("guards_fg_percentage_leaders"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Position guards chip stays visually tied to the generic leaderboard hero",
      ),
    ).toBeInTheDocument();
  });

  it("does not crash when some cases are loading and others hit request errors", async () => {
    const pending = deferred<QueryResponse>();

    vi.mocked(postQuery).mockImplementation((query) => {
      if (query === VISUAL_QA_CASES[0].query) {
        return pending.promise;
      }

      if (query === VISUAL_QA_CASES[1].query) {
        return Promise.reject(new Error("Backend unavailable"));
      }

      return Promise.resolve(makeNoResult(query));
    });

    render(<VisualQaPage />);

    await screen.findByText("guards_fg_percentage_leaders");

    const loadingCard = document.querySelector(
      '[data-visual-case-id="guards_fg_percentage_leaders"]',
    ) as HTMLElement | null;
    const errorCard = document.querySelector(
      '[data-visual-case-id="centers_rebound_leaders_wave4"]',
    ) as HTMLElement | null;

    expect(loadingCard).not.toBeNull();
    expect(errorCard).not.toBeNull();

    await waitFor(() =>
      expect(
        within(loadingCard as HTMLElement).getAllByText(
          "Loading live /query response...",
        ).length,
      ).toBeGreaterThan(0),
    );
    await waitFor(() =>
      expect(
        within(errorCard as HTMLElement).getByText("Backend unavailable"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getAllByText(
        "Pass/fail notes: capture desktop and mobile evidence, then record manual observations in the checklist doc.",
      ).length,
    ).toBeGreaterThan(0);

    pending.resolve(makeNoResult(VISUAL_QA_CASES[0].query));
    await screen.findByText("15 / 15 cases completed");
  });

  it("renders the capture button and passes every loaded case card to the screenshot helper", async () => {
    vi.mocked(postQuery).mockImplementation((query) =>
      Promise.resolve(makeNoResult(query)),
    );

    render(<VisualQaPage />);

    await screen.findByText("15 / 15 cases completed");

    const button = screen.getByRole("button", {
      name: "Download current viewport screenshots ZIP",
    });

    fireEvent.click(button);

    await waitFor(() =>
      expect(downloadReviewScreenshots).toHaveBeenCalledTimes(1),
    );
    expect(
      vi.mocked(downloadReviewScreenshots).mock.calls[0]?.[0],
    ).toHaveLength(VISUAL_QA_CASES.length);
  });

  it("routes the internal visual QA path to the visual QA page", () => {
    const view = resolveRootView(VISUAL_QA_INTERNAL_ROUTE);

    expect(isValidElement(view)).toBe(true);
    expect((view as ReactElement).type).toBe(VisualQaPage);
  });
});
