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

  it("routes team records to the dedicated record renderer", () => {
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
              pts_avg: 116.4,
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
    expect(screen.getAllByLabelText("Boston Celtics (BOS)").length).toBeGreaterThan(
      0,
    );
    expect(screen.getByLabelText("Los Angeles Lakers (LAL)")).toBeInTheDocument();
    expect(screen.getByText("4-1")).toBeInTheDocument();
    expect(screen.getByText("5 games / 80.0% win pct")).toBeInTheDocument();
    expect(screen.getAllByText("PTS").length).toBeGreaterThan(0);
    expect(screen.getByText("Record Detail")).toBeInTheDocument();
    expect(screen.getByText("By Season")).toBeInTheDocument();
  });

  it("renders team records when opponent identity is only a text filter", () => {
    const data = makeResponse({
      route: "team_record",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          route: "team_record",
          opponent: "LAL",
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
              wins: 2,
              losses: 2,
              games: 4,
              win_pct: 0.5,
            },
          ],
        },
      },
    });
    render(<ResultSections data={data} />);
    expect(screen.getByText("Team Record")).toBeInTheDocument();
    expect(screen.getByLabelText("LAL")).toBeInTheDocument();
    expect(screen.getByText("2-2")).toBeInTheDocument();
    expect(screen.getByText("Record Detail")).toBeInTheDocument();
  });

  it("renders sparse team records with long opponent names without requiring record fields", () => {
    const longOpponent =
      "A Very Long Opponent Name With Multiple Regional Qualifier Words";
    const data = makeResponse({
      route: "team_record",
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
            team_id: 999,
            team_abbr: "EXT",
            team_name: longOpponent,
          },
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              team_name: "Boston Celtics",
              games: 0,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    expect(screen.getByText("Team Record")).toBeInTheDocument();
    expect(
      screen.getByLabelText(`${longOpponent} (EXT)`),
    ).toBeInTheDocument();
    expect(screen.getByText("0 games")).toBeInTheDocument();
    expect(screen.queryByText("Record")).not.toBeInTheDocument();
    expect(screen.getByText("Record Detail")).toBeInTheDocument();
  });

  it("routes playoff histories to the C7 history layout", () => {
    const data = makeResponse({
      route: "playoff_history",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          route: "playoff_history",
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
              season_start: "2019-20",
              season_end: "2024-25",
              season_type: "Playoffs",
              games: 63,
              wins: 39,
              losses: 24,
              win_pct: 0.619,
              seasons_appeared: 6,
              playoff_round: "Finals",
            },
          ],
          by_season: [
            {
              season: "2023-24",
              games: 19,
              wins: 16,
              losses: 3,
              win_pct: 0.842,
              deepest_round: "Finals",
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const stats = screen.getByLabelText("Postseason summary stats");
    expect(screen.getByLabelText("Playoff result")).toBeInTheDocument();
    expect(screen.getByText("Playoff History")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Boston Celtics" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Boston Celtics (BOS)")).toBeInTheDocument();
    expect(within(stats).getByText("Seasons")).toBeInTheDocument();
    expect(within(stats).getByText("6")).toBeInTheDocument();
    expect(within(stats).getByText("39-24")).toBeInTheDocument();
    expect(screen.getByText("2019-20 to 2024-25")).toBeInTheDocument();
    expect(screen.getAllByText("Playoffs").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Finals").length).toBeGreaterThan(0);
    expect(screen.getByText("Postseason Summary Detail")).toBeInTheDocument();
    expect(screen.getByText("Season Breakdown")).toBeInTheDocument();
    expect(screen.queryByText("Team Summary")).not.toBeInTheDocument();
    expect(screen.queryByText("Player Summary")).not.toBeInTheDocument();
  });

  it("renders playoff appearances with round context and sparse rows", () => {
    const longTeam =
      "A Very Long Playoff Team Name With Several Market Segments";
    const longRound =
      "Conference Finals With A Very Long Historical Round Label";
    const data = makeResponse({
      route: "playoff_appearances",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          route: "playoff_appearances",
          start_season: "1980-81",
          end_season: "2024-25",
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              team_name: longTeam,
              appearances: 12,
              round: longRound,
            },
          ],
          by_season: [{ season: "2023-24" }],
        },
      },
    });

    render(<ResultSections data={data} />);
    const stats = screen.getByLabelText("Postseason summary stats");
    expect(screen.getByText("Playoff Appearances")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: longTeam })).toBeInTheDocument();
    expect(within(stats).getByText("Appearances")).toBeInTheDocument();
    expect(within(stats).getByText("12")).toBeInTheDocument();
    expect(screen.getByText("1980-81 to 2024-25")).toBeInTheDocument();
    expect(screen.getAllByText(longRound).length).toBeGreaterThan(0);
    expect(screen.getByText("Postseason Summary Detail")).toBeInTheDocument();
    expect(screen.getByText("Season Breakdown")).toBeInTheDocument();
  });

  it("routes playoff leaderboards to the C7 boundary owner", () => {
    const data = makeResponse({
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
              season_type: "Playoffs",
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const ranked = screen.getByLabelText("Playoff leaderboard rankings");
    expect(screen.getByLabelText("Playoff result")).toBeInTheDocument();
    expect(screen.getByText("Playoff Round Records")).toBeInTheDocument();
    expect(within(ranked).getByText("Boston Celtics")).toBeInTheDocument();
    expect(
      within(ranked).getByLabelText("Boston Celtics (BOS)"),
    ).toBeInTheDocument();
    expect(within(ranked).getByText("28-14")).toBeInTheDocument();
    expect(within(ranked).getByText("66.7%")).toBeInTheDocument();
    expect(within(ranked).getByText("Win Pct")).toBeInTheDocument();
    expect(within(ranked).getByText("42 games")).toBeInTheDocument();
    expect(within(ranked).getByText("Finals")).toBeInTheDocument();
    expect(
      within(ranked).getByText("1980-81 to 2024-25"),
    ).toBeInTheDocument();
    expect(screen.getByText("Full Playoff Leaderboard")).toBeInTheDocument();
    expect(
      screen.queryByLabelText("Ranked leaderboard"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Occurrence Leaderboard")).not.toBeInTheDocument();
  });

  it("renders playoff appearance leaderboards with sparse identity fallbacks", () => {
    const longRound =
      "Conference Finals With A Very Long Historical Round Label";
    const data = makeResponse({
      route: "playoff_appearances",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: { route: "playoff_appearances" },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              team_name: "Los Angeles Lakers",
              team_abbr: "LAL",
              appearances: 7,
              round: longRound,
              seasons: "2019-20 to 2024-25",
            },
            {
              rank: 2,
              appearances: 0,
              round: longRound,
              seasons: "2019-20 to 2024-25",
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const ranked = screen.getByLabelText("Playoff leaderboard rankings");
    expect(screen.getByText("Playoff Appearance Leaders")).toBeInTheDocument();
    expect(within(ranked).getByText("Los Angeles Lakers")).toBeInTheDocument();
    expect(within(ranked).getByText("Playoff Entry 2")).toBeInTheDocument();
    expect(within(ranked).getByText("7")).toBeInTheDocument();
    expect(within(ranked).getByText("0")).toBeInTheDocument();
    expect(within(ranked).getAllByText("Appearances").length).toBe(2);
    expect(within(ranked).getAllByText(longRound).length).toBe(2);
    expect(screen.getByText("Full Playoff Leaderboard")).toBeInTheDocument();
  });

  it("routes playoff matchup comparisons to the C7 boundary owner", () => {
    const data = makeResponse({
      route: "playoff_matchup_history",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: {
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
              BOS_wins: 3,
              BOS_losses: 4,
              MIA_wins: 4,
              MIA_losses: 3,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const teams = screen.getByLabelText("Playoff matchup teams");
    expect(screen.getByLabelText("Playoff result")).toBeInTheDocument();
    expect(screen.getByText("Playoff Matchup")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Boston Celtics vs Miami Heat" }),
    ).toBeInTheDocument();
    expect(
      within(teams).getByLabelText("Boston Celtics (BOS)"),
    ).toBeInTheDocument();
    expect(
      within(teams).getByLabelText("Miami Heat (MIA)"),
    ).toBeInTheDocument();
    expect(within(teams).getByText("4-3")).toBeInTheDocument();
    expect(within(teams).getByText("3-4")).toBeInTheDocument();
    expect(screen.getAllByText("Conference Finals").length).toBeGreaterThan(0);
    expect(screen.getByText("Postseason Summary Detail")).toBeInTheDocument();
    expect(screen.getByText("Series Detail")).toBeInTheDocument();
    expect(screen.queryByText("Players")).not.toBeInTheDocument();
    expect(screen.queryByText("Comparison")).not.toBeInTheDocument();
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

  it("routes team split summaries to bucket cards", () => {
    const data = makeResponse({
      route: "team_split_summary",
      result: {
        query_class: "split_summary",
        result_status: "ok",
        metadata: {
          route: "team_split_summary",
          split_type: "home_away",
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
              season_start: "2024-25",
              season_end: "2024-25",
              season_type: "Regular Season",
              split: "home_away",
              games_total: 6,
            },
          ],
          split_comparison: [
            {
              bucket: "home",
              games: 3,
              wins: 2,
              losses: 1,
              win_pct: 0.667,
              pts_avg: 119.3,
            },
            {
              bucket: "away",
              games: 3,
              wins: 1,
              losses: 2,
              win_pct: 0.333,
              pts_avg: 111.7,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    expect(screen.getByText("Team Split Summary")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Boston Celtics" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Home/Away / 2024-25 / Regular Season / 6 games")).toBeInTheDocument();
    const buckets = screen.getByLabelText("Split buckets");
    expect(within(buckets).getByText("Home")).toBeInTheDocument();
    expect(within(buckets).getByText("Away")).toBeInTheDocument();
    expect(within(buckets).getByText("2-1")).toBeInTheDocument();
    expect(within(buckets).getByText("1-2")).toBeInTheDocument();
    expect(screen.getByText("Split Summary Detail")).toBeInTheDocument();
    expect(screen.getByText("Split Comparison Detail")).toBeInTheDocument();
  });

  it("routes player split summaries to neutral bucket cards", () => {
    const data = makeResponse({
      route: "player_split_summary",
      result: {
        query_class: "split_summary",
        result_status: "ok",
        metadata: {
          route: "player_split_summary",
          split_type: "wins_losses",
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
              season_start: "2024-25",
              season_end: "2024-25",
              season_type: "Regular Season",
              split: "wins_losses",
              games_total: 8,
            },
          ],
          split_comparison: [
            {
              bucket: "wins",
              games: 5,
              wins: 5,
              losses: 0,
              win_pct: 1,
              minutes_avg: 34.5,
              pts_avg: 30.5,
            },
            {
              bucket: "losses",
              games: 3,
              wins: 0,
              losses: 3,
              win_pct: 0,
              minutes_avg: 36.2,
              pts_avg: 24.1,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    expect(screen.getByText("Player Split Summary")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Nikola Jokic" }),
    ).toBeInTheDocument();
    expect(
      screen.getAllByLabelText("Nikola Jokic avatar").length,
    ).toBeGreaterThan(0);
    const buckets = screen.getByLabelText("Split buckets");
    expect(within(buckets).getByText("Wins")).toBeInTheDocument();
    expect(within(buckets).getByText("Losses")).toBeInTheDocument();
    expect(within(buckets).getByText("30.5")).toBeInTheDocument();
    expect(within(buckets).getByText("34.5")).toBeInTheDocument();
  });

  it("renders long split bucket labels with sparse stats", () => {
    const data = makeResponse({
      route: "team_split_summary",
      result: {
        query_class: "split_summary",
        result_status: "ok",
        metadata: {
          route: "team_split_summary",
          team: "Long Bucket Team",
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [{ team_name: "Long Bucket Team", games_total: 1 }],
          split_comparison: [
            {
              bucket: "post_all_star_break_really_long_bucket",
              games: 1,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    expect(
      screen.getByText("Post All Star Break Really Long Bucket"),
    ).toBeInTheDocument();
    expect(screen.getAllByText("1 game").length).toBeGreaterThan(0);
    expect(screen.getByText("Split Comparison Detail")).toBeInTheDocument();
  });

  it("keeps unknown split summaries on the generic split renderer", () => {
    const data = makeResponse({
      route: "unknown_split_summary",
      result: {
        query_class: "split_summary",
        result_status: "ok",
        metadata: { route: "unknown_split_summary" },
        notes: [],
        caveats: [],
        sections: {
          summary: [{ label: "Fallback split" }],
          split_comparison: [{ bucket: "custom_bucket", games: 2 }],
        },
      },
    });

    render(<ResultSections data={data} />);
    expect(screen.getByText("Summary")).toBeInTheDocument();
    expect(screen.getByText("Split Comparison")).toBeInTheDocument();
    expect(screen.queryByText("Team Split Summary")).not.toBeInTheDocument();
    expect(screen.queryByText("Player Split Summary")).not.toBeInTheDocument();
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
    expect(screen.queryByText("Occurrence Leaderboard")).not.toBeInTheDocument();
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

  it("routes occurrence leaderboards to the occurrence owner", () => {
    const data = makeResponse({
      route: "player_occurrence_leaders",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: { route: "player_occurrence_leaders" },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              player_name: "Nikola Jokic",
              games_played: 72,
              "games_pts_30+_reb_10+": 12,
              season: "2024-25",
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    expect(screen.getByText("Occurrence Leaderboard")).toBeInTheDocument();
    expect(screen.getByText("Full Occurrence Detail")).toBeInTheDocument();
    expect(screen.queryByText("Full Leaderboard")).not.toBeInTheDocument();
    const ranked = screen.getByLabelText("Occurrence leaderboard rankings");
    expect(within(ranked).getByText("Nikola Jokic")).toBeInTheDocument();
    expect(within(ranked).getByText("12")).toBeInTheDocument();
    expect(within(ranked).getByText("Event Count")).toBeInTheDocument();
    expect(
      within(ranked).getByText("Games PTS 30+ REB 10+"),
    ).toBeInTheDocument();
    expect(within(ranked).getByText("72 games")).toBeInTheDocument();
    expect(within(ranked).getByText("2024-25")).toBeInTheDocument();
  });

  it("renders team occurrence leaderboards with neutral event-count rows", () => {
    const data = makeResponse({
      route: "team_occurrence_leaders",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          route: "team_occurrence_leaders",
          season_type: "Regular Season",
        },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              team_abbr: "BOS",
              games_played: 82,
              "games_pts_120+_fg3m_15+": 18,
              season: "2024-25",
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const ranked = screen.getByLabelText("Occurrence leaderboard rankings");
    expect(within(ranked).getAllByText("BOS").length).toBeGreaterThan(0);
    expect(within(ranked).getByText("18")).toBeInTheDocument();
    expect(
      within(ranked).getByText("Games PTS 120+ FG3M 15+"),
    ).toBeInTheDocument();
    expect(within(ranked).getByText("82 games")).toBeInTheDocument();
    expect(within(ranked).getByText("Regular Season")).toBeInTheDocument();
  });

  it("formats compound occurrence labels without parsing the event", () => {
    const data = makeResponse({
      route: "player_occurrence_leaders",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          route: "player_occurrence_leaders",
          start_date: "2024-11-01",
          end_date: "2025-02-01",
        },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 2,
              player_name:
                "A Very Long Player Name With Compound-Hyphen Context",
              team_abbr: "OKC",
              games_played: 41,
              min_games: 20,
              qualifier: "Road wins only",
              "games_pts_30+_reb_10+_ast_10+": 9,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const ranked = screen.getByLabelText("Occurrence leaderboard rankings");
    expect(
      within(ranked).getByText(
        "A Very Long Player Name With Compound-Hyphen Context",
      ),
    ).toBeInTheDocument();
    expect(within(ranked).getByText("9")).toBeInTheDocument();
    expect(
      within(ranked).getByText("Games PTS 30+ REB 10+ AST 10+"),
    ).toBeInTheDocument();
    expect(
      within(ranked).getByText("2024-11-01 to 2025-02-01"),
    ).toBeInTheDocument();
    expect(within(ranked).getByText("Min games 20")).toBeInTheDocument();
    expect(within(ranked).getByText("Road wins only")).toBeInTheDocument();
  });

  it("keeps sparse occurrence leaderboard rows readable", () => {
    const data = makeResponse({
      route: "team_occurrence_leaders",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          route: "team_occurrence_leaders",
          season: "2024-25",
        },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              games_played: 20,
              qualifying_games: 7,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const ranked = screen.getByLabelText("Occurrence leaderboard rankings");
    expect(within(ranked).getByText("Occurrence Entry")).toBeInTheDocument();
    expect(within(ranked).getByText("7")).toBeInTheDocument();
    expect(within(ranked).getByText("Qualifying Games")).toBeInTheDocument();
    expect(within(ranked).getByText("20 games")).toBeInTheDocument();
    expect(within(ranked).getByText("2024-25")).toBeInTheDocument();
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

  it("renders neutral empty display for empty ok leaderboard sections", () => {
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
    render(<ResultSections data={data} />);
    expect(screen.getByText("No Displayable Rows")).toBeInTheDocument();
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

  it("routes count results to the dedicated count renderer with finder detail", () => {
    const data = makeResponse({
      route: "player_game_finder",
      result: {
        query_class: "count",
        result_status: "ok",
        metadata: {
          route: "player_game_finder",
          query_class: "count",
          query_text: "how many 35 point games did Stephen Curry have",
          season: "2024-25",
          player_context: {
            player_id: 201939,
            player_name: "Stephen Curry",
          },
        },
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
    expect(
      screen.getByRole("heading", { name: "Stephen Curry" }),
    ).toBeInTheDocument();
    expect(screen.getAllByLabelText("Stephen Curry avatar").length).toBeGreaterThan(
      0,
    );
    expect(
      screen.getByText("how many 35 point games did Stephen Curry have"),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Count").length).toBeGreaterThan(0);
    expect(screen.getByText("Count Detail")).toBeInTheDocument();
    expect(screen.getByText("Matching Games")).toBeInTheDocument();
    expect(screen.getAllByText("Stephen Curry").length).toBeGreaterThan(0);
  });

  it("renders zero team occurrence counts without requiring detail rows", () => {
    const data = makeResponse({
      route: "team_occurrence_leaders",
      result: {
        query_class: "count",
        result_status: "ok",
        metadata: {
          route: "team_occurrence_leaders",
          query_class: "count",
          query_text: "how many 140 point games did the Celtics have",
          season: "2024-25",
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
          count: [{ count: 0 }],
        },
      },
    });

    render(<ResultSections data={data} />);
    expect(
      screen.getByRole("heading", { name: "Boston Celtics" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Boston Celtics (BOS)")).toBeInTheDocument();
    expect(screen.getAllByText("0").length).toBeGreaterThan(0);
    expect(screen.getByText("Regular Season")).toBeInTheDocument();
    expect(screen.queryByText("Matching Games")).not.toBeInTheDocument();
    expect(screen.getByText("Count Detail")).toBeInTheDocument();
  });

  it("renders distinct counts with long query context and custom detail", () => {
    const longQuery =
      "how many distinct players had a very long compound occurrence of thirty points and ten rebounds";
    const data = makeResponse({
      route: "player_occurrence_leaders",
      result: {
        query_class: "count",
        result_status: "ok",
        metadata: {
          route: "player_occurrence_leaders",
          query_class: "count",
          query_text: longQuery,
          season: "2024-25",
        },
        notes: [],
        caveats: [],
        sections: {
          count: [{ count: 47 }],
          custom_detail: [{ label: "kept detail" }],
        },
      },
    });

    render(<ResultSections data={data} />);
    expect(
      screen.getByRole("heading", { name: "Matching results" }),
    ).toBeInTheDocument();
    expect(screen.getByText(longQuery)).toBeInTheDocument();
    expect(screen.getAllByText("47").length).toBeGreaterThan(0);
    expect(screen.getByText("Custom Detail")).toBeInTheDocument();
    expect(screen.getByText("kept detail")).toBeInTheDocument();
  });

  it("renders no-result display for no_result status", () => {
    const data = makeResponse({
      result_status: "no_result",
      result_reason: "no_match",
      notes: ["No rows matched the requested filters"],
      caveats: ["Recent games may still be loading"],
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
    expect(screen.getByText("No Matching Results")).toBeInTheDocument();
    expect(screen.getByText(/No rows matched/)).toBeInTheDocument();
    expect(
      screen.getByText(/Recent games may still be loading/),
    ).toBeInTheDocument();
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
    expect(
      screen.queryByLabelText("Head-to-head result"),
    ).not.toBeInTheDocument();
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

  it("routes player head-to-head comparisons to the C7 boundary owner", () => {
    const data = makeResponse({
      route: "player_compare",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: {
          route: "player_compare",
          head_to_head_used: true,
          players_context: [
            { player_id: 203999, player_name: "Nikola Jokic" },
            { player_id: 203954, player_name: "Joel Embiid" },
          ],
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            { player_name: "Nikola Jokic", games: 3, wins: 2, losses: 1 },
            { player_name: "Joel Embiid", games: 3, wins: 1, losses: 2 },
          ],
          comparison: [
            {
              metric: "wins",
              "Nikola Jokic": 2,
              "Joel Embiid": 1,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const participants = screen.getByLabelText("Head-to-head participants");
    expect(screen.getByLabelText("Head-to-head result")).toBeInTheDocument();
    expect(screen.getByText("Head-to-Head")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Nikola Jokic vs Joel Embiid" }),
    ).toBeInTheDocument();
    expect(within(participants).getByText("Nikola Jokic")).toBeInTheDocument();
    expect(within(participants).getByText("Joel Embiid")).toBeInTheDocument();
    expect(
      within(participants)
        .getByLabelText("Nikola Jokic avatar")
        .querySelector("img"),
    ).toHaveAttribute(
      "src",
      "https://cdn.nba.com/headshots/nba/latest/1040x760/203999.png",
    );
    expect(within(participants).getByText("2-1")).toBeInTheDocument();
    expect(within(participants).getByText("1-2")).toBeInTheDocument();
    expect(screen.getByText("Participant Detail")).toBeInTheDocument();
    expect(screen.getByText("Metric Detail")).toBeInTheDocument();
    expect(screen.queryByText("Player Comparison")).not.toBeInTheDocument();
    expect(screen.queryByText("Player Summary Detail")).not.toBeInTheDocument();
    expect(screen.queryByText("Full Metric Detail")).not.toBeInTheDocument();
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
    expect(
      screen.queryByLabelText("Head-to-head result"),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Players")).toBeInTheDocument();
    expect(screen.getByText("Comparison")).toBeInTheDocument();
    expect(screen.queryByText("Player Comparison")).not.toBeInTheDocument();
    expect(screen.getAllByText("Celtics").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Lakers").length).toBeGreaterThan(0);
  });

  it("routes team head-to-head comparisons to the C7 boundary owner", () => {
    const data = makeResponse({
      route: "team_compare",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: {
          route: "team_compare",
          head_to_head_used: true,
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            { team_name: "Celtics", games: 4, wins: 3, losses: 1 },
            { team_name: "Lakers", games: 4, wins: 1, losses: 3 },
          ],
          comparison: [{ metric: "wins", Celtics: 3, Lakers: 1 }],
        },
      },
    });

    render(<ResultSections data={data} />);
    const participants = screen.getByLabelText("Head-to-head participants");
    expect(screen.getByLabelText("Head-to-head result")).toBeInTheDocument();
    expect(screen.getByText("Head-to-Head")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Celtics vs Lakers" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Head-to-head sample")).toBeInTheDocument();
    expect(within(participants).getByText("Celtics")).toBeInTheDocument();
    expect(within(participants).getByText("Lakers")).toBeInTheDocument();
    expect(within(participants).getByText("3-1")).toBeInTheDocument();
    expect(within(participants).getByText("1-3")).toBeInTheDocument();
    expect(screen.getByText("Participant Detail")).toBeInTheDocument();
    expect(screen.getByText("Metric Detail")).toBeInTheDocument();
    expect(screen.queryByText("Players")).not.toBeInTheDocument();
    expect(screen.queryByText("Player Comparison")).not.toBeInTheDocument();
  });

  it("renders tied head-to-head records without inventing a winner", () => {
    const data = makeResponse({
      route: "team_compare",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: {
          route: "team_compare",
          head_to_head_used: true,
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            { team_name: "Celtics", games: 2, wins: 1, losses: 1 },
            { team_name: "Lakers", games: 2, wins: 1, losses: 1 },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const participants = screen.getByLabelText("Head-to-head participants");
    expect(screen.getByText("Head-to-Head")).toBeInTheDocument();
    expect(within(participants).getAllByText("1-1").length).toBe(2);
    expect(screen.getByText("Participant Detail")).toBeInTheDocument();
  });

  it("routes team matchup records to the dedicated record renderer", () => {
    const data = makeResponse({
      route: "team_matchup_record",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: {
          route: "team_matchup_record",
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
              games: 4,
              wins: 3,
              losses: 1,
              win_pct: 0.75,
              pts_avg: 118.2,
            },
            {
              team_name: "Los Angeles Lakers",
              games: 4,
              wins: 1,
              losses: 3,
              win_pct: 0.25,
              pts_avg: 109.8,
            },
          ],
          comparison: [
            {
              metric: "wins",
              "Boston Celtics": 3,
              "Los Angeles Lakers": 1,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const participants = screen.getByLabelText("Head-to-head participants");
    expect(screen.getByLabelText("Head-to-head result")).toBeInTheDocument();
    expect(screen.getByText("Head-to-Head")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: "Boston Celtics vs Los Angeles Lakers",
      }),
    ).toBeInTheDocument();
    expect(
      within(participants).getByLabelText("Boston Celtics (BOS)"),
    ).toBeInTheDocument();
    expect(
      within(participants).getByLabelText("Los Angeles Lakers (LAL)"),
    ).toBeInTheDocument();
    expect(within(participants).getByText("3-1")).toBeInTheDocument();
    expect(within(participants).getByText("1-3")).toBeInTheDocument();
    expect(within(participants).getByText("118.2")).toBeInTheDocument();
    expect(screen.getByText("Participant Detail")).toBeInTheDocument();
    expect(screen.getByText("Metric Detail")).toBeInTheDocument();
    expect(screen.queryByText("Team Matchup Record")).not.toBeInTheDocument();
    expect(screen.queryByText("Team Summary Detail")).not.toBeInTheDocument();
    expect(screen.queryByText("Players")).not.toBeInTheDocument();
    expect(screen.queryByText("Player Comparison")).not.toBeInTheDocument();
  });

  it("routes matchup-by-decade comparisons to the C7 boundary owner", () => {
    const data = makeResponse({
      route: "matchup_by_decade",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: { route: "matchup_by_decade" },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            { team_name: "Celtics", games: 18, wins: 10, losses: 8 },
            { team_name: "Lakers", games: 18, wins: 8, losses: 10 },
          ],
          comparison: [
            {
              decade: "1980s",
              BOS_wins: 4,
              BOS_losses: 2,
              LAL_wins: 2,
              LAL_losses: 4,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const participants = screen.getByLabelText("Head-to-head participants");
    expect(screen.getByLabelText("Head-to-head result")).toBeInTheDocument();
    expect(screen.getByText("Head-to-Head")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Celtics vs Lakers" }),
    ).toBeInTheDocument();
    expect(within(participants).getByText("10-8")).toBeInTheDocument();
    expect(within(participants).getByText("8-10")).toBeInTheDocument();
    expect(screen.getByText("Participant Detail")).toBeInTheDocument();
    expect(screen.getByText("Metric Detail")).toBeInTheDocument();
    expect(screen.getByText("1980s")).toBeInTheDocument();
    expect(screen.queryByText("Players")).not.toBeInTheDocument();
  });

  it("renders sparse matchup records without team ids or record fields", () => {
    const data = makeResponse({
      route: "team_matchup_record",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: { route: "team_matchup_record" },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              team_name:
                "A Very Long Home Team Name With Several Market Segments",
              games: 0,
            },
            {
              team_name:
                "A Very Long Away Team Name With Several Market Segments",
              games: 0,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    const participants = screen.getByLabelText("Head-to-head participants");
    expect(screen.getByText("Head-to-Head")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: /A Very Long Home Team Name.*A Very Long Away Team Name/,
      }),
    ).toBeInTheDocument();
    expect(within(participants).getAllByText("Sample").length).toBe(2);
    expect(within(participants).getAllByText("0").length).toBe(2);
    expect(within(participants).getAllByText("games").length).toBe(2);
    expect(within(participants).queryByText("Record")).not.toBeInTheDocument();
    expect(screen.getByText("Participant Detail")).toBeInTheDocument();
    expect(screen.queryByText("Team Matchup Record")).not.toBeInTheDocument();
    expect(screen.queryByText("Team Summary Detail")).not.toBeInTheDocument();
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

  it("renders player streak cards with active status and detail", () => {
    const data = makeResponse({
      route: "player_streak_finder",
      result: {
        query_class: "streak",
        result_status: "ok",
        metadata: {
          route: "player_streak_finder",
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
              condition: "pts>=30",
              start_date: "2025-01-01",
              end_date: "2025-01-10",
              streak_length: 5,
              games: 5,
              wins: 4,
              losses: 1,
              is_active: 1,
              pts_avg: 32.6,
              reb_avg: 11.2,
            },
          ],
        },
      },
    });
    render(<ResultSections data={data} />);
    expect(screen.getByText("Streaks")).toBeInTheDocument();
    expect(screen.getByText("1 found")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Nikola Jokic" }),
    ).toBeInTheDocument();
    expect(screen.getAllByLabelText("Nikola Jokic avatar").length).toBeGreaterThan(
      0,
    );
    expect(screen.getAllByText("pts>=30").length).toBeGreaterThan(0);
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("4-1")).toBeInTheDocument();
    expect(screen.getByText("Full Streak Detail")).toBeInTheDocument();
    const span = screen.getByLabelText("Streak span");
    expect(within(span).getByText("2025-01-01")).toBeInTheDocument();
    expect(within(span).getByText("2025-01-10")).toBeInTheDocument();
  });

  it("renders team streak cards with team identity and completed status", () => {
    const data = makeResponse({
      route: "team_streak_finder",
      result: {
        query_class: "streak",
        result_status: "ok",
        metadata: {
          route: "team_streak_finder",
          team_context: {
            team_id: 1610612738,
            team_abbr: "BOS",
            team_name: "Boston Celtics",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          streak: [
            {
              team_name: "Boston Celtics",
              condition: "wins",
              start_date: "2025-02-01",
              end_date: "2025-02-08",
              streak_length: 4,
              games: 4,
              wins: 4,
              losses: 0,
              is_active: 0,
              pts_avg: 121.5,
              fg3m_avg: 15.2,
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    expect(screen.getByText("Team Streak")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Boston Celtics" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Boston Celtics (BOS)")).toBeInTheDocument();
    expect(screen.getAllByText("wins").length).toBeGreaterThan(0);
    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.getByText("4-0")).toBeInTheDocument();
    expect(screen.getByText("Full Streak Detail")).toBeInTheDocument();
  });

  it("renders sparse streak cards with long names and missing condition labels", () => {
    const longName =
      "A Very Long Player Name With Multiple Hyphenated-Surname Segments";
    const data = makeResponse({
      route: "player_streak_finder",
      result: {
        query_class: "streak",
        result_status: "ok",
        metadata: { route: "player_streak_finder" },
        notes: [],
        caveats: [],
        sections: {
          streak: [
            {
              player_name: longName,
              games: 2,
              start_date: "2025-03-01",
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    expect(screen.getByRole("heading", { name: longName })).toBeInTheDocument();
    expect(screen.getAllByText("Streak").length).toBeGreaterThan(0);
    expect(screen.getByText("2 games")).toBeInTheDocument();
    expect(screen.getAllByText("2025-03-01").length).toBeGreaterThan(0);
    expect(screen.getByText("Full Streak Detail")).toBeInTheDocument();
  });

  it("renders streak cards without length or dates while preserving detail", () => {
    const data = makeResponse({
      route: "player_streak_finder",
      result: {
        query_class: "streak",
        result_status: "ok",
        metadata: { route: "player_streak_finder" },
        notes: [],
        caveats: [],
        sections: {
          streak: [
            {
              player_name: "Sparse Streak Player",
              condition: "very_long_condition_label_with_no_supplied_span",
            },
          ],
        },
      },
    });

    render(<ResultSections data={data} />);
    expect(
      screen.getByRole("heading", { name: "Sparse Streak Player" }),
    ).toBeInTheDocument();
    expect(
      screen.getAllByText("very_long_condition_label_with_no_supplied_span")
        .length,
    ).toBeGreaterThan(0);
    expect(screen.queryByLabelText("Streak span")).not.toBeInTheDocument();
    expect(screen.getByText("Full Streak Detail")).toBeInTheDocument();
  });

  it("keeps unknown streak-shaped routes on the generic fallback renderer", () => {
    const data = makeResponse({
      route: "unknown_streak",
      result: {
        query_class: "streak",
        result_status: "ok",
        metadata: { route: "unknown_streak" },
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
    expect(screen.queryByText("1 found")).not.toBeInTheDocument();
    expect(screen.getByText("2025-01-01")).toBeInTheDocument();
  });
});
