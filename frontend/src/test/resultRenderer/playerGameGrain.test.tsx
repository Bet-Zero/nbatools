import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResultRenderer from "../../components/results/ResultRenderer";
import { makeResponse } from "./helpers";

const players = [
  { game_id: 22301149, game_date: "2024-04-09", player_id: 1630162, player_name: "Anthony Edwards", team_abbr: "MIN", opponent_abbr: "WAS", pts: 51, plus_minus: 6, wl: "W" },
  { game_id: 22300960, game_date: "2024-01-22", player_id: 203954, player_name: "Joel Embiid", team_abbr: "PHI", opponent_abbr: "SAS", pts: 70, plus_minus: -4, wl: "L" },
];

describe("player-game row grain", () => {
  it.each(["count", "finder"] as const)("preserves mixed-player identities and statistics in %s", query_class => {
    render(<ResultRenderer data={makeResponse({ route: "player_game_finder", result: {
      query_class, result_status: "ok", notes: [], caveats: [], metadata: {},
      sections: { finder: players, ...(query_class === "count" ? { count: [{ count: 2 }] } : {}) },
    } })} />);
    const table = screen.getByRole("table", { name: "Game log" });
    expect(within(table).getByRole("columnheader", { name: "Player" })).toBeInTheDocument();
    for (const name of ["Anthony Edwards", "Joel Embiid"]) expect(within(table).getByText(name)).toBeInTheDocument();
    for (const name of [/^Score$/i, /^Margin$/i, /^Opp PTS$/i]) expect(within(table).queryByRole("columnheader", { name })).not.toBeInTheDocument();
    expect(within(table).queryByText("51-45")).not.toBeInTheDocument();
    for (const [name, outcome] of [["Anthony Edwards", "W"], ["Joel Embiid", "L"]]) {
      const row = within(table).getByText(name).closest("tr")!;
      expect(within(row).getByText(outcome)).toBeInTheDocument();
    }
  });

  it.each([
    [{ team_context: { team_id: 1610612747, team_name: "Lakers", team_abbr: "LAL" } }, "Top 2 scoring games by Lakers players in 2023-24."],
    [{ position_filter: "guards", applied_filters: [{ kind: "position", label: "Experience", value: "Rookies" }] }, "Top 2 scoring games by rookie guards in 2023-24."],
    [{ position_filter: "centers", stat: "reb" }, "Top 2 rebounding games by centers in 2023-24."],
  ])("names the requested population rather than the first player (%s)", (scope, headline) => {
    render(<ResultRenderer data={makeResponse({ route: "player_game_finder", result: {
      query_class: "finder", result_status: "ok", notes: [], caveats: [],
      metadata: { season: "2023-24", sort_by: "stat", stat: "pts", ...scope },
      sections: { finder: players },
    } })} />);
    expect(screen.getByText(headline)).toBeVisible();
    expect(screen.queryByText(/Anthony Edwards's 2|Anthony Edwards had 2/)).not.toBeInTheDocument();
  });

  it("keeps a pinned player count in player grain without a redundant player column", () => {
    render(<ResultRenderer data={makeResponse({ route: "player_game_finder", result: {
      query_class: "count", result_status: "ok", notes: [], caveats: [],
      metadata: { player_context: { player_id: 1630162, player_name: "Anthony Edwards" } },
      sections: { count: [{ count: 1 }], finder: [players[0]] },
    } })} />);
    const table = screen.getByRole("table", { name: "Game log" });
    expect(within(table).queryByRole("columnheader", { name: "Player" })).not.toBeInTheDocument();
    expect(within(table).getByRole("columnheader", { name: "PTS" })).toBeInTheDocument();
    expect(within(table).queryByRole("columnheader", { name: "Score" })).not.toBeInTheDocument();
  });

  it("keeps actual team counts and their score/margin intact", () => {
    render(<ResultRenderer data={makeResponse({ route: "game_finder", result: {
      query_class: "count", result_status: "ok", notes: [], caveats: [], metadata: {},
      sections: { count: [{ count: 1 }], finder: [{ game_id: 1, game_date: "2024-04-09", team_abbr: "MIN", opponent_abbr: "WAS", pts: 130, plus_minus: 9, wl: "W" }] },
    } })} />);
    const table = screen.getByRole("table", { name: "Game log" });
    expect(within(table).queryByRole("columnheader", { name: "Player" })).not.toBeInTheDocument();
    expect(within(table).getByText("130-121")).toBeInTheDocument();
    expect(within(table).getByRole("columnheader", { name: "Margin" })).toBeInTheDocument();
  });

  it("never fills missing player-row team scores from player points or plus-minus", () => {
    render(<ResultRenderer data={makeResponse({ route: "player_game_finder", result: {
      query_class: "finder", result_status: "ok", notes: [], caveats: [], metadata: {},
      sections: { finder: [{ ...players[0], team_score: 130, opponent_score: 121 }, players[1]] },
    } })} />);
    const table = screen.getByRole("table", { name: "Game log" });
    expect(within(table).getByText("130-121")).toBeInTheDocument();
    expect(within(table).queryByText("70-74")).not.toBeInTheDocument();
  });
});
