import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResultRenderer from "../../components/results/ResultRenderer";
import { makeResponse } from "./helpers";

describe("ResultRenderer rolling stretch patterns", () => {

  it("renders league-wide rolling stretch leaderboards with the rolling stretch pattern", () => {
    const data = makeResponse({
      query: "best 3-game scoring stretches this season",
      route: "player_stretch_leaderboard",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          query_text: "best 3-game scoring stretches this season",
          route: "player_stretch_leaderboard",
          season: "2025-26",
          season_type: "Regular Season",
          window_size: 3,
          stretch_metric: "pts",
          total_count: 24,
        },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              player_name: "Luka Doncic",
              player_id: 1629029,
              team_abbr: "LAL",
              window_size: 3,
              stretch_metric: "pts",
              window_start_date: "2026-03-16",
              window_end_date: "2026-03-19",
              games_in_window: 3,
              stretch_value: 45.333,
              games_played: 3,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Best 3-game scoring stretch this season: Luka Doncic averaged 45.3 PPG from Mar 16 to Mar 19.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "PPG" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Season" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Rolling stretch leaderboard" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Showing top 1 of 24")).toBeInTheDocument();
    expect(
      screen.queryByRole("table", { name: "Leaderboard" }),
    ).not.toBeInTheDocument();
  });


  it("renders player-oriented rolling stretch leaderboards with one window per player", () => {
    const data = makeResponse({
      query: "Which players have the hottest 3-game scoring stretch this year?",
      route: "player_stretch_leaderboard",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          query_text:
            "Which players have the hottest 3-game scoring stretch this year?",
          route: "player_stretch_leaderboard",
          season: "2025-26",
          season_type: "Regular Season",
          window_size: 3,
          stretch_metric: "pts",
          stretch_display_mode: "players",
        },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              player_name: "Luka Doncic",
              player_id: 1629029,
              team_abbr: "LAL",
              window_size: 3,
              stretch_metric: "pts",
              window_start_date: "2026-03-16",
              window_end_date: "2026-03-19",
              window_end_season: "2025-26",
              stretch_value: 45.333,
            },
            {
              rank: 2,
              player_name: "Luka Doncic",
              player_id: 1629029,
              team_abbr: "LAL",
              window_size: 3,
              stretch_metric: "pts",
              window_start_date: "2026-03-18",
              window_end_date: "2026-03-21",
              window_end_season: "2025-26",
              stretch_value: 44.667,
            },
            {
              rank: 3,
              player_name: "Devin Booker",
              player_id: 1626164,
              team_abbr: "PHX",
              window_size: 3,
              stretch_metric: "pts",
              window_start_date: "2026-02-10",
              window_end_date: "2026-02-14",
              window_end_season: "2025-26",
              stretch_value: 41,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Luka Doncic had the hottest 3-game scoring stretch this season, averaging 45.3 PPG from Mar 16 to Mar 19.",
      ),
    ).toBeInTheDocument();
    const table = screen.getByRole("table", {
      name: "Rolling stretch leaderboard",
    });
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(3);
    expect(within(rows[1]).getByText("Luka Doncic")).toBeInTheDocument();
    expect(within(rows[2]).getByText("Devin Booker")).toBeInTheDocument();
  });


  it("renders named-player rolling stretches with top windows and optional game log", () => {
    const data = makeResponse({
      query: "Booker hottest 4-game scoring stretch",
      route: "player_stretch_leaderboard",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          query_text: "Booker hottest 4-game scoring stretch",
          route: "player_stretch_leaderboard",
          season: "2025-26",
          season_type: "Regular Season",
          window_size: 4,
          stretch_metric: "pts",
          player: "Devin Booker",
          player_context: {
            player_id: 1626164,
            player_name: "Devin Booker",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              player_name: "Devin Booker",
              player_id: 1626164,
              team_abbr: "PHX",
              window_size: 4,
              stretch_metric: "pts",
              window_start_date: "2026-02-10",
              window_end_date: "2026-02-17",
              window_start_season: "2025-26",
              games_in_window: 4,
              window_end_season: "2025-26",
              stretch_value: 39.75,
            },
          ],
          best_window_game_log: [
            {
              game_id: 10,
              game_date: "2026-02-10",
              player_name: "Devin Booker",
              player_id: 1626164,
              team_abbr: "PHX",
              opponent_team_abbr: "DAL",
              wl: "W",
              pts: 41,
              reb: 5,
              ast: 8,
            },
            {
              game_id: 11,
              game_date: "2026-02-12",
              player_name: "Devin Booker",
              player_id: 1626164,
              team_abbr: "PHX",
              opponent_team_abbr: "DEN",
              wl: "L",
              pts: 38,
              reb: 4,
              ast: 9,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Devin Booker's best 4-game scoring stretch in the 2025-26 regular season: averaging 39.8 PPG from Feb 10 to Feb 17.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Top Windows")).toBeInTheDocument();
    expect(screen.getByText("Best Window Games")).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Player rolling stretch windows" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Season" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Best stretch game log" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("table", { name: "Leaderboard" }),
    ).not.toBeInTheDocument();
  });
});
