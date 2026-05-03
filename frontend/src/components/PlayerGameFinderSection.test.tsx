import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PlayerGameFinderSection from "./PlayerGameFinderSection";

describe("PlayerGameFinderSection", () => {
  it("renders a condition header and recent-first player game cards", () => {
    render(
      <PlayerGameFinderSection
        metadata={{
          query_text: "games where Jokic had over 25 points and over 10 rebounds",
          route: "player_game_finder",
          player_context: {
            player_id: 203999,
            player_name: "Nikola Jokic",
          },
          threshold_conditions: [
            { stat: "pts", min_value: 25, max_value: null },
            { stat: "reb", min_value: 10, max_value: null },
          ],
        }}
        sections={{
          finder: [
            {
              game_id: "001",
              game_date: "2025-01-10",
              player_name: "Nikola Jokic",
              player_id: 203999,
              team_name: "Denver Nuggets",
              team_abbr: "DEN",
              team_id: 1610612743,
              opponent_team_name: "Los Angeles Lakers",
              opponent_team_abbr: "LAL",
              is_home: 1,
              wl: "W",
              team_score: 121,
              opponent_score: 114,
              season: "2024-25",
              season_type: "Regular Season",
              minutes: 37,
              pts: 28,
              reb: 14,
              ast: 9,
              fg3m: 2,
              fg3a: 5,
              fgm: 11,
              fga: 19,
              ftm: 4,
              fta: 5,
              stl: 1,
              blk: 2,
              tov: 3,
              plus_minus: 11,
            },
            {
              game_id: "002",
              game_date: "2025-02-12",
              player_name: "Nikola Jokic",
              player_id: 203999,
              team_name: "Denver Nuggets",
              team_abbr: "DEN",
              team_id: 1610612743,
              opponent_team_name: "Boston Celtics",
              opponent_team_abbr: "BOS",
              is_away: 1,
              wl: "L",
              team_score: 109,
              opponent_score: 115,
              season: "2024-25",
              season_type: "Regular Season",
              minutes: 35,
              pts: 31,
              reb: 12,
              ast: 8,
              fg3m: 3,
              fg3a: 6,
              fgm: 12,
              fga: 21,
              ftm: 4,
              fta: 4,
              stl: 0,
              blk: 1,
              tov: 4,
              plus_minus: -6,
            },
          ],
        }}
      />,
    );

    expect(screen.getByText("25+ PTS, 10+ REB")).toBeInTheDocument();
    expect(
      screen.getAllByRole("heading", { name: "Nikola Jokic" }).length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText("2 games found").length).toBeGreaterThan(0);

    const cards = screen.getByLabelText("Player game cards");
    const firstCard = cards.children.item(0) as HTMLElement;
    expect(within(firstCard).getByText("2025-02-12")).toBeInTheDocument();

    expect(within(cards).getByText("at BOS")).toBeInTheDocument();
    expect(within(cards).getByText("109-115")).toBeInTheDocument();
    expect(within(cards).getAllByText("PTS").length).toBeGreaterThan(0);
    expect(within(cards).getAllByText("REB").length).toBeGreaterThan(0);
    expect(within(cards).getAllByText("AST").length).toBeGreaterThan(0);
    expect(within(cards).getAllByText("3PM").length).toBeGreaterThan(0);
    expect(within(cards).getByText("FG 12/21")).toBeInTheDocument();
    expect(within(cards).getByText("3P 3/6")).toBeInTheDocument();
    expect(within(cards).getByText("FT 4/4")).toBeInTheDocument();
    expect(within(cards).getByText("+/- -6")).toBeInTheDocument();

    const detail = screen.getByRole("region", { name: "Player Game Detail" });
    expect(within(detail).queryByRole("table")).not.toBeInTheDocument();
  });

  it("renders point-game phrasing for single-stat finder queries", () => {
    render(
      <PlayerGameFinderSection
        metadata={{
          query_text: "Curry's 50-point games",
          route: "player_game_finder",
          player_context: {
            player_id: 201939,
            player_name: "Stephen Curry",
          },
          occurrence_event: { stat: "pts", min_value: 50 },
        }}
        sections={{
          finder: [
            {
              game_id: "003",
              game_date: "2025-03-01",
              player_name: "Stephen Curry",
              player_id: 201939,
              team_name: "Golden State Warriors",
              team_abbr: "GSW",
              team_id: 1610612744,
              opponent_team_name: "New York Knicks",
              opponent_team_abbr: "NYK",
              is_home: 1,
              wl: "W",
              pts: 50,
              reb: 4,
              ast: 6,
              fg3m: 10,
              fg3a: 17,
            },
          ],
        }}
      />,
    );

    expect(screen.getByText("50-point games")).toBeInTheDocument();
    expect(
      screen.getAllByRole("heading", { name: "Stephen Curry" }).length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText("1 game found").length).toBeGreaterThan(0);
    expect(screen.getByText("50")).toBeInTheDocument();
    expect(screen.getByText("3P 10/17")).toBeInTheDocument();
  });

  it("sorts ranked finder displays by the requested metric", () => {
    render(
      <PlayerGameFinderSection
        metadata={{
          route: "player_game_finder",
          player_context: {
            player_id: 203999,
            player_name: "Nikola Jokic",
          },
          stat: "pts",
          sort_by: "stat",
          ranked_intent: true,
        }}
        sections={{
          finder: [
            {
              game_id: "004",
              game_date: "2025-02-01",
              player_name: "Nikola Jokic",
              player_id: 203999,
              team_abbr: "DEN",
              opponent_team_abbr: "UTA",
              is_home: 1,
              pts: 31,
              reb: 12,
              ast: 8,
              fg3m: 1,
            },
            {
              game_id: "005",
              game_date: "2025-01-12",
              player_name: "Nikola Jokic",
              player_id: 203999,
              team_abbr: "DEN",
              opponent_team_abbr: "PHX",
              is_away: 1,
              pts: 45,
              reb: 10,
              ast: 7,
              fg3m: 4,
            },
          ],
        }}
      />,
    );

    const cards = screen.getByLabelText("Player game cards");
    const firstCard = cards.children.item(0) as HTMLElement;
    expect(within(firstCard).getByText("2025-01-12")).toBeInTheDocument();
    expect(within(firstCard).getByText("45")).toBeInTheDocument();
  });
});
