import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResultRenderer from "../../components/results/ResultRenderer";
import { makeResponse } from "./helpers";

describe("ResultRenderer game-log patterns", () => {

  it("renders player game finder rows through the game-log pattern", () => {
    const data = makeResponse({
      query: "games where Jokic had over 25 points and 10 rebounds",
      route: "player_game_finder",
      result: {
        query_class: "finder",
        result_status: "ok",
        metadata: {
          query_text: "games where Jokic had over 25 points and 10 rebounds",
          route: "player_game_finder",
          season: "2025-26",
          season_type: "Regular Season",
          stat: "pts",
          min_value: 25.0001,
          threshold_conditions: [
            { stat: "pts", min_value: 25.0001, max_value: null },
          ],
          player_context: {
            player_id: 203999,
            player_name: "Nikola Jokic",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          finder: [
            {
              rank: 1,
              game_id: 1,
              game_date: "2026-03-22",
              player_id: 203999,
              player_name: "Nikola Jokic",
              team_id: 1610612743,
              team_abbr: "DEN",
              team_name: "Denver Nuggets",
              opponent_team_id: 1610612757,
              opponent_team_abbr: "POR",
              opponent_team_name: "Portland Trail Blazers",
              is_home: 1,
              wl: "W",
              minutes: 35,
              pts: 32,
              reb: 14,
              ast: 10,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(screen.getByRole("table", { name: "Game log" })).toBeInTheDocument();
    expect(
      screen.queryByRole("columnheader", { name: "Player" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "PTS" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Mar 22")).toBeInTheDocument();
    expect(screen.queryByText("Player Game Detail")).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText("Player game cards"),
    ).not.toBeInTheDocument();
  });


  it("uses count_phrase as the primary finder headline when count metadata is present", () => {
    const data = makeResponse({
      query: "how many Jokic 30 point games this season",
      route: "player_game_finder",
      result: {
        query_class: "count",
        result_status: "ok",
        metadata: {
          query_text: "how many Jokic 30 point games this season",
          route: "player_game_finder",
          season: "2025-26",
          season_type: "Regular Season",
          stat: "pts",
          min_value: 30.0001,
          primary_count: 2,
          count_phrase:
            "Nikola Jokic has had 2 games with at least 30 points this season.",
          player_context: {
            player_id: 203999,
            player_name: "Nikola Jokic",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          count: [{ count: 2 }],
          finder: [
            {
              game_id: 1,
              game_date: "2026-03-22",
              player_id: 203999,
              player_name: "Nikola Jokic",
              team_abbr: "DEN",
              opponent_team_abbr: "POR",
              is_home: 1,
              wl: "W",
              pts: 32,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Nikola Jokic has had 2 games with at least 30 points this season.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Game log" })).toBeInTheDocument();
  });

  it("renders a zero-count hero without finder rows", () => {
    const data = makeResponse({
      query: "How many 100 point games did LeBron have in 2024-25?",
      route: "player_game_finder",
      result: {
        query_class: "count",
        result_status: "ok",
        metadata: {
          query_text: "How many 100 point games did LeBron have in 2024-25?",
          route: "player_game_finder",
          player: "LeBron James",
          primary_count: 0,
          count_phrase:
            "LeBron James has had 0 games with at least 100 points in 2024-25.",
        },
        notes: [],
        caveats: [],
        sections: { count: [{ count: 0 }] },
        current_through: "2025-04-13",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "LeBron James has had 0 games with at least 100 points in 2024-25.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: "Game log result" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("No Displayable Rows")).not.toBeInTheDocument();
    expect(screen.queryByRole("table", { name: "Game log" })).not.toBeInTheDocument();
  });

  it("renders a count-only fallback when backend prose is absent", () => {
    const data = makeResponse({
      query: "How many matching games?",
      route: "game_finder",
      result: {
        query_class: "count",
        result_status: "ok",
        metadata: { route: "game_finder", primary_count: 0 },
        notes: [],
        caveats: [],
        sections: { count: [{ count: 0 }] },
      },
    });

    render(<ResultRenderer data={data} />);

    expect(screen.getByText("0 matching games.")).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: "Game log result" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("No Displayable Rows")).not.toBeInTheDocument();
  });


  it("adds a plain-English count headline for player finder rows without backend copy", () => {
    const finderRows = Array.from({ length: 17 }, (_value, index) => ({
      rank: index + 1,
      game_id: index + 1,
      game_date: `2026-01-${String(index + 1).padStart(2, "0")}`,
      season: "2025-26",
      season_type: "Regular Season",
      player_id: 201939,
      player_name: "Stephen Curry",
      team_abbr: "GSW",
      team_name: "Golden State Warriors",
      opponent_team_abbr: "HOU",
      opponent_team_name: "Houston Rockets",
      is_home: 1,
      wl: index % 2 === 0 ? "W" : "L",
      minutes: 31,
      pts: 29,
      fg3m: 5,
    }));
    const data = makeResponse({
      query: "Curry 5+ threes this season",
      route: "player_game_finder",
      result: {
        query_class: "finder",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: { finder: finderRows },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText("Stephen Curry had 17 games with 5+ threes this season."),
    ).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Game log" })).toBeInTheDocument();
  });


  it("renders team game finder rows without a player column", () => {
    const data = makeResponse({
      query: "Celtics recent games",
      route: "game_finder",
      result: {
        query_class: "finder",
        result_status: "ok",
        metadata: {
          query_text: "Celtics recent games",
          route: "game_finder",
          season: "2025-26",
          season_type: "Regular Season",
          team_context: {
            team_id: 1610612738,
            team_abbr: "BOS",
            team_name: "Boston Celtics",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          finder: [
            {
              rank: 1,
              game_id: 1,
              game_date: "2026-04-12",
              team_id: 1610612738,
              team_abbr: "BOS",
              team_name: "Boston Celtics",
              opponent_team_abbr: "ORL",
              opponent_team_name: "Orlando Magic",
              is_home: 1,
              wl: "W",
              pts: 113,
              opponent_pts: 108,
              reb: 46,
              ast: 24,
              fgm: 41,
              fga: 88,
              fg3m: 14,
              fg3a: 36,
              ftm: 17,
              fta: 20,
              tov: 12,
              plus_minus: 5,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByRole("columnheader", { name: "Team" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("columnheader", { name: "Player" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Score" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Opp PTS" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Margin" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "3PM" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "FG" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "FT" }),
    ).toBeInTheDocument();
    expect(screen.getByText("113-108")).toBeInTheDocument();
    expect(screen.getByText("+5")).toBeInTheDocument();
    expect(screen.queryByText("Game Detail")).not.toBeInTheDocument();
  });


  it("renders team count game logs with defensive condition columns", () => {
    const data = makeResponse({
      query: "How often have the Lakers held opponents under 100 points this year?",
      route: "game_finder",
      result: {
        query_class: "count",
        result_status: "ok",
        metadata: {
          query_text:
            "How often have the Lakers held opponents under 100 points this year?",
          route: "game_finder",
          season: "2025-26",
          season_type: "Regular Season",
          stat: "opponent_pts",
          max_value: 99.9999,
          primary_count: 2,
          count_phrase:
            "The Lakers have held opponents under 100 points 2 times this season, going 1-1.",
          team_context: {
            team_id: 1610612747,
            team_abbr: "LAL",
            team_name: "Lakers",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          finder: [
            {
              game_id: 1,
              game_date: "2026-01-10",
              team_abbr: "LAL",
              opponent_team_abbr: "UTA",
              is_home: 1,
              wl: "W",
              pts: 108,
              opponent_pts: 95,
              reb: 44,
              ast: 25,
              fg3m: 12,
              tov: 10,
              plus_minus: 13,
            },
            {
              game_id: 2,
              game_date: "2026-02-12",
              team_abbr: "LAL",
              opponent_team_abbr: "DAL",
              is_away: 1,
              wl: "L",
              pts: 91,
              opponent_pts: 98,
              reb: 39,
              ast: 20,
              fg3m: 9,
              tov: 14,
              plus_minus: -7,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "The Lakers have held opponents under 100 points 2 times this season, going 1-1.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Opp PTS" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Margin" }),
    ).toBeInTheDocument();
    expect(screen.getByText("95")).toBeInTheDocument();
    expect(screen.getByText("-7")).toBeInTheDocument();
  });


  it("caps long product game logs and can expand/collapse them", () => {
    const data = makeResponse({
      query: "show Jokic triple doubles this season",
      route: "player_game_finder",
      result: {
        query_class: "finder",
        result_status: "ok",
        metadata: {
          query_text: "show Jokic triple doubles this season",
          route: "player_game_finder",
          season: "2025-26",
          season_type: "Regular Season",
          occurrence_event: { special_event: "triple_double" },
          player_context: {
            player_id: 203999,
            player_name: "Nikola Jokic",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          finder: Array.from({ length: 13 }, (_, index) => ({
            game_id: index + 1,
            game_date: `2026-03-${String(index + 1).padStart(2, "0")}`,
            player_id: 203999,
            player_name: "Nikola Jokic",
            team_abbr: "DEN",
            opponent_team_abbr: "POR",
            wl: "W",
            pts: 20 + index,
            reb: 10,
            ast: 10,
          })),
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    const table = screen.getByRole("table", { name: "Game log" });
    expect(within(table).getAllByRole("row")).toHaveLength(13);

    fireEvent.click(screen.getByRole("button", { name: "Show all 13 games" }));
    expect(within(table).getAllByRole("row")).toHaveLength(14);

    fireEvent.click(
      screen.getByRole("button", { name: "Show first 12 games" }),
    );
    expect(within(table).getAllByRole("row")).toHaveLength(13);
  });


  it("caps fixture-sized product game logs with total-row labels", () => {
    const gameRows = (count: number) =>
      Array.from({ length: count }, (_, index) => ({
        game_id: index + 1,
        game_date: `2026-03-${String(index + 1).padStart(2, "0")}`,
        player_id: 203999,
        player_name: "Nikola Jokic",
        team_abbr: "DEN",
        opponent_team_abbr: "POR",
        wl: "W",
        pts: 20 + index,
        reb: 10,
        ast: 10,
      }));

    const fixture71 = makeResponse({
      query: "Jokic game log",
      route: "player_game_finder",
      result: {
        query_class: "finder",
        result_status: "ok",
        metadata: {
          route: "player_game_finder",
          player_context: {
            player_id: 203999,
            player_name: "Nikola Jokic",
          },
        },
        notes: [],
        caveats: [],
        sections: { finder: gameRows(34) },
        current_through: "2026-04-12",
      },
    });

    const firstRender = render(<ResultRenderer data={fixture71} />);
    let table = screen.getByRole("table", { name: "Game log" });
    expect(within(table).getAllByRole("row")).toHaveLength(13);
    expect(
      screen.getByRole("button", { name: "Show all 34 games" }),
    ).toBeInTheDocument();
    firstRender.unmount();

    const fixture51 = makeResponse({
      query: "team game summary",
      route: "game_summary",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          route: "game_summary",
          team_context: {
            team_id: 1610612756,
            team_abbr: "PHX",
            team_name: "Suns",
          },
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [{ team_name: "Suns", games: 18, wins: 8, losses: 10 }],
          game_log: Array.from({ length: 18 }, (_, index) => ({
            game_id: index + 1,
            game_date: `2026-02-${String(index + 1).padStart(2, "0")}`,
            team_abbr: "PHX",
            team_name: "Suns",
            opponent_team_abbr: "LAC",
            wl: index % 2 === 0 ? "W" : "L",
            pts: 100 + index,
            opponent_pts: 98 + index,
          })),
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={fixture51} />);
    table = screen.getByRole("table", { name: "Game log" });
    expect(within(table).getAllByRole("row")).toHaveLength(15);
    expect(
      screen.getByRole("button", { name: "Show all 18 games" }),
    ).toBeInTheDocument();
  });
});
