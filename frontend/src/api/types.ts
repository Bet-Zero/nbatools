/** Typed API response interfaces matching the nbatools API envelope. */

// --- Health / Routes ---

export interface HealthResponse {
  status: string;
  version: string;
}

export interface RoutesResponse {
  routes: string[];
}

// --- Query response envelope ---

export interface QueryResponse {
  ok: boolean;
  query: string;
  route: string | null;
  result_status: "ok" | "no_result" | "error";
  result_reason: string | null;
  current_through: string | null;
  notes: string[];
  caveats: string[];
  result: ResultPayload;
}

export interface ErrorResponse {
  ok: false;
  error: string;
  detail: string | null;
}

// --- Result payload ---

export type QueryClass =
  | "summary"
  | "comparison"
  | "split_summary"
  | "finder"
  | "leaderboard"
  | "streak";

export interface ResultPayload {
  query_class: QueryClass | string;
  result_status: string;
  result_reason?: string;
  current_through?: string;
  metadata: Record<string, unknown>;
  notes: string[];
  caveats: string[];
  sections: Record<string, Record<string, unknown>[]>;
}

// --- Request bodies ---

export interface NaturalQueryRequest {
  query: string;
}

export interface StructuredQueryRequest {
  route: string;
  kwargs: Record<string, unknown>;
}
