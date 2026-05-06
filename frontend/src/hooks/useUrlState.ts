import { useCallback, useEffect, useEffectEvent, useState } from "react";

/** State derived from / synced to the URL search params. */
export interface UrlParams {
  q: string | null;
  route: string | null;
  kwargs: string | null;
}

/** Parse a URL search string into typed params. */
export function parseUrlParams(search: string): UrlParams {
  const sp = new URLSearchParams(search);
  return {
    q: sp.get("q") || null,
    route: sp.get("route") || null,
    kwargs: sp.get("kwargs") || null,
  };
}

/** Build a URL search string from params.  Returns "" when empty. */
export function buildUrlSearch(params: Partial<UrlParams>): string {
  const sp = new URLSearchParams();
  if (params.q) sp.set("q", params.q);
  if (params.route) sp.set("route", params.route);
  if (params.kwargs && params.kwargs !== "{}") sp.set("kwargs", params.kwargs);
  const str = sp.toString();
  return str ? `?${str}` : "";
}

/**
 * Hook that keeps URL search params in sync with app query state.
 *
 * - Reads initial params from the URL on mount.
 * - Provides push helpers that update both React state and the browser URL.
 * - Calls `onNavigate` when the user presses browser back / forward.
 */
export default function useUrlState(onNavigate?: (params: UrlParams) => void) {
  const [params, setParams] = useState<UrlParams>(() =>
    parseUrlParams(window.location.search),
  );
  const handleNavigate = useEffectEvent((next: UrlParams) => {
    onNavigate?.(next);
  });

  useEffect(() => {
    function handlePopState() {
      const next = parseUrlParams(window.location.search);
      setParams(next);
      handleNavigate(next);
    }
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  /** Push a natural-query URL entry (clears any structured params). */
  const pushQuery = useCallback((q: string) => {
    const next: UrlParams = { q, route: null, kwargs: null };
    window.history.pushState(
      null,
      "",
      buildUrlSearch(next) || window.location.pathname,
    );
    setParams(next);
  }, []);

  /** Push a structured-query URL entry (clears any natural-query param). */
  const pushStructured = useCallback((route: string, kwargs: string) => {
    const next: UrlParams = { q: null, route, kwargs };
    window.history.pushState(
      null,
      "",
      buildUrlSearch(next) || window.location.pathname,
    );
    setParams(next);
  }, []);

  /** Replace the current history entry with an empty URL (no query params). */
  const clearUrl = useCallback(() => {
    window.history.replaceState(null, "", window.location.pathname);
    setParams({ q: null, route: null, kwargs: null });
  }, []);

  /** Full shareable URL reflecting the current params. */
  const shareUrl = `${window.location.origin}${window.location.pathname}${buildUrlSearch(params)}`;

  return { params, pushQuery, pushStructured, clearUrl, shareUrl } as const;
}
