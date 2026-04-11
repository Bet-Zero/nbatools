import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import useUrlState, {
  parseUrlParams,
  buildUrlSearch,
} from "../hooks/useUrlState";

/* ------------------------------------------------------------------ */
/*  Pure-function tests                                                */
/* ------------------------------------------------------------------ */

describe("parseUrlParams", () => {
  it("returns all null for empty search string", () => {
    expect(parseUrlParams("")).toEqual({
      q: null,
      route: null,
      kwargs: null,
    });
  });

  it("parses a natural query param", () => {
    expect(parseUrlParams("?q=Jokic+last+10+games")).toEqual({
      q: "Jokic last 10 games",
      route: null,
      kwargs: null,
    });
  });

  it("parses structured route params", () => {
    const search =
      "?route=player_summary&kwargs=%7B%22player%22%3A%22Jokic%22%7D";
    expect(parseUrlParams(search)).toEqual({
      q: null,
      route: "player_summary",
      kwargs: '{"player":"Jokic"}',
    });
  });

  it("handles special characters in query", () => {
    expect(parseUrlParams("?q=who+had+30%2B+points")).toEqual({
      q: "who had 30+ points",
      route: null,
      kwargs: null,
    });
  });

  it("treats empty q value as null", () => {
    expect(parseUrlParams("?q=")).toEqual({
      q: null,
      route: null,
      kwargs: null,
    });
  });

  it("ignores unknown params", () => {
    expect(parseUrlParams("?q=test&foo=bar")).toEqual({
      q: "test",
      route: null,
      kwargs: null,
    });
  });
});

describe("buildUrlSearch", () => {
  it("returns empty string for empty params", () => {
    expect(buildUrlSearch({})).toBe("");
  });

  it("returns empty string for all-null params", () => {
    expect(buildUrlSearch({ q: null, route: null, kwargs: null })).toBe("");
  });

  it("builds a natural query search string", () => {
    const result = buildUrlSearch({ q: "Jokic last 10 games" });
    expect(result).toBe("?q=Jokic+last+10+games");
  });

  it("builds a structured query search string", () => {
    const result = buildUrlSearch({
      route: "player_summary",
      kwargs: '{"player":"Jokic"}',
    });
    expect(result).toContain("route=player_summary");
    expect(result).toContain("kwargs=");
    expect(result.startsWith("?")).toBe(true);
  });

  it("omits kwargs when value is '{}'", () => {
    const result = buildUrlSearch({ route: "player_summary", kwargs: "{}" });
    expect(result).toBe("?route=player_summary");
  });

  it("omits null or undefined values", () => {
    expect(buildUrlSearch({ q: "test", route: null })).toBe("?q=test");
  });

  it("round-trips through parseUrlParams", () => {
    const original = { q: "Luka 30+ point games", route: null, kwargs: null };
    const search = buildUrlSearch(original);
    const parsed = parseUrlParams(search);
    expect(parsed).toEqual(original);
  });
});

/* ------------------------------------------------------------------ */
/*  Hook tests                                                         */
/* ------------------------------------------------------------------ */

describe("useUrlState hook", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/");
  });

  it("reads initial params from URL", () => {
    window.history.replaceState(null, "", "/?q=test+query");
    const { result } = renderHook(() => useUrlState());
    expect(result.current.params.q).toBe("test query");
    expect(result.current.params.route).toBeNull();
  });

  it("starts with null params when URL is clean", () => {
    const { result } = renderHook(() => useUrlState());
    expect(result.current.params).toEqual({
      q: null,
      route: null,
      kwargs: null,
    });
  });

  it("pushQuery updates URL and params", () => {
    const { result } = renderHook(() => useUrlState());
    act(() => {
      result.current.pushQuery("new query");
    });
    expect(result.current.params.q).toBe("new query");
    expect(result.current.params.route).toBeNull();
    expect(window.location.search).toBe("?q=new+query");
  });

  it("pushStructured updates URL and params", () => {
    const { result } = renderHook(() => useUrlState());
    act(() => {
      result.current.pushStructured("player_summary", '{"player":"Jokic"}');
    });
    expect(result.current.params.route).toBe("player_summary");
    expect(result.current.params.q).toBeNull();
    expect(window.location.search).toContain("route=player_summary");
  });

  it("clearUrl removes all params from URL", () => {
    window.history.replaceState(null, "", "/?q=old");
    const { result } = renderHook(() => useUrlState());
    act(() => {
      result.current.clearUrl();
    });
    expect(result.current.params.q).toBeNull();
    expect(window.location.search).toBe("");
  });

  it("shareUrl reflects current params", () => {
    const { result } = renderHook(() => useUrlState());
    act(() => {
      result.current.pushQuery("Jokic stats");
    });
    expect(result.current.shareUrl).toContain("?q=Jokic+stats");
  });

  it("shareUrl is origin-only when no params", () => {
    const { result } = renderHook(() => useUrlState());
    expect(result.current.shareUrl).toBe(`${window.location.origin}/`);
  });

  it("calls onNavigate on popstate event", () => {
    const onNavigate = vi.fn();
    renderHook(() => useUrlState(onNavigate));

    // Simulate a back/forward navigation: change URL then fire popstate
    window.history.replaceState(null, "", "/?q=navigated");
    act(() => {
      window.dispatchEvent(new PopStateEvent("popstate"));
    });

    expect(onNavigate).toHaveBeenCalledWith({
      q: "navigated",
      route: null,
      kwargs: null,
    });
  });

  it("updates params on popstate event", () => {
    const { result } = renderHook(() => useUrlState());

    window.history.replaceState(null, "", "/?q=from+back");
    act(() => {
      window.dispatchEvent(new PopStateEvent("popstate"));
    });

    expect(result.current.params.q).toBe("from back");
  });

  it("pushQuery clears structured params", () => {
    const { result } = renderHook(() => useUrlState());
    act(() => {
      result.current.pushStructured("some_route", '{"a":1}');
    });
    expect(result.current.params.route).toBe("some_route");

    act(() => {
      result.current.pushQuery("natural query");
    });
    expect(result.current.params.q).toBe("natural query");
    expect(result.current.params.route).toBeNull();
    expect(result.current.params.kwargs).toBeNull();
  });

  it("pushStructured clears natural query param", () => {
    const { result } = renderHook(() => useUrlState());
    act(() => {
      result.current.pushQuery("some query");
    });
    expect(result.current.params.q).toBe("some query");

    act(() => {
      result.current.pushStructured("route_x", "{}");
    });
    expect(result.current.params.route).toBe("route_x");
    expect(result.current.params.q).toBeNull();
  });
});
