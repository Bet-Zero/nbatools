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

describe("Wave 2 table pattern contracts", () => {
  it("renders split comparison and on/off split visible header contracts", () => {
    const splitData = makeResponse("player_split_summary", {
      queryClass: "split_summary",
      metadata: {
        player_context: { player_id: 201939, player_name: "Stephen Curry" },
        season: "2025-26",
        season_type: "Regular Season",
      },
      sections: {
        summary: [
          {
            player_name: "Stephen Curry",
            split: "home_away",
            games_total: 20,
          },
        ],
        split_comparison: [
          {
            bucket: "home",
            games: 10,
            wins: 7,
            losses: 3,
            pts_avg: 31.1,
            reb_avg: 4.2,
            ast_avg: 6.3,
            minutes_avg: 34.5,
            fg3m_avg: 5.4,
            ts_pct_avg: 0.64,
            efg_pct_avg: 0.61,
            plus_minus_avg: 8.1,
          },
          {
            bucket: "away",
            games: 10,
            wins: 5,
            losses: 5,
            pts_avg: 27.2,
            reb_avg: 3.8,
            ast_avg: 5.9,
            minutes_avg: 33.1,
            fg3m_avg: 4.8,
            ts_pct_avg: 0.59,
            efg_pct_avg: 0.56,
            plus_minus_avg: 1.2,
          },
        ],
      },
    });

    const { rerender } = render(
      <ResultRenderer data={splitData} displayMode="review" />,
    );

    const splitTable = screen.getByRole("table", { name: "Split buckets" });
    expectHeaders(splitTable, [
      "Split",
      "GP",
      "Record",
      "PTS",
      "REB",
      "AST",
      "MIN",
      "3PM",
      "TS%",
      "eFG%",
      "+/-",
    ]);
    expect(within(splitTable).getByText("Home")).toBeInTheDocument();
    expect(within(splitTable).getByText("Away")).toBeInTheDocument();
    expect(screen.getByLabelText("Split edges")).toBeInTheDocument();

    const onOffData = makeResponse("player_on_off", {
      metadata: {
        player_context: { player_id: 203999, player_name: "Nikola Jokic" },
        season: "2025-26",
        season_type: "Regular Season",
      },
      sections: {
        summary: [
          {
            player_name: "Nikola Jokic",
            team_abbr: "DEN",
            presence_state: "on",
            gp: 42,
            minutes: 1480,
            plus_minus: 430,
            off_rating: 124.2,
            def_rating: 110.1,
            net_rating: 14.1,
          },
          {
            player_name: "Nikola Jokic",
            team_abbr: "DEN",
            presence_state: "off",
            gp: 42,
            minutes: 540,
            plus_minus: -120,
            off_rating: 108.4,
            def_rating: 116.2,
            net_rating: -7.8,
          },
        ],
      },
    });

    rerender(<ResultRenderer data={onOffData} displayMode="review" />);
    const onOffTable = screen.getByRole("table", { name: "Split buckets" });
    expectHeaders(onOffTable, ["Split", "GP", "ORtg", "DRtg", "Net", "MIN", "+/-"]);
    expect(within(onOffTable).getByText("On")).toBeInTheDocument();
    expect(within(onOffTable).getByText("Off")).toBeInTheDocument();
    expect(screen.getByLabelText("On/Off Detail")).toBeInTheDocument();
  });

  it("renders player and team streak visible header contracts", () => {
    const playerData = makeResponse("player_streak_finder", {
      queryClass: "streak",
      sections: {
        streak: [
          {
            rank: 1,
            player_name: "Stephen Curry",
            condition: "pts>=20",
            streak_length: 8,
            games: 8,
            start_date: "2026-02-01",
            end_date: "2026-02-15",
            wins: 6,
            losses: 2,
            is_active: 1,
            pts_avg: 31.2,
            ast_avg: 6.4,
            plus_minus_avg: 7.3,
          },
        ],
      },
    });
    const { rerender } = render(
      <ResultRenderer data={playerData} displayMode="review" />,
    );

    const playerTable = screen.getByRole("table", { name: "Streaks" });
    expectHeaders(playerTable, [
      "#",
      "Player",
      "Streak",
      "Length",
      "Status",
      "Start",
      "End",
      "Games",
      "Record",
      "PTS",
      "AST",
      "+/-",
    ]);
    expect(within(playerTable).getByText("20+ PTS")).toBeInTheDocument();
    expect(within(playerTable).getByText("Active")).toBeInTheDocument();

    const teamData = makeResponse("team_streak_finder", {
      queryClass: "streak",
      sections: {
        streak: [
          {
            rank: 1,
            team_name: "Boston Celtics",
            team_abbr: "BOS",
            condition: "wins",
            streak_length: 5,
            games: 5,
            start_date: "2026-03-01",
            end_date: "2026-03-10",
            wins: 5,
            losses: 0,
            is_active: 0,
            pts_avg: 119.4,
          },
        ],
      },
    });

    rerender(<ResultRenderer data={teamData} displayMode="review" />);
    const teamTable = screen.getByRole("table", { name: "Streaks" });
    expectHeaders(teamTable, ["#", "Team", "Streak", "Length", "PTS"]);
    expect(within(teamTable).getByText("Wins")).toBeInTheDocument();
  });

  it("renders comparison metric and head-to-head visible header contracts", () => {
    const playerData = makeResponse("player_compare", {
      queryClass: "comparison",
      metadata: {
        players_context: [
          { player_id: 203999, player_name: "Nikola Jokic" },
          { player_id: 203954, player_name: "Joel Embiid" },
        ],
      },
      sections: {
        summary: [
          { player_name: "Nikola Jokic", games: 60, pts_avg: 28.1 },
          { player_name: "Joel Embiid", games: 50, pts_avg: 30.4 },
        ],
        comparison: [
          { metric: "pts_avg", "Nikola Jokic": 28.1, "Joel Embiid": 30.4 },
          { metric: "reb_avg", "Nikola Jokic": 12.5, "Joel Embiid": 10.8 },
        ],
      },
    });
    const { rerender } = render(
      <ResultRenderer data={playerData} displayMode="review" />,
    );

    const comparisonTable = screen.getByRole("table", {
      name: "Comparison metrics",
    });
    expectHeaders(comparisonTable, [
      "Metric",
      "Nikola Jokic",
      "Joel Embiid",
      "Edge / Difference",
    ]);
    expect(within(comparisonTable).getByText("PTS Avg")).toBeInTheDocument();
    expect(screen.getByLabelText("Compared players")).toBeInTheDocument();

    const matchupData = makeResponse("team_matchup_record", {
      queryClass: "comparison",
      sections: {
        summary: [
          { team_name: "Lakers", wins: 3, losses: 1, win_pct: 0.75 },
          { team_name: "Celtics", wins: 1, losses: 3, win_pct: 0.25 },
        ],
        comparison: [{ metric: "wins", Lakers: 3, Celtics: 1 }],
      },
    });

    rerender(<ResultRenderer data={matchupData} displayMode="review" />);
    const headToHeadTable = screen.getByRole("table", {
      name: "Comparison metrics",
    });
    expectHeaders(headToHeadTable, ["Metric", "Lakers", "Celtics", "Edge / Difference"]);
    expect(screen.getByLabelText("Head-to-head participants")).toBeInTheDocument();
  });

  it("renders playoff history, round record, and matchup history header contracts", () => {
    const historyData = makeResponse("playoff_history", {
      metadata: {
        team_context: {
          team_id: 1610612738,
          team_abbr: "BOS",
          team_name: "Boston Celtics",
        },
      },
      sections: {
        summary: [{ team_name: "Boston Celtics", appearances: 3, wins: 20, losses: 12 }],
        by_season: [
          {
            season: "2024-25",
            deepest_round: "Conference Finals",
            wins: 8,
            losses: 5,
            result: "Lost Conference Finals",
            opponent: "New York Knicks",
            win_pct: 0.615,
            games: 13,
          },
        ],
      },
    });
    const { rerender } = render(
      <ResultRenderer data={historyData} displayMode="review" />,
    );

    expectHeaders(screen.getByRole("table", { name: "Playoff season breakdown" }), [
      "Season",
      "Round Reached",
      "Record",
      "Result",
      "Opponent",
      "Win Pct",
      "Games",
    ]);

    const roundData = makeResponse("playoff_round_record", {
      queryClass: "leaderboard",
      query: "best finals record",
      metadata: { playoff_round: "Finals" },
      sections: {
        leaderboard: [
          {
            rank: 1,
            team_name: "Los Angeles Lakers",
            team_abbr: "LAL",
            round: "Finals",
            wins: 42,
            losses: 28,
            games_played: 70,
            win_pct: 0.6,
            seasons: "1996-97 to 2024-25",
          },
        ],
      },
    });

    rerender(<ResultRenderer data={roundData} displayMode="review" />);
    expectHeaders(screen.getByRole("table", { name: "Playoff round records" }), [
      "#",
      "Team",
      "Round",
      "Record",
      "Games",
      "Win Pct",
      "Seasons",
    ]);

    const matchupData = makeResponse("playoff_matchup_history", {
      queryClass: "comparison",
      metadata: {
        teams_context: [
          { team_id: 1610612738, team_abbr: "BOS", team_name: "Boston Celtics" },
          { team_id: 1610612747, team_abbr: "LAL", team_name: "Los Angeles Lakers" },
        ],
      },
      sections: {
        summary: [
          { team_name: "Boston Celtics", wins: 4, losses: 2 },
          { team_name: "Los Angeles Lakers", wins: 2, losses: 4 },
        ],
        comparison: [
          {
            season: "2023-24",
            round: "Finals",
            winner: "Boston Celtics",
            series_result: "BOS won 4-2",
            BOS_wins: 4,
            BOS_losses: 2,
            LAL_wins: 2,
            LAL_losses: 4,
          },
        ],
      },
    });

    rerender(<ResultRenderer data={matchupData} displayMode="review" />);
    expectHeaders(screen.getByRole("table", { name: "Playoff series" }), [
      "Season",
      "Round",
      "Winner",
      "Series Result",
      "BOS",
      "LAL",
      "Games",
    ]);
  });

  it("renders decade record and matchup visible header contracts", () => {
    const decadeData = makeResponse("record_by_decade", {
      metadata: {
        team_context: {
          team_id: 1610612759,
          team_abbr: "SAS",
          team_name: "San Antonio Spurs",
        },
      },
      sections: {
        summary: [{ team_name: "San Antonio Spurs", wins: 500, losses: 320 }],
        by_season: [
          {
            decade: "2010s",
            seasons_appeared: 10,
            wins: 520,
            losses: 300,
            win_pct: 0.634,
            games: 820,
            season_type: "Regular Season",
          },
        ],
      },
    });
    const { rerender } = render(
      <ResultRenderer data={decadeData} displayMode="review" />,
    );

    expectHeaders(screen.getByRole("table", { name: "Record by decade" }), [
      "Decade",
      "Seasons",
      "W-L",
      "Win %",
      "Games",
      "Season Type",
    ]);

    const leaderboardData = makeResponse("record_by_decade_leaderboard", {
      queryClass: "leaderboard",
      query: "best record by decade",
      metadata: { stat: "win_pct" },
      sections: {
        leaderboard: [
          {
            rank: 1,
            team_name: "San Antonio Spurs",
            team_abbr: "SAS",
            decade: "2010s",
            games_played: 820,
            wins: 520,
            losses: 300,
            win_pct: 0.634,
            seasons: "2010-11 to 2019-20",
            season_type: "Regular Season",
          },
        ],
      },
    });

    rerender(<ResultRenderer data={leaderboardData} displayMode="review" />);
    expectHeaders(
      screen.getByRole("table", { name: "Record by decade leaderboard" }),
      ["#", "Team", "Decade", "Win %", "W-L", "Games", "Seasons", "Season Type"],
    );

    const matchupData = makeResponse("matchup_by_decade", {
      queryClass: "comparison",
      metadata: {
        teams_context: [
          { team_id: 1610612738, team_abbr: "BOS", team_name: "Boston Celtics" },
          { team_id: 1610612747, team_abbr: "LAL", team_name: "Los Angeles Lakers" },
        ],
      },
      sections: {
        summary: [
          { team_name: "Boston Celtics", team_abbr: "BOS", wins: 12, losses: 10 },
          { team_name: "Los Angeles Lakers", team_abbr: "LAL", wins: 10, losses: 12 },
        ],
        comparison: [
          {
            decade: "1980s",
            games: 22,
            BOS_wins: 12,
            BOS_losses: 10,
            BOS_win_pct: 0.545,
            LAL_wins: 10,
            LAL_losses: 12,
            LAL_win_pct: 0.455,
          },
        ],
      },
    });

    rerender(<ResultRenderer data={matchupData} displayMode="review" />);
    expectHeaders(screen.getByRole("table", { name: "Matchup by decade" }), [
      "Decade",
      "Games",
      "BOS W-L",
      "BOS Win %",
      "LAL W-L",
      "LAL Win %",
    ]);
  });

  it("renders lineup summary and lineup leaderboard contracts", () => {
    const summaryData = makeResponse("lineup_summary", {
      metadata: { season: "2025-26", season_type: "Regular Season" },
      sections: {
        summary: [
          {
            lineup: "Jayson Tatum / Jaylen Brown",
            team_abbr: "BOS",
            minutes: 420,
            off_rating: 122.4,
            def_rating: 111.4,
            net_rating: 11,
            pace: 99.8,
          },
        ],
      },
    });
    const { rerender } = render(
      <ResultRenderer data={summaryData} displayMode="review" />,
    );

    expect(screen.getByText(/Jayson Tatum \/ Jaylen Brown posted/)).toBeInTheDocument();
    expect(screen.getByText(/net rating/)).toBeInTheDocument();
    expect(screen.queryByText("Summary")).not.toBeInTheDocument();

    const leaderboardData = makeResponse("lineup_leaderboard", {
      queryClass: "leaderboard",
      sections: {
        leaderboard: [
          {
            rank: 1,
            lineup: "Nikola Jokic / Jamal Murray",
            team_abbr: "DEN",
            minutes: 500,
            off_rating: 125.2,
            def_rating: 110.2,
            net_rating: 15,
          },
        ],
      },
    });

    rerender(<ResultRenderer data={leaderboardData} displayMode="review" />);
    const table = screen.getByRole("table", { name: "Leaderboard" });
    expectHeaders(table, ["#", "Name", "Net", "TM", "Minutes", "ORtg", "DRtg"]);
    expect(within(table).getByText("Nikola Jokic / Jamal Murray")).toBeInTheDocument();
  });
});
