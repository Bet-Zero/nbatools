import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import StreakSection from "./StreakSection";

describe("StreakSection", () => {
  it("renders player streak cards with condition, status, dates, and averages", () => {
    render(
      <StreakSection
        route="player_streak_finder"
        metadata={{
          route: "player_streak_finder",
          season: "2024-25",
          season_type: "Regular Season",
          player_context: {
            player_id: 203999,
            player_name: "Nikola Jokic",
          },
        }}
        sections={{
          streak: [
            {
              player_name: "Nikola Jokic",
              player_id: 203999,
              condition: "pts>=25",
              streak_length: 6,
              games: 6,
              start_date: "2025-01-01",
              end_date: "2025-01-12",
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
        }}
      />,
    );

    expect(screen.getByText("Streaks")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Nikola Jokic" }),
    ).toBeInTheDocument();
    expect(screen.getByText("25+ PTS")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("6 games / 2024-25 / Regular Season")).toBeInTheDocument();
    expect(screen.getByText("5-1")).toBeInTheDocument();
    expect(screen.getByText("TS%")).toBeInTheDocument();

    const span = screen.getByLabelText("Streak span");
    expect(within(span).getByText("2025-01-01")).toBeInTheDocument();
    expect(within(span).getByText("2025-01-12")).toBeInTheDocument();

    const detail = screen.getByRole("region", { name: "Full Streak Detail" });
    expect(within(detail).queryByRole("table")).not.toBeInTheDocument();
  });
});
