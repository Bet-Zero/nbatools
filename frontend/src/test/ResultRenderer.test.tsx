import { fireEvent, render, screen, within } from "@testing-library/react";
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
              fgm: 9,
              fga: 15,
              fg3m: 2,
              fg3a: 5,
              ftm: 2,
              fta: 3,
              stl: 1,
              blk: 2,
              tov: 3,
              plus_minus: 8,
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
              fgm: 10,
              fga: 16,
              fg3m: 1,
              fg3a: 4,
              ftm: 2,
              fta: 4,
              stl: 2,
              blk: 1,
              tov: 4,
              plus_minus: 4,
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
    expect(
      screen.getByRole("columnheader", { name: "PTS" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "FG" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "3P" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "FT" }),
    ).toBeInTheDocument();
    expect(screen.getByText("10-16")).toBeInTheDocument();
    expect(screen.getByText("Average")).toBeInTheDocument();
    expect(screen.getByText("Total")).toBeInTheDocument();
    expect(screen.getByText("253")).toBeInTheDocument();
    expect(screen.queryByLabelText("Summary averages")).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText("Game-log averages"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Recent Games")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Show raw table" }),
    ).not.toBeInTheDocument();
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
    expect(screen.queryByLabelText("Summary averages")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("table", { name: "Game log" }),
    ).not.toBeInTheDocument();
  });

  it("prioritizes team record heroes for record-when player condition summaries", () => {
    const data = makeResponse({
      query: "What is Denver's record when Nikola Jokić has a triple-double?",
      route: "player_game_summary",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          query_text:
            "What is Denver's record when Nikola Jokić has a triple-double?",
          route: "player_game_summary",
          season: "2025-26",
          season_type: "Regular Season",
          scope_kind: "single_season",
          occurrence_event: { special_event: "triple_double" },
          player_context: {
            player_id: 203999,
            player_name: "Nikola Jokić",
          },
          team_context: {
            team_id: 1610612743,
            team_abbr: "DEN",
            team_name: "Nuggets",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              player_name: "Nikola Jokić",
              games: 34,
              wins: 24,
              losses: 10,
              win_pct: 0.706,
              pts_avg: 31.2,
              reb_avg: 14.1,
              ast_avg: 12.3,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "The Nuggets are 24-10 when Nikola Jokić records a triple-double this season.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Nikola Jokić has averaged/)).not.toBeInTheDocument();
  });

  it("trims trailing .0 from integer hero averages", () => {
    const data = makeResponse({
      query: "Luka last 5 games",
      route: "player_game_summary",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          query_text: "Luka last 5 games",
          route: "player_game_summary",
          window_size: 5,
          player_context: {
            player_id: 1629029,
            player_name: "Luka Doncic",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              player_name: "Luka Doncic",
              games: 5,
              pts_avg: 34.0,
              reb_avg: 6.0,
              ast_avg: 7.0,
            },
          ],
          game_log: [{ game_id: 1, game_date: "2026-03-01", pts: 34 }],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Luka Doncic has averaged 34 points, 6 rebounds and 7 assists in his last 5 games.",
      ),
    ).toBeInTheDocument();
  });

  it("renders by-season breakdowns for multi-period entity summaries", () => {
    const data = makeResponse({
      query: "Jokic career vs Lakers",
      route: "player_game_summary",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          query_text: "Jokic career vs Lakers",
          route: "player_game_summary",
          scope_kind: "career",
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
              games: 2,
              pts_avg: 25.5,
              reb_avg: 11,
              ast_avg: 8,
            },
          ],
          by_season: [
            {
              season: "2024-25",
              games: 0,
              pts_avg: 0,
              reb_avg: 0,
              ast_avg: 0,
              fg_pct_avg: 0,
            },
            {
              season: "2025-26",
              games: 2,
              pts_avg: 25.5,
              reb_avg: 11,
              ast_avg: 8,
              fg_pct_avg: 0.545,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    const table = screen.getByRole("table", { name: "Season breakdown" });
    expect(table).toBeInTheDocument();
    expect(
      within(table).getByRole("columnheader", { name: "PPG" }),
    ).toBeInTheDocument();
    expect(
      within(table).getByRole("columnheader", { name: "FG%" }),
    ).toBeInTheDocument();

    const rows = within(table).getAllByRole("row");
    expect(within(rows[1]).getByText("2025-26")).toBeInTheDocument();
    expect(within(rows[2]).getByText("2024-25")).toBeInTheDocument();
    expect(within(rows[2]).getAllByText("—").length).toBeGreaterThan(0);
  });

  it("keeps single-season entity summaries hero-only even when by_season exists", () => {
    const data = makeResponse({
      query: "Curry this season",
      route: "player_game_summary",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          query_text: "Curry this season",
          route: "player_game_summary",
          scope_kind: "single_season",
          player_context: {
            player_id: 201939,
            player_name: "Stephen Curry",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [{ player_name: "Stephen Curry", pts_avg: 26.5 }],
          by_season: [{ season: "2025-26", games: 60, pts_avg: 26.5 }],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.queryByRole("table", { name: "Season breakdown" }),
    ).not.toBeInTheDocument();
  });

  it("renders opponent-scoped player summaries with the matchup game log", () => {
    const data = makeResponse({
      query: "Jokic vs Lakers this season",
      route: "player_game_summary",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          query_text: "Jokic vs Lakers this season",
          route: "player_game_summary",
          scope_kind: "single_season",
          player_context: {
            player_id: 203999,
            player_name: "Nikola Jokic",
          },
          opponent_context: {
            team_id: 1610612747,
            team_abbr: "LAL",
            team_name: "Los Angeles Lakers",
          },
          applied_filters: [
            { label: "Opponent", value: "Lakers", kind: "team" },
          ],
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              player_name: "Nikola Jokic",
              games: 2,
              pts_avg: 28,
              reb_avg: 12,
              ast_avg: 9,
            },
          ],
          game_log: [
            {
              game_id: 1,
              game_date: "2026-01-02",
              player_name: "Nikola Jokic",
              team_abbr: "DEN",
              opponent_team_abbr: "LAL",
              is_home: 1,
              wl: "W",
              pts: 26,
              reb: 11,
              ast: 10,
            },
            {
              game_id: 2,
              game_date: "2026-03-01",
              player_name: "Nikola Jokic",
              team_abbr: "DEN",
              opponent_team_abbr: "LAL",
              is_away: 1,
              wl: "L",
              pts: 30,
              reb: 13,
              ast: 8,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Nikola Jokic has averaged 28 points, 12 rebounds and 9 assists in 2 games against Lakers this season.",
      ),
    ).toBeInTheDocument();
    const gameLog = screen.getByRole("table", { name: "Game log" });
    expect(gameLog).toBeInTheDocument();
    const rows = within(gameLog).getAllByRole("row");
    expect(within(rows[1]).getByText("Mar 1")).toBeInTheDocument();
    expect(within(rows[2]).getByText("Jan 2")).toBeInTheDocument();
    expect(
      screen.queryByLabelText("Game-log averages"),
    ).not.toBeInTheDocument();
  });

  it("preserves opponent-quality filters in entity summary heroes and shows the filtered game log", () => {
    const data = makeResponse({
      query: "How has Jayson Tatum played against good teams this season?",
      route: "player_game_summary",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          query_text:
            "How has Jayson Tatum played against good teams this season?",
          route: "player_game_summary",
          season: "2025-26",
          season_type: "Regular Season",
          player_context: {
            player_id: 1628369,
            player_name: "Jayson Tatum",
          },
          applied_filters: [
            {
              label: "Opponent quality",
              value: "good teams",
              kind: "quality",
            },
          ],
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              player_name: "Jayson Tatum",
              games: 2,
              pts_avg: 23,
              reb_avg: 9.5,
              ast_avg: 5.5,
            },
          ],
          game_log: [
            {
              game_id: 1,
              game_date: "2026-02-01",
              player_name: "Jayson Tatum",
              team_abbr: "BOS",
              opponent_team_abbr: "OKC",
              is_home: 1,
              wl: "W",
              pts: 25,
              reb: 10,
              ast: 6,
            },
            {
              game_id: 2,
              game_date: "2026-03-04",
              player_name: "Jayson Tatum",
              team_abbr: "BOS",
              opponent_team_abbr: "DEN",
              is_away: 1,
              wl: "L",
              pts: 21,
              reb: 9,
              ast: 5,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Jayson Tatum has averaged 23 points, 9.5 rebounds and 5.5 assists in 2 games against good teams this season.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Game log" })).toBeInTheDocument();
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
    expect(
      screen.getByRole("columnheader", { name: "Win %" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "W-L" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Games" }),
    ).toBeInTheDocument();
    expect(screen.getByText("578-304")).toBeInTheDocument();
    expect(screen.getByText("882")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Show raw table" }),
    ).not.toBeInTheDocument();
  });

  it("renders team records with a team hero, record table, and collapsed details", () => {
    const data = makeResponse({
      query: "Lakers record this season",
      route: "team_record",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          query_text: "Lakers record this season",
          route: "team_record",
          season: "2025-26",
          season_type: "Regular Season",
          team_context: {
            team_id: 1610612747,
            team_abbr: "LAL",
            team_name: "Lakers",
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
              games: 82,
              wins: 53,
              losses: 29,
              win_pct: 0.646,
              pts_avg: 116.341,
              reb_avg: 40.988,
              ast_avg: 25.878,
              fg3m_avg: 11.829,
              plus_minus_avg: 1.751,
            },
          ],
          by_season: [
            {
              season: "2025-26",
              games: 82,
              wins: 53,
              losses: 29,
              win_pct: 0.646,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "The Los Angeles Lakers are 53-29 this season, a 64.6% win rate.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Team record" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "W-L" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Win %" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("columnheader", { name: "3PM" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Record Detail")).toBeInTheDocument();
    expect(screen.queryByText("By Season Detail")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Show raw table" }),
    ).not.toBeInTheDocument();
  });

  it("preserves playoff-team opponent groups in team record heroes and tables", () => {
    const data = makeResponse({
      query: "What is the Celtics' record against playoff teams?",
      route: "team_record",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          query_text: "What is the Celtics' record against playoff teams?",
          route: "team_record",
          season: "2024-25",
          season_type: "Playoffs",
          team_context: {
            team_id: 1610612738,
            team_abbr: "BOS",
            team_name: "Celtics",
          },
          applied_filters: [
            {
              label: "Opponent quality",
              value: "playoff teams",
              kind: "quality",
            },
          ],
        },
        notes: [],
        caveats: ["record filtered to games vs 20 opponents (ATL, BOS, CHI, ...)"],
        sections: {
          summary: [
            {
              team_name: "Boston Celtics",
              season_start: "2024-25",
              season_end: "2024-25",
              season_type: "Playoffs",
              games: 11,
              wins: 6,
              losses: 5,
              win_pct: 0.545,
              pts_avg: 105.727,
              reb_avg: 43.091,
              ast_avg: 20,
              fg3m_avg: 14.182,
              plus_minus_avg: 5.545,
            },
          ],
        },
        current_through: "2025-06-22",
      },
      caveats: ["record filtered to games vs 20 opponents (ATL, BOS, CHI, ...)"],
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "The Boston Celtics are 6-5 against 2024-25 playoff teams, a 54.5% win rate.",
      ),
    ).toBeInTheDocument();
    const table = screen.getByRole("table", { name: "Team record" });
    expect(
      within(table).getByRole("columnheader", { name: "Opponent Group" }),
    ).toBeInTheDocument();
    expect(
      within(table).getByRole("columnheader", { name: "PPG" }),
    ).toBeInTheDocument();
    expect(
      within(table).getByRole("columnheader", { name: "+/-" }),
    ).toBeInTheDocument();
    expect(
      within(table).queryByRole("columnheader", { name: "REB" }),
    ).not.toBeInTheDocument();
    expect(
      within(table).queryByRole("columnheader", { name: "AST" }),
    ).not.toBeInTheDocument();
    expect(
      within(table).queryByRole("columnheader", { name: "3PM" }),
    ).not.toBeInTheDocument();
    expect(within(table).getByText("Playoff Teams")).toBeInTheDocument();
    expect(
      within(table).queryByRole("columnheader", { name: "Season Type" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(/in the 2024-25 playoffs/i),
    ).not.toBeInTheDocument();
  });

  it("renders team records without a player as team-first results with game logs", () => {
    const data = makeResponse({
      query: "What is the Knicks' record when Jalen Brunson doesn't play?",
      route: "team_record",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          query_text: "What is the Knicks' record when Jalen Brunson doesn't play?",
          route: "team_record",
          season: "2025-26",
          season_type: "Regular Season",
          without_player: "Jalen Brunson",
          team_context: {
            team_id: 1610612752,
            team_abbr: "NYK",
            team_name: "Knicks",
          },
        },
        notes: [],
        caveats: ["record filtered to games without Jalen Brunson"],
        sections: {
          summary: [
            {
              team_name: "New York Knicks",
              season_start: "2025-26",
              season_end: "2025-26",
              season_type: "Regular Season",
              games: 8,
              wins: 3,
              losses: 5,
              win_pct: 0.375,
              pts_avg: 116.375,
              reb_avg: 47.375,
              ast_avg: 27.75,
              fg3m_avg: 14.125,
              plus_minus_avg: -0.25,
            },
          ],
          game_log: [
            {
              game_id: 1,
              game_date: "2026-01-01",
              team_abbr: "NYK",
              team_name: "Knicks",
              opponent_team_abbr: "BOS",
              opponent_team_name: "Celtics",
              wl: "L",
              pts: 112,
              opponent_pts: 118,
              reb: 44,
              ast: 24,
              fg3m: 13,
              plus_minus: -6,
            },
          ],
        },
        current_through: "2026-04-12",
      },
      caveats: ["record filtered to games without Jalen Brunson"],
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "The New York Knicks are 3-5 in 8 games without Jalen Brunson in the 2025-26 regular season, a 37.5% win rate.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Jalen Brunson has averaged/)).not.toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Team record" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Game log" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Opp PTS" })).toBeInTheDocument();
  });

  it("renders multi-season team record by-season tables in the body", () => {
    const data = makeResponse({
      query: "Lakers record since 2024",
      route: "team_record",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          query_text: "Lakers record since 2024",
          route: "team_record",
          scope_kind: "season_range",
          start_season: "2024-25",
          end_season: "2025-26",
          season_type: "Regular Season",
          team_context: {
            team_id: 1610612747,
            team_abbr: "LAL",
            team_name: "Lakers",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              team_name: "Los Angeles Lakers",
              season_start: "2024-25",
              season_end: "2025-26",
              season_type: "Regular Season",
              games: 164,
              wins: 100,
              losses: 64,
              win_pct: 0.61,
            },
          ],
          by_season: [
            {
              season: "2024-25",
              games: 82,
              wins: 47,
              losses: 35,
              win_pct: 0.573,
              pts_avg: 113.4,
            },
            {
              season: "2025-26",
              games: 82,
              wins: 53,
              losses: 29,
              win_pct: 0.646,
              pts_avg: 116.3,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    const table = screen.getByRole("table", { name: "Team record by season" });
    expect(table).toBeInTheDocument();
    expect(
      within(table).getByRole("columnheader", { name: "W-L" }),
    ).toBeInTheDocument();
    const rows = within(table).getAllByRole("row");
    expect(within(rows[1]).getByText("2025-26")).toBeInTheDocument();
    expect(within(rows[2]).getByText("2024-25")).toBeInTheDocument();
  });

  it("renders team records grouped by decade as a dedicated decade table", () => {
    const data = makeResponse({
      query: "Lakers by decade",
      route: "record_by_decade",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          query_text: "Lakers by decade",
          route: "record_by_decade",
          season_type: "Regular Season",
          team_context: {
            team_id: 1610612747,
            team_abbr: "LAL",
            team_name: "Lakers",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              team_name: "Los Angeles Lakers",
              season_start: "1996-97",
              season_end: "2025-26",
              season_type: "Regular Season",
              games: 2391,
              wins: 1361,
              losses: 1030,
              win_pct: 0.569,
            },
          ],
          by_season: [
            {
              decade: "1990s",
              games: 296,
              wins: 215,
              losses: 81,
              seasons_appeared: 4,
              win_pct: 0.726,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "The Los Angeles Lakers are 1,361-1,030 (56.9%) in the regular season from 1996-97 to 2025-26.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Record by decade" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Decade" }),
    ).toBeInTheDocument();
    expect(screen.getByText("1990s")).toBeInTheDocument();
    expect(screen.getByText("72.6%")).toBeInTheDocument();
    expect(screen.getByText("Record Detail")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Show record details" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("By Season")).not.toBeInTheDocument();
  });

  it("renders record-by-decade leaderboards with decade and requested metric highlighted", () => {
    const data = makeResponse({
      query: "most wins by decade since 1980",
      route: "record_by_decade_leaderboard",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          query_text: "most wins by decade since 1980",
          route: "record_by_decade_leaderboard",
          start_season: "1980-81",
          end_season: "2025-26",
          season_type: "Regular Season",
          stat: "wins",
        },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              team_name: "Utah Jazz",
              team_abbr: "UTA",
              decade: "1990s",
              games_played: 296,
              wins: 218,
              losses: 78,
              win_pct: 0.736,
              season_type: "Regular Season",
              seasons: "1980-81 to 2025-26",
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "The Utah Jazz won the most games in the 1990s since 1980, with 218 wins.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Record by decade leaderboard" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Wins" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Decade" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "W-L" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Show raw table" }),
    ).not.toBeInTheDocument();
  });

  it("renders matchup-by-decade results with team identities and decade comparison rows", () => {
    const data = makeResponse({
      query: "Lakers vs Celtics by decade",
      route: "matchup_by_decade",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: {
          query_text: "Lakers vs Celtics by decade",
          route: "matchup_by_decade",
          season_type: "Regular Season",
          teams_context: [
            {
              team_id: 1610612747,
              team_abbr: "LAL",
              team_name: "Lakers",
            },
            {
              team_id: 1610612738,
              team_abbr: "BOS",
              team_name: "Celtics",
            },
          ],
        },
        notes: [],
        caveats: [
          "matchup history: LAL vs BOS by decade",
          "across 1996-97 to 2025-26",
        ],
        sections: {
          summary: [
            {
              team_name: "Los Angeles Lakers",
              games: 58,
              wins: 31,
              losses: 27,
              win_pct: 0.534,
            },
            {
              team_name: "Boston Celtics",
              games: 58,
              wins: 27,
              losses: 31,
              win_pct: 0.466,
            },
          ],
          comparison: [
            {
              decade: "1990s",
              LAL_wins: 4,
              LAL_losses: 2,
              LAL_win_pct: 0.667,
              BOS_wins: 2,
              BOS_losses: 4,
              BOS_win_pct: 0.333,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "The Los Angeles Lakers lead the Boston Celtics 31-27 in regular-season games from 1996-97 through 2025-26.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Matchup by decade" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Games" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "LAL W-L" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "BOS W-L" }),
    ).toBeInTheDocument();
    expect(screen.getByText("4-2")).toBeInTheDocument();
    expect(screen.getByText("2-4")).toBeInTheDocument();
    expect(screen.getByText("Matchup Summary Detail")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Show matchup summary" }),
    ).toBeInTheDocument();
  });

  it("renders league-wide rolling stretch leaderboards with the rolling stretch pattern", () => {
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
          total_count: 24,
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
              games_played: 3,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Best 3-game scoring stretch this season: Luka Doncic averaged 45.3 PPG from Mar 16 to Mar 19.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "PPG" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Season" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Rolling stretch leaderboard" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Showing top 1 of 24")).toBeInTheDocument();
    expect(
      screen.queryByRole("table", { name: "Leaderboard" }),
    ).not.toBeInTheDocument();
  });

  it("renders player-oriented rolling stretch leaderboards with one window per player", () => {
    const data = makeResponse({
      query: "Which players have the hottest 3-game scoring stretch this year?",
      route: "player_stretch_leaderboard",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          query_text:
            "Which players have the hottest 3-game scoring stretch this year?",
          route: "player_stretch_leaderboard",
          season: "2025-26",
          season_type: "Regular Season",
          window_size: 3,
          stretch_metric: "pts",
          stretch_display_mode: "players",
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
              window_end_season: "2025-26",
              stretch_value: 45.333,
            },
            {
              rank: 2,
              player_name: "Luka Doncic",
              player_id: 1629029,
              team_abbr: "LAL",
              window_size: 3,
              stretch_metric: "pts",
              window_start_date: "2026-03-18",
              window_end_date: "2026-03-21",
              window_end_season: "2025-26",
              stretch_value: 44.667,
            },
            {
              rank: 3,
              player_name: "Devin Booker",
              player_id: 1626164,
              team_abbr: "PHX",
              window_size: 3,
              stretch_metric: "pts",
              window_start_date: "2026-02-10",
              window_end_date: "2026-02-14",
              window_end_season: "2025-26",
              stretch_value: 41,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Luka Doncic had the hottest 3-game scoring stretch this season, averaging 45.3 PPG from Mar 16 to Mar 19.",
      ),
    ).toBeInTheDocument();
    const table = screen.getByRole("table", {
      name: "Rolling stretch leaderboard",
    });
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(3);
    expect(within(rows[1]).getByText("Luka Doncic")).toBeInTheDocument();
    expect(within(rows[2]).getByText("Devin Booker")).toBeInTheDocument();
  });

  it("renders named-player rolling stretches with top windows and optional game log", () => {
    const data = makeResponse({
      query: "Booker hottest 4-game scoring stretch",
      route: "player_stretch_leaderboard",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          query_text: "Booker hottest 4-game scoring stretch",
          route: "player_stretch_leaderboard",
          season: "2025-26",
          season_type: "Regular Season",
          window_size: 4,
          stretch_metric: "pts",
          player: "Devin Booker",
          player_context: {
            player_id: 1626164,
            player_name: "Devin Booker",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              player_name: "Devin Booker",
              player_id: 1626164,
              team_abbr: "PHX",
              window_size: 4,
              stretch_metric: "pts",
              window_start_date: "2026-02-10",
              window_end_date: "2026-02-17",
              window_start_season: "2025-26",
              games_in_window: 4,
              window_end_season: "2025-26",
              stretch_value: 39.75,
            },
          ],
          best_window_game_log: [
            {
              game_id: 10,
              game_date: "2026-02-10",
              player_name: "Devin Booker",
              player_id: 1626164,
              team_abbr: "PHX",
              opponent_team_abbr: "DAL",
              wl: "W",
              pts: 41,
              reb: 5,
              ast: 8,
            },
            {
              game_id: 11,
              game_date: "2026-02-12",
              player_name: "Devin Booker",
              player_id: 1626164,
              team_abbr: "PHX",
              opponent_team_abbr: "DEN",
              wl: "L",
              pts: 38,
              reb: 4,
              ast: 9,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Devin Booker's best 4-game scoring stretch in the 2025-26 regular season: averaging 39.8 PPG from Feb 10 to Feb 17.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Top Windows")).toBeInTheDocument();
    expect(screen.getByText("Best Window Games")).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Player rolling stretch windows" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Season" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Best stretch game log" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("table", { name: "Leaderboard" }),
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
    expect(
      screen.getByRole("columnheader", { name: "Round" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Seasons" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Playoff leaderboard rankings"),
    ).not.toBeInTheDocument();
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
    expect(
      screen.queryByRole("columnheader", { name: "Player" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "PTS" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Mar 22")).toBeInTheDocument();
    expect(screen.queryByText("Player Game Detail")).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText("Player game cards"),
    ).not.toBeInTheDocument();
  });

  it("uses count_phrase as the primary finder headline when count metadata is present", () => {
    const data = makeResponse({
      query: "how many Jokic 30 point games this season",
      route: "player_game_finder",
      result: {
        query_class: "finder",
        result_status: "ok",
        metadata: {
          query_text: "how many Jokic 30 point games this season",
          route: "player_game_finder",
          season: "2025-26",
          season_type: "Regular Season",
          stat: "pts",
          min_value: 30.0001,
          primary_count: 2,
          count_phrase:
            "Nikola Jokic has had 2 games with at least 30 points this season.",
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
              game_id: 1,
              game_date: "2026-03-22",
              player_id: 203999,
              player_name: "Nikola Jokic",
              team_abbr: "DEN",
              opponent_team_abbr: "POR",
              is_home: 1,
              wl: "W",
              pts: 32,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Nikola Jokic has had 2 games with at least 30 points this season.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Game log" })).toBeInTheDocument();
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
              fgm: 41,
              fga: 88,
              fg3m: 14,
              fg3a: 36,
              ftm: 17,
              fta: 20,
              tov: 12,
              plus_minus: 5,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByRole("columnheader", { name: "Team" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("columnheader", { name: "Player" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Score" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Opp PTS" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Margin" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "3PM" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "FG" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "FT" }),
    ).toBeInTheDocument();
    expect(screen.getByText("113-108")).toBeInTheDocument();
    expect(screen.getByText("+5")).toBeInTheDocument();
    expect(screen.queryByText("Game Detail")).not.toBeInTheDocument();
  });

  it("renders team count game logs with defensive condition columns", () => {
    const data = makeResponse({
      query: "How often have the Lakers held opponents under 100 points this year?",
      route: "game_finder",
      result: {
        query_class: "count",
        result_status: "ok",
        metadata: {
          query_text:
            "How often have the Lakers held opponents under 100 points this year?",
          route: "game_finder",
          season: "2025-26",
          season_type: "Regular Season",
          stat: "opponent_pts",
          max_value: 99.9999,
          primary_count: 2,
          count_phrase:
            "The Lakers have held opponents under 100 points 2 times this season, going 1-1.",
          team_context: {
            team_id: 1610612747,
            team_abbr: "LAL",
            team_name: "Lakers",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          finder: [
            {
              game_id: 1,
              game_date: "2026-01-10",
              team_abbr: "LAL",
              opponent_team_abbr: "UTA",
              is_home: 1,
              wl: "W",
              pts: 108,
              opponent_pts: 95,
              reb: 44,
              ast: 25,
              fg3m: 12,
              tov: 10,
              plus_minus: 13,
            },
            {
              game_id: 2,
              game_date: "2026-02-12",
              team_abbr: "LAL",
              opponent_team_abbr: "DAL",
              is_away: 1,
              wl: "L",
              pts: 91,
              opponent_pts: 98,
              reb: 39,
              ast: 20,
              fg3m: 9,
              tov: 14,
              plus_minus: -7,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "The Lakers have held opponents under 100 points 2 times this season, going 1-1.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Opp PTS" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Margin" }),
    ).toBeInTheDocument();
    expect(screen.getByText("95")).toBeInTheDocument();
    expect(screen.getByText("-7")).toBeInTheDocument();
  });

  it("caps long product game logs and can expand/collapse them", () => {
    const data = makeResponse({
      query: "show Jokic triple doubles this season",
      route: "player_game_finder",
      result: {
        query_class: "finder",
        result_status: "ok",
        metadata: {
          query_text: "show Jokic triple doubles this season",
          route: "player_game_finder",
          season: "2025-26",
          season_type: "Regular Season",
          occurrence_event: { special_event: "triple_double" },
          player_context: {
            player_id: 203999,
            player_name: "Nikola Jokic",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          finder: Array.from({ length: 13 }, (_, index) => ({
            game_id: index + 1,
            game_date: `2026-03-${String(index + 1).padStart(2, "0")}`,
            player_id: 203999,
            player_name: "Nikola Jokic",
            team_abbr: "DEN",
            opponent_team_abbr: "POR",
            wl: "W",
            pts: 20 + index,
            reb: 10,
            ast: 10,
          })),
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    const table = screen.getByRole("table", { name: "Game log" });
    expect(within(table).getAllByRole("row")).toHaveLength(13);

    fireEvent.click(screen.getByRole("button", { name: "Show all 13 games" }));
    expect(within(table).getAllByRole("row")).toHaveLength(14);

    fireEvent.click(
      screen.getByRole("button", { name: "Show first 12 games" }),
    );
    expect(within(table).getAllByRole("row")).toHaveLength(13);
  });

  it("caps fixture-sized product game logs with total-row labels", () => {
    const gameRows = (count: number) =>
      Array.from({ length: count }, (_, index) => ({
        game_id: index + 1,
        game_date: `2026-03-${String(index + 1).padStart(2, "0")}`,
        player_id: 203999,
        player_name: "Nikola Jokic",
        team_abbr: "DEN",
        opponent_team_abbr: "POR",
        wl: "W",
        pts: 20 + index,
        reb: 10,
        ast: 10,
      }));

    const fixture71 = makeResponse({
      query: "Jokic game log",
      route: "player_game_finder",
      result: {
        query_class: "finder",
        result_status: "ok",
        metadata: {
          route: "player_game_finder",
          player_context: {
            player_id: 203999,
            player_name: "Nikola Jokic",
          },
        },
        notes: [],
        caveats: [],
        sections: { finder: gameRows(34) },
        current_through: "2026-04-12",
      },
    });

    const firstRender = render(<ResultRenderer data={fixture71} />);
    let table = screen.getByRole("table", { name: "Game log" });
    expect(within(table).getAllByRole("row")).toHaveLength(13);
    expect(
      screen.getByRole("button", { name: "Show all 34 games" }),
    ).toBeInTheDocument();
    firstRender.unmount();

    const fixture51 = makeResponse({
      query: "team game summary",
      route: "game_summary",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          route: "game_summary",
          team_context: {
            team_id: 1610612756,
            team_abbr: "PHX",
            team_name: "Suns",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [{ team_name: "Suns", games: 18, wins: 8, losses: 10 }],
          game_log: Array.from({ length: 18 }, (_, index) => ({
            game_id: index + 1,
            game_date: `2026-02-${String(index + 1).padStart(2, "0")}`,
            team_abbr: "PHX",
            team_name: "Suns",
            opponent_team_abbr: "LAC",
            wl: index % 2 === 0 ? "W" : "L",
            pts: 100 + index,
            opponent_pts: 98 + index,
          })),
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={fixture51} />);
    table = screen.getByRole("table", { name: "Game log" });
    expect(within(table).getAllByRole("row")).toHaveLength(15);
    expect(
      screen.getByRole("button", { name: "Show all 18 games" }),
    ).toBeInTheDocument();
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
    expect(screen.queryByText("Game Detail")).not.toBeInTheDocument();
    expect(screen.queryByText("Summary Detail")).not.toBeInTheDocument();
    expect(screen.queryByText("By Season Detail")).not.toBeInTheDocument();
    expect(screen.getByText("Top Performers Detail")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Show top performer details" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Top player performers")).not.toBeInTheDocument();
  });

  it("renders filtered team summaries with a record strip and game-log table", () => {
    const data = makeResponse({
      query: "How do the Suns perform when Devin Booker didn't play?",
      route: "game_summary",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          query_text: "How do the Suns perform when Devin Booker didn't play?",
          route: "game_summary",
          season: "2025-26",
          season_type: "Regular Season",
          without_player: "Devin Booker",
          answer_phrase:
            "The Suns are 8-10 in 18 games without Devin Booker, averaging 103.8 PPG.",
          team_context: {
            team_id: 1610612756,
            team_abbr: "PHX",
            team_name: "Suns",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              team_name: "Suns",
              games: 18,
              wins: 8,
              losses: 10,
              pts_avg: 103.8,
              reb_avg: 43.1,
              ast_avg: 21.7,
            },
          ],
          by_season: [{ season: "2025-26", games: 18, pts_avg: 103.8 }],
          game_log: [
            {
              game_id: 1,
              game_date: "2026-01-03",
              team_abbr: "PHX",
              team_name: "Suns",
              opponent_team_abbr: "LAC",
              opponent_team_name: "Clippers",
              is_home: 1,
              wl: "W",
              pts: 105,
              opponent_pts: 99,
              reb: 45,
              ast: 22,
              fg3m: 11,
              tov: 12,
              plus_minus: 6,
            },
            {
              game_id: 2,
              game_date: "2026-02-04",
              team_abbr: "PHX",
              team_name: "Suns",
              opponent_team_abbr: "DEN",
              opponent_team_name: "Nuggets",
              is_away: 1,
              wl: "L",
              pts: 98,
              opponent_pts: 111,
              reb: 41,
              ast: 19,
              fg3m: 9,
              tov: 15,
              plus_minus: -13,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "The Suns are 8-10 in 18 games without Devin Booker, averaging 103.8 PPG.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("GP")).toBeInTheDocument();
    expect(screen.getByText("Record")).toBeInTheDocument();
    expect(screen.getByText("8-10")).toBeInTheDocument();
    expect(screen.getByText("PPG")).toBeInTheDocument();
    expect(screen.getByText("18")).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Game log" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Opp PTS" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Margin" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Summary Detail")).not.toBeInTheDocument();
    expect(screen.queryByText("By Season Detail")).not.toBeInTheDocument();
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
      screen.getByText(
        "Nikola Jokic's home/away split for 2025-26 Regular Season.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Split buckets" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "PTS" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "+/-" }),
    ).toBeInTheDocument();
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
    expect(screen.getByText("Home +8.0 PPG")).toBeInTheDocument();
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
      screen.getByText(
        "LeBron James' on/off split for 2025-26 Regular Season.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Net" }),
    ).toBeInTheDocument();
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
      screen.getByText(
        "Nikola Jokic is on a 6-game streak of scoring 25+ points, ongoing.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Streaks" })).toBeInTheDocument();
    expect(
      screen.queryByRole("columnheader", { name: "Player" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "PTS" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("columnheader", { name: "TS%" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("Full Streak Detail")).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Show additional columns" }),
    );
    expect(
      screen.getByRole("columnheader", { name: "Ts Pct Avg" }),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Streak results")).not.toBeInTheDocument();
  });

  it("preserves minimum streak thresholds and hides all-completed status columns", () => {
    const data = makeResponse({
      query: "Jokic 5 straight games with 20+ points",
      route: "player_streak_finder",
      result: {
        query_class: "streak",
        result_status: "ok",
        metadata: {
          query_text: "Jokic 5 straight games with 20+ points",
          route: "player_streak_finder",
          min_streak_length: 5,
          player_context: {
            player_id: 203999,
            player_name: "Nikola Jokić",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          streak: [
            {
              player_name: "Nikola Jokić",
              player_id: 203999,
              condition: "pts>=20",
              streak_length: 18,
              games: 18,
              start_date: "2024-10-26",
              end_date: "2024-12-08",
              is_active: 0,
              wins: 11,
              losses: 7,
              pts_avg: 33.167,
              reb_avg: 13.667,
              ast_avg: 10,
            },
            {
              player_name: "Nikola Jokić",
              player_id: 203999,
              condition: "pts>=20",
              streak_length: 17,
              games: 17,
              start_date: "2025-02-27",
              end_date: "2025-04-11",
              is_active: 0,
              wins: 9,
              losses: 8,
              pts_avg: 31.529,
              reb_avg: 13.471,
              ast_avg: 9.941,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Nikola Jokić has 2 streaks of 5+ straight games with 20+ points. The longest was 18 games, from Oct 26 to Dec 8, 2024.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("columnheader", { name: "Status" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Completed")).not.toBeInTheDocument();
    const table = screen.getByRole("table", { name: "Streaks" });
    expect(
      within(table).getByRole("columnheader", { name: "PTS" }),
    ).toBeInTheDocument();
    expect(
      within(table).queryByRole("columnheader", { name: "REB" }),
    ).not.toBeInTheDocument();
    expect(
      within(table).queryByRole("columnheader", { name: "AST" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Full Streak Detail")).toBeInTheDocument();
  });

  it("renders team streaks with team identity and hides repetitive completed status", () => {
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
      screen.getByText(
        "The Los Angeles Lakers won 4 straight games from Feb 1 to Feb 8, 2026.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("Completed")).not.toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "PTS" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("columnheader", { name: "+/-" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("4-0")).toBeInTheDocument();
  });

  it("promotes an active streak row into the headline even when it is not first", () => {
    const data = makeResponse({
      query: "Curry made three streak",
      route: "player_streak_finder",
      result: {
        query_class: "streak",
        result_status: "ok",
        metadata: {
          query_text: "Curry made three streak",
          route: "player_streak_finder",
          player_context: {
            player_id: 201939,
            player_name: "Stephen Curry",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          streak: [
            {
              player_name: "Stephen Curry",
              player_id: 201939,
              condition: "made_three",
              streak_length: 268,
              games: 268,
              is_active: false,
              start_date: "2018-12-01",
              end_date: "2023-12-17",
            },
            {
              player_name: "Stephen Curry",
              player_id: 201939,
              condition: "made_three",
              streak_length: 47,
              games: 47,
              is_active: true,
              start_date: "2025-01-01",
              end_date: "2026-04-12",
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Stephen Curry is on a 47-game streak of making at least one three, ongoing.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Streaks" })).toBeInTheDocument();
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
              season: "1999-00",
              wins: 6,
              losses: 5,
              deepest_round: "Unknown Round",
              result: "Lost",
              opponent_team_abbr: "POR",
            },
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
    expect(history.textContent).toContain(
      "From 2019-20 through 2024-25, the Los Angeles Lakers made the playoffs 5 times and went 52-32.",
    );
    expect(
      within(history).getByText("made the playoffs", { exact: false }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Playoff season breakdown" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Round Reached" }),
    ).toBeInTheDocument();
    expect(screen.getByText("First Round")).toBeInTheDocument();
    expect(screen.queryByText("Unknown Round")).not.toBeInTheDocument();
    expect(screen.getByText("Round unavailable")).toBeInTheDocument();
    expect(screen.getByText("1-4")).toBeInTheDocument();
    expect(screen.getByText("Postseason Summary Detail")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Show postseason summary" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Season Breakdown Detail")).not.toBeInTheDocument();
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
    expect(roundRecord.textContent).toContain(
      "The Boston Celtics have the best Finals record from 1980-81 to 2024-25, going 28-14, a 66.7% win rate, across 42 games.",
    );
    expect(
      within(roundRecord).getByText("Finals record", { exact: false }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Playoff round records" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Win Pct" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("66.7%").length).toBeGreaterThan(0);
    expect(screen.getAllByText("28-14").length).toBeGreaterThan(0);
    expect(screen.queryByText("Playoff Round Detail")).not.toBeInTheDocument();
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
              season: "1999-00",
              round: "Unknown Round",
              winner_team_name: "Miami Heat",
              series_result: "MIA won 3-2",
              BOS_wins: 2,
              BOS_losses: 3,
              MIA_wins: 3,
              MIA_losses: 2,
            },
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
      screen.getByText(
        "The Boston Celtics lead the Miami Heat 4-3 in playoff games. The Miami Heat lead 2-0 in playoff series.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Playoff series" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "BOS" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "MIA" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Winner" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Series Result" }),
    ).toBeInTheDocument();
    expect(screen.getByText("MIA won 4-3")).toBeInTheDocument();
    expect(screen.queryByText("Unknown Round")).not.toBeInTheDocument();
    expect(screen.getByText("Round unavailable")).toBeInTheDocument();
    expect(screen.getByText("3-4")).toBeInTheDocument();
    expect(screen.getAllByText("4-3").length).toBeGreaterThan(0);
    expect(screen.queryByText("Series Detail")).not.toBeInTheDocument();
  });

  it("renders player comparisons with subject panels and metric edges", () => {
    const data = makeResponse({
      query: "Jokic vs Embiid this season",
      route: "player_compare",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: {
          query_text: "Jokic vs Embiid this season",
          route: "player_compare",
          season: "2025-26",
          season_type: "Regular Season",
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
              team_abbr: "DEN",
              games: 72,
              wins: 51,
              losses: 21,
              win_pct: 0.708,
              pts_avg: 26.4,
              reb_avg: 12.1,
              ast_avg: 9.3,
            },
            {
              player_name: "Joel Embiid",
              team_abbr: "PHI",
              games: 68,
              wins: 44,
              losses: 24,
              win_pct: 0.647,
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
            {
              metric: "ast_avg",
              "Nikola Jokic": 9.3,
              "Joel Embiid": 5.7,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    const compared = screen.getByLabelText("Compared players");
    expect(screen.getByLabelText("Comparison result")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Nikola Jokic has 51 wins to Joel Embiid's 44 in the 2025-26 regular season.",
      ),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Nikola Jokic").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Joel Embiid").length).toBeGreaterThan(0);
    expect(within(compared).getByText("51-21")).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Comparison metrics" }),
    ).toBeInTheDocument();
    expect(screen.getByText("PTS Avg")).toBeInTheDocument();
    expect(screen.getAllByText("Joel Embiid +3.7 PTS").length).toBeGreaterThan(
      0,
    );
    expect(screen.getByText("Nikola Jokic +3.6 AST")).toBeInTheDocument();
    expect(screen.queryByText("Player Summary Detail")).not.toBeInTheDocument();
    expect(screen.queryByText("Full Metric Detail")).not.toBeInTheDocument();
  });

  it("renders recent-form comparisons with compact primary metrics and safe differences", () => {
    const data = makeResponse({
      query: "Jokic vs Embiid recent form",
      route: "player_compare",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: {
          query_text: "Jokic vs Embiid recent form",
          route: "player_compare",
          season: "2025-26",
          season_type: "Regular Season",
          applied_filters: [
            { label: "Last N games", value: "10", kind: "window" },
          ],
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              player_name: "Nikola Jokić",
              games: 10,
              wins: 10,
              losses: 0,
              win_pct: 1,
              minutes_avg: 35.2,
              pts_avg: 25.3,
              reb_avg: 14.5,
              ast_avg: 11.9,
              stl_avg: 1.2,
              blk_avg: 0.7,
              tov_avg: 3,
              plus_minus_avg: 11,
              efg_pct_avg: 0.589,
              ts_pct_avg: 0.637,
            },
            {
              player_name: "Joel Embiid",
              games: 10,
              wins: 7,
              losses: 3,
              win_pct: 0.7,
              minutes_avg: 33.2,
              pts_avg: 28.8,
              reb_avg: 8.2,
              ast_avg: 4.2,
              stl_avg: 0.3,
              blk_avg: 1.5,
              tov_avg: 2.3,
              plus_minus_avg: 2.6,
              efg_pct_avg: 0.545,
              ts_pct_avg: 0.623,
            },
          ],
          comparison: [
            { metric: "games", "Nikola Jokić": 10, "Joel Embiid": 10 },
            { metric: "wins", "Nikola Jokić": 10, "Joel Embiid": 7 },
            { metric: "losses", "Nikola Jokić": 0, "Joel Embiid": 3 },
            { metric: "win_pct", "Nikola Jokić": 1, "Joel Embiid": 0.7 },
            { metric: "minutes_avg", "Nikola Jokić": 35.2, "Joel Embiid": 33.2 },
            { metric: "pts_avg", "Nikola Jokić": 25.3, "Joel Embiid": 28.8 },
            { metric: "reb_avg", "Nikola Jokić": 14.5, "Joel Embiid": 8.2 },
            { metric: "ast_avg", "Nikola Jokić": 11.9, "Joel Embiid": 4.2 },
            { metric: "stl_avg", "Nikola Jokić": 1.2, "Joel Embiid": 0.3 },
            { metric: "blk_avg", "Nikola Jokić": 0.7, "Joel Embiid": 1.5 },
            { metric: "tov_avg", "Nikola Jokić": 3, "Joel Embiid": 2.3 },
            { metric: "plus_minus_avg", "Nikola Jokić": 11, "Joel Embiid": 2.6 },
            { metric: "efg_pct_avg", "Nikola Jokić": 0.589, "Joel Embiid": 0.545 },
            { metric: "ts_pct_avg", "Nikola Jokić": 0.637, "Joel Embiid": 0.623 },
            { metric: "usg_pct_avg", "Nikola Jokić": 28.2, "Joel Embiid": 33.1 },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Over their last 10 games, Nikola Jokić has averaged 25.3 points, 14.5 rebounds and 11.9 assists, while Joel Embiid has averaged 28.8 points, 8.2 rebounds and 4.2 assists.",
      ),
    ).toBeInTheDocument();
    const table = screen.getByRole("table", { name: "Comparison metrics" });
    expect(within(table).getByText("Record")).toBeInTheDocument();
    expect(within(table).queryByText("USG% Avg")).not.toBeInTheDocument();
    expect(screen.getByText("Difference 2.0 MIN")).toBeInTheDocument();
    expect(screen.queryByText("Nikola Jokić +3 losses")).not.toBeInTheDocument();
    const showMore = screen.getByRole("button", { name: "Show more metrics" });
    fireEvent.click(showMore);
    expect(screen.getByText("USG% Avg")).toBeInTheDocument();
    expect(screen.getByText("Nikola Jokić 3 fewer losses")).toBeInTheDocument();
    expect(
      screen.getByText("Nikola Jokić +30.0 percentage points"),
    ).toBeInTheDocument();
  });

  it("renders team comparisons with team identity and metric deltas", () => {
    const data = makeResponse({
      query: "Celtics vs Lakers",
      route: "team_compare",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: {
          query_text: "Celtics vs Lakers",
          route: "team_compare",
          season: "2024-25",
          season_type: "Regular Season",
          teams_context: [
            {
              team_id: 1610612738,
              team_abbr: "BOS",
              team_name: "Boston Celtics",
            },
            {
              team_id: 1610612747,
              team_abbr: "LAL",
              team_name: "Los Angeles Lakers",
            },
          ],
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              team_name: "Boston Celtics",
              games: 82,
              wins: 60,
              losses: 22,
              win_pct: 0.732,
              pts_avg: 120.6,
            },
            {
              team_name: "Los Angeles Lakers",
              games: 82,
              wins: 47,
              losses: 35,
              win_pct: 0.573,
              pts_avg: 116.1,
            },
          ],
          comparison: [
            { metric: "wins", BOS: 60, LAL: 47 },
            { metric: "pts_avg", BOS: 120.6, LAL: 116.1 },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    const compared = screen.getByLabelText("Compared teams");
    expect(
      within(compared).getByLabelText("Boston Celtics (BOS)"),
    ).toBeInTheDocument();
    expect(
      within(compared).getByLabelText("Los Angeles Lakers (LAL)"),
    ).toBeInTheDocument();
    expect(within(compared).getByText("60-22")).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "BOS" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "LAL" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Boston Celtics +13 wins")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Show more metrics" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Team Summary Detail")).not.toBeInTheDocument();
    expect(screen.queryByText("Full Metric Detail")).not.toBeInTheDocument();
  });

  it("renders matchup records as head-to-head comparisons", () => {
    const data = makeResponse({
      query: "Lakers vs Celtics head-to-head",
      route: "team_matchup_record",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: {
          query_text: "Lakers vs Celtics head-to-head",
          route: "team_matchup_record",
          teams_context: [
            {
              team_id: 1610612747,
              team_abbr: "LAL",
              team_name: "Los Angeles Lakers",
            },
            {
              team_id: 1610612738,
              team_abbr: "BOS",
              team_name: "Boston Celtics",
            },
          ],
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              team_name: "Los Angeles Lakers",
              games: 4,
              wins: 1,
              losses: 3,
              pts_avg: 109.8,
            },
            {
              team_name: "Boston Celtics",
              games: 4,
              wins: 3,
              losses: 1,
              pts_avg: 118.2,
            },
          ],
          comparison: [
            {
              metric: "wins",
              "Los Angeles Lakers": 1,
              "Boston Celtics": 3,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    const participants = screen.getByLabelText("Head-to-head participants");
    expect(
      screen.getByText(/Boston Celtics lead Los Angeles Lakers/),
    ).toBeInTheDocument();
    expect(within(participants).getByText("1-3")).toBeInTheDocument();
    expect(within(participants).getByText("3-1")).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Comparison metrics" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Participant Detail")).not.toBeInTheDocument();
    expect(screen.queryByText("Metric Detail")).not.toBeInTheDocument();
  });
});
