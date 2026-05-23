import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { QueryResponse } from "../api/types";
import visualQaCorpusRawText from "../../../qa/frontend_visual_qa_corpus.yaml?raw";

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
import styles from "../VisualQaPage.module.css";

const APPROVED_VISUAL_QA_CASE_IDS = [
  "guards_fg_percentage_leaders",
  "centers_rebound_leaders_wave4",
  "fewest_points_allowed_team_leader",
  "most_points_allowed_team_leaders_wave4",
  "opponent_ppg_leaders_wave4",
  "personal_foul_leaders_wave4",
  "rookie_scoring_leaders_wave4",
  "starter_assist_leaders_wave4",
  "bench_scoring_leaders_wave4",
  "celtics_bench_scoring_boundary_wave4",
  "record_when_jokic_triple_double",
  "lakers_road_record_last_season",
  "heat_knicks_playoff_series_record_wave4",
  "lebron_durant_comparison_wave4",
  "biggest_scoring_games",
  "jokic_season_summary",
  "jokic_triple_double_finder",
  "jokic_home_away_split",
  "curry_3_threes_streak",
  "jokic_best_5_rebounding_stretch",
] as const;

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
  it("loads the visual QA corpus even though raw corpus text is not valid JSON", async () => {
    expect(() => JSON.parse(visualQaCorpusRawText)).toThrow();

    vi.mocked(postQuery).mockImplementation((query) =>
      Promise.resolve(makeNoResult(query)),
    );

    render(<VisualQaPage />);

    expect(
      await screen.findByText("20 / 20 cases completed"),
    ).toBeInTheDocument();
    expect(document.querySelectorAll("[data-visual-case-id]").length).toBe(
      VISUAL_QA_CASES.length,
    );
    expect(VISUAL_QA_CASES).toHaveLength(20);
    expect(APPROVED_VISUAL_QA_CASE_IDS).toHaveLength(20);
    expect(VISUAL_QA_CASES.map((caseItem) => caseItem.id).sort()).toEqual(
      [...APPROVED_VISUAL_QA_CASE_IDS].sort(),
    );

    for (const caseId of APPROVED_VISUAL_QA_CASE_IDS) {
      expect(screen.getByText(caseId)).toBeInTheDocument();
    }

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
    await screen.findByText("20 / 20 cases completed");
  });

  it("renders the capture button and passes every loaded case card to the screenshot helper", async () => {
    vi.mocked(postQuery).mockImplementation((query) =>
      Promise.resolve(makeNoResult(query)),
    );

    render(<VisualQaPage />);

    await screen.findByText("20 / 20 cases completed");

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

  it("keeps stable case cards inside the visual QA layout wrappers", async () => {
    vi.mocked(postQuery).mockImplementation((query) =>
      Promise.resolve(makeNoResult(query)),
    );

    render(<VisualQaPage />);

    await screen.findByText("20 / 20 cases completed");

    const page = document.querySelector("main");
    const shell = document.querySelector(`.${styles.shell}`);
    const card = document.querySelector(
      '[data-visual-case-id="biggest_scoring_games"]',
    );

    expect(page).toHaveClass(styles.page);
    expect(shell).toBeInTheDocument();
    expect(card).toHaveClass(styles.caseCard);
    expect(card?.querySelector(`.${styles.cardBody}`)).toBeInTheDocument();
    expect(card?.querySelector(`.${styles.resultColumn}`)).toBeInTheDocument();
    expect(card?.querySelector(`.${styles.captureTarget}`)).toBeInTheDocument();
  });

  it("routes the internal visual QA path to the visual QA page", async () => {
    vi.mocked(postQuery).mockImplementation((query) =>
      Promise.resolve(makeNoResult(query)),
    );

    render(resolveRootView(VISUAL_QA_INTERNAL_ROUTE));

    expect(
      await screen.findByRole("heading", {
        name: "Frontend Visual QA Wave 1",
      }),
    ).toBeInTheDocument();
  });
});
