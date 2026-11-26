/**
 * Typed API client for the nbatools local API.
 *
 * All calls go to the same origin by default (API served on same host).
 * In Vite dev mode, the proxy in vite.config.ts forwards every contracted
 * public route plus the explicit local-only operator routes to FastAPI.
 */

import type {
  AdminFeedbackFilters,
  AdminFeedbackGroupDetailResponse,
  AdminFeedbackGroupsResponse,
  AdminFeedbackTriagePayload,
  AdminFeedbackTriageResponse,
  DevFixturesResponse,
  ErrorResponse,
  FreshnessResponse,
  HealthResponse,
  QueryFeedbackPayload,
  QueryFeedbackResponse,
  QueryResponse,
  RoutesResponse,
} from "./types";
import { ApiRequestError, retryAfterSeconds } from "./requestError";

const BASE = "";

function bodyPreview(body: string): string {
  const cleaned = body.replace(/\s+/g, " ").trim();
  if (!cleaned) return "empty response body";
  return cleaned.length > 180 ? `${cleaned.slice(0, 177)}...` : cleaned;
}

function isErrorResponse(value: unknown): value is ErrorResponse {
  return (
    typeof value === "object" &&
    value !== null &&
    ("detail" in value || "error" in value)
  );
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response;
  let body: string;
  try {
    res = await fetch(BASE + url, init);
    body = await res.text();
  } catch (err) {
    const aborted = typeof err === "object" && err !== null && "name" in err && err.name === "AbortError";
    if (init?.signal?.aborted || aborted) throw err;
    throw new ApiRequestError(
      "The connection was interrupted. Try again when you're online.",
      "network_error",
    );
  }
  const requestId =
    res.headers?.get("X-Request-ID") ?? res.headers?.get("X-Vercel-Id") ?? undefined;
  const retryAfter = retryAfterSeconds(res.headers?.get("Retry-After"));
  const failure = (message: string, code: string) =>
    new ApiRequestError(message, code, res.status, requestId, retryAfter);
  let data: unknown = null;

  if (body.trim()) {
    try {
      data = JSON.parse(body);
    } catch {
      if (res.status === 504) {
        throw failure("The server timed out before it returned an answer.", "execution_timeout");
      }
      throw failure(
        `HTTP ${res.status} returned non-JSON response: ${bodyPreview(body)}`,
        "invalid_response",
      );
    }
  }

  if (!res.ok) {
    if (isErrorResponse(data)) {
      throw failure(data.detail ?? data.error ?? `HTTP ${res.status}`, data.error ?? "http_error");
    }
    if (res.status === 504) {
      throw failure("The server timed out before it returned an answer.", "execution_timeout");
    }
    throw failure(`HTTP ${res.status}: ${bodyPreview(body)}`, "http_error");
  }

  if (data === null) {
    throw failure(`HTTP ${res.status}: empty response body`, "invalid_response");
  }

  return data as T;
}

function adminHeaders(adminToken?: string): HeadersInit {
  const headers: Record<string, string> = {};
  if (adminToken?.trim()) {
    headers["X-NBATools-Admin-Token"] = adminToken.trim();
  }
  return headers;
}

function adminJsonHeaders(adminToken?: string): HeadersInit {
  return {
    "Content-Type": "application/json",
    ...adminHeaders(adminToken),
  };
}

function adminFeedbackQuery(filters?: AdminFeedbackFilters): string {
  const params = new URLSearchParams();
  Object.entries(filters ?? {}).forEach(([key, value]) => {
    const text = String(value ?? "").trim();
    if (text) params.set(key, text);
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

function currentSourcePage(): string {
  if (typeof window === "undefined") return "/";
  return window.location.pathname || "/";
}

export async function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export async function fetchRoutes(): Promise<RoutesResponse> {
  return request<RoutesResponse>("/routes");
}

export async function postQuery(
  query: string,
  options?: { signal?: AbortSignal; sourcePage?: string },
): Promise<QueryResponse> {
  return request<QueryResponse>("/query", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-NBATools-Source-Page": options?.sourcePage ?? currentSourcePage(),
    },
    signal: options?.signal,
    body: JSON.stringify({ query }),
  });
}

export async function postStructuredQuery(
  route: string,
  kwargs: Record<string, unknown>,
  options?: { signal?: AbortSignal; sourcePage?: string },
): Promise<QueryResponse> {
  return request<QueryResponse>("/structured-query", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-NBATools-Source-Page": options?.sourcePage ?? currentSourcePage(),
    },
    signal: options?.signal,
    body: JSON.stringify({ route, kwargs }),
  });
}

export async function postQueryFeedback(
  payload: QueryFeedbackPayload,
): Promise<QueryFeedbackResponse> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-NBATools-Source-Page": payload.source_page ?? currentSourcePage(),
  };
  if (payload.submission_id) {
    headers["X-NBATools-Idempotency-Key"] = payload.submission_id;
  }
  return request<QueryFeedbackResponse>("/query-feedback", {
    method: "POST",
    headers,
    body: JSON.stringify({
      ...payload,
      source_page: payload.source_page ?? currentSourcePage(),
    }),
  });
}

export async function fetchFreshness(options?: {
  signal?: AbortSignal;
}): Promise<FreshnessResponse> {
  return request<FreshnessResponse>(
    "/freshness",
    options?.signal ? { signal: options.signal } : undefined,
  );
}

export async function fetchDevFixtures(): Promise<DevFixturesResponse> {
  return request<DevFixturesResponse>("/api/dev/fixtures");
}

export async function fetchAdminFeedbackGroups(
  filters?: AdminFeedbackFilters,
  options?: { adminToken?: string },
): Promise<AdminFeedbackGroupsResponse> {
  return request<AdminFeedbackGroupsResponse>(
    `/api/admin/feedback/groups${adminFeedbackQuery(filters)}`,
    { headers: adminHeaders(options?.adminToken) },
  );
}

export async function fetchAdminFeedbackGroupDetail(
  groupId: string,
  options?: { adminToken?: string },
): Promise<AdminFeedbackGroupDetailResponse> {
  return request<AdminFeedbackGroupDetailResponse>(
    `/api/admin/feedback/groups/${encodeURIComponent(groupId)}`,
    { headers: adminHeaders(options?.adminToken) },
  );
}

export async function fetchAdminFeedbackTriage(
  groupId: string,
  options?: { adminToken?: string },
): Promise<AdminFeedbackTriageResponse> {
  return request<AdminFeedbackTriageResponse>(
    `/api/admin/feedback/groups/${encodeURIComponent(groupId)}/triage`,
    { headers: adminHeaders(options?.adminToken) },
  );
}

export async function saveAdminFeedbackTriage(
  groupId: string,
  payload: AdminFeedbackTriagePayload,
  options?: { adminToken?: string },
): Promise<AdminFeedbackTriageResponse> {
  return request<AdminFeedbackTriageResponse>(
    `/api/admin/feedback/groups/${encodeURIComponent(groupId)}/triage`,
    {
      method: "PUT",
      headers: adminJsonHeaders(options?.adminToken),
      body: JSON.stringify(payload),
    },
  );
}
