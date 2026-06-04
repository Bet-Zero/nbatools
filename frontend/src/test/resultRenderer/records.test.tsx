import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResultRenderer from "../../components/results/ResultRenderer";
import { makeResponse } from "./helpers";

describe("ResultRenderer record patterns", () => {

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


  it("renders team records with game logs as team-first results with collapsed game detail", () => {
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
          game_log: Array.from({ length: 64 }, (_value, index) => ({
            game_id: index + 1,
            game_date: `2026-01-${String((index % 28) + 1).padStart(2, "0")}`,
            team_abbr: "NYK",
            team_name: "Knicks",
            opponent_team_abbr: "BOS",
            opponent_team_name: "Celtics",
            wl: index % 2 === 0 ? "W" : "L",
            pts: 112,
            opponent_pts: 118,
            reb: 44,
            ast: 24,
            fg3m: 13,
            plus_minus: -6,
          })),
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
    expect(screen.queryByRole("table", { name: "Game log" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Game Detail")).toHaveTextContent("64 rows");
    expect(
      screen.getByRole("button", { name: "Show game detail" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("columnheader", { name: "Opp PTS" }),
    ).not.toBeInTheDocument();
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
});
