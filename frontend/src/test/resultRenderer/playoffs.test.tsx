import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResultRenderer from "../../components/results/ResultRenderer";
import { makeResponse } from "./helpers";

describe("ResultRenderer playoff patterns", () => {

  it("renders playoff appearances as a leaderboard pattern", () => {
    const data = makeResponse({
      query: "most playoff appearances",
      route: "playoff_appearances",
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          query_text: "most playoff appearances",
          route: "playoff_appearances",
          season_type: "Playoffs",
        },
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            {
              rank: 1,
              team_abbr: "MIA",
              team_name: "Miami Heat",
              appearances: 23,
              round: "Playoffs",
              seasons: "1996-97 to 2024-25",
            },
          ],
        },
        current_through: "2025-06-22",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "The Miami Heat had the most playoff appearances from 1996-97 to 2024-25, with 23.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Appearances" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Round" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Seasons" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Playoff leaderboard rankings"),
    ).not.toBeInTheDocument();
  });


  it("renders playoff history as a hero plus season table", () => {
    const data = makeResponse({
      query: "Lakers playoff history",
      route: "playoff_history",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          query_text: "Lakers playoff history",
          route: "playoff_history",
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
              season_start: "2019-20",
              season_end: "2024-25",
              season_type: "Playoffs",
              games: 84,
              wins: 52,
              losses: 32,
              win_pct: 0.619,
              seasons_appeared: 5,
              titles: 1,
            },
          ],
          by_season: [
            {
              season: "1999-00",
              wins: 6,
              losses: 5,
              deepest_round: "Unknown Round",
              result: "Lost",
              opponent_team_abbr: "POR",
            },
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
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(screen.getByLabelText("Playoff history result")).toBeInTheDocument();
    expect(screen.getAllByText("Los Angeles Lakers").length).toBeGreaterThan(0);
    const history = screen.getByLabelText("Playoff history result");
    expect(history.textContent).toContain(
      "From 2019-20 through 2024-25, the Los Angeles Lakers made the playoffs 5 times and went 52-32.",
    );
    expect(
      within(history).getByText("made the playoffs", { exact: false }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Playoff season breakdown" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Round Reached" }),
    ).toBeInTheDocument();
    expect(screen.getByText("First Round")).toBeInTheDocument();
    expect(screen.queryByText("Unknown Round")).not.toBeInTheDocument();
    expect(screen.getByText("Round unavailable")).toBeInTheDocument();
    expect(screen.getByText("1-4")).toBeInTheDocument();
    expect(screen.getByText("Postseason Summary Detail")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Show postseason summary" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Season Breakdown Detail")).not.toBeInTheDocument();
  });


  it("renders playoff round records through the playoff history pattern", () => {
    const data = makeResponse({
      query: "best Finals record",
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
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByLabelText("Playoff round record result"),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Boston Celtics").length).toBeGreaterThan(0);
    const roundRecord = screen.getByLabelText("Playoff round record result");
    expect(roundRecord.textContent).toContain(
      "The Boston Celtics have the best Finals record from 1980-81 to 2024-25, going 28-14, a 66.7% win rate, across 42 games.",
    );
    expect(
      within(roundRecord).getByText("Finals record", { exact: false }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Playoff round records" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Win Pct" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("66.7%").length).toBeGreaterThan(0);
    expect(screen.getAllByText("28-14").length).toBeGreaterThan(0);
    expect(screen.queryByText("Playoff Round Detail")).not.toBeInTheDocument();
  });


  it("renders playoff matchup history as a series table", () => {
    const data = makeResponse({
      query: "Celtics vs Heat playoff matchups",
      route: "playoff_matchup_history",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: {
          query_text: "Celtics vs Heat playoff matchups",
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
              season: "1999-00",
              round: "Unknown Round",
              winner_team_name: "Miami Heat",
              series_result: "MIA won 3-2",
              BOS_wins: 2,
              BOS_losses: 3,
              MIA_wins: 3,
              MIA_losses: 2,
            },
            {
              season: "2022-23",
              round: "Conference Finals",
              winner_team_name: "Miami Heat",
              series_result: "MIA won 4-3",
              BOS_wins: 3,
              BOS_losses: 4,
              MIA_wins: 4,
              MIA_losses: 3,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(screen.getByLabelText("Playoff matchup result")).toBeInTheDocument();
    expect(screen.getAllByText("Boston Celtics").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Miami Heat").length).toBeGreaterThan(0);
    expect(
      screen.getByText(
        "The Boston Celtics lead the Miami Heat 4-3 in playoff games. The Miami Heat lead 2-0 in playoff series.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Playoff series" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "BOS" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "MIA" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Winner" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Series Result" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Season" }),
    ).toHaveAttribute("data-mobile-priority", "primary");
    expect(
      screen.getByRole("columnheader", { name: "Round" }),
    ).toHaveAttribute("data-mobile-priority", "primary");
    expect(
      screen.getByRole("columnheader", { name: "Winner" }),
    ).toHaveAttribute("data-mobile-priority", "primary");
    expect(
      screen.getByRole("columnheader", { name: "Series Result" }),
    ).toHaveAttribute("data-mobile-priority", "primary");
    expect(screen.getByRole("columnheader", { name: "BOS" })).toHaveAttribute(
      "data-mobile-priority",
      "secondary",
    );
    expect(screen.getByRole("columnheader", { name: "MIA" })).toHaveAttribute(
      "data-mobile-priority",
      "secondary",
    );
    expect(
      screen.getByRole("columnheader", { name: "Games" }),
    ).toHaveAttribute("data-mobile-priority", "secondary");
    expect(screen.getByText("MIA won 4-3")).toBeInTheDocument();
    expect(screen.queryByText("Unknown Round")).not.toBeInTheDocument();
    expect(screen.getByText("Round unavailable")).toBeInTheDocument();
    expect(screen.getByText("3-4")).toBeInTheDocument();
    expect(screen.getAllByText("4-3").length).toBeGreaterThan(0);
    expect(screen.queryByText("Series Detail")).not.toBeInTheDocument();
  });
});
