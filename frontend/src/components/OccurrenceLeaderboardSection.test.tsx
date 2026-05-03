import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import OccurrenceLeaderboardSection from "./OccurrenceLeaderboardSection";

describe("OccurrenceLeaderboardSection", () => {
  it("renders player occurrence leaders with count hero and condition context", () => {
    render(
      <OccurrenceLeaderboardSection
        metadata={{
          route: "player_occurrence_leaders",
          season: "2024-25",
          season_type: "Regular Season",
          occurrence_event: { stat: "pts", min_value: 30 },
        }}
        sections={{
          leaderboard: [
            {
              rank: 1,
              player_id: 203999,
              player_name: "Nikola Jokic",
              team_abbr: "DEN",
              games_played: 72,
              "games_pts_30+": 12,
              season: "2024-25",
            },
          ],
        }}
      />,
    );

    const ranked = screen.getByLabelText("Occurrence leaderboard rankings");
    expect(within(ranked).getByText("Nikola Jokic")).toBeInTheDocument();
    expect(within(ranked).getByText("Event Count")).toBeInTheDocument();
    expect(within(ranked).getByText("12")).toBeInTheDocument();
    expect(within(ranked).getByText("30+ PTS")).toBeInTheDocument();
    expect(within(ranked).getByText("72 games")).toBeInTheDocument();
    expect(screen.getByText("Full Occurrence Detail")).toBeInTheDocument();
  });

  it("renders team occurrence leaders with record context", () => {
    render(
      <OccurrenceLeaderboardSection
        metadata={{
          route: "team_occurrence_leaders",
          season: "2024-25",
          season_type: "Regular Season",
          occurrence_event: { stat: "pts", min_value: 120 },
        }}
        sections={{
          leaderboard: [
            {
              rank: 1,
              team_id: 1610612738,
              team_name: "Boston Celtics",
              team_abbr: "BOS",
              games_played: 82,
              wins: 18,
              losses: 7,
              "games_pts_120+": 18,
              season: "2024-25",
            },
          ],
        }}
      />,
    );

    const ranked = screen.getByLabelText("Occurrence leaderboard rankings");
    expect(within(ranked).getByText("Boston Celtics")).toBeInTheDocument();
    expect(within(ranked).getByText("120+ PTS")).toBeInTheDocument();
    expect(within(ranked).getByText("18-7")).toBeInTheDocument();
    expect(within(ranked).getAllByText("18").length).toBeGreaterThan(0);
  });
});
