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
  "team_record_leaderboard",
  "top_player_games",
  "top_team_games",
  "player_occurrence_leaders",
  "team_occurrence_leaders",
  "player_stretch_leaderboard",
];

const WAVE_2_ROUTES = [
  "player_split_summary",
  "team_split_summary",
  "player_on_off",
  "player_streak_finder",
  "team_streak_finder",
  "player_compare",
  "team_compare",
  "team_matchup_record",
  "playoff_history",
  "playoff_appearances",
  "playoff_matchup_history",
  "playoff_round_record",
  "record_by_decade",
  "record_by_decade_leaderboard",
  "matchup_by_decade",
  "lineup_summary",
  "lineup_leaderboard",
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
        collapseToDetail: true,
      },
    ]);
  });

  it("routes Wave 1 leaderboard routes to the leaderboard pattern", () => {
    for (const route of [
      "season_leaders",
      "season_team_leaders",
      "team_record_leaderboard",
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

  it("guards every Wave 2 route from falling through to fallback_table", () => {
    for (const route of WAVE_2_ROUTES) {
      const patterns = routeToPattern(makeResponse(route));
      expect(patterns, route).not.toHaveLength(0);
      expect(patterns.map((pattern) => pattern.type), route).not.toContain(
        "fallback_table",
      );
    }
  });

  it("routes Wave 2 split routes to split patterns", () => {
    expectPattern("player_split_summary", [{ type: "split", subject: "player" }]);
    expectPattern("team_split_summary", [{ type: "split", subject: "team" }]);
    expectPattern("player_on_off", [
      {
        type: "split",
        sectionKey: "summary",
        summaryKey: "summary",
        subject: "player",
        bucketKey: "presence_state",
        splitLabelOverride: "On/Off",
        primaryDetailTitle: "On/Off Detail",
        summaryDetailTitle: null,
      },
    ]);
  });

  it("routes Wave 2 streak routes to the streak pattern", () => {
    expectPattern("player_streak_finder", [
      { type: "streak", sectionKey: "streak" },
    ]);
    expectPattern("team_streak_finder", [
      { type: "streak", sectionKey: "streak" },
    ]);
  });

  it("routes Wave 2 comparison routes to comparison patterns", () => {
    expectPattern("player_compare", [
      { type: "comparison", subject: "player", headToHead: false },
    ]);
    expectPattern("team_compare", [
      { type: "comparison", subject: "team", headToHead: false },
    ]);
    expectPattern("team_matchup_record", [
      { type: "comparison", subject: "team", headToHead: true },
    ]);

    expect(
      routeToPattern(
        makeResponse("player_compare", {
          metadata: { head_to_head_used: true },
        }),
      ),
    ).toEqual([{ type: "comparison", subject: "player", headToHead: true }]);
  });

  it("routes Wave 2 playoff/history routes to their specific modes", () => {
    expectPattern("playoff_history", [
      { type: "playoff_history", mode: "history" },
    ]);
    expectPattern("playoff_round_record", [
      { type: "playoff_history", mode: "round_record" },
    ]);
    expectPattern("playoff_matchup_history", [
      { type: "playoff_history", mode: "matchup" },
    ]);
    expectPattern("playoff_appearances", [
      {
        type: "leaderboard",
        sectionKey: "leaderboard",
        metricKey: "appearances",
        sentenceMetricLabel: "playoff appearances",
      },
    ]);
  });

  it("branches playoff appearances between leaderboard and single-team summary variants", () => {
    expect(
      routeToPattern(
        makeResponse("playoff_appearances", {
          sections: {
            leaderboard: [
              {
                rank: 1,
                team_name: "Los Angeles Lakers",
                appearances: 31,
              },
            ],
          },
        }),
      ),
    ).toEqual([
      {
        type: "leaderboard",
        sectionKey: "leaderboard",
        metricKey: "appearances",
        sentenceMetricLabel: "playoff appearances",
      },
    ]);

    expect(
      routeToPattern(
        makeResponse("playoff_appearances", {
          sections: {
            summary: [
              {
                team_name: "Los Angeles Lakers",
                appearances: 18,
                round: "Finals",
                season_start: "1996-97",
                season_end: "2024-25",
              },
            ],
            by_season: [{ season: "2024-25", wins: 8, losses: 5 }],
          },
        }),
      ),
    ).toEqual([{ type: "playoff_history", mode: "appearances" }]);
  });

  it("routes Wave 2 decade and matchup record routes to record patterns", () => {
    expectPattern("record_by_decade", [
      { type: "record", mode: "record_by_decade" },
    ]);
    expectPattern("record_by_decade_leaderboard", [
      { type: "record", mode: "record_by_decade_leaderboard" },
    ]);
    expectPattern("matchup_by_decade", [
      { type: "record", mode: "matchup_by_decade" },
    ]);
  });

  it("routes Wave 2 lineup routes to summary and leaderboard patterns", () => {
    expectPattern("lineup_summary", [
      { type: "entity_summary", sectionKey: "summary" },
    ]);
    expectPattern("lineup_leaderboard", [
      {
        type: "leaderboard",
        sectionKey: "leaderboard",
        metricKey: "net_rating",
      },
    ]);
  });
});
