import { describe, expect, it } from "vitest";
import type { QueryResponse, ResultMetadata, SectionRow } from "../api/types";
import {
  routeToPattern,
  type PatternConfig,
} from "../components/results/config/routeToPattern";

function makeResponse(
  route: string,
  options: {
    metadata?: ResultMetadata;
    sections?: Record<string, SectionRow[]>;
    query?: string;
  } = {},
): QueryResponse {
  return {
    ok: true,
    query: options.query ?? "sample query",
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
      metadata: { route, ...options.metadata },
      notes: [],
      caveats: [],
      sections: options.sections ?? {
        leaderboard: [{ rank: 1, player_name: "Sample Player" }],
      },
    },
  };
}

const WAVE_1_ROUTES = [
  "player_game_summary",
  "player_game_finder",
  "game_finder",
  "game_summary",
  "team_record",
  "season_leaders",
  "season_team_leaders",
  "top_player_games",
  "top_team_games",
  "player_occurrence_leaders",
  "team_occurrence_leaders",
  "player_stretch_leaderboard",
];

function expectPattern(route: string, expected: PatternConfig[]) {
  expect(routeToPattern(makeResponse(route))).toEqual(expected);
}

describe("routeToPattern", () => {
  it("guards every Wave 1 route from falling through to fallback_table", () => {
    for (const route of WAVE_1_ROUTES) {
      const patterns = routeToPattern(makeResponse(route));
      expect(patterns, route).not.toHaveLength(0);
      expect(patterns.map((pattern) => pattern.type), route).not.toContain(
        "fallback_table",
      );
    }
  });

  it("routes broad player summaries to the entity-summary pattern only", () => {
    expect(
      routeToPattern(
        makeResponse("player_game_summary", {
          sections: {
            summary: [{ player_name: "Stephen Curry", pts_avg: 26.5 }],
            game_log: [{ game_date: "2026-01-01", pts: 25 }],
          },
        }),
      ),
    ).toEqual([{ type: "entity_summary", sectionKey: "summary" }]);
  });

  it("routes filtered player summaries with game rows to the entity-summary plus game-log stack", () => {
    expect(
      routeToPattern(
        makeResponse("player_game_summary", {
          query: "Tatum against good teams this season",
          metadata: {
            applied_filters: [
              { label: "Opponent quality", value: "good teams", kind: "quality" },
            ],
          },
          sections: {
            summary: [{ player_name: "Jayson Tatum", pts_avg: 23 }],
            game_log: [{ game_date: "2026-03-01", pts: 23 }],
          },
        }),
      ),
    ).toEqual([
      { type: "entity_summary", sectionKey: "summary" },
      {
        type: "game_log",
        sectionKey: "game_log",
        summaryKey: "summary",
        showSummaryStrip: false,
      },
    ]);
  });

  it("routes finder and team summary routes to the expected game-log configs", () => {
    expectPattern("player_game_finder", [
      {
        type: "game_log",
        sectionKey: "finder",
        mode: "player",
        rawDetailTitle: "Player Game Detail",
      },
    ]);
    expectPattern("game_finder", [
      {
        type: "game_log",
        sectionKey: "finder",
        mode: "team",
        rawDetailTitle: "Game Detail",
      },
    ]);
    expectPattern("game_summary", [
      {
        type: "game_log",
        sectionKey: "game_log",
        summaryKey: "summary",
        mode: "team",
        rawDetailTitle: "Game Detail",
        detailSectionKeys: ["top_performers"],
      },
    ]);
  });

  it("routes team records to record only unless a game log is present", () => {
    expect(
      routeToPattern(
        makeResponse("team_record", {
          sections: {
            summary: [{ team_name: "Knicks", wins: 3, losses: 5 }],
          },
        }),
      ),
    ).toEqual([{ type: "record", mode: "team_record" }]);

    expect(
      routeToPattern(
        makeResponse("team_record", {
          sections: {
            summary: [{ team_name: "Knicks", wins: 3, losses: 5 }],
            game_log: [{ game_date: "2026-03-01", team_abbr: "NYK" }],
          },
        }),
      ),
    ).toEqual([
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

  it("routes Wave 1 leaderboard routes to the leaderboard pattern", () => {
    for (const route of [
      "season_leaders",
      "season_team_leaders",
      "player_occurrence_leaders",
      "team_occurrence_leaders",
    ]) {
      expectPattern(route, [{ type: "leaderboard", sectionKey: "leaderboard" }]);
    }
  });

  it("routes top player and team games to the top performances pattern", () => {
    expectPattern("top_player_games", [
      {
        type: "top_performances",
        sectionKey: "leaderboard",
        subject: "player",
      },
    ]);
    expectPattern("top_team_games", [
      {
        type: "top_performances",
        sectionKey: "leaderboard",
        subject: "team",
      },
    ]);
  });

  it("routes player stretch leaderboards to the rolling stretch pattern", () => {
    expectPattern("player_stretch_leaderboard", [
      {
        type: "rolling_stretch",
        sectionKey: "leaderboard",
      },
    ]);
  });
});
