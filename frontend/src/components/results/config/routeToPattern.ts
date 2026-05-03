import type { QueryResponse } from "../../../api/types";

/**
 * The route → pattern mapping. Every engine route resolves to an
 * ordered array of pattern configs that the renderer stacks
 * vertically.
 *
 * For now, every route resolves to a single `fallback_table` pattern.
 * As real patterns ship, route mappings move out of the `default`
 * branch into named cases below. See
 * `docs/planning/result_display_patterns.md` for the architecture and
 * `docs/planning/result_display_implementation_plan.md` for the build
 * sequence.
 */
export type PatternConfig =
  | { type: "leaderboard"; sectionKey?: string }
  | { type: "fallback_table" };

export function routeToPattern(data: QueryResponse): PatternConfig[] {
  switch (data.route ?? data.result?.metadata?.route) {
    case "season_leaders":
    case "season_team_leaders":
    case "team_record_leaderboard":
      return [{ type: "leaderboard", sectionKey: "leaderboard" }];
    default:
      return [{ type: "fallback_table" }];
  }
}
