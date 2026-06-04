import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResultRenderer from "../../components/results/ResultRenderer";
import { makeResponse } from "./helpers";

describe("ResultRenderer leaderboard patterns", () => {

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
          interpreted_as: "most ppg by a player in 2025 playoffs",
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
        "Shai Gilgeous-Alexander led the NBA with 29.9 PPG in the 2025 playoffs.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Interpreted as: most ppg by a player in 2025 playoffs"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Leaderboard" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "PPG" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Team" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "GP" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Jalen Williams")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Show raw table" }),
    ).not.toBeInTheDocument();
  });


  it("includes position context in guard-filtered leaderboard heroes", () => {
    const data = makeResponse({
      query: "What players have the best field goal percentage among guards?",
      route: "season_leaders",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          query_text:
            "What players have the best field goal percentage among guards?",
          route: "season_leaders",
          season: "2025-26",
          season_type: "Regular Season",
          position_filter: "guards",
          stat: "fg_pct",
          applied_filters: [
            { label: "Position", value: "guards", kind: "position" },
          ],
        },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              player_name: "Gary Payton II",
              player_id: 1627780,
              team_abbr: "GSW",
              games_played: 73,
              fg_pct: 0.583,
              season: "2025-26",
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
        "Gary Payton II led guards with 58.3% field-goal percentage in the 2025-26 regular season.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/led the NBA/i)).not.toBeInTheDocument();
  });


  it("includes position context in center-filtered leaderboard heroes", () => {
    const data = makeResponse({
      query: "Which centers have the most rebounds this season?",
      route: "season_leaders",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          query_text: "Which centers have the most rebounds this season?",
          route: "season_leaders",
          season: "2025-26",
          season_type: "Regular Season",
          position_filter: "centers",
          stat: "reb",
          applied_filters: [
            { label: "Position", value: "centers", kind: "position" },
          ],
        },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              player_name: "Nikola Jokić",
              player_id: 203999,
              team_abbr: "DEN",
              games_played: 65,
              reb_per_game: 12.862,
              season: "2025-26",
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
        "Nikola Jokić led centers with 12.9 RPG in the 2025-26 regular season.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/led the NBA/i)).not.toBeInTheDocument();
  });


  it("renders season team leaderboards with a team-first sentence and highlighted metric", () => {
    const data = makeResponse({
      query: "team assists leaders this season",
      route: "season_team_leaders",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          query_text: "team assists leaders this season",
          route: "season_team_leaders",
          season: "2025-26",
          season_type: "Regular Season",
        },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              team_name: "Denver Nuggets",
              team_abbr: "DEN",
              team_id: 1610612743,
              games_played: 82,
              ast_per_game: 29.7,
              pts_per_game: 120.8,
              season: "2025-26",
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
        "The Denver Nuggets had the most assists per game in the 2025-26 regular season, with 29.7 per game.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Leaderboard" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "APG" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "GP" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Season Type" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("columnheader", { name: "PPG" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Show raw table" }),
    ).not.toBeInTheDocument();
  });


  it("uses lowest-direction copy for fewest points allowed leaderboards", () => {
    const data = makeResponse({
      query: "Which team has allowed the fewest points per game this season?",
      route: "season_team_leaders",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          query_text:
            "Which team has allowed the fewest points per game this season?",
          route: "season_team_leaders",
          season: "2025-26",
          season_type: "Regular Season",
          stat: "opponent_pts_per_game",
          ascending: true,
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
              games_played: 82,
              opponent_pts_per_game: 107.1585,
              season: "2025-26",
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
        "The Boston Celtics allowed the fewest points per game in the 2025-26 regular season, with 107.2 per game.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/most opponent pts per game/i),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Opponent PTS Per Game" }),
    ).toBeInTheDocument();
  });


  it("uses highest-direction copy for most points allowed leaderboards", () => {
    const data = makeResponse({
      query: "which teams allow the most points per game this season",
      route: "season_team_leaders",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          query_text: "which teams allow the most points per game this season",
          route: "season_team_leaders",
          season: "2025-26",
          season_type: "Regular Season",
          stat: "opponent_pts_per_game",
          ascending: false,
        },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              team_name: "Utah Jazz",
              team_abbr: "UTA",
              team_id: 1610612762,
              games_played: 82,
              opponent_pts_per_game: 126.0122,
              season: "2025-26",
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
        "The Utah Jazz allowed the most points per game in the 2025-26 regular season, with 126 per game.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Opponent PTS Per Game" }),
    ).toBeInTheDocument();
  });


  it("keeps wins as the primary metric for team season wins leaderboards", () => {
    const data = makeResponse({
      query: "most wins by a team in 2025-26",
      route: "season_team_leaders",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          query_text: "most wins by a team in 2025-26",
          route: "season_team_leaders",
          season: "2025-26",
          season_type: "Regular Season",
        },
        notes: [],
        caveats: [],
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
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "The Oklahoma City Thunder won the most games in the 2025-26 regular season, with 68 wins.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Wins" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "W-L" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Win %" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Show raw table" }),
    ).not.toBeInTheDocument();
  });


  it("renders occurrence leaderboards without the old card-row detail toggle", () => {
    const data = makeResponse({
      query: "teams with most 120-point games this season",
      route: "team_occurrence_leaders",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          query_text: "teams with most 120-point games this season",
          route: "team_occurrence_leaders",
          season: "2025-26",
          season_type: "Regular Season",
          primary_count: 55,
          count_phrase:
            "The Nuggets had 55 games with at least 120 points this season.",
        },
        notes: [],
        caveats: [],
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
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "The Nuggets had 55 games with at least 120 points this season.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Leaderboard" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Games PTS 120+" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("DEN").length).toBeGreaterThan(0);
    expect(
      screen.queryByRole("button", { name: "Show raw table" }),
    ).not.toBeInTheDocument();
  });


  it("renders lineup leaderboards as dense rows with the lineup identity", () => {
    const data = makeResponse({
      query: "best 3-man units this season",
      route: "lineup_leaderboard",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          query_text: "best 3-man units this season",
          route: "lineup_leaderboard",
          season: "2025-26",
          season_type: "Regular Season",
        },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              season: "2025-26",
              season_type: "Regular Season",
              team_abbr: "BOS",
              unit_size: 3,
              lineup_id: "BOS-001",
              lineup_name: "Jayson Tatum | Jaylen Brown | Derrick White",
              player_ids: "1628369|1627759|1628401",
              player_names: "Jayson Tatum|Jaylen Brown|Derrick White",
              minute_minimum: 200,
              minutes: 240,
              off_rating: 122.1,
              def_rating: 103.6,
              net_rating: 18.5,
              pace: 99.4,
              ts_pct: 0.64,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText("Jayson Tatum / Jaylen Brown / Derrick White"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Lineup" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Team" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Net" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "ORtg" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "DRtg" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Pace" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "TS%" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("BOS-001")).not.toBeInTheDocument();
    expect(
      screen.queryByText("1628369|1627759|1628401"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Jayson Tatum|Jaylen Brown|Derrick White"),
    ).not.toBeInTheDocument();
  });


  it("renders top player games as league-wide top performances", () => {
    const data = makeResponse({
      query: "highest scoring games this season",
      route: "top_player_games",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          query_text: "highest scoring games this season",
          route: "top_player_games",
          season: "2025-26",
          season_type: "Regular Season",
          stat: "pts",
          total_count: 35,
        },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              player_name: "Bam Adebayo",
              player_id: 1628389,
              team_abbr: "MIA",
              game_date: "2026-03-10",
              game_id: 1,
              pts: 83,
              reb: 9,
              ast: 3,
              fg3m: 5,
              opponent_team_abbr: "WAS",
              is_home: 1,
              wl: "W",
            },
            {
              rank: 2,
              player_name: "Luka Doncic",
              player_id: 1629029,
              team_abbr: "LAL",
              game_date: "2026-03-19",
              game_id: 2,
              pts: 60,
              reb: 7,
              ast: 3,
              fg3m: 4,
              opponent_team_abbr: "MIA",
              is_away: 1,
              wl: "W",
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Bam Adebayo had the top scoring game this season with 83 points in a win against WAS on Mar 10.",
      ),
    ).toBeInTheDocument();
    const table = screen.getByRole("table", { name: "Top performances" });
    const rows = within(table).getAllByRole("row");
    expect(within(rows[1]).getByText("Bam Adebayo")).toBeInTheDocument();
    expect(within(rows[2]).getByText("Luka Doncic")).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Rank" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Player" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "PTS" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "3PM" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Rank" }),
    ).toHaveAttribute("data-mobile-priority", "primary");
    expect(
      screen.getByRole("columnheader", { name: "Player" }),
    ).toHaveAttribute("data-mobile-priority", "primary");
    expect(
      screen.getByRole("columnheader", { name: "Date" }),
    ).toHaveAttribute("data-mobile-priority", "primary");
    expect(
      screen.getByRole("columnheader", { name: "PTS" }),
    ).toHaveAttribute("data-mobile-priority", "primary");
    expect(
      screen.getByRole("columnheader", { name: "Opp" }),
    ).toHaveAttribute("data-mobile-priority", "secondary");
    expect(
      screen.getByRole("columnheader", { name: "3PM" }),
    ).toHaveAttribute("data-mobile-priority", "secondary");
    expect(screen.getByText("Showing top 2 of 35")).toBeInTheDocument();
    expect(
      screen.queryByRole("table", { name: "Game log" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Top Player Games Detail"),
    ).not.toBeInTheDocument();
  });


  it("renders top player triple-double games with a composite primary metric", () => {
    const data = makeResponse({
      query: "biggest triple-double games this season",
      route: "top_player_games",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          query_text: "biggest triple-double games this season",
          route: "top_player_games",
          season: "2025-26",
          season_type: "Regular Season",
          occurrence_event: { special_event: "triple_double" },
        },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              player_name: "Nikola Jokic",
              player_id: 203999,
              team_abbr: "DEN",
              game_date: "2026-01-08",
              game_id: 3,
              pts: 35,
              reb: 15,
              ast: 15,
              opponent_team_abbr: "BOS",
              wl: "W",
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Nikola Jokic had the top triple-double game this season with 35-15-15 in a win against BOS on Jan 8.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "PTS-REB-AST" }),
    ).toBeInTheDocument();
  });


  it("renders top team games as team top performances", () => {
    const data = makeResponse({
      query: "top team scoring games",
      route: "top_team_games",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          query_text: "top team scoring games",
          route: "top_team_games",
          season: "2025-26",
          season_type: "Regular Season",
          stat: "pts",
        },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              team_name: "Denver Nuggets",
              team_abbr: "DEN",
              game_date: "2026-02-20",
              game_id: 1,
              pts: 157,
              opponent_pts: 103,
              opponent_team_abbr: "POR",
              is_away: 1,
              wl: "W",
              reb: 60,
              ast: 41,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Denver Nuggets had the top scoring game in the 2025-26 regular season with 157 points in a 157-103 win against POR on Feb 20.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Team" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Result" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Score" }),
    ).toBeInTheDocument();
    expect(screen.getByText("157-103")).toBeInTheDocument();
    expect(screen.getAllByText("Denver Nuggets").length).toBeGreaterThan(0);
    expect(
      screen.getByRole("table", { name: "Top performances" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("table", { name: "Game log" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Top Team Games Detail")).not.toBeInTheDocument();
  });
});
