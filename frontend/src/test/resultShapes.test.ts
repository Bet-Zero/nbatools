import { describe, expect, it } from "vitest";
import type { QueryResponse, ResultPayload, SectionRow } from "../api/types";
import {
  classifyResultShape,
  RESULT_SHAPES,
} from "../components/results/resultShapes";

function makeResponse(
  options: {
    route?: string | null;
    result_status?: QueryResponse["result_status"];
    result_reason?: string | null;
    metadata?: Record<string, unknown>;
    sections?: Record<string, SectionRow[]>;
    query?: string;
    notes?: string[];
    caveats?: string[];
  } = {},
): QueryResponse {
  const result: ResultPayload = {
    query_class: "summary",
    result_status: options.result_status ?? "ok",
    result_reason: options.result_reason ?? null,
    metadata: options.metadata ?? {},
    notes: options.notes ?? [],
    caveats: options.caveats ?? [],
    sections: options.sections ?? {},
  };

  return {
    ok: (options.result_status ?? "ok") === "ok",
    query: options.query ?? "sample query",
    route: options.route ?? null,
    result_status: options.result_status ?? "ok",
    result_reason: options.result_reason ?? null,
    current_through: null,
    confidence: null,
    intent: null,
    alternates: [],
    notes: options.notes ?? [],
    caveats: options.caveats ?? [],
    result,
  };
}

