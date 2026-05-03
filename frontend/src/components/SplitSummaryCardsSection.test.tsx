import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import SplitSummaryCardsSection from "./SplitSummaryCardsSection";

describe("SplitSummaryCardsSection", () => {
  it("renders player home-away split cards with stat tiles and an edge row", () => {
    render(
      <SplitSummaryCardsSection
        route="player_split_summary"
        metadata={{
          route: "player_split_summary",
          split_type: "home_away",
          stat: "pts",
          min_value: 30,
          player_context: {
            player_id: 203999,
            player_name: "Nikola Jokic",
          },
        }}
        sections={{
          summary: [
            {
              player_name: "Nikola Jokic",
              season_start: "2024-25",
              season_end: "2024-25",
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
        }}
      />,
    );

    expect(screen.getByText("Player Split Summary")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Nikola Jokic" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Home/Away / 2024-25 / Regular Season / 8 games / 30+ PTS"),
    ).toBeInTheDocument();

    const buckets = screen.getByLabelText("Split buckets");
    expect(within(buckets).getByText("Home")).toBeInTheDocument();
    expect(within(buckets).getByText("Away")).toBeInTheDocument();
    expect(within(buckets).getByText("3-1")).toBeInTheDocument();
    expect(within(buckets).getAllByText("PTS").length).toBeGreaterThan(0);
    expect(within(buckets).getAllByText("REB").length).toBeGreaterThan(0);
    expect(within(buckets).getAllByText("AST").length).toBeGreaterThan(0);
    expect(within(buckets).getAllByText("MIN").length).toBeGreaterThan(0);
    expect(within(buckets).getAllByText("TS%").length).toBeGreaterThan(0);
    expect(within(buckets).getAllByText("3P%").length).toBeGreaterThan(0);
    expect(within(buckets).getAllByText("+/-").length).toBeGreaterThan(0);

    const edges = screen.getByLabelText("Split edges");
    expect(within(edges).getByText("Home +3.2 PPG")).toBeInTheDocument();

    const detail = screen.getByRole("region", {
      name: "Split Comparison Detail",
    });
    expect(within(detail).queryByRole("table")).not.toBeInTheDocument();
  });

  it("renders player wins-losses split cards with the same shape", () => {
    render(
      <SplitSummaryCardsSection
        route="player_split_summary"
        metadata={{
          route: "player_split_summary",
          split_type: "wins_losses",
          player_context: {
            player_id: 201939,
            player_name: "Stephen Curry",
          },
        }}
        sections={{
          summary: [
            {
              player_name: "Stephen Curry",
              season_start: "2024-25",
              season_end: "2024-25",
              season_type: "Regular Season",
              split: "wins_losses",
              games_total: 7,
            },
          ],
          split_comparison: [
            {
              bucket: "wins",
              games: 5,
              wins: 5,
              losses: 0,
              win_pct: 1,
              pts_avg: 32.2,
              reb_avg: 4.4,
              ast_avg: 6.1,
              minutes_avg: 33.8,
              efg_pct_avg: 0.642,
              fg3_pct_avg: 0.451,
              plus_minus_avg: 12.4,
            },
            {
              bucket: "losses",
              games: 2,
              wins: 0,
              losses: 2,
              win_pct: 0,
              pts_avg: 27.1,
              reb_avg: 3.8,
              ast_avg: 5.7,
              minutes_avg: 35.2,
              efg_pct_avg: 0.591,
              fg3_pct_avg: 0.388,
              plus_minus_avg: -5.5,
            },
          ],
        }}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Stephen Curry" }),
    ).toBeInTheDocument();
    const buckets = screen.getByLabelText("Split buckets");
    expect(within(buckets).getByText("Wins")).toBeInTheDocument();
    expect(within(buckets).getByText("Losses")).toBeInTheDocument();
    expect(within(buckets).getByText("5-0")).toBeInTheDocument();
    expect(within(buckets).getAllByText("eFG%").length).toBeGreaterThan(0);

    const edges = screen.getByLabelText("Split edges");
    expect(within(edges).getByText("Wins +5.1 PPG")).toBeInTheDocument();
  });
});
