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
  | "filter_not_supported"
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
  | "player_stretch_leaderboard"
  | "playoff_history"
  | "playoff_appearances"
  | "playoff_matchup_history"
  | "playoff_round_record"
  | "record_by_decade"
  | "record_by_decade_leaderboard"
  | "matchup_by_decade"
  | "lineup_summary"
  | "lineup_leaderboard";

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

export interface AppliedFilter {
  label: string;
  value: string;
  kind: string;
}

export interface DisambiguationCandidate {
  id?: number | string | null;
  display_name?: string | null;
  team_abbr?: string | null;
  position?: string | null;
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
  scope_kind?: string | null;
  applied_filters?: AppliedFilter[];
  primary_count?: number | null;
  count_phrase?: string | null;
  answer_phrase?: string | null;
  stretch_display_mode?: "named_player" | "players" | "windows" | null;
  candidates?: DisambiguationCandidate[];
  suggested_queries?: string[];
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

// --- Query feedback ---

export type FeedbackSource = "user_submitted";

export type FeedbackType =
  | "wrong_answer"
  | "expected_supported"
  | "confusing_answer"
  | "no_result"
  | "unsupported"
  | "error"
  | "ui_issue"
  | "other";

export interface QueryFeedbackResultShape {
  query_class?: string | null;
  section_keys?: string[];
  section_row_counts?: Record<string, number>;
}

export interface QueryFeedbackPayload {
  submission_id?: string;
  query: string;
  feedback_source: FeedbackSource;
  feedback_type: FeedbackType;
  source_page?: string;
  route?: string | null;
  status?: string | null;
  reason?: string | null;
  result_shape?: QueryFeedbackResultShape;
  metadata?: Record<string, unknown>;
  notes?: string[];
  caveats?: string[];
  user_note?: string;
  answer_text_preview?: string | null;
  error_message?: string | null;
  elapsed_ms?: number;
}

export interface QueryFeedbackResponse {
  ok: boolean;
  feedback_id?: string;
  submission_id?: string | null;
  stored: boolean;
  disabled: boolean;
  idempotent_replay?: boolean;
  error?: string;
  detail?: string | null;
}

// --- Admin query feedback review ---

export type AdminFeedbackReviewStatus = "new" | "reviewed" | "deferred" | "closed";

export type AdminFeedbackTriageDecision =
  | "bug"
  | "support_candidate"
  | "expected_unsupported"
  | "duplicate"
  | "no_action"
  | "needs_more_data"
  | "parser_routing_risk"
  | "ui_copy_issue";

export interface AdminFeedbackTriageOverlay {
  schema_version: number;
  group_id: string;
  review_status: AdminFeedbackReviewStatus;
  triage_decision: AdminFeedbackTriageDecision | null;
  review_notes: string;
  linked_case_or_issue: string;
  reviewer_source?: string | null;
  updated_at?: string | null;
  source_record_ids?: string[];
}

export interface AdminFeedbackGroup {
  group_id: string;
  count: number;
  first_seen: string;
  last_seen: string;
  representative_query: string;
  feedback_sources: string[];
  feedback_types: string[];
  routes: string[];
  statuses: string[];
  reasons: string[];
  unsupported_filters: string[];
  user_notes: string[];
  record_ids: string[];
  object_keys: string[];
  suggested_triage: string;
  triage_modifiers: string[];
  triage_overlay?: AdminFeedbackTriageOverlay;
  review_status?: AdminFeedbackReviewStatus;
  triage_decision?: AdminFeedbackTriageDecision | null;
}

export interface AdminFeedbackRecord {
  id: string;
  created_at: string;
  feedback_source: string;
  feedback_type: string;
  query: string;
  route: string;
  status: string;
  reason: string;
  unsupported_filters: string[];
  user_note: string;
  notes: string[];
  caveats: string[];
  answer_text_preview: string;
  error_message: string;
  elapsed_ms: number | null;
  object_key: string;
  [key: string]: unknown;
}

export interface AdminFeedbackFilters {
  review_status?: string;
  triage_decision?: string;
  feedback_source?: string;
  feedback_type?: string;
  route?: string;
  status?: string;
  reason?: string;
}

export interface AdminFeedbackGroupsResponse {
  ok: true;
  source_mode: string;
  bucket: string;
  prefix: string;
  total_found: number;
  total_exported: number;
  excluded_smoke_count: number;
  group_count: number;
  groups: AdminFeedbackGroup[];
}

export interface AdminFeedbackGroupDetailResponse {
  ok: true;
  group: AdminFeedbackGroup;
  records: AdminFeedbackRecord[];
  triage_overlay: AdminFeedbackTriageOverlay;
  handoff_summary: string;
}

export interface AdminFeedbackTriageResponse {
  ok: true;
  triage_overlay: AdminFeedbackTriageOverlay;
}

export interface AdminFeedbackTriagePayload {
  review_status: AdminFeedbackReviewStatus;
  triage_decision: AdminFeedbackTriageDecision | null;
  review_notes: string;
  linked_case_or_issue: string;
  reviewer_source?: string | null;
}

// --- Request bodies ---

export interface NaturalQueryRequest {
  query: string;
}

export interface StructuredQueryRequest {
  route: string;
  kwargs: Record<string, unknown>;
}

export interface DevFixture {
  case_id: string;
  query: string;
}

export interface DevFixturesResponse {
  source_path: string;
  fixtures: DevFixture[];
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
  validation_state: "passed" | "failed" | "unknown" | "legacy_unverified";
  generation_id: string | null;
  validation_errors: string[];
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
