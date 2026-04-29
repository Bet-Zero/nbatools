/** Typed API response interfaces matching the nbatools API envelope. */

// --- Health / Routes ---

export interface HealthResponse {
  status: string;
  version: string;
}

export interface RoutesResponse {
  routes: string[];
}

// --- Result status / reason ---

export type ResultStatus = "ok" | "no_result" | "error";
export type ResultReason =
  | "no_match"
  | "no_data"
  | "unrouted"
  | "ambiguous"
  | "unsupported"
  | "error"
  | null;

// --- Query classes ---

export type QueryClass =
  | "summary"
  | "comparison"
  | "split_summary"
  | "finder"
  | "leaderboard"
  | "streak"
  | "count";

// --- Route names ---

export type RouteName =
  | "player_game_finder"
  | "game_finder"
  | "player_game_summary"
  | "game_summary"
  | "player_compare"
  | "team_compare"
  | "player_split_summary"
  | "team_split_summary"
  | "season_leaders"
  | "season_team_leaders"
  | "top_player_games"
  | "top_team_games"
  | "player_streak_finder"
  | "team_streak_finder"
  | "team_record"
  | "team_matchup_record"
  | "team_record_leaderboard"
  | "player_occurrence_leaders"
  | "team_occurrence_leaders"
  | "playoff_history"
  | "playoff_appearances"
  | "playoff_matchup_history"
  | "playoff_round_record"
  | "record_by_decade"
  | "record_by_decade_leaderboard"
  | "matchup_by_decade";

// --- Result metadata ---

export interface PlayerIdentityContext {
  player_id: number;
  player_name: string;
}

export interface TeamIdentityContext {
  team_id: number;
  team_abbr: string;
  team_name: string;
}

export interface ResultMetadata {
  query_text?: string;
  route?: string | null;
  query_class?: string;
  season?: string | null;
  start_season?: string | null;
  end_season?: string | null;
  season_type?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  player?: string | null;
  players?: string[];
  player_context?: PlayerIdentityContext | null;
  players_context?: PlayerIdentityContext[];
  team?: string | null;
  teams?: string[];
  team_context?: TeamIdentityContext | null;
  teams_context?: TeamIdentityContext[];
  opponent_context?: TeamIdentityContext | null;
  opponent?: string | null;
  split_type?: string | null;
  grouped_boolean_used?: boolean;
  head_to_head_used?: boolean;
  current_through?: string | null;
  notes?: string[];
  [key: string]: unknown;
}

// --- Section row types ---

export type SectionRow = Record<string, unknown>;

// --- Result payload ---

export interface ResultPayload {
  query_class: QueryClass | string;
  result_status: ResultStatus | string;
  result_reason?: string | null;
  current_through?: string | null;
  metadata: ResultMetadata;
  notes: string[];
  caveats: string[];
  sections: Record<string, SectionRow[]>;
}

// --- Alternate parse ---

export interface AlternateParse {
  intent: string;
  route: string;
  description: string;
  confidence: number;
}

// --- Query response envelope ---

export interface QueryResponse {
  ok: boolean;
  query: string;
  route: RouteName | string | null;
  result_status: ResultStatus;
  result_reason: string | null;
  current_through: string | null;
  confidence: number | null;
  intent: string | null;
  alternates: AlternateParse[];
  notes: string[];
  caveats: string[];
  result: ResultPayload;
}

export interface ErrorResponse {
  ok: false;
  error: string;
  detail: string | null;
}

// --- Request bodies ---

export interface NaturalQueryRequest {
  query: string;
}

export interface StructuredQueryRequest {
  route: string;
  kwargs: Record<string, unknown>;
}

// --- Query history ---

export interface QueryHistoryEntry {
  id: number;
  query: string;
  route: string | null;
  result_status: ResultStatus;
  query_class: string | null;
  timestamp: number;
}

// --- Freshness status ---

export type FreshnessStatusValue = "fresh" | "stale" | "unknown" | "failed";

export interface SeasonFreshness {
  season: string;
  season_type: string;
  status: FreshnessStatusValue;
  current_through: string | null;
  raw_complete: boolean;
  processed_complete: boolean;
  loaded_at: string | null;
}

export interface FreshnessResponse {
  status: FreshnessStatusValue;
  current_through: string | null;
  checked_at: string | null;
  seasons: SeasonFreshness[];
  last_refresh_ok: boolean | null;
  last_refresh_at: string | null;
  last_refresh_error: string | null;
}
