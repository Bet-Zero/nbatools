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

  it("routes team summaries to the dedicated team summary renderer", () => {
    const data = makeResponse({
      route: "game_summary",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          route: "game_summary",
          team_context: {
            team_id: 1610612747,
            team_abbr: "LAL",
            team_name: "Los Angeles Lakers",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              team_name: "Los Angeles Lakers",
              season_start: "2024-25",
              season_end: "2024-25",
              season_type: "Regular Season",
              wins: 50,
              losses: 32,
              games: 82,
              win_pct: 0.61,
              pts_avg: 117.2,
            },
          ],
        },
      },
    });
    render(<ResultSections data={data} />);
    expect(screen.getByText("Team Summary")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Los Angeles Lakers" }),
    ).toBeInTheDocument();
    expect(
      screen.getAllByLabelText("Los Angeles Lakers (LAL)").length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("50-32")).toBeInTheDocument();
    expect(
      screen.getByText("2024-25 / Regular Season / 82 games"),
    ).toBeInTheDocument();
    expect(screen.getAllByText("PTS").length).toBeGreaterThan(0);
    expect(screen.getByText("Full Summary")).toBeInTheDocument();
    expect(screen.queryByText("Player Summary")).not.toBeInTheDocument();
  });

  it("renders team summaries without team ids, logos, or optional stats", () => {
    const data = makeResponse({
      route: "game_summary",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          route: "game_summary",
          team: "Mystery Team",
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              team_name: "Mystery Team",
              games: 12,
            },
          ],
        },
      },
    });
    render(<ResultSections data={data} />);
    expect(screen.getByText("Team Summary")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Mystery Team" }),
    ).toBeInTheDocument();
    expect(screen.getAllByLabelText("Mystery Team (MT)").length).toBeGreaterThan(
      0,
    );
    expect(screen.getByText("12 games")).toBeInTheDocument();
    expect(screen.queryByText("Record")).not.toBeInTheDocument();
    expect(screen.getByText("Full Summary")).toBeInTheDocument();
  });

  it("keeps long team names readable in the team summary hero", () => {
    const longName =
      "A Very Long Team Name With Multiple Hyphenated-Market Segments";
    const data = makeResponse({
      route: "game_summary",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: { route: "game_summary", team: longName },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              team_name: longName,
              wins: 3,
              losses: 4,
              win_pct: 0.429,
            },
          ],
        },
      },
    });
    render(<ResultSections data={data} />);
    expect(screen.getByRole("heading", { name: longName })).toBeInTheDocument();
    expect(screen.getByText("3-4")).toBeInTheDocument();
    expect(screen.getByText("Full Summary")).toBeInTheDocument();
  });

  it("routes team records to the dedicated team summary renderer", () => {
    const data = makeResponse({
      route: null,
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          route: "team_record",
          team_context: {
            team_id: 1610612738,
            team_abbr: "BOS",
            team_name: "Boston Celtics",
          },
          opponent_context: {
            team_id: 1610612747,
            team_abbr: "LAL",
            team_name: "Los Angeles Lakers",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              team_name: "Boston Celtics",
              wins: 4,
              losses: 1,
              games: 5,
              win_pct: 0.8,
            },
          ],
          by_season: [{ season: "2024-25", wins: 4, losses: 1 }],
        },
      },
    });
    render(<ResultSections data={data} />);
    expect(screen.getByText("Team Record")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Boston Celtics" }),
    ).toBeInTheDocument();
    expect(screen.getByText("4-1")).toBeInTheDocument();
    expect(screen.getByText("Full Summary")).toBeInTheDocument();
    expect(screen.getByText("By Season")).toBeInTheDocument();
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
    expect(screen.queryByText("Team Summary")).not.toBeInTheDocument();
    expect(screen.queryByText("Player Summary")).not.toBeInTheDocument();
    expect(screen.getByText("Lakers")).toBeInTheDocument();
  });

  it("keeps unknown summary routes on the generic summary renderer", () => {
    const data = makeResponse({
      route: "unknown_summary",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: { route: "unknown_summary" },
        notes: [],
        caveats: [],
        sections: {
          summary: [{ team_name: "Fallback Team", wins: 12 }],
        },
      },
    });
    render(<ResultSections data={data} />);
    expect(screen.getByText("Summary")).toBeInTheDocument();
    expect(screen.queryByText("Team Summary")).not.toBeInTheDocument();
    expect(screen.queryByText("Player Summary")).not.toBeInTheDocument();
    expect(screen.getByText("Fallback Team")).toBeInTheDocument();
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

  it("routes player game finders to the dedicated renderer", () => {
    const data = makeResponse({
      route: "player_game_finder",
      result: {
        query_class: "finder",
        result_status: "ok",
        metadata: { route: "player_game_finder" },
        notes: [],
        caveats: [],
        sections: {
          finder: [
            {
              rank: 1,
              game_date: "2025-01-15",
              player_name: "Stephen Curry",
              player_id: 201939,
              team_name: "Golden State Warriors",
              team_abbr: "GSW",
              opponent_team_name: "Boston Celtics",
              opponent_team_abbr: "BOS",
              is_home: 1,
              wl: "W",
              season: "2024-25",
              season_type: "Regular Season",
              minutes: 36,
              pts: 42,
              reb: 6,
              ast: 8,
              fg3m: 7,
              plus_minus: 12,
              clutch_events: 2,
            },
            {
              rank: 2,
              game_date: "2025-01-20",
              player_name: "Stephen Curry",
              player_id: 201939,
              team_name: "Golden State Warriors",
              team_abbr: "GSW",
              opponent_team_name: "Los Angeles Lakers",
              opponent_team_abbr: "LAL",
              is_away: 1,
              wl: "L",
              season: "2024-25",
              season_type: "Regular Season",
              minutes: 34,
              pts: 35,
              reb: 5,
              ast: 7,
              fg3m: 5,
              plus_minus: -3,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const cards = screen.getByLabelText("Player game cards");
    expect(screen.getByText("Player Games")).toBeInTheDocument();
    expect(screen.getByText("2 games")).toBeInTheDocument();
    expect(screen.getByText("Player Game Detail")).toBeInTheDocument();
    expect(screen.queryByText("Matching Games")).not.toBeInTheDocument();
    expect(within(cards).getAllByText("Stephen Curry").length).toBeGreaterThan(
      0,
    );
    expect(
      within(cards)
        .getAllByLabelText("Stephen Curry avatar")[0]
        .querySelector("img"),
    ).toHaveAttribute(
      "src",
      "https://cdn.nba.com/headshots/nba/latest/1040x760/201939.png",
    );
    expect(
      within(cards).getAllByLabelText("Golden State Warriors (GSW)").length,
    ).toBeGreaterThan(0);
    expect(
      within(cards).getByLabelText("Boston Celtics (BOS)").querySelector("img"),
    ).toBeNull();
    expect(within(cards).getByText("#1 / 2025-01-15")).toBeInTheDocument();
    expect(within(cards).getByText("vs BOS")).toBeInTheDocument();
    expect(within(cards).getByText("at LAL")).toBeInTheDocument();
    expect(within(cards).getByText("W")).toBeInTheDocument();
    expect(within(cards).getAllByText("PTS").length).toBeGreaterThan(0);
    expect(within(cards).getAllByText("FG3M").length).toBeGreaterThan(0);
    expect(within(cards).getByText("42")).toBeInTheDocument();
    expect(within(cards).getAllByText("7").length).toBeGreaterThan(0);
    expect(within(cards).getAllByText("2024-25").length).toBeGreaterThan(0);
    expect(within(cards).getAllByText("Regular Season").length).toBeGreaterThan(
      0,
    );
    expect(within(cards).getByText("MIN 36")).toBeInTheDocument();
    expect(within(cards).getByText("+/- +12")).toBeInTheDocument();
    expect(within(cards).getByText("Clutch events 2")).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Player Name" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Stephen Curry").length).toBeGreaterThan(0);
  });

  it("renders sparse player game cards with identity fallbacks", () => {
    const data = makeResponse({
      route: "player_game_finder",
      result: {
        query_class: "finder",
        result_status: "ok",
        metadata: { route: "player_game_finder" },
        notes: [],
        caveats: [],
        sections: {
          finder: [
            {
              game_date: "2025-01-15",
              player_name: "Mystery Player",
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const cards = screen.getByLabelText("Player game cards");
    expect(within(cards).getByText("Mystery Player")).toBeInTheDocument();
    expect(within(cards).getByText("2025-01-15")).toBeInTheDocument();
    expect(
      within(cards)
        .getByLabelText("Mystery Player avatar")
        .querySelector("img"),
    ).toBeNull();
    expect(within(cards).queryByText(/vs |at /)).not.toBeInTheDocument();
    expect(within(cards).queryByText("PTS")).not.toBeInTheDocument();
    expect(screen.getByText("Player Game Detail")).toBeInTheDocument();
  });

  it("keeps long player, opponent, and custom stat labels readable", () => {
    const longPlayer =
      "A Very Long Player Name With Multiple Hyphenated-Surnames And Suffixes";
    const longOpponent =
      "A Very Long Opponent Team Name With Historical Qualifier";
    const data = makeResponse({
      route: "player_game_finder",
      result: {
        query_class: "finder",
        result_status: "ok",
        metadata: { route: "player_game_finder" },
        notes: [],
        caveats: [],
        sections: {
          finder: [
            {
              rank: 1,
              game_date: "2025-02-01",
              player_name: longPlayer,
              opponent_team_name: longOpponent,
              opponent_team_abbr: "LONG",
              is_away: true,
              wl: "W",
              very_long_custom_metric_label_for_display: 12,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const cards = screen.getByLabelText("Player game cards");
    expect(within(cards).getByText(longPlayer)).toBeInTheDocument();
    expect(
      within(cards).getByLabelText(`${longOpponent} (LONG)`),
    ).toBeInTheDocument();
    expect(within(cards).getByText("at LONG")).toBeInTheDocument();
    expect(
      within(cards).getByText("Very Long Custom Metric Label For Display"),
    ).toBeInTheDocument();
    expect(within(cards).getByText("12")).toBeInTheDocument();
    expect(screen.getByText("Player Game Detail")).toBeInTheDocument();
  });

  it("keeps team game finders on the generic finder renderer", () => {
    const data = makeResponse({
      route: "game_finder",
      result: {
        query_class: "finder",
        result_status: "ok",
        metadata: { route: "game_finder" },
        notes: [],
        caveats: [],
        sections: {
          finder: [
            {
              game_date: "2025-01-15",
              team_name: "Boston Celtics",
              pts: 118,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    expect(screen.getByText("Matching Games")).toBeInTheDocument();
    expect(screen.getByText("1 game")).toBeInTheDocument();
    expect(screen.queryByText("Player Games")).not.toBeInTheDocument();
    expect(screen.getByText("Boston Celtics")).toBeInTheDocument();
  });

  it("keeps count results with finder detail on the fallback renderer", () => {
    const data = makeResponse({
      route: "player_game_finder",
      result: {
        query_class: "count",
        result_status: "ok",
        metadata: { route: "player_game_finder", query_class: "count" },
        notes: [],
        caveats: [],
        sections: {
          count: [{ count: 2 }],
          finder: [
            { game_date: "2025-01-15", player_name: "Stephen Curry", pts: 42 },
            { game_date: "2025-01-20", player_name: "Stephen Curry", pts: 35 },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    expect(screen.queryByText("Player Games")).not.toBeInTheDocument();
    expect(screen.getByText("count")).toBeInTheDocument();
    expect(screen.getByText("Matching Games")).toBeInTheDocument();
    expect(screen.getAllByText("Stephen Curry").length).toBeGreaterThan(0);
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

  it("routes player comparisons to the dedicated renderer", () => {
    const data = makeResponse({
      route: "player_compare",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: {
          route: "player_compare",
          players_context: [
            { player_id: 203999, player_name: "Nikola Jokic" },
            { player_id: 203954, player_name: "Joel Embiid" },
          ],
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              player_name: "Nikola Jokic",
              team_name: "Denver Nuggets",
              team_abbr: "DEN",
              team_id: 1610612743,
              games: 10,
              wins: 7,
              losses: 3,
              win_pct: 0.7,
              pts_avg: 26.4,
              reb_avg: 12.1,
              ast_avg: 9.3,
              efg_pct_avg: 0.62,
            },
            {
              player_name: "Joel Embiid",
              games: 8,
              wins: 5,
              losses: 3,
              win_pct: 0.625,
              pts_avg: 30.1,
              reb_avg: 10.8,
              ast_avg: 5.7,
            },
          ],
          comparison: [
            {
              metric: "pts_avg",
              "Nikola Jokic": 26.4,
              "Joel Embiid": 30.1,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const compared = screen.getByLabelText("Compared players");
    const metricCards = screen.getByLabelText("Metric comparison cards");
    expect(screen.getByText("Player Comparison")).toBeInTheDocument();
    expect(screen.getByText("2 players")).toBeInTheDocument();
    expect(screen.getByText("Metric Comparison")).toBeInTheDocument();
    expect(screen.getByText("Player Summary Detail")).toBeInTheDocument();
    expect(screen.getByText("Full Metric Detail")).toBeInTheDocument();
    expect(screen.queryByText("Players")).not.toBeInTheDocument();
    expect(within(compared).getByText("Nikola Jokic")).toBeInTheDocument();
    expect(within(compared).getByText("Joel Embiid")).toBeInTheDocument();
    expect(
      within(compared)
        .getByLabelText("Nikola Jokic avatar")
        .querySelector("img"),
    ).toHaveAttribute(
      "src",
      "https://cdn.nba.com/headshots/nba/latest/1040x760/203999.png",
    );
    expect(within(compared).getByText("Denver Nuggets")).toBeInTheDocument();
    expect(within(compared).getAllByText("PTS").length).toBeGreaterThan(0);
    expect(within(compared).getByText("26.4")).toBeInTheDocument();
    expect(within(compared).getByText("7-3")).toBeInTheDocument();
    expect(within(metricCards).getByText("PTS Avg")).toBeInTheDocument();
    expect(
      within(metricCards).getByText("Joel Embiid leads by 3.7"),
    ).toBeInTheDocument();
  });

  it("keeps team comparisons on the generic comparison renderer", () => {
    const data = makeResponse({
      route: "team_compare",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: { route: "team_compare" },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            { team_name: "Celtics", wins: 60 },
            { team_name: "Lakers", wins: 47 },
          ],
          comparison: [{ metric: "wins", Celtics: 60, Lakers: 47 }],
        },
      },
    });

    render(<ResultSections data={data} />);
    expect(screen.getByText("Players")).toBeInTheDocument();
    expect(screen.getByText("Comparison")).toBeInTheDocument();
    expect(screen.queryByText("Player Comparison")).not.toBeInTheDocument();
    expect(screen.getAllByText("Celtics").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Lakers").length).toBeGreaterThan(0);
  });

  it("renders sparse player comparison cards with identity fallbacks", () => {
    const data = makeResponse({
      route: "player_compare",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: { route: "player_compare" },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            { player_name: "Mystery Player" },
            { player_name: "Sparse Opponent", games: 0 },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const compared = screen.getByLabelText("Compared players");
    expect(within(compared).getByText("Mystery Player")).toBeInTheDocument();
    expect(within(compared).getByText("Sparse Opponent")).toBeInTheDocument();
    expect(
      within(compared)
        .getByLabelText("Mystery Player avatar")
        .querySelector("img"),
    ).toBeNull();
    expect(screen.getByText("Player Summary Detail")).toBeInTheDocument();
    expect(screen.queryByText("Metric Comparison")).not.toBeInTheDocument();
  });

  it("handles tied, nonnumeric, and missing comparison metric values", () => {
    const data = makeResponse({
      route: "player_compare",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: { route: "player_compare" },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            { player_name: "Player A" },
            { player_name: "Player B" },
          ],
          comparison: [
            { metric: "ast_avg", "Player A": 8, "Player B": 8 },
            { metric: "status", "Player A": "available", "Player B": null },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const metricCards = screen.getByLabelText("Metric comparison cards");
    expect(within(metricCards).getByText("AST Avg")).toBeInTheDocument();
    expect(within(metricCards).getByText("Tie")).toBeInTheDocument();
    expect(within(metricCards).getByText("Status")).toBeInTheDocument();
    expect(within(metricCards).getByText("available")).toBeInTheDocument();
    expect(
      within(metricCards).queryByText(/status leads/i),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Full Metric Detail")).toBeInTheDocument();
  });

  it("keeps long player names and custom metric labels in player comparisons", () => {
    const longFirst =
      "A Very Long Player Name With Multiple Hyphenated-Surnames And Suffixes";
    const longSecond =
      "Another Extended Player Name With Several Middle Names";
    const data = makeResponse({
      route: "player_compare",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: { route: "player_compare" },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              player_name: longFirst,
              team_name: "A Very Long Historical Team Name For Wrapping Tests",
              team_abbr: "LONG",
              pts_avg: 27.4,
              reb_avg: 9.1,
              ast_avg: 8.8,
            },
            {
              player_name: longSecond,
              pts_avg: 26.9,
              reb_avg: 10.2,
              ast_avg: 7.6,
            },
          ],
          comparison: [
            {
              metric: "very_long_metric_label_with_extra_context",
              [longFirst]: 123.456,
              [longSecond]: 98.765,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const compared = screen.getByLabelText("Compared players");
    const metricCards = screen.getByLabelText("Metric comparison cards");
    expect(within(compared).getByText(longFirst)).toBeInTheDocument();
    expect(within(compared).getByText(longSecond)).toBeInTheDocument();
    expect(
      within(compared).getByLabelText(
        "A Very Long Historical Team Name For Wrapping Tests (LONG)",
      ),
    ).toBeInTheDocument();
    expect(
      within(metricCards).getByText(
        "Very Long Metric Label With Extra Context",
      ),
    ).toBeInTheDocument();
    expect(
      within(metricCards).queryByText(/leads by/i),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Player Summary Detail")).toBeInTheDocument();
    expect(screen.getByText("Full Metric Detail")).toBeInTheDocument();
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
