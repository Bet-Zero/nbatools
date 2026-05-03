import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PlayoffSection from "./PlayoffSection";

describe("PlayoffSection", () => {
  it("renders playoff history hero stats and visible season breakdown", () => {
    render(
      <PlayoffSection
        queryClass="summary"
        route="playoff_history"
        metadata={{
          route: "playoff_history",
          team_context: {
            team_id: 1610612747,
            team_abbr: "LAL",
            team_name: "Los Angeles Lakers",
          },
        }}
        sections={{
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
              finals: 2,
              conference_finals: 3,
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
        }}
      />,
    );

    expect(screen.getByText("Playoff History")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Los Angeles Lakers" }),
    ).toBeInTheDocument();

    const stats = screen.getByLabelText("Postseason summary stats");
    expect(within(stats).getByText("Seasons")).toBeInTheDocument();
    expect(within(stats).getByText("5")).toBeInTheDocument();
    expect(within(stats).getByText("52-32")).toBeInTheDocument();
    expect(within(stats).getByText("Games")).toBeInTheDocument();
    expect(within(stats).getByText("84")).toBeInTheDocument();
    expect(within(stats).getByText("Titles")).toBeInTheDocument();
    expect(within(stats).getByText("Finals")).toBeInTheDocument();
    expect(within(stats).getByText("Conf Finals")).toBeInTheDocument();

    const breakdown = screen.getByLabelText("Playoff season breakdown");
    expect(within(breakdown).getByText("2023-24")).toBeInTheDocument();
    expect(within(breakdown).getByText("First Round")).toBeInTheDocument();
    expect(within(breakdown).getByText("1-4")).toBeInTheDocument();
    expect(within(breakdown).getAllByText("DEN").length).toBeGreaterThan(0);

    const detail = screen.getByRole("region", { name: "Season Breakdown" });
    expect(within(detail).queryByRole("table")).not.toBeInTheDocument();
  });
});
