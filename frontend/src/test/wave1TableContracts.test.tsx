import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { QueryResponse, ResultMetadata, SectionRow } from "../api/types";
import ResultRenderer from "../components/results/ResultRenderer";

function makeResponse(
  route: string,
  options: {
    metadata?: ResultMetadata;
    query?: string;
    queryClass?: string;
    sections: Record<string, SectionRow[]>;
  },
): QueryResponse {
  return {
    ok: true,
    query: options.query ?? "sample query",
    route,
    result_status: "ok",
    result_reason: null,
    current_through: "2026-04-12",
    confidence: null,
    intent: null,
    alternates: [],
    notes: [],
    caveats: [],
    result: {
      query_class: options.queryClass ?? "summary",
      result_status: "ok",
      result_reason: null,
      current_through: "2026-04-12",
      metadata: { route, ...options.metadata },
      notes: [],
      caveats: [],
      sections: options.sections,
    },
  };
}

function expectHeaders(table: HTMLElement, headers: string[]): void {
  for (const header of headers) {
    expect(
      within(table).getByRole("columnheader", { name: header }),
    ).toBeInTheDocument();
  }
}

function expectNoHeaders(table: HTMLElement, headers: string[]): void {
  for (const header of headers) {
    expect(
      within(table).queryByRole("columnheader", { name: header }),
    ).not.toBeInTheDocument();
  }
}

