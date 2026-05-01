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
  Avatar,
  TeamBadge,
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
    expect(screen.getByText("PTS")).toHaveAttribute("title", "Points");
    expect(screen.getByText("PTS")).toHaveAccessibleName("PTS: Points");
    expect(screen.getByText("26.4")).toBeInTheDocument();
    expect(screen.getByText("per game")).toBeInTheDocument();
    expect(screen.getByText("REB")).toHaveAttribute("title", "Rebounds");
    expect(screen.getByText("12.1")).toBeInTheDocument();
  });

  it("allows explicit stat help without changing visible labels", () => {
    render(<Stat label="CUSTOM" value="12" help="Custom supplied metric" />);

    expect(screen.getByText("CUSTOM")).toHaveAccessibleName(
      "CUSTOM: Custom supplied metric",
    );
    expect(screen.getByText("CUSTOM")).toHaveAttribute(
      "title",
      "Custom supplied metric",
    );
    expect(screen.getByText("12")).toBeInTheDocument();
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

  it("renders avatar and team badge fallbacks with accessible labels", () => {
    render(
      <>
        <Avatar name="Nikola Jokic" />
        <Avatar name="Unavailable Player" unavailable />
        <TeamBadge abbreviation="DEN" name="Denver Nuggets" />
      </>,
    );

    expect(screen.getByLabelText("Nikola Jokic avatar")).toHaveTextContent(
      "NJ",
    );
    expect(
      screen.getByLabelText("Unavailable Player avatar unavailable"),
    ).toHaveTextContent("UP");
    expect(screen.getByLabelText("Denver Nuggets (DEN)")).toHaveTextContent(
      "DEN",
    );
  });

  it("falls back to initials when an avatar image cannot load", () => {
    const { container } = render(
      <Avatar name="Nikola Jokic" imageUrl="https://example.test/jokic.png" />,
    );

    const img = container.querySelector("img");
    expect(img).toHaveAttribute("src", "https://example.test/jokic.png");

    fireEvent.error(img as HTMLImageElement);

    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByLabelText("Nikola Jokic avatar")).toHaveTextContent(
      "NJ",
    );
  });

  it("falls back to abbreviation when a team logo cannot load", () => {
    const { container } = render(
      <TeamBadge
        abbreviation="DEN"
        name="Denver Nuggets"
        logoUrl="https://example.test/nuggets.svg"
      />,
    );

    const img = container.querySelector("img");
    expect(img).toHaveAttribute("src", "https://example.test/nuggets.svg");

    fireEvent.error(img as HTMLImageElement);

    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByLabelText("Denver Nuggets (DEN)")).toHaveTextContent(
      "DEN",
    );
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
          player_context: {
            player_id: 203999,
            player_name: "Nikola Jokic",
          },
          team: "DEN",
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
    expect(screen.getByLabelText("Nikola Jokic avatar")).toBeInTheDocument();
    expect(screen.getByLabelText("Nikola Jokic avatar").querySelector("img"))
      .toHaveAttribute(
        "src",
        "https://cdn.nba.com/headshots/nba/latest/1040x760/203999.png",
      );
    expect(screen.getByLabelText("DEN")).toBeInTheDocument();
    expect(screen.getByText("2024-25")).toBeInTheDocument();
    expect(screen.getByText("Using regular-season logs")).toBeInTheDocument();
    expect(screen.getByText("Playoff games excluded")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "jokic last 10" }));
    expect(onAlternateSelect).toHaveBeenCalledWith("jokic last 10");
  });

  it("keeps long envelope content available for mobile wrapping", () => {
    const onAlternateSelect = vi.fn();
    const longQuery =
      "show playoff matchup history for a very specific pair of teams " +
      "with ExtremelyLongUnbrokenMobileQueryToken1234567890";
    const longAlternate =
      "try the same postseason matchup search with " +
      "ExtremelyLongAlternateSuggestionToken1234567890";
    const longNote =
      "Using a long envelope note that should remain readable on narrow viewports.";
    const longCaveat =
      "Long caveat text stays available when the shell stacks on mobile.";
    const data = makeResponse({
      query: longQuery,
      route: "playoff_matchup_history_with_extra_long_route_label",
      alternates: [
        {
          intent: "playoff_matchup",
          route: "playoff_matchup_history",
          description: longAlternate,
          confidence: 0.64,
        },
      ],
      notes: [longNote],
      caveats: [longCaveat],
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: {
          teams: [
            "A Very Long Team Name With Several Market Segments",
            "Another Very Long Team Name With Several Market Segments",
          ],
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

    expect(
      screen.getByText(
        (_, element) => element?.textContent === `\u201c${longQuery}\u201d`,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("playoff matchup history with extra long route label"),
    ).toBeInTheDocument();
    expect(screen.getByText("comparison")).toBeInTheDocument();
    expect(
      screen.getByText(
        "A Very Long Team Name With Several Market Segments, Another Very Long Team Name With Several Market Segments",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("2024-25")).toBeInTheDocument();
    expect(screen.getByText(longNote)).toBeInTheDocument();
    expect(screen.getByText(longCaveat)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: longAlternate }));
    expect(onAlternateSelect).toHaveBeenCalledWith(longAlternate);
  });

  it("uses team and opponent metadata contexts for logos and colors", () => {
    const data = makeResponse({
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          team: "BOS",
          team_context: {
            team_id: 1610612738,
            team_abbr: "BOS",
            team_name: "Celtics",
          },
          opponent: "LAL",
          opponent_context: {
            team_id: 1610612747,
            team_abbr: "LAL",
            team_name: "Lakers",
          },
        },
        notes: [],
        caveats: [],
        sections: {},
      },
    });

    render(<ResultEnvelope data={data} />);

    const teamBadge = screen.getByLabelText("Celtics (BOS)");
    expect(teamBadge).toHaveStyle("--team-primary: #007A33");
    expect(teamBadge.querySelector("img")).toHaveAttribute(
      "src",
      "https://cdn.nba.com/logos/nba/1610612738/primary/L/logo.svg",
    );

    expect(screen.getByLabelText("Lakers (LAL)").querySelector("img"))
      .toHaveAttribute(
        "src",
        "https://cdn.nba.com/logos/nba/1610612747/primary/L/logo.svg",
      );
  });
});
