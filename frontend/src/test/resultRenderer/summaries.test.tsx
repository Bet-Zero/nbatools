import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResultRenderer from "../../components/results/ResultRenderer";
import { makeResponse } from "./helpers";

describe("ResultRenderer summary patterns", () => {

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


  it("renders broad player summaries with compact key stat cards", () => {
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
              wins: 24,
              losses: 19,
              season: "2025-26",
              season_type: "Regular Season",
              team_abbr: "GSW",
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
    expect(screen.getByLabelText("Season summary")).toHaveTextContent("Games");
    expect(screen.getByLabelText("Season summary")).toHaveTextContent("43");
    expect(screen.getByLabelText("Season summary")).toHaveTextContent("Record");
    expect(screen.getByLabelText("Season summary")).toHaveTextContent("24-19");
    expect(screen.getByLabelText("Season summary")).toHaveTextContent("PPG");
    expect(screen.getByLabelText("Season summary")).toHaveTextContent("26.6");
    expect(screen.getByLabelText("Season summary")).toHaveTextContent("RPG");
    expect(screen.getByLabelText("Season summary")).toHaveTextContent("3.6");
    expect(screen.getByLabelText("Season summary")).toHaveTextContent("APG");
    expect(screen.getByLabelText("Season summary")).toHaveTextContent("4.7");
    expect(
      screen.queryByRole("table", { name: "Game log" }),
    ).not.toBeInTheDocument();
  });


  it("uses filtered team record fields for record-when player condition summaries", () => {
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
          applied_filters: [
            {
              label: "Special Event",
              value: "Triple Double",
              kind: "special_event",
            },
          ],
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
    expect(screen.queryByText(/43-22/)).not.toBeInTheDocument();
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
});
