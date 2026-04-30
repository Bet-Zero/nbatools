import { render, screen, within } from "@testing-library/react";
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

  it("covers long-name, missing-image, dense-stat, and short-sample fallback", () => {
    const longName =
      "A Very Long Player Name With Multiple Hyphenated-Surnames";
    const data = makeResponse({
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              player_name: longName,
              games: 1,
              wins: 1,
              losses: 0,
              win_pct: 1,
              pts_avg: 101.5,
              reb_avg: 20.5,
              ast_avg: 18.5,
              minutes_avg: 48,
              efg_pct_avg: 0.755,
              ts_pct_avg: 0.82,
              fg3_pct_avg: 0.5,
              plus_minus_avg: 27,
            },
          ],
          game_log: [
            {
              game_date: "2024-10-24",
              game_id: "001",
              wl: "W",
              minutes: 48,
              pts: 101.5,
              reb: 20.5,
              ast: 18.5,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);

    expect(screen.getByRole("heading", { name: longName })).toBeInTheDocument();
    expect(
      screen.getAllByLabelText(`${longName} avatar`).length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("TS%")).toBeInTheDocument();
    expect(screen.getByText("+/-")).toBeInTheDocument();
    expect(screen.getByText("1 game")).toBeInTheDocument();
    expect(screen.getByLabelText("Opponent (OPP)")).toBeInTheDocument();
    expect(
      screen.queryByRole("img", { name: /points over/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Full Summary")).toBeInTheDocument();
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
    expect(screen.getByLabelText("Ranked leaderboard")).toBeInTheDocument();
    expect(screen.getByText("#1")).toBeInTheDocument();
    expect(screen.getAllByText("Luka").length).toBeGreaterThan(0);
    expect(screen.getByText("Full Leaderboard")).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Player Name" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "PTS" }),
    ).toBeInTheDocument();
  });

  it("renders player identity marks in leaderboard rows", () => {
    const data = makeResponse({
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              player_name: "Nikola Jokic",
              player_id: 203999,
              team_abbr: "DEN",
              games_played: 70,
              pts_per_game: 29.6,
            },
            {
              rank: 2,
              player_name: "Mystery Player",
              team_abbr: "UNK",
              games_played: 12,
              pts_per_game: 18.2,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const ranked = screen.getByLabelText("Ranked leaderboard");
    const jokicAvatar = within(ranked).getByLabelText("Nikola Jokic avatar");
    expect(jokicAvatar.querySelector("img")).toHaveAttribute(
      "src",
      "https://cdn.nba.com/headshots/nba/latest/1040x760/203999.png",
    );
    expect(
      within(ranked)
        .getByLabelText("Mystery Player avatar")
        .querySelector("img"),
    ).toBeNull();
  });

  it("renders team identity marks in leaderboard rows", () => {
    const data = makeResponse({
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              team_name: "Los Angeles Lakers",
              team_abbr: "LAL",
              team_id: 1610612747,
              games_played: 82,
              pts_per_game: 118.4,
            },
            {
              rank: 2,
              team_abbr: "SEA",
              games_played: 4,
              "games_pts_120+": 3,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const ranked = screen.getByLabelText("Ranked leaderboard");
    const lakersBadge = within(ranked).getByLabelText(
      "Los Angeles Lakers (LAL)",
    );
    expect(lakersBadge.querySelector("img")).toHaveAttribute(
      "src",
      "https://cdn.nba.com/logos/nba/1610612747/primary/L/logo.svg",
    );
    expect(
      within(ranked).getByLabelText("SEA").querySelector("img"),
    ).toBeNull();
  });

  it("renders sparse leaderboard rows without identity fields", () => {
    const data = makeResponse({
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              entity: "Best lineup",
              games_played: 11,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const ranked = screen.getByLabelText("Ranked leaderboard");
    expect(within(ranked).getByText("Best lineup")).toBeInTheDocument();
    expect(within(ranked).queryByLabelText(/avatar/)).not.toBeInTheDocument();
  });

  it("promotes occurrence metrics ahead of qualifier columns", () => {
    const longName =
      "A Very Long Leaderboard Player Name With Hyphenated-Surnames";
    const data = makeResponse({
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              player_name: longName,
              min_games: 10,
              games_played: 12,
              season: "2024-25",
              qualifier: "Playoff games only",
              "games_pts_30+_reb_10+_ast_10+": 6,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const ranked = screen.getByLabelText("Ranked leaderboard");
    expect(within(ranked).getByText(longName)).toBeInTheDocument();
    expect(within(ranked).getByText("6")).toBeInTheDocument();
    expect(
      within(ranked).getByText("Games PTS 30+ REB 10+ AST 10+"),
    ).toBeInTheDocument();
    expect(within(ranked).getByText("12 games")).toBeInTheDocument();
    expect(within(ranked).getByText("2024-25")).toBeInTheDocument();
    expect(within(ranked).getByText("Min games 10")).toBeInTheDocument();
    expect(within(ranked).getByText("Playoff games only")).toBeInTheDocument();
  });

  it("surfaces game and team context as secondary leaderboard metadata", () => {
    const data = makeResponse({
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              player_name: "Nikola Jokic",
              player_id: 203999,
              team_abbr: "DEN",
              game_date: "2024-10-24",
              opponent_team_abbr: "LAL",
              is_away: true,
              wl: "W",
              pts: 41,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const ranked = screen.getByLabelText("Ranked leaderboard");
    expect(within(ranked).getByText("41")).toBeInTheDocument();
    expect(within(ranked).getByText("PTS")).toBeInTheDocument();
    expect(within(ranked).getByText("DEN")).toBeInTheDocument();
    expect(within(ranked).getByText("2024-10-24")).toBeInTheDocument();
    expect(within(ranked).getByText("at LAL")).toBeInTheDocument();
    expect(within(ranked).getByText("W")).toBeInTheDocument();
  });

  it("renders rows that do not have a ranked metric value", () => {
    const data = makeResponse({
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              entity: "Sparse leaderboard entry",
              season: "2024-25",
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const ranked = screen.getByLabelText("Ranked leaderboard");
    expect(
      within(ranked).getByText("Sparse leaderboard entry"),
    ).toBeInTheDocument();
    expect(within(ranked).getByText("2024-25")).toBeInTheDocument();
    expect(within(ranked).queryByText("Games Played")).not.toBeInTheDocument();
    expect(screen.getByText("Full Leaderboard")).toBeInTheDocument();
  });

  it("renders nothing for empty ok leaderboard sections", () => {
    const data = makeResponse({
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [],
        },
      },
    });
    const { container } = render(<ResultSections data={data} />);
    expect(container).toBeEmptyDOMElement();
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

  it("keeps unknown query classes on the generic fallback renderer", () => {
    const data = makeResponse({
      route: "unknown_route",
      result: {
        query_class: "experimental_result",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          custom_section: [{ label: "Fallback row", value: 42 }],
        },
      },
    });

    render(<ResultSections data={data} />);
    expect(screen.getByText("custom section")).toBeInTheDocument();
    expect(screen.getByText("Fallback row")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(
      screen.queryByLabelText("Ranked leaderboard"),
    ).not.toBeInTheDocument();
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