describe("Wave 1 table pattern contracts", () => {
  it("renders the player game-log visible header contract", () => {
    const data = makeResponse("player_game_summary", {
      query: "Stephen Curry last 2 games",
      metadata: {
        window_size: 2,
        player_context: { player_id: 201939, player_name: "Stephen Curry" },
      },
      sections: {
        summary: [
          {
            player_name: "Stephen Curry",
            games: 2,
            minutes_avg: 34.5,
            minutes_sum: 69,
            pts_avg: 30,
            pts_sum: 60,
            reb_avg: 5,
            reb_sum: 10,
            ast_avg: 7,
            ast_sum: 14,
          },
        ],
        game_log: [
          {
            game_id: "1",
            game_date: "2026-03-01",
            player_id: 201939,
            player_name: "Stephen Curry",
            team_abbr: "GSW",
            opponent_team_abbr: "LAL",
            is_home: 1,
            team_score: 118,
            opponent_score: 111,
            wl: "W",
            minutes: 35,
            pts: 32,
            reb: 5,
            ast: 8,
            fgm: 11,
            fga: 20,
            fg3m: 6,
            fg3a: 12,
            ftm: 4,
            fta: 4,
            stl: 2,
            blk: 1,
            tov: 3,
            plus_minus: 9,
            ts_pct: 0.68,
            efg_pct: 0.7,
          },
        ],
      },
    });

    render(<ResultRenderer data={data} displayMode="review" />);

    const table = screen.getByRole("table", { name: "Game log" });
    expectHeaders(table, [
      "Date",
      "TM",
      "Opp",
      "Score",
      "W/L",
      "MIN",
      "PTS",
      "REB",
      "AST",
      "FG",
      "3P",
      "FT",
      "STL",
      "BLK",
      "TOV",
      "+/-",
      "TS%",
      "eFG%",
    ]);
    expect(within(table).getByText("Average")).toBeInTheDocument();
    expect(within(table).getByText("Total")).toBeInTheDocument();
  });

  it("renders the team game-log visible header contract", () => {
    const data = makeResponse("game_finder", {
      queryClass: "finder",
      metadata: {
        team_context: {
          team_id: 1610612747,
          team_abbr: "LAL",
          team_name: "Los Angeles Lakers",
        },
      },
      sections: {
        finder: [
          {
            game_id: "1",
            game_date: "2026-03-01",
            team_id: 1610612747,
            team_abbr: "LAL",
            team_name: "Los Angeles Lakers",
            opponent_team_abbr: "BOS",
            is_away: 1,
            wl: "L",
            pts: 112,
            opponent_pts: 120,
            reb: 43,
            ast: 26,
            fg3m: 14,
            fgm: 40,
            fga: 88,
            fg3a: 37,
            ftm: 18,
            fta: 22,
            tov: 13,
            stl: 7,
            blk: 5,
            oreb: 9,
            dreb: 34,
          },
        ],
      },
    });

    render(<ResultRenderer data={data} displayMode="review" />);

    const table = screen.getByRole("table", { name: "Game log" });
    expectHeaders(table, [
      "Date",
      "Team",
      "Opp",
      "Score",
      "W/L",
      "PTS",
      "Opp PTS",
      "Margin",
      "REB",
      "AST",
      "3PM",
      "FG",
      "3P",
      "FT",
      "TOV",
      "STL",
      "BLK",
      "ORB",
      "DRB",
    ]);
  });

  it("renders the team-record visible header contract", () => {
    const data = makeResponse("team_record", {
      metadata: {
        season: "2025-26",
        season_type: "Regular Season",
        team_context: {
          team_id: 1610612752,
          team_abbr: "NYK",
          team_name: "New York Knicks",
        },
      },
      sections: {
        summary: [
          {
            team_name: "New York Knicks",
            wins: 42,
            losses: 28,
            games: 70,
            win_pct: 0.6,
            pts_avg: 115.2,
            plus_minus_avg: 4.3,
            reb_avg: 44.1,
            ast_avg: 26.4,
            fg3m_avg: 13.2,
            opponent_pts_avg: 110.9,
            net_rating: 4.4,
          },
        ],
      },
    });

    render(<ResultRenderer data={data} displayMode="review" />);

    const table = screen.getByRole("table", { name: "Team record" });
    expectHeaders(table, [
      "Team",
      "W-L",
      "Games",
      "Win %",
      "PPG",
      "+/-",
      "REB",
      "AST",
      "3PM",
      "Season Type",
      "Season",
      "Opp PPG",
      "Net",
    ]);
  });

  it("renders player season leaderboards with route-specific support columns", () => {
    const data = makeResponse("season_leaders", {
      queryClass: "leaderboard",
      metadata: { stat: "pts_per_game", season: "2025-26" },
      sections: {
        leaderboard: [
          {
            rank: 1,
            player_name: "Shai Gilgeous-Alexander",
            player_id: 1628983,
            team_abbr: "OKC",
            games_played: 72,
            pts_per_game: 31.1,
            season: "2025-26",
            season_type: "Regular Season",
          },
        ],
      },
    });

    render(<ResultRenderer data={data} displayMode="review" />);

    const table = screen.getByRole("table", { name: "Leaderboard" });
    expectHeaders(table, [
      "#",
      "Player",
      "PPG",
      "Team",
      "GP",
      "Season",
      "Season Type",
    ]);
    expect(within(table).queryByText("1628983")).not.toBeInTheDocument();
  });

  it("renders player season shooting leaderboards with made and attempt context", () => {
    const data = makeResponse("season_leaders", {
      queryClass: "leaderboard",
      metadata: { stat: "fg_pct", season: "2025-26" },
      sections: {
        leaderboard: [
          {
            rank: 1,
            player_name: "Nikola Jokic",
            team_abbr: "DEN",
            games_played: 70,
            fg_pct: 0.635,
            fgm_total: 820,
            fga_total: 1291,
            season: "2025-26",
            season_type: "Regular Season",
          },
        ],
      },
    });

    render(<ResultRenderer data={data} displayMode="review" />);

    const table = screen.getByRole("table", { name: "Leaderboard" });
    expectHeaders(table, ["#", "Player", "FG%", "Team", "GP", "FGM", "FGA"]);
  });

  it("renders team season leaderboards with stable rating and record context", () => {
    const ratingData = makeResponse("season_team_leaders", {
      queryClass: "leaderboard",
      metadata: { stat: "off_rating", season: "2025-26" },
      sections: {
        leaderboard: [
          {
            rank: 1,
            team_name: "Denver Nuggets",
            team_abbr: "DEN",
            team_id: 1610612743,
            games_played: 82,
            off_rating: 121.4,
            season: "2025-26",
            season_type: "Regular Season",
          },
        ],
      },
    });

    const { rerender } = render(
      <ResultRenderer data={ratingData} displayMode="review" />,
    );

    let table = screen.getByRole("table", { name: "Leaderboard" });
    expectHeaders(table, [
      "#",
      "Team",
      "ORtg",
      "GP",
      "Season",
      "Season Type",
    ]);
    expect(within(table).queryByText("1610612743")).not.toBeInTheDocument();

    const recordData = makeResponse("season_team_leaders", {
      queryClass: "leaderboard",
      metadata: { stat: "wins", season: "2025-26" },
      sections: {
        leaderboard: [
          {
            rank: 1,
            team_name: "Oklahoma City Thunder",
            team_abbr: "OKC",
            team_id: 1610612760,
            games_played: 82,
            wins: 68,
            losses: 14,
            win_pct: 0.829,
            season: "2025-26",
            season_type: "Regular Season",
          },
        ],
      },
    });

    rerender(<ResultRenderer data={recordData} displayMode="review" />);
    table = screen.getByRole("table", { name: "Leaderboard" });
    expectHeaders(table, ["#", "Team", "Wins", "W-L", "Win %", "GP"]);
    expect(within(table).getByText("68-14")).toBeInTheDocument();
  });

  it("renders team record leaderboards with explicit W-L semantics", () => {
    const data = makeResponse("team_record_leaderboard", {
      queryClass: "leaderboard",
      metadata: { stat: "win_pct", season: "2025-26" },
      sections: {
        leaderboard: [
          {
            rank: 1,
            team_name: "Boston Celtics",
            team_abbr: "BOS",
            team_id: 1610612738,
            games_played: 82,
            wins: 61,
            losses: 21,
            win_pct: 0.744,
            season: "2025-26",
            season_type: "Regular Season",
          },
        ],
      },
    });

    render(<ResultRenderer data={data} displayMode="review" />);

    const table = screen.getByRole("table", { name: "Leaderboard" });
    expectHeaders(table, [
      "#",
      "Team",
      "W-L",
      "Win %",
      "Games",
      "Season",
      "Season Type",
    ]);
    expect(within(table).getByText("61-21")).toBeInTheDocument();
    expect(within(table).queryByText("1610612738")).not.toBeInTheDocument();
  });

  it("renders player occurrence leaderboards with count, team, and GP context", () => {
    const specialEventData = makeResponse("player_occurrence_leaders", {
      queryClass: "leaderboard",
      sections: {
        leaderboard: [
          {
            rank: 1,
            player_name: "Nikola Jokic",
            team_abbr: "DEN",
            games_played: 78,
            "triple doubles": 32,
            season: "2025-26",
            season_type: "Regular Season",
          },
        ],
      },
    });

    const { rerender } = render(
      <ResultRenderer data={specialEventData} displayMode="review" />,
    );

    let table = screen.getByRole("table", { name: "Leaderboard" });
    expectHeaders(table, [
      "#",
      "Player",
      "Triple Doubles",
      "Team",
      "GP",
      "Season",
      "Season Type",
    ]);

    const thresholdData = makeResponse("player_occurrence_leaders", {
      queryClass: "leaderboard",
      metadata: { stat: "pts", min_value: 40 },
      sections: {
        leaderboard: [
          {
            rank: 1,
            player_name: "Shai Gilgeous-Alexander",
            team_abbr: "OKC",
            games_played: 72,
            "games_pts_40+": 12,
            season: "2025-26",
            season_type: "Regular Season",
          },
        ],
      },
    });

    rerender(<ResultRenderer data={thresholdData} displayMode="review" />);
    table = screen.getByRole("table", { name: "Leaderboard" });
    expectHeaders(table, ["Games PTS 40+", "Team", "GP"]);
    expect(within(table).getByText("12")).toBeInTheDocument();
  });

  it("renders team occurrence leaderboards with team-abbreviation identity and GP context", () => {
    const data = makeResponse("team_occurrence_leaders", {
      queryClass: "leaderboard",
      sections: {
        leaderboard: [
          {
            rank: 1,
            team_abbr: "DEN",
            games_played: 82,
            "games_pts_120+": 55,
            season: "2025-26",
            season_type: "Regular Season",
          },
        ],
      },
    });

    render(<ResultRenderer data={data} displayMode="review" />);

    const table = screen.getByRole("table", { name: "Leaderboard" });
    expectHeaders(table, [
      "#",
      "Team",
      "Games PTS 120+",
      "GP",
      "Season",
      "Season Type",
    ]);
    expect(within(table).getAllByText("DEN").length).toBeGreaterThan(0);
    expectNoHeaders(table, ["Team Id"]);
  });

  it("renders the top-performance rank, subject, context, and primary metric contract", () => {
    const playerData = makeResponse("top_player_games", {
      queryClass: "leaderboard",
      metadata: { stat: "pts", season: "2025-26" },
      sections: {
        leaderboard: [
          {
            rank: 1,
            player_name: "Anthony Edwards",
            team_abbr: "MIN",
            game_date: "2026-02-01",
            opponent_team_abbr: "DEN",
            wl: "W",
            team_score: 124,
            opponent_score: 118,
            pts: 52,
            reb: 7,
            ast: 5,
            fg3m: 6,
          },
        ],
      },
    });
    const teamData = makeResponse("top_team_games", {
      queryClass: "leaderboard",
      metadata: { stat: "pts", season: "2025-26" },
      sections: {
        leaderboard: [
          {
            rank: 1,
            team_name: "Indiana Pacers",
            team_abbr: "IND",
            game_date: "2026-02-01",
            opponent_team_abbr: "ATL",
            wl: "W",
            pts: 152,
            opponent_pts: 140,
          },
        ],
      },
    });

    const { rerender } = render(
      <ResultRenderer data={playerData} displayMode="review" />,
    );

    expectHeaders(screen.getByRole("table", { name: "Top performances" }), [
      "Rank",
      "Player",
      "Date",
      "Opp",
      "Result",
      "Score",
      "PTS",
    ]);

    rerender(<ResultRenderer data={teamData} displayMode="review" />);
    expectHeaders(screen.getByRole("table", { name: "Top performances" }), [
      "Rank",
      "Team",
      "Date",
      "Opp",
      "Result",
      "Score",
      "PTS",
    ]);
  });

  it("renders the rolling-stretch rank, window context, and primary metric contract", () => {
    const data = makeResponse("player_stretch_leaderboard", {
      queryClass: "leaderboard",
      metadata: { stretch_metric: "pts", season: "2025-26" },
      sections: {
        leaderboard: [
          {
            rank: 1,
            player_name: "Luka Doncic",
            team_abbr: "LAL",
            window_size: 10,
            stretch_metric: "pts",
            stretch_value: 35.4,
            window_start_date: "2026-01-10",
            window_end_date: "2026-02-01",
            season: "2025-26",
          },
        ],
      },
    });

    render(<ResultRenderer data={data} displayMode="review" />);

    const table = screen.getByRole("table", {
      name: "Rolling stretch leaderboard",
    });
    expectHeaders(table, [
      "Rank",
      "Player",
      "Window",
      "PPG",
      "Start",
      "End",
      "Season",
    ]);
  });
});
