import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LeaderboardSection from "./LeaderboardSection";

describe("LeaderboardSection", () => {
  it("shows win-loss context for record leaderboards", () => {
    render(
      <LeaderboardSection
        sections={{
          leaderboard: [
            {
              rank: 1,
              team_name: "Boston Celtics",
              team_abbr: "BOS",
              games_played: 82,
              wins: 64,
              losses: 18,
              win_pct: 0.78,
            },
          ],
        }}
      />,
    );

    const ranked = screen.getByLabelText("Ranked leaderboard");
    expect(within(ranked).getByText("78.0%")).toBeInTheDocument();
    expect(within(ranked).getByText("Win Pct")).toBeInTheDocument();
    expect(within(ranked).getByText("64-18")).toBeInTheDocument();
    expect(within(ranked).getByText("82 games")).toBeInTheDocument();
  });

  it("uses wins as the hero metric when wins is the row target", () => {
    render(
      <LeaderboardSection
        sections={{
          leaderboard: [
            {
              rank: 1,
              team_name: "Golden State Warriors",
              team_abbr: "GSW",
              games_played: 82,
              wins: 67,
              losses: 15,
            },
          ],
        }}
      />,
    );

    const ranked = screen.getByLabelText("Ranked leaderboard");
    expect(within(ranked).getByText("67")).toBeInTheDocument();
    expect(within(ranked).getByText("Wins")).toBeInTheDocument();
    expect(within(ranked).getByText("67-15")).toBeInTheDocument();
    expect(within(ranked).getByText("82 games")).toBeInTheDocument();
  });

  it("shows percentage volume companions from total columns", () => {
    render(
      <LeaderboardSection
        sections={{
          leaderboard: [
            {
              rank: 1,
              player_name: "Stephen Curry",
              games_played: 74,
              fg_pct: 0.512,
              fgm_total: 812,
              fga_total: 1586,
            },
          ],
        }}
      />,
    );

    const ranked = screen.getByLabelText("Ranked leaderboard");
    expect(within(ranked).getByText("51.2%")).toBeInTheDocument();
    expect(within(ranked).getByText("FG Pct")).toBeInTheDocument();
    expect(within(ranked).getByText("812/1,586 FG")).toBeInTheDocument();
  });
});
