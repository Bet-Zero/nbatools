import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { QueryResponse } from "../api/types";
import ResultRenderer from "../components/results/ResultRenderer";

function makeResponse(overrides: Partial<QueryResponse> = {}): QueryResponse {
  return {
    ok: true,
    query: "test query",
    route: "player_game_summary",
    result_status: "ok",
    result_reason: null,
    current_through: "2025-04-01",
    confidence: null,
    intent: null,
    alternates: [],
    notes: [],
    caveats: [],
    result: {
      query_class: "summary",
      result_status: "ok",
      metadata: {},
      notes: [],
      caveats: [],
      sections: {},
      current_through: "2025-04-01",
    },
    ...overrides,
  };
}

describe("ResultRenderer (substrate)", () => {
  it("routes every result through the fallback table by default", () => {
    const data = makeResponse({
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          summary: [{ player_name: "Jokic", pts: 27.4, reb: 12.6, ast: 9.2 }],
        },
        current_through: "2025-04-01",
      },
    });

    render(<ResultRenderer data={data} />);

    // Fallback renders one section card per non-empty section.
    expect(screen.getByText("Summary")).toBeInTheDocument();
    // The data inside the section makes it through to the rendered table.
    expect(screen.getByText("Jokic")).toBeInTheDocument();
  });

  it("renders nothing for fully empty results", () => {
    const data = makeResponse({
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {},
        current_through: "2025-04-01",
      },
    });

    const { container } = render(<ResultRenderer data={data} />);
    // NoResultDisplay is the empty-state component; assert at least one
    // child is rendered (i.e. we did not silently render nothing).
    expect(container.firstChild).not.toBeNull();
  });

  it("renders a fallback for every non-empty section", () => {
    const data = makeResponse({
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          summary: [{ player_name: "Jokic", pts: 27 }],
          by_season: [{ season: "2025-26", pts_avg: 27 }],
        },
        current_through: "2025-04-01",
      },
    });

    render(<ResultRenderer data={data} />);
    expect(screen.getByText("Summary")).toBeInTheDocument();
    expect(screen.getByText("By Season")).toBeInTheDocument();
  });

  it("renders season leaderboards as a sentence hero and dense answer table", () => {
    const data = makeResponse({
      query: "most ppg in 2025 playoffs",
      route: "season_leaders",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          query_text: "most ppg in 2025 playoffs",
          route: "season_leaders",
          season: "2024-25",
          season_type: "Playoffs",
        },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              player_name: "Shai Gilgeous-Alexander",
              player_id: 1628983,
              team_abbr: "OKC",
              games_played: 23,
              pts_per_game: 29.913,
              season: "2024-25",
              season_type: "Playoffs",
            },
            {
              rank: 2,
              player_name: "Jalen Williams",
              player_id: 1631114,
              team_abbr: "OKC",
              games_played: 23,
              pts_per_game: 21.391,
              season: "2024-25",
              season_type: "Playoffs",
            },
          ],
        },
        current_through: "2025-06-22",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Shai Gilgeous-Alexander scored the most points per game in the 2025 playoffs, with 29.9 per game.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Leaderboard" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "PPG" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "TM" })).toBeInTheDocument();
    expect(screen.getByText("Jalen Williams")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Show raw table" })).not.toBeInTheDocument();
  });

  it("renders team record leaderboards with W-L context in the hero and table", () => {
    const data = makeResponse({
      query: "best record since 2015",
      route: "team_record_leaderboard",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          query_text: "best record since 2015",
          route: "team_record_leaderboard",
          start_season: "2015-16",
          end_season: "2025-26",
          season_type: "Regular Season",
        },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              team_name: "Boston Celtics",
              team_abbr: "BOS",
              team_id: 1610612738,
              games_played: 882,
              wins: 578,
              losses: 304,
              win_pct: 0.655,
              seasons: "2015-16 to 2025-26",
              season_type: "Regular Season",
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "The Boston Celtics had the best record since 2015, going 578-304 (65.5%).",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Win %" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Wins" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Losses" })).toBeInTheDocument();
    expect(screen.getByText("882")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Show raw table" })).not.toBeInTheDocument();
  });
});
