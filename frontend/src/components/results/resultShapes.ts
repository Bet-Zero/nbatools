import type { QueryResponse } from "../../api/types";
import { routeToPattern } from "./config/routeToPattern";

export type ResultShapeKey =
  | "no_result_guided"
  | "no_result_message"
  | "entity_summary"
  | "entity_summary_with_gamelog"
  | "game_log_player_table"
  | "game_log_team_table"
  | "game_log_team_detail"
  | "split_table"
  | "on_off_split"
  | "streak_table"
  | "playoff_history"
  | "playoff_round_record"
  | "playoff_matchup_history"
  | "comparison"
  | "team_record"
  | "record_by_decade"
  | "record_by_decade_leaderboard"
  | "matchup_by_decade"
  | "leaderboard_table"
  | "fallback_table"
  | "unclassified";

export interface ResultShapeDefinition {
  key: ResultShapeKey;
  name: string;
  description: string;
}

export const RESULT_SHAPE_ORDER: ResultShapeKey[] = [
  "no_result_guided",
  "no_result_message",
  "entity_summary",
  "entity_summary_with_gamelog",
  "game_log_player_table",
  "game_log_team_table",
  "game_log_team_detail",
  "split_table",
  "on_off_split",
  "streak_table",
  "playoff_history",
  "playoff_round_record",
  "playoff_matchup_history",
  "comparison",
  "team_record",
  "record_by_decade",
  "record_by_decade_leaderboard",
  "matchup_by_decade",
  "leaderboard_table",
  "fallback_table",
  "unclassified",
];

export const RESULT_SHAPES: Record<ResultShapeKey, ResultShapeDefinition> = {
  no_result_guided: {
    key: "no_result_guided",
    name: "Guided No Result",
    description: "Message card with suggested next-step chips.",
  },
  no_result_message: {
    key: "no_result_message",
    name: "Message No Result",
    description: "Message card without the recovery suggestion grid.",
  },
  entity_summary: {
    key: "entity_summary",
    name: "Entity Summary",
    description: "Single hero answer card for a player summary.",
  },
  entity_summary_with_gamelog: {
    key: "entity_summary_with_gamelog",
    name: "Entity Summary + Recent Games",
    description: "Player summary hero followed by a recent-games table.",
  },
  game_log_player_table: {
    key: "game_log_player_table",
    name: "Player Game Log",
    description: "Summary strip plus player-first game table.",
  },
  game_log_team_table: {
    key: "game_log_team_table",
    name: "Team Game Log",
    description: "Summary strip plus team-first game table.",
  },
  game_log_team_detail: {
    key: "game_log_team_detail",
    name: "Game Summary Log",
    description: "Team game table with extra raw-detail drawers.",
  },
  split_table: {
    key: "split_table",
    name: "Split Comparison",
    description: "Hero, split bucket table, edge chips, and detail drawers.",
  },
  on_off_split: {
    key: "on_off_split",
    name: "On/Off Split",
    description: "Two-bucket on/off table with edge chips and one raw drawer.",
  },
  streak_table: {
    key: "streak_table",
    name: "Streak Table",
    description: "Hero, ranked streak table, and highlighted raw detail.",
  },
  playoff_history: {
    key: "playoff_history",
    name: "Playoff History",
    description: "Team playoff hero with season-by-season table.",
  },
  playoff_round_record: {
    key: "playoff_round_record",
    name: "Playoff Round Records",
    description: "Round leaderboard with a highlighted playoff metric.",
  },
  playoff_matchup_history: {
    key: "playoff_matchup_history",
    name: "Playoff Matchup History",
    description: "Two-team playoff matchup hero with series table.",
  },
  comparison: {
    key: "comparison",
    name: "Comparison Panels",
    description:
      "Head-to-head hero, subject panels, and metric comparison table.",
  },
  team_record: {
    key: "team_record",
    name: "Team Record",
    description: "Team record hero with a single-summary record table.",
  },
  record_by_decade: {
    key: "record_by_decade",
    name: "Record By Decade",
    description: "Team hero plus decade breakdown table.",
  },
  record_by_decade_leaderboard: {
    key: "record_by_decade_leaderboard",
    name: "Record By Decade Leaderboard",
    description: "Ranked decade leaderboard for team records.",
  },
  matchup_by_decade: {
    key: "matchup_by_decade",
    name: "Matchup By Decade",
    description: "Two-team hero with decade-by-decade matchup table.",
  },
  leaderboard_table: {
    key: "leaderboard_table",
    name: "Leaderboard Table",
    description: "Hero sentence over a ranked leaderboard table.",
  },
  fallback_table: {
    key: "fallback_table",
    name: "Fallback Tables",
    description: "One plain data card per populated section.",
  },
  unclassified: {
    key: "unclassified",
    name: "Unclassified",
    description:
      "Loaded result whose pattern stack does not match the catalog.",
  },
};

