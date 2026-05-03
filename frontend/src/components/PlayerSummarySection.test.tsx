import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PlayerSummarySection from "./PlayerSummarySection";
import type { SectionRow } from "../api/types";

function summaryRow(games: number): SectionRow {
  return {
    player_name: "Nikola Jokic",
    games,
    pts_avg: 28.5,
    reb_avg: 11.2,
    ast_avg: 8.7,
  };
}

function gameRow(index: number, overrides: SectionRow = {}): SectionRow {
  const day = String(index).padStart(2, "0");
  return {
    game_id: `game-${day}`,
    game_date: `2025-01-${day}`,
    opponent_team_abbr: "LAL",
    opponent_team_name: "Los Angeles Lakers",
    is_home: index % 2 === 0 ? 1 : 0,
    is_away: index % 2 === 1 ? 1 : 0,
    wl: index % 2 === 0 ? "W" : "L",
    minutes: 34 + index / 10,
    pts: 20 + index,
    reb: 8 + index,
    ast: 5 + index,
    ...overrides,
  };
}

function renderSummary(gameLog: SectionRow[]) {
  render(
    <PlayerSummarySection
      sections={{
        summary: [summaryRow(gameLog.length)],
        game_log: gameLog,
      }}
    />,
  );
}

function recentGameDates(): string[] {
  const list = screen.getByLabelText("Recent games");
  return within(list)
    .getAllByText(/^2025-01-/)
    .map((node) => node.textContent ?? "");
}

describe("PlayerSummarySection", () => {
  it("renders every requested recent game newest first", () => {
    renderSummary(Array.from({ length: 10 }, (_, index) => gameRow(index + 1)));

    expect(
      screen.getByRole("heading", { name: "Recent Games (10)" }),
    ).toBeInTheDocument();
    expect(screen.getByText("10 games")).toBeInTheDocument();
    expect(recentGameDates()).toEqual([
      "2025-01-10",
      "2025-01-09",
      "2025-01-08",
      "2025-01-07",
      "2025-01-06",
      "2025-01-05",
      "2025-01-04",
      "2025-01-03",
      "2025-01-02",
      "2025-01-01",
    ]);
  });

  it("renders five-game samples without truncating further", () => {
    renderSummary(Array.from({ length: 5 }, (_, index) => gameRow(index + 1)));

    expect(
      screen.getByRole("heading", { name: "Recent Games (5)" }),
    ).toBeInTheDocument();
    expect(recentGameDates()).toHaveLength(5);
  });

  it("shows matchup, score, and richer box stats when available", () => {
    renderSummary([
      gameRow(1, {
        is_home: 1,
        is_away: 0,
        team_score: 118,
        opponent_score: 111,
        fgm: 12,
        fga: 20,
        fg3m: 3,
        fg3a: 7,
        ftm: 4,
        fta: 5,
        stl: 2,
        blk: 1,
        tov: 3,
        plus_minus: 9,
      }),
    ]);

    expect(screen.getByLabelText("Los Angeles Lakers (LAL)")).toBeInTheDocument();
    expect(screen.getByText("vs LAL")).toBeInTheDocument();
    expect(screen.getByText("118-111")).toBeInTheDocument();
    expect(screen.getByText("12-20")).toBeInTheDocument();
    expect(screen.getByText("3-7")).toBeInTheDocument();
    expect(screen.getByText("4-5")).toBeInTheDocument();
    expect(screen.getByText("STL")).toBeInTheDocument();
    expect(screen.getByText("BLK")).toBeInTheDocument();
    expect(screen.getByText("TOV")).toBeInTheDocument();
    expect(screen.getByText("+9")).toBeInTheDocument();
  });

  it("caps broad game logs at thirty visible rows", () => {
    renderSummary(Array.from({ length: 35 }, (_, index) => gameRow(index + 1)));

    expect(
      screen.getByRole("heading", { name: "Recent Games (30)" }),
    ).toBeInTheDocument();
    expect(screen.getByText("30 games")).toBeInTheDocument();
    expect(screen.getByText("showing 30 of 35 games")).toBeInTheDocument();
    expect(recentGameDates()).toHaveLength(30);
    expect(screen.getByText("2025-01-35")).toBeInTheDocument();
    expect(screen.queryByText("2025-01-05")).not.toBeInTheDocument();
  });
});
