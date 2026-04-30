import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResultSections from "../components/ResultSections";
import type { QueryResponse } from "../api/types";

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
    },
    ...overrides,
  };
}

describe("ResultSections", () => {
  it("routes player summaries to the dedicated player summary renderer", () => {
    const data = makeResponse({
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          player_context: {
            player_id: 203999,
            player_name: "Nikola Jokic",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              player_name: "Nikola Jokic",
              games: 25,
              wins: 18,
              losses: 7,
              win_pct: 0.72,
              pts_avg: 26.4,
              reb_avg: 12.1,
              ast_avg: 9.3,
              efg_pct_avg: 0.62,
            },
          ],
        },
      },
    });
    render(<ResultSections data={data} />);
    expect(screen.getByText("Player Summary")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Nikola Jokic" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("PTS").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("26.4").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("18-7")).toBeInTheDocument();
    expect(screen.getByText("Full Summary")).toBeInTheDocument();
  });

  it("renders sparse player summaries without optional identity or stats", () => {
    const data = makeResponse({
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          summary: [{ player_name: "Mystery Player" }],
        },
      },
    });
    render(<ResultSections data={data} />);
    expect(screen.getByText("Player Summary")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Mystery Player" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Full Summary")).toBeInTheDocument();
  });

  it("renders a scoring sparkline and recent games from player game logs", () => {
    const data = makeResponse({
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          player_context: {
            player_id: 203999,
            player_name: "Nikola Jokic",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              player_name: "Nikola Jokic",
              games: 3,
              pts_avg: 31.7,
              reb_avg: 10.7,
              ast_avg: 8.7,
            },
          ],
          game_log: [
            {
              game_date: "2024-10-24",
              game_id: "001",
              opponent_team_id: 1610612747,
              opponent_team_abbr: "LAL",
              opponent_team_name: "Los Angeles Lakers",
              wl: "W",
              minutes: 35.2,
              pts: 28,
              reb: 10,
              ast: 8,
            },
            {
              game_date: "2024-10-26",
              game_id: "002",
              opponent_team_abbr: "LAC",
              opponent_team_name: "LA Clippers",
              wl: "L",
              minutes: 33.8,
              pts: 32,
              reb: 11,
              ast: 9,
            },
            {
              game_date: "2024-10-29",
              game_id: "003",
              opponent_team_abbr: "UTA",
              opponent_team_name: "Utah Jazz",
              wl: "W",
              minutes: 36.1,
              pts: 35,
              reb: 11,
              ast: 9,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);

    expect(screen.getByText("Recent Games")).toBeInTheDocument();
    expect(screen.getByText("3 games")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Points over 3 games" }),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText("Los Angeles Lakers (LAL)"),
    ).toBeInTheDocument();
    expect(screen.getAllByLabelText("Result W")).toHaveLength(2);
    expect(screen.getByLabelText("Result L")).toBeInTheDocument();
    expect(screen.getByText("2024-10-29")).toBeInTheDocument();
  });

  it("does not render game context when the game log section is missing", () => {
    const data = makeResponse({
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          summary: [{ player_name: "Mystery Player", games: 10 }],
        },
      },
    });

    render(<ResultSections data={data} />);

    expect(screen.queryByText("Recent Games")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("img", { name: /points over/i }),
    ).not.toBeInTheDocument();
  });

  it("renders single-game context without a sparkline", () => {
    const data = makeResponse({
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          summary: [{ player_name: "Mystery Player", games: 1 }],
          game_log: [
            {
              game_date: "2024-10-24",
              game_id: "001",
              opponent_team_abbr: "BOS",
              opponent_team_name: "Boston Celtics",
              wl: "L",
              minutes: 34,
              pts: 41,
              reb: 7,
              ast: 6,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);

    expect(screen.getByText("Recent Games")).toBeInTheDocument();
    expect(screen.getByText("1 game")).toBeInTheDocument();
    expect(screen.getByLabelText("Boston Celtics (BOS)")).toBeInTheDocument();
    expect(
      screen.queryByRole("img", { name: /points over/i }),
    ).not.toBeInTheDocument();
  });

  it("treats an empty game log section like missing game context", () => {
    const data = makeResponse({
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          summary: [{ player_name: "Mystery Player", games: 0 }],
          game_log: [],
        },
      },
    });

    render(<ResultSections data={data} />);

    expect(screen.queryByText("Recent Games")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("img", { name: /points over/i }),
    ).not.toBeInTheDocument();
  });

  it("keeps team summaries on the generic summary renderer", () => {
    const data = makeResponse({
      route: "game_summary",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          summary: [{ team_name: "Lakers", wins: 50, losses: 32 }],
        },
      },
    });
    render(<ResultSections data={data} />);
    expect(screen.getByText("Summary")).toBeInTheDocument();
    expect(screen.queryByText("Player Summary")).not.toBeInTheDocument();
    expect(screen.getByText("Lakers")).toBeInTheDocument();
  });

  it("keeps playoff summaries on the generic summary renderer", () => {
    const data = makeResponse({
      route: "playoff_history",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: { route: "playoff_history" },
        notes: [],
        caveats: [],
        sections: {
          summary: [{ team_name: "Lakers", seasons_appeared: 21 }],
        },
      },
    });
    render(<ResultSections data={data} />);
    expect(screen.getByText("Summary")).toBeInTheDocument();
    expect(screen.queryByText("Player Summary")).not.toBeInTheDocument();
    expect(screen.getByText("Lakers")).toBeInTheDocument();
  });

  it("renders leaderboard sections", () => {
    const data = makeResponse({
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            { rank: 1, player_name: "Luka", PTS: 33 },
            { rank: 2, player_name: "SGA", PTS: 31 },
          ],
        },
      },
    });
    render(<ResultSections data={data} />);
    expect(screen.getByText("Leaderboard")).toBeInTheDocument();
    expect(screen.getByText("2 entries")).toBeInTheDocument();
    expect(screen.getByText("Luka")).toBeInTheDocument();
  });

  it("renders finder sections with count", () => {
    const data = makeResponse({
      result: {
        query_class: "finder",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          finder: [
            { game_date: "2025-01-15", PTS: 30 },
            { game_date: "2025-01-20", PTS: 35 },
          ],
        },
      },
    });
    render(<ResultSections data={data} />);
    expect(screen.getByText("Matching Games")).toBeInTheDocument();
    expect(screen.getByText("2 games")).toBeInTheDocument();
  });

  it("renders no-result display for no_result status", () => {
    const data = makeResponse({
      result_status: "no_result",
      result_reason: "no_match",
      result: {
        query_class: "finder",
        result_status: "no_result",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {},
      },
    });
    render(<ResultSections data={data} />);
    expect(screen.getByText("No Results")).toBeInTheDocument();
  });

  it("renders comparison sections", () => {
    const data = makeResponse({
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          summary: [
            { player_name: "Jokic", PTS: 26 },
            { player_name: "Embiid", PTS: 28 },
          ],
          comparison: [{ metric: "PTS", Jokic: 26, Embiid: 28 }],
        },
      },
    });
    render(<ResultSections data={data} />);
    expect(screen.getByText("Players")).toBeInTheDocument();
    expect(screen.getByText("Comparison")).toBeInTheDocument();
  });

  it("renders streak sections", () => {
    const data = makeResponse({
      result: {
        query_class: "streak",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          streak: [
            {
              start_date: "2025-01-01",
              end_date: "2025-01-10",
              streak_length: 5,
            },
          ],
        },
      },
    });
    render(<ResultSections data={data} />);
    expect(screen.getByText("Streaks")).toBeInTheDocument();
    expect(screen.getByText("1 found")).toBeInTheDocument();
  });
});
