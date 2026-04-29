import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { QueryResponse } from "../api/types";
import ResultEnvelope from "../components/ResultEnvelope";
import { Card, ResultEnvelopeShell, SectionHeader } from "../design-system";

function makeResponse(overrides: Partial<QueryResponse> = {}): QueryResponse {
  return {
    ok: true,
    query: "jokic points vs lakers",
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

describe("layout primitives", () => {
  it("renders card content with a custom semantic element", () => {
    render(
      <Card as="section" aria-label="Result panel" depth="elevated">
        Result content
      </Card>,
    );

    expect(
      screen.getByRole("region", { name: "Result panel" }),
    ).toHaveTextContent("Result content");
  });

  it("renders section title, count, eyebrow, and actions", () => {
    render(
      <SectionHeader
        eyebrow="Results"
        title="Leaderboard"
        count="2 entries"
        actions={<button type="button">Export</button>}
      />,
    );

    expect(screen.getByText("Results")).toBeInTheDocument();
    expect(screen.getByText("Leaderboard")).toBeInTheDocument();
    expect(screen.getByText("2 entries")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export" })).toBeInTheDocument();
  });

  it("renders result envelope slots without owning response semantics", () => {
    render(
      <ResultEnvelopeShell
        meta={<span>Success</span>}
        query={<span>jokic points</span>}
        context={<span>Player Jokic</span>}
        notices={<span>Data note</span>}
        alternates={<button type="button">Try another query</button>}
      />,
    );

    expect(screen.getByText("Success")).toBeInTheDocument();
    expect(screen.getByText("jokic points")).toBeInTheDocument();
    expect(screen.getByText("Player Jokic")).toBeInTheDocument();
    expect(screen.getByText("Data note")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Try another query" }),
    ).toBeInTheDocument();
  });
});

describe("migrated result envelope", () => {
  it("preserves metadata, notes, caveats, and alternate actions", () => {
    const onAlternateSelect = vi.fn();
    const data = makeResponse({
      alternates: [
        {
          intent: "summary",
          route: "player_game_summary",
          description: "jokic last 10",
          confidence: 0.7,
        },
      ],
      caveats: ["Playoff games excluded"],
      notes: ["Using regular-season logs"],
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          player: "Nikola Jokic",
          season: "2024-25",
        },
        notes: [],
        caveats: [],
        sections: {},
      },
    });

    render(
      <ResultEnvelope data={data} onAlternateSelect={onAlternateSelect} />,
    );

    expect(screen.getByText("Success")).toBeInTheDocument();
    expect(screen.getByText("player game summary")).toBeInTheDocument();
    expect(screen.getByText(/Data through/)).toBeInTheDocument();
    expect(screen.getByText("2025-04-01")).toBeInTheDocument();
    expect(screen.getByText("Nikola Jokic")).toBeInTheDocument();
    expect(screen.getByText("2024-25")).toBeInTheDocument();
    expect(screen.getByText("Using regular-season logs")).toBeInTheDocument();
    expect(screen.getByText("Playoff games excluded")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "jokic last 10" }));
    expect(onAlternateSelect).toHaveBeenCalledWith("jokic last 10");
  });
});
