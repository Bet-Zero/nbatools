import { describe, expect, it } from "vitest";
import type { QueryResponse, ResultMetadata, SectionRow } from "../api/types";
import { routeToPattern } from "../components/results/config/routeToPattern";
import {
  classifyResultShape,
  RESULT_SHAPES,
} from "../components/results/resultShapes";

function makeResponse(
  route: string,
  options: {
    metadata?: ResultMetadata;
    query?: string;
    queryClass?: string;
    sections: Record<string, SectionRow[]>;
  },
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
      query_class: options.queryClass ?? "summary",
      result_status: "ok",
      result_reason: null,
      metadata: { route, ...options.metadata },
      notes: [],
      caveats: [],
      sections: options.sections,
    },
  };
}

function expectRequiredSections(
  data: QueryResponse,
  required: string[],
): void {
  for (const key of required) {
    expect(data.result.sections[key], `${data.route}:${key}`).toBeDefined();
    expect(data.result.sections[key]?.length, `${data.route}:${key}`).toBeGreaterThan(0);
  }
}

describe("Wave 2 result section contracts", () => {
  it("protects split summary sections consumed by SplitResult", () => {
    for (const route of ["player_split_summary", "team_split_summary"]) {
      const data = makeResponse(route, {
        queryClass: "split_summary",
        sections: {
          summary: [{ split: "home_away", games_total: 20 }],
          split_comparison: [{ bucket: "home", games: 10, pts_avg: 29.4 }],
        },
      });

      expectRequiredSections(data, ["summary", "split_comparison"]);
      expect(routeToPattern(data)[0]).toMatchObject({ type: "split" });
      expect(classifyResultShape(data)).toBe(RESULT_SHAPES.split_table);
    }
  });

  it("protects player_on_off summary rows and presence-state bucket behavior", () => {
    const data = makeResponse("player_on_off", {
      sections: {
        summary: [
          { player_name: "Nikola Jokic", presence_state: "on", gp: 42 },
          { player_name: "Nikola Jokic", presence_state: "off", gp: 42 },
        ],
      },
    });

    expectRequiredSections(data, ["summary"]);
    expect(routeToPattern(data)).toEqual([
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
    expect(classifyResultShape(data)).toBe(RESULT_SHAPES.on_off_split);
  });

  it("protects streak section names for player and team streak finders", () => {
    for (const route of ["player_streak_finder", "team_streak_finder"]) {
      const data = makeResponse(route, {
        queryClass: "streak",
        sections: {
          streak: [{ rank: 1, condition: "pts>=20", streak_length: 8 }],
        },
      });

      expectRequiredSections(data, ["streak"]);
      expect(routeToPattern(data)).toEqual([
        { type: "streak", sectionKey: "streak" },
      ]);
      expect(classifyResultShape(data)).toBe(RESULT_SHAPES.streak_table);
    }
  });

  it("protects comparison sections for compare and head-to-head routes", () => {
    for (const route of ["player_compare", "team_compare", "team_matchup_record"]) {
      const data = makeResponse(route, {
        queryClass: "comparison",
        sections: {
          summary: [{ team_name: "Lakers" }, { team_name: "Celtics" }],
          comparison: [{ metric: "wins", Lakers: 3, Celtics: 1 }],
        },
      });

      expectRequiredSections(data, ["summary", "comparison"]);
      expect(routeToPattern(data)[0]).toMatchObject({ type: "comparison" });
      expect(classifyResultShape(data)).toBe(RESULT_SHAPES.comparison);
    }
  });

  it("protects playoff history and playoff leaderboard section names", () => {
    const playoffHistory = makeResponse("playoff_history", {
      sections: {
        summary: [{ team_name: "Boston Celtics", wins: 12, losses: 6 }],
        by_season: [{ season: "2024-25", wins: 8, losses: 5 }],
      },
    });
    const playoffAppearances = makeResponse("playoff_appearances", {
      queryClass: "leaderboard",
      sections: {
        leaderboard: [{ rank: 1, team_name: "Los Angeles Lakers", appearances: 20 }],
      },
    });
    const singleTeamAppearances = makeResponse("playoff_appearances", {
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
        by_season: [
          { season: "2024-25", games: 13, wins: 8, losses: 5, win_pct: 0.615 },
        ],
      },
    });
    const playoffMatchup = makeResponse("playoff_matchup_history", {
      queryClass: "comparison",
      sections: {
        summary: [{ team_name: "Celtics" }, { team_name: "Lakers" }],
        comparison: [{ season: "2023-24", BOS_wins: 4, LAL_wins: 2 }],
      },
    });
    const playoffRound = makeResponse("playoff_round_record", {
      queryClass: "leaderboard",
      sections: {
        leaderboard: [{ rank: 1, team_name: "Lakers", round: "Finals" }],
      },
    });

    expectRequiredSections(playoffHistory, ["summary", "by_season"]);
    expect(classifyResultShape(playoffHistory)).toBe(RESULT_SHAPES.playoff_history);
    expectRequiredSections(playoffAppearances, ["leaderboard"]);
    expect(routeToPattern(playoffAppearances)[0]).toMatchObject({
      type: "leaderboard",
      sectionKey: "leaderboard",
    });
    expect(classifyResultShape(playoffAppearances)).toBe(
      RESULT_SHAPES.leaderboard_table,
    );
    expectRequiredSections(singleTeamAppearances, ["summary", "by_season"]);
    expect(routeToPattern(singleTeamAppearances)).toEqual([
      { type: "playoff_history", mode: "appearances" },
    ]);
    expect(classifyResultShape(singleTeamAppearances)).toBe(
      RESULT_SHAPES.playoff_history,
    );
    expectRequiredSections(playoffMatchup, ["summary", "comparison"]);
    expect(classifyResultShape(playoffMatchup)).toBe(
      RESULT_SHAPES.playoff_matchup_history,
    );
    expectRequiredSections(playoffRound, ["leaderboard"]);
    expect(classifyResultShape(playoffRound)).toBe(
      RESULT_SHAPES.playoff_round_record,
    );
  });

  it("protects decade record, matchup, and lineup section names", () => {
    const cases: Array<{
      data: QueryResponse;
      required: string[];
      shape: typeof RESULT_SHAPES[keyof typeof RESULT_SHAPES];
    }> = [
      {
        data: makeResponse("record_by_decade", {
          sections: {
            summary: [{ team_name: "Spurs", wins: 500, losses: 320 }],
            by_season: [{ decade: "2010s", wins: 520, losses: 300 }],
          },
        }),
        required: ["summary", "by_season"],
        shape: RESULT_SHAPES.record_by_decade,
      },
      {
        data: makeResponse("record_by_decade_leaderboard", {
          queryClass: "leaderboard",
          sections: {
            leaderboard: [{ rank: 1, team_name: "Spurs", decade: "2010s" }],
          },
        }),
        required: ["leaderboard"],
        shape: RESULT_SHAPES.record_by_decade_leaderboard,
      },
      {
        data: makeResponse("matchup_by_decade", {
          queryClass: "comparison",
          sections: {
            summary: [{ team_name: "Celtics" }, { team_name: "Lakers" }],
            comparison: [{ decade: "1980s", BOS_wins: 12, LAL_wins: 10 }],
          },
        }),
        required: ["summary", "comparison"],
        shape: RESULT_SHAPES.matchup_by_decade,
      },
      {
        data: makeResponse("lineup_summary", {
          sections: {
            summary: [
              {
                lineup_name: "Jayson Tatum | Jaylen Brown",
                player_names: "Jayson Tatum|Jaylen Brown",
                team_abbr: "BOS",
                minutes: 420,
                off_rating: 122.4,
                def_rating: 111.4,
                net_rating: 11,
                pace: 99.8,
                ts_pct: 0.62,
              },
            ],
          },
        }),
        required: ["summary"],
        shape: RESULT_SHAPES.entity_summary,
      },
      {
        data: makeResponse("lineup_leaderboard", {
          queryClass: "leaderboard",
          sections: {
            leaderboard: [
              { rank: 1, lineup: "Nikola Jokic / Jamal Murray", net_rating: 15 },
            ],
          },
        }),
        required: ["leaderboard"],
        shape: RESULT_SHAPES.leaderboard_table,
      },
    ];

    for (const { data, required, shape } of cases) {
      expectRequiredSections(data, required);
      expect(routeToPattern(data)[0]?.type).not.toBe("fallback_table");
      expect(classifyResultShape(data), data.route ?? "route").toBe(shape);
    }
  });
});
