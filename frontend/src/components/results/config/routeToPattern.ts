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
  | {
      type: "game_log";
      sectionKey?: string;
      summaryKey?: string;
      fallbackSectionKey?: string;
      mode?: "auto" | "player" | "team";
      metricKey?: string;
      preserveOrder?: boolean;
      showSummaryStrip?: boolean;
      rawDetailTitle?: string;
      detailSectionKeys?: string[];
    }
  | {
      type: "leaderboard";
      sectionKey?: string;
      metricKey?: string;
      metricLabel?: string;
      sentenceMetricLabel?: string;
      valueSuffix?: string;
      verb?: string;
    }
  | {
      type: "split";
      sectionKey?: string;
      summaryKey?: string | null;
      subject?: "player" | "team";
      bucketKey?: string;
      splitLabelOverride?: string;
      primaryDetailTitle?: string;
      summaryDetailTitle?: string | null;
    }
  | { type: "streak"; sectionKey?: string }
  | { type: "playoff_history"; mode?: "history" | "round_record" | "matchup" }
  | { type: "comparison"; subject?: "player" | "team"; headToHead?: boolean }
  | {
      type: "record";
      mode:
        | "team_record"
        | "record_by_decade"
        | "record_by_decade_leaderboard"
        | "matchup_by_decade";
    }
  | { type: "fallback_table" };

export function routeToPattern(data: QueryResponse): PatternConfig[] {
  switch (data.route ?? data.result?.metadata?.route) {
    case "player_game_summary":
      return isLastNPlayerSummary(data)
        ? [
            { type: "entity_summary", sectionKey: "summary" },
            {
              type: "game_log",
              sectionKey: "game_log",
              summaryKey: "summary",
              showSummaryStrip: false,
            },
          ]
        : [{ type: "entity_summary", sectionKey: "summary" }];
    case "player_game_finder":
      return [
        {
          type: "game_log",
          sectionKey: "finder",
          mode: "player",
          rawDetailTitle: "Player Game Detail",
        },
      ];
    case "game_finder":
      return [
        {
          type: "game_log",
          sectionKey: "finder",
          mode: "team",
          rawDetailTitle: "Game Detail",
        },
      ];
    case "top_player_games":
      return [
        {
          type: "game_log",
          sectionKey: "leaderboard",
          mode: "player",
          preserveOrder: true,
          rawDetailTitle: "Top Player Games Detail",
        },
      ];
    case "top_team_games":
      return [
        {
          type: "game_log",
          sectionKey: "leaderboard",
          mode: "team",
          preserveOrder: true,
          rawDetailTitle: "Top Team Games Detail",
        },
      ];
    case "game_summary":
      return [
        {
          type: "game_log",
          sectionKey: "game_log",
          fallbackSectionKey: "summary",
          summaryKey: "summary",
          mode: "team",
          rawDetailTitle: "Game Detail",
          detailSectionKeys: ["summary", "by_season", "top_performers"],
        },
      ];
    case "player_split_summary":
      return [{ type: "split", subject: "player" }];
    case "team_split_summary":
      return [{ type: "split", subject: "team" }];
    case "player_on_off":
      return [
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
      ];
    case "player_streak_finder":
    case "team_streak_finder":
      return [{ type: "streak", sectionKey: "streak" }];
    case "playoff_history":
      return [{ type: "playoff_history", mode: "history" }];
    case "playoff_round_record":
      return [{ type: "playoff_history", mode: "round_record" }];
    case "playoff_matchup_history":
      return [{ type: "playoff_history", mode: "matchup" }];
    case "player_compare":
      return [
        {
          type: "comparison",
          subject: "player",
          headToHead: data.result?.metadata?.head_to_head_used === true,
        },
      ];
    case "team_compare":
      return [
        {
          type: "comparison",
          subject: "team",
          headToHead: data.result?.metadata?.head_to_head_used === true,
        },
      ];
    case "team_matchup_record":
      return [{ type: "comparison", subject: "team", headToHead: true }];
    case "team_record":
      return [{ type: "record", mode: "team_record" }];
    case "record_by_decade":
      return [{ type: "record", mode: "record_by_decade" }];
    case "record_by_decade_leaderboard":
      return [{ type: "record", mode: "record_by_decade_leaderboard" }];
    case "matchup_by_decade":
      return [{ type: "record", mode: "matchup_by_decade" }];
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
