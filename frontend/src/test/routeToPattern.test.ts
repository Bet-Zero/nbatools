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

  it("routes filtered player summaries with game rows to the entity-summary plus game-log stack", () => {
    const data = makeResponse("player_game_summary");
    data.query = "Tatum against good teams this season";
    data.result.metadata = {
      route: "player_game_summary",
      applied_filters: [
        { label: "Opponent quality", value: "good teams", kind: "quality" },
      ],
    };
    data.result.sections = {
      summary: [{ player_name: "Jayson Tatum", pts_avg: 23 }],
      game_log: [{ game_date: "2026-03-01", pts: 23 }],
    };

    expect(routeToPattern(data)).toEqual([
      { type: "entity_summary", sectionKey: "summary" },
      {
        type: "game_log",
        sectionKey: "game_log",
        summaryKey: "summary",
        showSummaryStrip: false,
      },
    ]);
  });

  it("stacks team-record game logs when the backend provides matching games", () => {
    const data = makeResponse("team_record");
    data.result.sections = {
      summary: [{ team_name: "Knicks", wins: 3, losses: 5 }],
      game_log: [{ game_date: "2026-03-01", team_abbr: "NYK" }],
    };

    expect(routeToPattern(data)).toEqual([
      { type: "record", mode: "team_record" },
      {
        type: "game_log",
        sectionKey: "game_log",
        summaryKey: "summary",
        mode: "team",
        showSummaryStrip: false,
        rawDetailTitle: "Game Detail",
      },
    ]);
  });
});
