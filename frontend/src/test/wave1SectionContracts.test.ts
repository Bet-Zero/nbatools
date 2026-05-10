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

describe("Wave 1 result section contracts", () => {
  it("protects player_game_summary summary and optional game-log sections", () => {
    const summaryOnly = makeResponse("player_game_summary", {
      sections: {
        summary: [{ player_name: "Stephen Curry", pts_avg: 26.5 }],
      },
    });

    expectRequiredSections(summaryOnly, ["summary"]);
    expect(routeToPattern(summaryOnly)).toEqual([
      { type: "entity_summary", sectionKey: "summary" },
    ]);
    expect(classifyResultShape(summaryOnly)).toBe(RESULT_SHAPES.entity_summary);

    const withGameLog = makeResponse("player_game_summary", {
      query: "Stephen Curry last 5 games",
      metadata: { window_size: 5 },
      sections: {
        summary: [{ player_name: "Stephen Curry", pts_avg: 29.1 }],
        game_log: [{ player_name: "Stephen Curry", game_date: "2026-02-01" }],
      },
    });

    expectRequiredSections(withGameLog, ["summary", "game_log"]);
    expect(routeToPattern(withGameLog)).toEqual([
      { type: "entity_summary", sectionKey: "summary" },
      {
        type: "game_log",
        sectionKey: "game_log",
        summaryKey: "summary",
        showSummaryStrip: false,
      },
    ]);
    expect(classifyResultShape(withGameLog)).toBe(
      RESULT_SHAPES.entity_summary_with_gamelog,
    );
  });

  it("protects finder section names for player and team game finders", () => {
    const playerFinder = makeResponse("player_game_finder", {
      queryClass: "finder",
      sections: {
        finder: [{ player_name: "Stephen Curry", game_date: "2026-02-01" }],
      },
    });
    const teamFinder = makeResponse("game_finder", {
      queryClass: "finder",
      sections: {
        finder: [{ team_name: "Los Angeles Lakers", game_date: "2026-02-01" }],
      },
    });

    expectRequiredSections(playerFinder, ["finder"]);
    expect(routeToPattern(playerFinder)[0]).toMatchObject({
      type: "game_log",
      sectionKey: "finder",
      mode: "player",
    });
    expect(classifyResultShape(playerFinder)).toBe(
      RESULT_SHAPES.game_log_player_table,
    );

    expectRequiredSections(teamFinder, ["finder"]);
    expect(routeToPattern(teamFinder)[0]).toMatchObject({
      type: "game_log",
      sectionKey: "finder",
      mode: "team",
    });
    expect(classifyResultShape(teamFinder)).toBe(
      RESULT_SHAPES.game_log_team_table,
    );
  });

  it("protects game_summary game-log, summary, and top-performer detail sections", () => {
    const data = makeResponse("game_summary", {
      sections: {
        summary: [{ team_name: "Boston Celtics", wins: 4, losses: 1 }],
        game_log: [{ team_name: "Boston Celtics", game_date: "2026-02-01" }],
        top_performers: [{ player_name: "Jayson Tatum", pts: 33 }],
      },
    });

    expectRequiredSections(data, ["game_log"]);
    expect(data.result.sections.summary).toBeDefined();
    expect(data.result.sections.top_performers).toBeDefined();
    expect(routeToPattern(data)).toEqual([
      {
        type: "game_log",
        sectionKey: "game_log",
        summaryKey: "summary",
        mode: "team",
        rawDetailTitle: "Game Detail",
        detailSectionKeys: ["top_performers"],
      },
    ]);
    expect(classifyResultShape(data)).toBe(RESULT_SHAPES.game_log_team_detail);
  });

  it("protects team_record summary behavior and optional stacked game logs", () => {
    const recordOnly = makeResponse("team_record", {
      sections: {
        summary: [{ team_name: "New York Knicks", wins: 3, losses: 5 }],
      },
    });

    expectRequiredSections(recordOnly, ["summary"]);
    expect(routeToPattern(recordOnly)).toEqual([
      { type: "record", mode: "team_record" },
    ]);
    expect(classifyResultShape(recordOnly)).toBe(RESULT_SHAPES.team_record);

    const withGameLog = makeResponse("team_record", {
      sections: {
        summary: [{ team_name: "New York Knicks", wins: 3, losses: 5 }],
        game_log: [{ team_name: "New York Knicks", game_date: "2026-02-01" }],
      },
    });

    expectRequiredSections(withGameLog, ["summary", "game_log"]);
    expect(routeToPattern(withGameLog)).toEqual([
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
    expect(classifyResultShape(withGameLog)).toBe(RESULT_SHAPES.team_record);
  });

  it("protects leaderboard section names for Wave 1 leaderboard-family routes", () => {
    for (const route of [
      "season_leaders",
      "season_team_leaders",
      "player_occurrence_leaders",
      "team_occurrence_leaders",
      "top_player_games",
      "top_team_games",
      "player_stretch_leaderboard",
    ]) {
      const data = makeResponse(route, {
        queryClass: "leaderboard",
        sections: {
          leaderboard: [{ rank: 1, player_name: "Sample Leader", pts: 30 }],
        },
      });

      expectRequiredSections(data, ["leaderboard"]);
      const patterns = routeToPattern(data);
      expect(patterns.some((pattern) => pattern.type === "fallback_table")).toBe(
        false,
      );
      expect(patterns[0]).toMatchObject({ sectionKey: "leaderboard" });
    }
  });
});