describe("classifyResultShape", () => {
  it("classifies representative Wave 1 result shapes", () => {
    const cases: Array<{
      name: string;
      data: QueryResponse;
      expected: typeof RESULT_SHAPES[keyof typeof RESULT_SHAPES];
    }> = [
      {
        name: "entity_summary",
        data: makeResponse({
          route: "player_game_summary",
          sections: {
            summary: [{ player_name: "Nikola Jokic", pts_avg: 28.1 }],
          },
        }),
        expected: RESULT_SHAPES.entity_summary,
      },
      {
        name: "entity_summary_with_gamelog",
        data: makeResponse({
          route: "player_game_summary",
          query: "Nikola Jokic last 5 games",
          metadata: { window_size: 5 },
          sections: {
            summary: [{ player_name: "Nikola Jokic", pts_avg: 31.2 }],
            game_log: [{ player_name: "Nikola Jokic", game_date: "2026-04-01" }],
          },
        }),
        expected: RESULT_SHAPES.entity_summary_with_gamelog,
      },
      {
        name: "game_log_player_table",
        data: makeResponse({
          route: "player_game_finder",
          sections: {
            finder: [{ player_name: "Stephen Curry", game_date: "2026-02-01" }],
          },
        }),
        expected: RESULT_SHAPES.game_log_player_table,
      },
      {
        name: "game_log_team_table",
        data: makeResponse({
          route: "game_finder",
          sections: {
            finder: [{ team_name: "Los Angeles Lakers", game_date: "2026-02-01" }],
          },
        }),
        expected: RESULT_SHAPES.game_log_team_table,
      },
      {
        name: "game_log_team_detail",
        data: makeResponse({
          route: "game_summary",
          sections: {
            summary: [{ team_name: "Boston Celtics", wins: 3, losses: 2 }],
            game_log: [{ team_name: "Boston Celtics", game_date: "2026-02-01" }],
            top_performers: [{ player_name: "Jayson Tatum", pts: 33 }],
          },
        }),
        expected: RESULT_SHAPES.game_log_team_detail,
      },
      {
        name: "team_record",
        data: makeResponse({
          route: "team_record",
          sections: {
            summary: [{ team_name: "New York Knicks", wins: 3, losses: 5 }],
          },
        }),
        expected: RESULT_SHAPES.team_record,
      },
      {
        name: "leaderboard_table",
        data: makeResponse({
          route: "season_leaders",
          sections: {
            leaderboard: [{ rank: 1, player_name: "Shai Gilgeous-Alexander" }],
          },
        }),
        expected: RESULT_SHAPES.leaderboard_table,
      },
      {
        name: "top_performances",
        data: makeResponse({
          route: "top_player_games",
          sections: {
            leaderboard: [{ rank: 1, player_name: "Bam Adebayo", pts: 40 }],
          },
        }),
        expected: RESULT_SHAPES.top_performances,
      },
      {
        name: "rolling_stretch",
        data: makeResponse({
          route: "player_stretch_leaderboard",
          sections: {
            leaderboard: [{ rank: 1, player_name: "Luka Doncic", stretch_value: 34 }],
          },
        }),
        expected: RESULT_SHAPES.rolling_stretch,
      },
    ];

    for (const { name, data, expected } of cases) {
      expect(classifyResultShape(data), name).toBe(expected);
    }
  });

  it("collapses leaderboard routes into the same shape", () => {
    const playerLeaders = makeResponse({
      route: "season_leaders",
      sections: { leaderboard: [{ rank: 1, player_name: "Nikola Jokic" }] },
    });
    const teamLeaders = makeResponse({
      route: "team_record_leaderboard",
      sections: { leaderboard: [{ rank: 1, team_name: "Thunder" }] },
    });

    expect(classifyResultShape(playerLeaders)).toBe(
      RESULT_SHAPES.leaderboard_table,
    );
    expect(classifyResultShape(teamLeaders)).toBe(
      RESULT_SHAPES.leaderboard_table,
    );
  });

  it("classifies representative Wave 2 result shapes", () => {
    const cases: Array<{
      name: string;
      data: QueryResponse;
      expected: typeof RESULT_SHAPES[keyof typeof RESULT_SHAPES];
    }> = [
      {
        name: "split_table",
        data: makeResponse({
          route: "player_split_summary",
          sections: {
            split_comparison: [{ bucket: "home", games: 10, pts_avg: 29.4 }],
          },
        }),
        expected: RESULT_SHAPES.split_table,
      },
      {
        name: "on_off_split",
        data: makeResponse({
          route: "player_on_off",
          sections: {
            summary: [{ presence_state: "on", gp: 42, net_rating: 12.3 }],
          },
        }),
        expected: RESULT_SHAPES.on_off_split,
      },
      {
        name: "streak_table",
        data: makeResponse({
          route: "player_streak_finder",
          sections: {
            streak: [{ rank: 1, player_name: "Stephen Curry", streak_length: 8 }],
          },
        }),
        expected: RESULT_SHAPES.streak_table,
      },
      {
        name: "comparison",
        data: makeResponse({
          route: "team_compare",
          sections: {
            summary: [{ team_name: "Lakers" }, { team_name: "Celtics" }],
            comparison: [{ metric: "wins", Lakers: 42, Celtics: 45 }],
          },
        }),
        expected: RESULT_SHAPES.comparison,
      },
      {
        name: "playoff_history",
        data: makeResponse({
          route: "playoff_history",
          sections: {
            summary: [{ team_name: "Boston Celtics", appearances: 5 }],
            by_season: [{ season: "2024-25", wins: 8, losses: 5 }],
          },
        }),
        expected: RESULT_SHAPES.playoff_history,
      },
      {
        name: "playoff_appearances_leaderboard",
        data: makeResponse({
          route: "playoff_appearances",
          sections: {
            leaderboard: [
              { rank: 1, team_name: "Los Angeles Lakers", appearances: 31 },
            ],
          },
        }),
        expected: RESULT_SHAPES.leaderboard_table,
      },
      {
        name: "playoff_appearances_single_team",
        data: makeResponse({
          route: "playoff_appearances",
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
        expected: RESULT_SHAPES.playoff_history,
      },
      {
        name: "playoff_round_record",
        data: makeResponse({
          route: "playoff_round_record",
          sections: {
            leaderboard: [{ rank: 1, team_name: "Lakers", win_pct: 0.61 }],
          },
        }),
        expected: RESULT_SHAPES.playoff_round_record,
      },
      {
        name: "playoff_matchup_history",
        data: makeResponse({
          route: "playoff_matchup_history",
          sections: {
            summary: [{ team_name: "Celtics" }, { team_name: "Lakers" }],
            comparison: [{ season: "2023-24", BOS_wins: 4, LAL_wins: 2 }],
          },
        }),
        expected: RESULT_SHAPES.playoff_matchup_history,
      },
      {
        name: "record_by_decade",
        data: makeResponse({
          route: "record_by_decade",
          sections: {
            summary: [{ team_name: "Spurs", wins: 500, losses: 320 }],
            by_season: [{ decade: "2010s", wins: 520, losses: 300 }],
          },
        }),
        expected: RESULT_SHAPES.record_by_decade,
      },
      {
        name: "record_by_decade_leaderboard",
        data: makeResponse({
          route: "record_by_decade_leaderboard",
          sections: {
            leaderboard: [{ rank: 1, team_name: "Spurs", decade: "2010s" }],
          },
        }),
        expected: RESULT_SHAPES.record_by_decade_leaderboard,
      },
      {
        name: "matchup_by_decade",
        data: makeResponse({
          route: "matchup_by_decade",
          sections: {
            summary: [{ team_name: "Celtics" }, { team_name: "Lakers" }],
            comparison: [{ decade: "1980s", BOS_wins: 12, LAL_wins: 10 }],
          },
        }),
        expected: RESULT_SHAPES.matchup_by_decade,
      },
      {
        name: "lineup_summary",
        data: makeResponse({
          route: "lineup_summary",
          sections: {
            summary: [
              {
                lineup_name: "Jayson Tatum | Jaylen Brown",
                player_names: "Jayson Tatum|Jaylen Brown",
                net_rating: 11,
              },
            ],
          },
        }),
        expected: RESULT_SHAPES.entity_summary,
      },
      {
        name: "lineup_leaderboard",
        data: makeResponse({
          route: "lineup_leaderboard",
          sections: {
            leaderboard: [
              { rank: 1, lineup: "Nikola Jokic / Jamal Murray", net_rating: 15 },
            ],
          },
        }),
        expected: RESULT_SHAPES.leaderboard_table,
      },
    ];

    for (const { name, data, expected } of cases) {
      expect(classifyResultShape(data), name).toBe(expected);
    }
  });

  it("classifies top performances and rolling stretches as dedicated shapes", () => {
    const topGames = makeResponse({
      route: "top_player_games",
      sections: { leaderboard: [{ rank: 1, player_name: "Bam Adebayo" }] },
    });
    const stretches = makeResponse({
      route: "player_stretch_leaderboard",
      sections: { leaderboard: [{ rank: 1, player_name: "Luka Doncic" }] },
    });

    expect(classifyResultShape(topGames)).toBe(RESULT_SHAPES.top_performances);
    expect(classifyResultShape(stretches)).toBe(RESULT_SHAPES.rolling_stretch);
  });

  it("distinguishes plain player summaries from recent-game stacks", () => {
    const summary = makeResponse({
      route: "player_game_summary",
      sections: { summary: [{ player_name: "Nikola Jokic", pts_avg: 28.1 }] },
    });
    const recent = makeResponse({
      route: "player_game_summary",
      metadata: { window_size: 5 },
      sections: {
        summary: [{ player_name: "Nikola Jokic", pts_avg: 31.2 }],
        game_log: [{ player_name: "Nikola Jokic", game_date: "2026-04-01" }],
      },
      query: "Nikola Jokic last 5 games",
    });

    expect(classifyResultShape(summary)).toBe(RESULT_SHAPES.entity_summary);
    expect(classifyResultShape(recent)).toBe(
      RESULT_SHAPES.entity_summary_with_gamelog,
    );
  });

  it("treats recoverable and non-recoverable no-result cards separately", () => {
    const guided = makeResponse({
      result_status: "no_result",
      result_reason: "no_match",
    });
    const message = makeResponse({
      result_status: "error",
      result_reason: "unrouted",
    });

    expect(classifyResultShape(guided)).toBe(RESULT_SHAPES.no_result_guided);
    expect(classifyResultShape(message)).toBe(RESULT_SHAPES.no_result_message);
  });

  it("classifies unsupported no-results with safe recovery as guided", () => {
    const guidedUnsupported = makeResponse({
      route: "season_team_leaders",
      result_status: "no_result",
      result_reason: "unsupported",
      notes: ["Column 'def_rating' not available"],
      metadata: {
        route: "season_team_leaders",
        stat: "def_rating",
        applied_filters: [
          { label: "Last N games", value: "10", kind: "window" },
        ],
      },
    });
    const hardUnsupported = makeResponse({
      result_status: "no_result",
      result_reason: "unsupported",
    });

    expect(classifyResultShape(guidedUnsupported)).toBe(
      RESULT_SHAPES.no_result_guided,
    );
    expect(classifyResultShape(hardUnsupported)).toBe(
      RESULT_SHAPES.no_result_message,
    );
  });

  it("collapses comparison variants into one comparison shape", () => {
    const playerCompare = makeResponse({
      route: "player_compare",
      sections: {
        summary: [
          { player_name: "Nikola Jokic" },
          { player_name: "Joel Embiid" },
        ],
        comparison: [{ metric: "pts_avg", player_1: 28.1, player_2: 29.7 }],
      },
    });
    const headToHead = makeResponse({
      route: "team_matchup_record",
      sections: {
        summary: [
          { team_name: "Lakers", wins: 3, losses: 1 },
          { team_name: "Celtics", wins: 1, losses: 3 },
        ],
        comparison: [{ metric: "wins", team_1: 3, team_2: 1 }],
      },
    });

    expect(classifyResultShape(playerCompare)).toBe(RESULT_SHAPES.comparison);
    expect(classifyResultShape(headToHead)).toBe(RESULT_SHAPES.comparison);
  });

  it("keeps on-off split separate from generic split tables", () => {
    const split = makeResponse({
      route: "player_split_summary",
      sections: { split_comparison: [{ bucket: "Home", pts_avg: 29.4 }] },
    });
    const onOff = makeResponse({
      route: "player_on_off",
      sections: { summary: [{ presence_state: "On", net_rating: 12.3 }] },
    });

    expect(classifyResultShape(split)).toBe(RESULT_SHAPES.split_table);
    expect(classifyResultShape(onOff)).toBe(RESULT_SHAPES.on_off_split);
  });

  it("keeps team records with supporting game logs in the team-record shape", () => {
    const recordWithGameLog = makeResponse({
      route: "team_record",
      sections: {
        summary: [{ team_name: "New York Knicks", wins: 3, losses: 5 }],
        game_log: [{ team_name: "Knicks", game_date: "2026-01-01" }],
      },
    });

    expect(classifyResultShape(recordWithGameLog)).toBe(
      RESULT_SHAPES.team_record,
    );
  });

  it("classifies unmapped routed payloads as fallback tables", () => {
    const fallback = makeResponse({
      route: "unmapped_route",
      sections: { summary: [{ lineup: "A / B / C / D / E", net_rating: 8.1 }] },
    });

    expect(classifyResultShape(fallback)).toBe(RESULT_SHAPES.fallback_table);
  });
});
