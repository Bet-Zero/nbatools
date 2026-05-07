import { describe, expect, it } from "vitest";
import type { QueryResponse } from "../api/types";
import { routeToPattern } from "../components/results/config/routeToPattern";

function makeResponse(route: string): QueryResponse {
  return {
    ok: true,
    query: "sample query",
    route,
    result_status: "ok",
    result_reason: null,
    current_through: null,
    confidence: null,
    intent: null,
    alternates: [],
    notes: [],
    caveats: [],
    result: {
      query_class: "leaderboard",
      result_status: "ok",
      metadata: { route },
      notes: [],
      caveats: [],
      sections: {
        leaderboard: [{ rank: 1, player_name: "Sample Player" }],
      },
    },
  };
}

describe("routeToPattern", () => {
  it("routes top player and team games to the top performances pattern", () => {
    expect(routeToPattern(makeResponse("top_player_games"))).toEqual([
      {
        type: "top_performances",
        sectionKey: "leaderboard",
        subject: "player",
      },
    ]);
    expect(routeToPattern(makeResponse("top_team_games"))).toEqual([
      {
        type: "top_performances",
        sectionKey: "leaderboard",
        subject: "team",
      },
    ]);
  });

  it("routes player stretch leaderboards to the rolling stretch pattern", () => {
    expect(routeToPattern(makeResponse("player_stretch_leaderboard"))).toEqual([
      {
        type: "rolling_stretch",
        sectionKey: "leaderboard",
      },
    ]);
  });
});
