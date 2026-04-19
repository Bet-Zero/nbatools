import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResultSections from "../components/ResultSections";
import type { QueryResponse } from "../api/types";

function makeResponse(overrides: Partial<QueryResponse> = {}): QueryResponse {
  return {
    ok: true,
    query: "test query",
    route: "player_game_summary",
    result_status: "ok",
    result_reason: null,
    current_through: "2025-04-01",
    confidence: null,
    intent: null,
    alternates: [],
    notes: [],
    caveats: [],
    result: {
      query_class: "summary",
      result_status: "ok",
      metadata: {},
      notes: [],
      caveats: [],
      sections: {},
    },
    ...overrides,
  };
}

describe("ResultSections", () => {
  it("renders summary sections", () => {
    const data = makeResponse({
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          summary: [{ player_name: "Jokic", PTS: 26 }],
        },
      },
    });
    render(<ResultSections data={data} />);
    expect(screen.getByText("Summary")).toBeInTheDocument();
    expect(screen.getByText("Jokic")).toBeInTheDocument();
  });

  it("renders leaderboard sections", () => {
    const data = makeResponse({
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          leaderboard: [
            { rank: 1, player_name: "Luka", PTS: 33 },
            { rank: 2, player_name: "SGA", PTS: 31 },
          ],
        },
      },
    });
    render(<ResultSections data={data} />);
    expect(screen.getByText("Leaderboard")).toBeInTheDocument();
    expect(screen.getByText("2 entries")).toBeInTheDocument();
    expect(screen.getByText("Luka")).toBeInTheDocument();
  });

  it("renders finder sections with count", () => {
    const data = makeResponse({
      result: {
        query_class: "finder",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          finder: [
            { game_date: "2025-01-15", PTS: 30 },
            { game_date: "2025-01-20", PTS: 35 },
          ],
        },
      },
    });
    render(<ResultSections data={data} />);
    expect(screen.getByText("Matching Games")).toBeInTheDocument();
    expect(screen.getByText("2 games")).toBeInTheDocument();
  });

  it("renders no-result display for no_result status", () => {
    const data = makeResponse({
      result_status: "no_result",
      result_reason: "no_match",
      result: {
        query_class: "finder",
        result_status: "no_result",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {},
      },
    });
    render(<ResultSections data={data} />);
    expect(screen.getByText("No Results")).toBeInTheDocument();
  });

  it("renders comparison sections", () => {
    const data = makeResponse({
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          summary: [
            { player_name: "Jokic", PTS: 26 },
            { player_name: "Embiid", PTS: 28 },
          ],
          comparison: [{ metric: "PTS", Jokic: 26, Embiid: 28 }],
        },
      },
    });
    render(<ResultSections data={data} />);
    expect(screen.getByText("Players")).toBeInTheDocument();
    expect(screen.getByText("Comparison")).toBeInTheDocument();
  });

  it("renders streak sections", () => {
    const data = makeResponse({
      result: {
        query_class: "streak",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          streak: [
            {
              start_date: "2025-01-01",
              end_date: "2025-01-10",
              streak_length: 5,
            },
          ],
        },
      },
    });
    render(<ResultSections data={data} />);
    expect(screen.getByText("Streaks")).toBeInTheDocument();
    expect(screen.getByText("1 found")).toBeInTheDocument();
  });
});
