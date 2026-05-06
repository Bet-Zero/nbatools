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
  } = {},
): QueryResponse {
  const result: ResultPayload = {
    query_class: "summary",
    result_status: options.result_status ?? "ok",
    result_reason: options.result_reason ?? null,
    metadata: options.metadata ?? {},
    notes: [],
    caveats: [],
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
    notes: [],
    caveats: [],
    result,
  };
}

describe("classifyResultShape", () => {
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

  it("classifies unmapped routed payloads as fallback tables", () => {
    const fallback = makeResponse({
      route: "lineup_summary",
      sections: { summary: [{ lineup: "A / B / C / D / E", net_rating: 8.1 }] },
    });

    expect(classifyResultShape(fallback)).toBe(RESULT_SHAPES.fallback_table);
  });
});
