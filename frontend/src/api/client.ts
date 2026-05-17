/**
 * Typed API client for the nbatools local API.
 *
 * All calls go to the same origin by default (API served on same host).
 * In Vite dev mode, the proxy in vite.config.ts forwards /api/* to the
 * FastAPI backend.
 */

import type {
  DevFixturesResponse,
  ErrorResponse,
  FreshnessResponse,
  HealthResponse,
  QueryResponse,
  RoutesResponse,
} from "./types";

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
  const res = await fetch(BASE + url, init);
  const body = await res.text();
  let data: unknown = null;

  if (body.trim()) {
    try {
      data = JSON.parse(body);
    } catch {
      throw new Error(
        `HTTP ${res.status} returned non-JSON response: ${bodyPreview(body)}`,
      );
    }
  }

  if (!res.ok) {
    if (isErrorResponse(data)) {
      throw new Error(data.detail ?? data.error ?? `HTTP ${res.status}`);
    }
    throw new Error(`HTTP ${res.status}: ${bodyPreview(body)}`);
  }

  if (data === null) {
    throw new Error(`HTTP ${res.status}: empty response body`);
  }

  return data as T;
}

export async function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export async function fetchRoutes(): Promise<RoutesResponse> {
  return request<RoutesResponse>("/routes");
}

export async function postQuery(
  query: string,
  options?: { signal?: AbortSignal },
): Promise<QueryResponse> {
  return request<QueryResponse>("/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    signal: options?.signal,
    body: JSON.stringify({ query }),
  });
}

export async function postStructuredQuery(
  route: string,
  kwargs: Record<string, unknown>,
): Promise<QueryResponse> {
  return request<QueryResponse>("/structured-query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ route, kwargs }),
  });
}

export async function fetchFreshness(): Promise<FreshnessResponse> {
  return request<FreshnessResponse>("/freshness");
}

export async function fetchDevFixtures(): Promise<DevFixturesResponse> {
  return request<DevFixturesResponse>("/api/dev/fixtures");
}
