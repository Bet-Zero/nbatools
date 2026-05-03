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
  | { type: "entity_summary"; sectionKey?: string }
  | { type: "game_log"; sectionKey?: string; summaryKey?: string }
  | {
      type: "leaderboard";
      sectionKey?: string;
      metricKey?: string;
      metricLabel?: string;
      sentenceMetricLabel?: string;
      valueSuffix?: string;
      verb?: string;
    }
  | { type: "fallback_table" };

export function routeToPattern(data: QueryResponse): PatternConfig[] {
  switch (data.route ?? data.result?.metadata?.route) {
    case "player_game_summary":
      return isLastNPlayerSummary(data)
        ? [
            { type: "entity_summary", sectionKey: "summary" },
            { type: "game_log", sectionKey: "game_log", summaryKey: "summary" },
          ]
        : [{ type: "entity_summary", sectionKey: "summary" }];
    case "season_leaders":
    case "season_team_leaders":
    case "team_record_leaderboard":
    case "player_occurrence_leaders":
    case "team_occurrence_leaders":
      return [{ type: "leaderboard", sectionKey: "leaderboard" }];
    case "player_stretch_leaderboard":
      return [
        {
          type: "leaderboard",
          sectionKey: "leaderboard",
          metricKey: "stretch_value",
          metricLabel: "PPG",
          sentenceMetricLabel: "points per game",
          valueSuffix: "per game",
          verb: "averaged",
        },
      ];
    case "lineup_leaderboard":
      return [
        {
          type: "leaderboard",
          sectionKey: "leaderboard",
          metricKey: "net_rating",
        },
      ];
    case "playoff_appearances":
      return [
        {
          type: "leaderboard",
          sectionKey: "leaderboard",
          metricKey: "appearances",
          sentenceMetricLabel: "playoff appearances",
        },
      ];
    default:
      return [{ type: "fallback_table" }];
  }
}

function isLastNPlayerSummary(data: QueryResponse): boolean {
  const windowSize = data.result?.metadata?.window_size;
  if (typeof windowSize === "number" && Number.isFinite(windowSize)) {
    return true;
  }

  const query = `${data.query ?? ""} ${data.result?.metadata?.query_text ?? ""}`;
  return /\blast\s+\d+\s*(?:games?|gms?)?\b/i.test(query);
}