export function classifyResultShape(
  data: QueryResponse,
): ResultShapeDefinition {
  if (!hasDisplayableRows(data)) {
    return RESULT_SHAPES[noResultShape(data)];
  }

  const patterns = routeToPattern(data);
  if (
    patterns.length === 2 &&
    patterns[0]?.type === "entity_summary" &&
    patterns[1]?.type === "game_log"
  ) {
    return RESULT_SHAPES.entity_summary_with_gamelog;
  }

  if (patterns.length !== 1) {
    return RESULT_SHAPES.unclassified;
  }

  const pattern = patterns[0];
  switch (pattern.type) {
    case "entity_summary":
      return RESULT_SHAPES.entity_summary;
    case "game_log":
      if ((pattern.detailSectionKeys?.length ?? 0) > 0) {
        return RESULT_SHAPES.game_log_team_detail;
      }
      return pattern.mode === "player"
        ? RESULT_SHAPES.game_log_player_table
        : RESULT_SHAPES.game_log_team_table;
    case "split":
      return pattern.bucketKey === "presence_state"
        ? RESULT_SHAPES.on_off_split
        : RESULT_SHAPES.split_table;
    case "streak":
      return RESULT_SHAPES.streak_table;
    case "playoff_history":
      switch (pattern.mode) {
        case "history":
          return RESULT_SHAPES.playoff_history;
        case "round_record":
          return RESULT_SHAPES.playoff_round_record;
        case "matchup":
          return RESULT_SHAPES.playoff_matchup_history;
        default:
          return RESULT_SHAPES.unclassified;
      }
    case "comparison":
      return RESULT_SHAPES.comparison;
    case "record":
      switch (pattern.mode) {
        case "team_record":
          return RESULT_SHAPES.team_record;
        case "record_by_decade":
          return RESULT_SHAPES.record_by_decade;
        case "record_by_decade_leaderboard":
          return RESULT_SHAPES.record_by_decade_leaderboard;
        case "matchup_by_decade":
          return RESULT_SHAPES.matchup_by_decade;
        default:
          return RESULT_SHAPES.unclassified;
      }
    case "leaderboard":
      return RESULT_SHAPES.leaderboard_table;
    case "fallback_table":
      return RESULT_SHAPES.fallback_table;
    default:
      return RESULT_SHAPES.unclassified;
  }
}

export function resultShapeOrderIndex(key: ResultShapeKey): number {
  const index = RESULT_SHAPE_ORDER.indexOf(key);
  return index === -1 ? RESULT_SHAPE_ORDER.length : index;
}

function hasDisplayableRows(data: QueryResponse): boolean {
  const sections = data.result?.sections;
  if (!sections || Object.keys(sections).length === 0) {
    return false;
  }

  return Object.values(sections).some((rows) => rows && rows.length > 0);
}

function noResultShape(data: QueryResponse): ResultShapeKey {
  const reason = data.result_reason;
  if (data.result_status === "error" || reason === "error") {
    return "no_result_message";
  }

  if (reason === "no_match" || reason === "no_data" || !reason) {
    return "no_result_guided";
  }

  return "no_result_message";
}
