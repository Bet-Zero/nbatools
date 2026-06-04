import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResultRenderer from "../../components/results/ResultRenderer";
import { makeResponse } from "./helpers";

describe("ResultRenderer split and streak patterns", () => {

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
});
