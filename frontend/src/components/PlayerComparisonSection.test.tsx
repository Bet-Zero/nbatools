import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PlayerComparisonSection from "./PlayerComparisonSection";

describe("PlayerComparisonSection", () => {
  it("renders player cards, context, metric edges, and collapsed raw details", () => {
    render(
      <PlayerComparisonSection
        metadata={{
          query_text: "Jokic vs Embiid this season",
          route: "player_compare",
          season: "2025-26",
          season_type: "Regular Season",
          players_context: [
            { player_id: 203999, player_name: "Nikola Jokic" },
            { player_id: 203954, player_name: "Joel Embiid" },
          ],
        }}
        sections={{
          summary: [
            {
              player_name: "Nikola Jokic",
              team_name: "Denver Nuggets",
              team_abbr: "DEN",
              team_id: 1610612743,
              games: 72,
              wins: 51,
              losses: 21,
              win_pct: 0.708,
              pts_avg: 26.4,
              reb_avg: 12.1,
              ast_avg: 9.3,
              minutes_avg: 34.6,
              ts_pct_avg: 0.651,
              plus_minus_avg: 7.8,
            },
            {
              player_name: "Joel Embiid",
              team_name: "Philadelphia 76ers",
              team_abbr: "PHI",
              team_id: 1610612755,
              games: 68,
              wins: 44,
              losses: 24,
              win_pct: 0.647,
              pts_avg: 30.1,
              reb_avg: 10.8,
              ast_avg: 5.7,
              minutes_avg: 33.4,
              efg_pct_avg: 0.562,
              plus_minus_avg: 5.2,
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
        }}
      />,
    );

    expect(screen.getByText("Nikola Jokic vs Joel Embiid")).toBeInTheDocument();

    const headerContext = screen.getByLabelText("Comparison context");
    expect(within(headerContext).getByText("2025-26")).toBeInTheDocument();
    expect(
      within(headerContext).getByText("Regular Season"),
    ).toBeInTheDocument();
    expect(
      within(headerContext).getByText("72 vs 68 games"),
    ).toBeInTheDocument();

    const players = screen.getByLabelText("Compared players");
    expect(within(players).getByText("Nikola Jokic")).toBeInTheDocument();
    expect(within(players).getByText("Joel Embiid")).toBeInTheDocument();
    expect(within(players).getByText("Denver Nuggets")).toBeInTheDocument();
    expect(within(players).getByText("Philadelphia 76ers")).toBeInTheDocument();
    expect(within(players).getByText("51-21")).toBeInTheDocument();
    expect(within(players).getByText("70.8% win pct")).toBeInTheDocument();
    expect(within(players).getByText("TS%")).toBeInTheDocument();
    expect(within(players).getByText("34.6")).toBeInTheDocument();

    const metrics = screen.getByLabelText("Metric comparison cards");
    expect(
      within(metrics).getByText("Joel Embiid +3.7 PTS"),
    ).toBeInTheDocument();
    expect(
      within(metrics).getByText("Nikola Jokic +3.6 AST"),
    ).toBeInTheDocument();

    const summaryDetail = screen.getByRole("region", {
      name: "Player Summary Detail",
    });
    const metricDetail = screen.getByRole("region", {
      name: "Full Metric Detail",
    });
    expect(within(summaryDetail).queryByRole("table")).not.toBeInTheDocument();
    expect(within(metricDetail).queryByRole("table")).not.toBeInTheDocument();
  });

  it("distinguishes career averages from career totals", () => {
    render(
      <PlayerComparisonSection
        metadata={{
          query_text: "LeBron vs MJ career",
          route: "player_compare",
          start_season: "1984-85",
          end_season: "2025-26",
          season_type: "Regular Season",
          players_context: [
            { player_id: 2544, player_name: "LeBron James" },
            { player_id: 893, player_name: "Michael Jordan" },
          ],
        }}
        sections={{
          summary: [
            {
              player_name: "LeBron James",
              games: 1560,
              pts_avg: 27.1,
              reb_avg: 7.5,
              ast_avg: 7.4,
            },
            {
              player_name: "Michael Jordan",
              games: 1072,
              pts_avg: 30.1,
              reb_avg: 6.2,
              ast_avg: 5.3,
            },
          ],
          comparison: [
            {
              metric: "pts_avg",
              "LeBron James": 27.1,
              "Michael Jordan": 30.1,
            },
            {
              metric: "pts_sum",
              "LeBron James": 42300,
              "Michael Jordan": 32292,
            },
          ],
        }}
      />,
    );

    expect(
      screen.getByText("LeBron James vs Michael Jordan"),
    ).toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Comparison context")).getByText(
        "Career averages and totals",
      ),
    ).toBeInTheDocument();

    const metrics = screen.getByLabelText("Metric comparison cards");
    expect(within(metrics).getByText("PTS Avg")).toBeInTheDocument();
    expect(within(metrics).getByText("PTS Total")).toBeInTheDocument();
    expect(
      within(metrics).getByText("Michael Jordan +3.0 PTS"),
    ).toBeInTheDocument();
    expect(
      within(metrics).getByText("LeBron James +10,008 PTS"),
    ).toBeInTheDocument();
  });
});
