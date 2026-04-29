import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { QueryResponse } from "../api/types";
import ResultEnvelope from "../components/ResultEnvelope";
import {
  Badge,
  Card,
  ResultEnvelopeShell,
  SectionHeader,
  Skeleton,
  SkeletonBlock,
  SkeletonText,
  Stat,
  StatBlock,
} from "../design-system";

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

  it("renders badge variants and stat values", () => {
    render(
      <>
        <Badge variant="success" uppercase>
          fresh
        </Badge>
        <Stat label="PTS" value="26.4" context="per game" semantic="accent" />
        <StatBlock
          stats={[
            { label: "REB", value: "12.1" },
            { label: "AST", value: "8.9" },
          ]}
          columns={2}
        />
      </>,
    );

    expect(screen.getByText("fresh")).toBeInTheDocument();
    expect(screen.getByText("PTS")).toBeInTheDocument();
    expect(screen.getByText("26.4")).toBeInTheDocument();
    expect(screen.getByText("per game")).toBeInTheDocument();
    expect(screen.getByText("REB")).toBeInTheDocument();
    expect(screen.getByText("12.1")).toBeInTheDocument();
  });

  it("renders skeleton shapes, text, and blocks", () => {
    const { container } = render(
      <>
        <Skeleton width="50%" height="20px" />
        <SkeletonText aria-label="Loading text" lines={2} width="80%" />
        <SkeletonBlock aria-label="Loading table" rows={2} />
      </>,
    );

    expect(container.querySelectorAll("[aria-hidden='true']").length).toBe(10);
    expect(screen.getByLabelText("Loading text")).toBeInTheDocument();
    expect(screen.getByLabelText("Loading table")).toBeInTheDocument();
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
