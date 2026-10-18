import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResultRenderer from "../../components/results/ResultRenderer";
import { formatValue, formatAverageValue, formatProseValue } from "../../components/tableFormatting";
import { makeResponse } from "./helpers";

describe("summary and ranking display meaning", () => {
  it("names every opponent in a union without a singleton identity", () => {
    render(<ResultRenderer data={makeResponse({ route: "team_record", result: {
      query_class: "summary", result_status: "ok", notes: [], caveats: [],
      metadata: {
        team: "NYK", opponent: "MIA, WAS", opponents: ["MIA", "WAS"],
        applied_filters: [{ label: "Opponent", value: "MIA, WAS", kind: "team" }],
      },
      sections: { summary: [{ team_name: "New York Knicks", games: 3, wins: 2, losses: 1, win_pct: 0.667 }] },
    } })} />);
    expect(screen.getByText(/against MIA or WAS/)).toBeInTheDocument();
    expect(screen.queryByText(/undefined/)).not.toBeInTheDocument();
  });

  it("names an abbreviation-only opponent without inventing a full name", () => {
    render(<ResultRenderer data={makeResponse({ route: "team_record", result: {
      query_class: "summary", result_status: "ok", notes: [], caveats: [],
      metadata: { opponent_context: JSON.parse('{"team_abbr":"NYK"}') },
      sections: { summary: [{ team_name: "Boston Celtics", games: 3, wins: 3, losses: 0, win_pct: 1 }] },
    } })} />);
    expect(screen.getByText(/against NYK/)).toBeInTheDocument();
    expect(screen.queryByText(/undefined/)).not.toBeInTheDocument();
  });

  it.each([false, true])("preserves ranked payload order including ties (ascending=%s)", ascending => {
    const rows = [
      { game_id: 1, game_date: "2024-01-01", pts: 60 },
      { game_id: 2, game_date: "2024-01-04", pts: 46 },
      { game_id: 3, game_date: "2024-01-02", pts: 46 },
    ];
    const ordered = ascending ? [rows[1], rows[2], rows[0]] : rows;
    render(<ResultRenderer data={makeResponse({ route: "player_game_finder", result: {
      query_class: "finder", result_status: "ok", notes: [], caveats: [],
      metadata: { sort_by: "stat", stat: "pts", ascending, player_context: { player_name: "Stephen Curry", player_id: 201939 } },
      sections: { finder: ordered },
    } })} />);
    const table = screen.getByRole("table", { name: "Game log" });
    const headers = within(table).getAllByRole("columnheader").map(x => x.textContent);
    const pts = headers.indexOf("PTS");
    const dateColumn = headers.indexOf("Date");
    expect(within(table).getAllByRole("row").slice(1).map(row => within(row).getAllByRole("cell")[dateColumn].textContent)).toEqual(ordered.map(row => `Jan ${Number(row.game_date.slice(-2))}`));
    expect(within(table).getAllByRole("row").slice(1).map(row => within(row).getAllByRole("cell")[pts].textContent)).toEqual(ordered.map(row => String(row.pts)));
    expect(screen.getByText(new RegExp(ascending ? "lowest-scoring" : "highest-scoring"))).toBeInTheDocument();
  });

  it("formats ratio efficiencies above 100% while retaining percentage-point fields", () => {
    expect(formatValue(1.125, "ts_pct")).toBe("112.5%");
    expect(formatAverageValue(1.125, "efg_pct_avg")).toBe("112.5%");
    expect(formatProseValue(1.125, "ts_pct_avg")).toBe("112.5%");
    expect(formatValue(28.35, "usg_pct")).toBe("28.4%");
    expect(formatValue(0.5, "fg_pct")).toBe("50.0%");
  });

  it("does not add efficiency percentages in the total row", () => {
    render(<ResultRenderer data={makeResponse({ route: "player_game_summary", result: {
      query_class: "summary", result_status: "ok", notes: [], caveats: [],
      metadata: { last_n: 1, window_size: 1 },
      sections: { summary: [{ games: 1, pts_avg: 23, ts_pct_avg: 1.125 }], game_log: [{ game_id: 1, game_date: "2024-04-09", player_name: "Stephen Curry", pts: 23, ts_pct: 1.125, efg_pct: 1.111 }] },
    } })} />);
    const table = screen.getByRole("table", { name: "Game log" });
    const total = within(table).getByText("Total").closest("tr")!;
    expect(total.textContent).not.toContain("%");
    expect(within(table).getAllByText("112.5%").length).toBeGreaterThan(0);
  });

  it.each([
    ["games_40p", "Games with 40+ PTS", "games with 40+ points"],
    ["games_pts_40+", "Games with 40+ PTS", "games with 40+ points"],
    ["games_ast_10+_tov_0", "Games with 10+ AST and 0 TOV", "games with 10+ assists and 0 turnovers"],
  ])("explains occurrence metric %s", (metric, heading, phrase) => {
    render(<ResultRenderer data={makeResponse({ route: "player_occurrence_leaders", result: {
      query_class: "leaderboard", result_status: "ok", notes: [], caveats: [], metadata: { stat: metric },
      sections: { leaderboard: [{ rank: 1, player_name: "Luka Dončić", games_played: 70, [metric]: 13, season: "2023-24" }] },
    } })} />);
    expect(screen.getByRole("columnheader", { name: heading })).toBeInTheDocument();
    expect(screen.getByText(new RegExp(phrase.replace(/\+/g, "\\+")))).toBeInTheDocument();
  });
});
