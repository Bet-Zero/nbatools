import { render, screen, within } from "@testing-library/react";
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
      route: "unmapped_route",
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
      route: "unmapped_route",
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

  it("composes player last-N summaries with a game-log answer table", () => {
    const data = makeResponse({
      query: "Jokic last 10 games",
      route: "player_game_summary",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          query_text: "Jokic last 10 games",
          route: "player_game_summary",
          season: "2025-26",
          season_type: "Regular Season",
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
              games: 10,
              wins: 10,
              losses: 0,
              pts_avg: 25.3,
              pts_sum: 253,
              reb_avg: 14.5,
              reb_sum: 145,
              ast_avg: 11.9,
              ast_sum: 119,
              minutes_avg: 35.2,
              minutes_sum: 352,
            },
          ],
          game_log: [
            {
              game_id: 1,
              game_date: "2026-03-22",
              player_id: 203999,
              player_name: "Nikola Jokic",
              team_id: 1610612743,
              team_abbr: "DEN",
              team_name: "Denver Nuggets",
              opponent_team_id: 1610612757,
              opponent_team_abbr: "POR",
              opponent_team_name: "Portland Trail Blazers",
              is_home: 1,
              wl: "W",
              minutes: 35,
              pts: 22,
              reb: 14,
              ast: 14,
            },
            {
              game_id: 2,
              game_date: "2026-03-24",
              player_id: 203999,
              player_name: "Nikola Jokic",
              team_id: 1610612743,
              team_abbr: "DEN",
              team_name: "Denver Nuggets",
              opponent_team_id: 1610612756,
              opponent_team_abbr: "PHX",
              opponent_team_name: "Phoenix Suns",
              is_away: 1,
              wl: "W",
              minutes: 35,
              pts: 23,
              reb: 17,
              ast: 17,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Nikola Jokic has averaged 25.3 points, 14.5 rebounds and 11.9 assists in his last 10 games.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Game log" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "PTS" })).toBeInTheDocument();
    expect(screen.getByText("Average")).toBeInTheDocument();
    expect(screen.getByText("Total")).toBeInTheDocument();
    expect(screen.getByText("253")).toBeInTheDocument();
    expect(screen.queryByText("Recent Games")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Show raw table" })).not.toBeInTheDocument();
  });

  it("keeps broad player summaries to the entity summary pattern only", () => {
    const data = makeResponse({
      query: "Curry this season",
      route: "player_game_summary",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          query_text: "Curry this season",
          route: "player_game_summary",
          season: "2025-26",
          season_type: "Regular Season",
          player_context: {
            player_id: 201939,
            player_name: "Stephen Curry",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              player_name: "Stephen Curry",
              games: 43,
              pts_avg: 26.558,
              reb_avg: 3.581,
              ast_avg: 4.721,
            },
          ],
          game_log: [
            {
              game_date: "2025-10-21",
              player_name: "Stephen Curry",
              pts: 23,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Stephen Curry has averaged 26.6 points, 3.6 rebounds and 4.7 assists this season.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("table", { name: "Game log" })).not.toBeInTheDocument();
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

  it("renders player stretch leaderboards through the leaderboard pattern", () => {
    const data = makeResponse({
      query: "best 3-game scoring stretches this season",
      route: "player_stretch_leaderboard",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          query_text: "best 3-game scoring stretches this season",
          route: "player_stretch_leaderboard",
          season: "2025-26",
          season_type: "Regular Season",
          window_size: 3,
          stretch_metric: "pts",
        },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              player_name: "Luka Doncic",
              player_id: 1629029,
              team_abbr: "LAL",
              window_size: 3,
              stretch_metric: "pts",
              window_start_date: "2026-03-16",
              window_end_date: "2026-03-19",
              games_in_window: 3,
              stretch_value: 45.333,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Luka Doncic averaged the most points per game in the 2025-26 regular season, with 45.3 per game.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "PPG" })).toBeInTheDocument();
    expect(screen.queryByText("Stretch Games")).not.toBeInTheDocument();
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

    expect(screen.getByRole("table", { name: "Leaderboard" })).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Games PTS 120+" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("DEN").length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: "Show raw table" })).not.toBeInTheDocument();
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
              lineup_members: ["Jayson Tatum", "Jaylen Brown", "Derrick White"],
              team_abbr: "BOS",
              games: 22,
              minutes: 240,
              net_rating: 18.5,
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
      screen.getByText("Jayson Tatum / Jaylen Brown / Derrick White"),
    ).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Net" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "TM" })).toBeInTheDocument();
  });

  it("renders playoff appearances as a leaderboard pattern", () => {
    const data = makeResponse({
      query: "most playoff appearances",
      route: "playoff_appearances",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          query_text: "most playoff appearances",
          route: "playoff_appearances",
          season_type: "Playoffs",
        },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              team_abbr: "MIA",
              team_name: "Miami Heat",
              appearances: 23,
              round: "Playoffs",
              seasons: "1996-97 to 2024-25",
            },
          ],
        },
        current_through: "2025-06-22",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "The Miami Heat had the most playoff appearances from 1996-97 to 2024-25, with 23.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Appearances" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Playoff leaderboard rankings")).not.toBeInTheDocument();
  });

  it("renders player game finder rows through the game-log pattern", () => {
    const data = makeResponse({
      query: "games where Jokic had over 25 points and 10 rebounds",
      route: "player_game_finder",
      result: {
        query_class: "finder",
        result_status: "ok",
        metadata: {
          query_text: "games where Jokic had over 25 points and 10 rebounds",
          route: "player_game_finder",
          season: "2025-26",
          season_type: "Regular Season",
          stat: "pts",
          min_value: 25.0001,
          threshold_conditions: [
            { stat: "pts", min_value: 25.0001, max_value: null },
          ],
          player_context: {
            player_id: 203999,
            player_name: "Nikola Jokic",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          finder: [
            {
              rank: 1,
              game_id: 1,
              game_date: "2026-03-22",
              player_id: 203999,
              player_name: "Nikola Jokic",
              team_id: 1610612743,
              team_abbr: "DEN",
              team_name: "Denver Nuggets",
              opponent_team_id: 1610612757,
              opponent_team_abbr: "POR",
              opponent_team_name: "Portland Trail Blazers",
              is_home: 1,
              wl: "W",
              minutes: 35,
              pts: 32,
              reb: 14,
              ast: 10,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(screen.getByRole("table", { name: "Game log" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Player" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "PTS" })).toBeInTheDocument();
    expect(screen.getByText("Nikola Jokic")).toBeInTheDocument();
    expect(screen.getByText("Player Game Detail")).toBeInTheDocument();
    expect(screen.queryByLabelText("Player game cards")).not.toBeInTheDocument();
  });

  it("renders team game finder rows without a player column", () => {
    const data = makeResponse({
      query: "Celtics recent games",
      route: "game_finder",
      result: {
        query_class: "finder",
        result_status: "ok",
        metadata: {
          query_text: "Celtics recent games",
          route: "game_finder",
          season: "2025-26",
          season_type: "Regular Season",
          team_context: {
            team_id: 1610612738,
            team_abbr: "BOS",
            team_name: "Boston Celtics",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          finder: [
            {
              rank: 1,
              game_id: 1,
              game_date: "2026-04-12",
              team_id: 1610612738,
              team_abbr: "BOS",
              team_name: "Boston Celtics",
              opponent_team_abbr: "ORL",
              opponent_team_name: "Orlando Magic",
              is_home: 1,
              wl: "W",
              pts: 113,
              opponent_pts: 108,
              reb: 46,
              ast: 24,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(screen.getByRole("columnheader", { name: "Team" })).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Player" })).not.toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Score" })).toBeInTheDocument();
    expect(screen.getByText("113-108")).toBeInTheDocument();
    expect(screen.getByText("Game Detail")).toBeInTheDocument();
  });

  it("renders top player games in leaderboard order through the game-log pattern", () => {
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

    const rows = screen.getAllByRole("row");
    expect(within(rows[1]).getByText("Bam Adebayo")).toBeInTheDocument();
    expect(within(rows[2]).getByText("Luka Doncic")).toBeInTheDocument();
    expect(screen.getByText("Top Player Games Detail")).toBeInTheDocument();
    expect(screen.queryByLabelText("Ranked player games")).not.toBeInTheDocument();
  });

  it("renders top team games with team identity and score", () => {
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

    expect(screen.getByRole("columnheader", { name: "Team" })).toBeInTheDocument();
    expect(screen.getByText("Denver Nuggets")).toBeInTheDocument();
    expect(screen.getByText("157-103")).toBeInTheDocument();
    expect(screen.getByText("Top Team Games Detail")).toBeInTheDocument();
  });

  it("renders single-game team summaries as game logs with detail sections", () => {
    const data = makeResponse({
      query: "Celtics recent game",
      route: "game_summary",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          query_text: "Celtics recent game",
          route: "game_summary",
          season: "2025-26",
          season_type: "Regular Season",
          team_context: {
            team_id: 1610612738,
            team_abbr: "BOS",
            team_name: "Boston Celtics",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              team_name: "Boston Celtics",
              games: 1,
              wins: 1,
              losses: 0,
              pts_avg: 113,
              pts_sum: 113,
              reb_avg: 46,
              reb_sum: 46,
              ast_avg: 24,
              ast_sum: 24,
            },
          ],
          by_season: [{ season: "2025-26", games: 1, pts_avg: 113 }],
          game_log: [
            {
              game_date: "2026-04-12",
              game_id: 1,
              team_id: 1610612738,
              team_abbr: "BOS",
              team_name: "Boston Celtics",
              opponent_team_abbr: "ORL",
              opponent_team_name: "Orlando Magic",
              is_home: 1,
              wl: "W",
              pts: 113,
              opponent_pts: 108,
              reb: 46,
              ast: 24,
            },
          ],
          top_performers: [
            {
              leader_type: "pts",
              leader_label: "Points",
              player_name: "Baylor Scheierman",
              value: 30,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(screen.getByText("Boston Celtics")).toBeInTheDocument();
    expect(screen.getByText("113-108")).toBeInTheDocument();
    expect(screen.getByText("Summary Detail")).toBeInTheDocument();
    expect(screen.getByText("By Season Detail")).toBeInTheDocument();
    expect(screen.getByText("Top Performers Detail")).toBeInTheDocument();
    expect(screen.queryByText("Top player performers")).not.toBeInTheDocument();
  });

  it("renders player split summaries through the split pattern", () => {
    const data = makeResponse({
      query: "Jokic home vs away",
      route: "player_split_summary",
      result: {
        query_class: "split_summary",
        result_status: "ok",
        metadata: {
          query_text: "Jokic home vs away",
          route: "player_split_summary",
          season: "2025-26",
          season_type: "Regular Season",
          split_type: "home_away",
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
              season_start: "2025-26",
              season_end: "2025-26",
              season_type: "Regular Season",
              split: "home_away",
              games_total: 8,
            },
          ],
          split_comparison: [
            {
              bucket: "home",
              games: 4,
              wins: 3,
              losses: 1,
              win_pct: 0.75,
              pts_avg: 31.4,
              reb_avg: 12.1,
              ast_avg: 8.2,
              minutes_avg: 34.6,
              ts_pct_avg: 0.668,
              fg3_pct_avg: 0.412,
              plus_minus_avg: 8.5,
            },
            {
              bucket: "away",
              games: 4,
              wins: 2,
              losses: 2,
              win_pct: 0.5,
              pts_avg: 28.2,
              reb_avg: 10,
              ast_avg: 9.4,
              minutes_avg: 35.1,
              ts_pct_avg: 0.631,
              fg3_pct_avg: 0.356,
              plus_minus_avg: 1.2,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText("Nikola Jokic's home/away split for 2025-26 Regular Season."),
    ).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Split buckets" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "PTS" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "+/-" })).toBeInTheDocument();
    expect(screen.getByText("Home +3.2 PPG")).toBeInTheDocument();
    expect(screen.getByText("Split Summary Detail")).toBeInTheDocument();
    expect(screen.getByText("Split Comparison Detail")).toBeInTheDocument();
    expect(screen.queryByText("Player Split Summary")).not.toBeInTheDocument();
  });

  it("renders team split summaries with team identity", () => {
    const data = makeResponse({
      query: "Lakers home vs away",
      route: "team_split_summary",
      result: {
        query_class: "split_summary",
        result_status: "ok",
        metadata: {
          query_text: "Lakers home vs away",
          route: "team_split_summary",
          season: "2025-26",
          season_type: "Regular Season",
          split_type: "home_away",
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
              season_start: "2025-26",
              season_end: "2025-26",
              season_type: "Regular Season",
              split: "home_away",
              games_total: 10,
            },
          ],
          split_comparison: [
            {
              bucket: "home",
              games: 5,
              wins: 4,
              losses: 1,
              pts_avg: 118,
              ast_avg: 28,
              plus_minus_avg: 7.4,
            },
            {
              bucket: "away",
              games: 5,
              wins: 2,
              losses: 3,
              pts_avg: 110,
              ast_avg: 23,
              plus_minus_avg: -2.1,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Los Angeles Lakers' home/away split for 2025-26 Regular Season.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Los Angeles Lakers")).toBeInTheDocument();
    expect(screen.getByText("Home +8 PPG")).toBeInTheDocument();
  });

  it("renders player on-off summaries as split results", () => {
    const data = makeResponse({
      query: "Lakers on/off LeBron",
      route: "player_on_off",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          query_text: "Lakers on/off LeBron",
          route: "player_on_off",
          season: "2025-26",
          season_type: "Regular Season",
          player_context: {
            player_id: 2544,
            player_name: "LeBron James",
          },
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
              season: "2025-26",
              season_type: "Regular Season",
              player_name: "LeBron James",
              team_abbr: "LAL",
              team_name: "Los Angeles Lakers",
              presence_state: "on",
              gp: 20,
              minutes: 640,
              off_rating: 120.4,
              def_rating: 108,
              net_rating: 12.4,
              plus_minus: 180,
            },
            {
              season: "2025-26",
              season_type: "Regular Season",
              player_name: "LeBron James",
              team_abbr: "LAL",
              team_name: "Los Angeles Lakers",
              presence_state: "off",
              gp: 20,
              minutes: 320,
              off_rating: 106.2,
              def_rating: 109.1,
              net_rating: -2.9,
              plus_minus: -42,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText("LeBron James' on/off split for 2025-26 Regular Season."),
    ).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Net" })).toBeInTheDocument();
    expect(screen.getByText("On +15.3 net rating")).toBeInTheDocument();
    expect(screen.getByText("On/Off Detail")).toBeInTheDocument();
    expect(screen.queryByText("Player On/Off")).not.toBeInTheDocument();
  });

  it("renders player streaks through the streak pattern", () => {
    const data = makeResponse({
      query: "Jokic 25-point game streak",
      route: "player_streak_finder",
      result: {
        query_class: "streak",
        result_status: "ok",
        metadata: {
          query_text: "Jokic 25-point game streak",
          route: "player_streak_finder",
          season: "2025-26",
          season_type: "Regular Season",
          player_context: {
            player_id: 203999,
            player_name: "Nikola Jokic",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          streak: [
            {
              player_name: "Nikola Jokic",
              player_id: 203999,
              condition: "pts>=25",
              streak_length: 6,
              games: 6,
              start_date: "2026-01-01",
              end_date: "2026-01-12",
              is_active: true,
              wins: 5,
              losses: 1,
              pts_avg: 31.5,
              reb_avg: 12.2,
              ast_avg: 9.1,
              minutes_avg: 35.4,
              ts_pct_avg: 0.672,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(screen.getAllByText("6 games").length).toBeGreaterThan(0);
    expect(
      screen.getByText(/Nikola Jokic's active 25\+ pts streak/),
    ).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Streaks" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "TS%" })).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("Full Streak Detail")).toBeInTheDocument();
    expect(screen.queryByLabelText("Streak results")).not.toBeInTheDocument();
  });

  it("renders team streaks with team identity and completed status", () => {
    const data = makeResponse({
      query: "Lakers longest win streak",
      route: "team_streak_finder",
      result: {
        query_class: "streak",
        result_status: "ok",
        metadata: {
          query_text: "Lakers longest win streak",
          route: "team_streak_finder",
          season: "2025-26",
          season_type: "Regular Season",
          team_context: {
            team_id: 1610612747,
            team_abbr: "LAL",
            team_name: "Los Angeles Lakers",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          streak: [
            {
              team_name: "Los Angeles Lakers",
              team_abbr: "LAL",
              team_id: 1610612747,
              condition: "wins",
              streak_length: 4,
              games: 4,
              start_date: "2026-02-01",
              end_date: "2026-02-08",
              is_active: false,
              wins: 4,
              losses: 0,
              pts_avg: 118.2,
              plus_minus_avg: 7.5,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(screen.getAllByText("Los Angeles Lakers").length).toBeGreaterThan(0);
    expect(
      screen.getByText(/Los Angeles Lakers' completed wins streak/),
    ).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "+/-" })).toBeInTheDocument();
    expect(screen.getByText("4-0")).toBeInTheDocument();
  });

  it("renders playoff history as a hero plus season table", () => {
    const data = makeResponse({
      query: "Lakers playoff history",
      route: "playoff_history",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          query_text: "Lakers playoff history",
          route: "playoff_history",
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
              season_start: "2019-20",
              season_end: "2024-25",
              season_type: "Playoffs",
              games: 84,
              wins: 52,
              losses: 32,
              win_pct: 0.619,
              seasons_appeared: 5,
              titles: 1,
            },
          ],
          by_season: [
            {
              season: "2023-24",
              wins: 1,
              losses: 4,
              deepest_round: "First Round",
              result: "Lost",
              opponent_team_abbr: "DEN",
            },
            {
              season: "2022-23",
              wins: 8,
              losses: 8,
              deepest_round: "Conference Finals",
              result: "Lost",
              opponent_team_abbr: "DEN",
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(screen.getByLabelText("Playoff history result")).toBeInTheDocument();
    expect(screen.getAllByText("Los Angeles Lakers").length).toBeGreaterThan(0);
    const history = screen.getByLabelText("Playoff history result");
    expect(
      within(history).getByText("playoff appearances", { exact: false }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Playoff season breakdown" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Round" })).toBeInTheDocument();
    expect(screen.getByText("First Round")).toBeInTheDocument();
    expect(screen.getByText("1-4")).toBeInTheDocument();
    expect(screen.getByText("Postseason Summary Detail")).toBeInTheDocument();
    expect(screen.getByText("Season Breakdown Detail")).toBeInTheDocument();
  });

  it("renders playoff round records through the playoff history pattern", () => {
    const data = makeResponse({
      query: "best Finals record",
      route: "playoff_round_record",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: { route: "playoff_round_record" },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              team_id: 1610612738,
              team_name: "Boston Celtics",
              team_abbr: "BOS",
              games_played: 42,
              wins: 28,
              losses: 14,
              win_pct: 0.667,
              round: "Finals",
              seasons: "1980-81 to 2024-25",
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByLabelText("Playoff round record result"),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Boston Celtics").length).toBeGreaterThan(0);
    const roundRecord = screen.getByLabelText("Playoff round record result");
    expect(
      within(roundRecord).getByText("finals playoff mark", { exact: false }),
    ).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Playoff round records" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Win Pct" })).toBeInTheDocument();
    expect(screen.getAllByText("66.7%").length).toBeGreaterThan(0);
    expect(screen.getAllByText("28-14").length).toBeGreaterThan(0);
    expect(screen.getByText("Playoff Round Detail")).toBeInTheDocument();
  });

  it("renders playoff matchup history as a series table", () => {
    const data = makeResponse({
      query: "Celtics vs Heat playoff matchups",
      route: "playoff_matchup_history",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: {
          query_text: "Celtics vs Heat playoff matchups",
          route: "playoff_matchup_history",
          teams_context: [
            {
              team_id: 1610612738,
              team_abbr: "BOS",
              team_name: "Boston Celtics",
            },
            {
              team_id: 1610612748,
              team_abbr: "MIA",
              team_name: "Miami Heat",
            },
          ],
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            { team_name: "Celtics", games: 7, wins: 4, losses: 3 },
            { team_name: "Heat", games: 7, wins: 3, losses: 4 },
          ],
          comparison: [
            {
              season: "2022-23",
              round: "Conference Finals",
              winner_team_name: "Miami Heat",
              series_result: "MIA won 4-3",
              BOS_wins: 3,
              BOS_losses: 4,
              MIA_wins: 4,
              MIA_losses: 3,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(screen.getByLabelText("Playoff matchup result")).toBeInTheDocument();
    expect(screen.getAllByText("Boston Celtics").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Miami Heat").length).toBeGreaterThan(0);
    expect(
      screen.getByText(/Boston Celtics and Miami Heat have a playoff matchup history/),
    ).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Playoff series" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "BOS" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "MIA" })).toBeInTheDocument();
    expect(screen.getByText("MIA won 4-3")).toBeInTheDocument();
    expect(screen.getByText("3-4")).toBeInTheDocument();
    expect(screen.getAllByText("4-3").length).toBeGreaterThan(0);
    expect(screen.getByText("Series Detail")).toBeInTheDocument();
  });
});
