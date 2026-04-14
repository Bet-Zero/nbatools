/**
 * Typed API client for the nbatools local API.
 *
 * All calls go to the same origin by default (API served on same host).
 * In Vite dev mode, the proxy in vite.config.ts forwards /api/* to the
 * FastAPI backend.
 */

import type {
  ErrorResponse,
  FreshnessResponse,
  HealthResponse,
  QueryResponse,
  RoutesResponse,
} from "./types";

const BASE = "";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + url, init);
  const data = await res.json();

  if (!res.ok) {
    const err = data as ErrorResponse;
    throw new Error(err.detail ?? err.error ?? `HTTP ${res.status}`);
  }
  return data as T;
}

export async function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export async function fetchRoutes(): Promise<RoutesResponse> {
  return request<RoutesResponse>("/routes");
}

export async function postQuery(query: string): Promise<QueryResponse> {
  return request<QueryResponse>("/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
