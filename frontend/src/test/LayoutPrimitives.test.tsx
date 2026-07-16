import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { QueryResponse } from "../api/types";
import ResultEnvelope, {
  ResultContextSummary,
} from "../components/ResultEnvelope";
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

const originalMatchMedia = window.matchMedia;

function mockReducedMotion(matches: boolean) {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: query === "(prefers-reduced-motion: reduce)" ? matches : false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
}

afterEach(() => {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: originalMatchMedia,
  });
});

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

  it("applies opt-in stat value motion when motion is allowed", () => {
    mockReducedMotion(false);

    render(<Stat label="PTS" value="26.4" size="hero" animateValue />);

    expect(screen.getByText("26.4")).toHaveAttribute("data-motion", "value");
  });

  it("keeps opt-in stat value motion still under reduced motion", () => {
    mockReducedMotion(true);

    render(<Stat label="PTS" value="26.4" size="hero" animateValue />);

    expect(screen.getByText("26.4")).toHaveAttribute("data-motion", "reduced");
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
    expect(screen.getByLabelText("Denver Nuggets (DEN)")).toHaveAttribute(
      "role",
      "img",
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
      <ResultEnvelope data={data} onAlternateSelect={onAlternateSelect} displayMode="debug" />,
    );

    expect(screen.getByText("Success")).toBeInTheDocument();
    expect(screen.getByText("player game summary")).toBeInTheDocument();
    expect(screen.getByText(/Data through/)).toBeInTheDocument();
    expect(screen.getByText("2025-04-01")).toBeInTheDocument();
    expect(screen.getByText("Nikola Jokic")).toBeInTheDocument();
    expect(screen.getByLabelText("Nikola Jokic avatar")).toBeInTheDocument();
    expect(
      screen.getByLabelText("Nikola Jokic avatar").querySelector("img"),
    ).toHaveAttribute(
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
      <ResultEnvelope data={data} onAlternateSelect={onAlternateSelect} displayMode="debug" />,
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

    render(<ResultEnvelope data={data} displayMode="debug" />);

    const teamBadge = screen.getByLabelText("Celtics (BOS)");
    expect(teamBadge).toHaveStyle("--team-primary: #007A33");
    expect(teamBadge.querySelector("img")).toHaveAttribute(
      "src",
      "https://cdn.nba.com/logos/nba/1610612738/primary/L/logo.svg",
    );

    expect(
      screen.getByLabelText("Lakers (LAL)").querySelector("img"),
    ).toHaveAttribute(
      "src",
      "https://cdn.nba.com/logos/nba/1610612747/primary/L/logo.svg",
    );
  });

  it("renders applied filters as envelope chips", () => {
    const data = makeResponse({
      result: {
        query_class: "finder",
        result_status: "ok",
        metadata: {
          applied_filters: [
            { label: "Opponent", value: "Lakers", kind: "team" },
            { label: "pts min", value: "30.0001", kind: "threshold" },
            { label: "OPP PTS max", value: "99.9999", kind: "threshold" },
            {
              label: "Special Event",
              value: "Triple Double",
              kind: "special_event",
            },
            {
              label: "Date range",
              value: "2026-04-01 \u2013 2026-04-12",
              kind: "date",
            },
          ],
        },
        notes: [],
        caveats: [],
        sections: {},
      },
    });

    render(<ResultEnvelope data={data} displayMode="debug" />);

    expect(screen.getByText("Opponent")).toBeInTheDocument();
    expect(screen.getByText("Lakers")).toBeInTheDocument();
    expect(screen.getAllByText("Filter").length).toBeGreaterThan(0);
    expect(screen.getAllByText("30+ PTS").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Opp PTS <= 100").length).toBeGreaterThan(0);
    expect(screen.getByText("Special Event")).toBeInTheDocument();
    expect(screen.getAllByText("Triple Double").length).toBeGreaterThan(0);
    expect(screen.getByText("Date range")).toBeInTheDocument();
    expect(screen.getAllByText("Apr 1\u201312, 2026").length).toBeGreaterThan(0);
    expect(screen.queryByText(/2026-04-01/)).not.toBeInTheDocument();
  });

  it("shows the explicit boolean join mode before applied filter chips", () => {
    const data = makeResponse({
      result: {
        query_class: "count",
        result_status: "ok",
        metadata: {
          boolean_filter_mode: "any",
          applied_filters: [
            { label: "pts min", value: "20 (exclusive)", kind: "threshold" },
            { label: "ast min", value: "10 (exclusive)", kind: "threshold" },
          ],
        },
        notes: [],
        caveats: [],
        sections: {},
      },
    });

    render(<ResultContextSummary data={data} />);

    const contextStrip = screen.getByLabelText("Result context");
    expect(contextStrip).toHaveTextContent("LogicAny filter (OR)");
    expect(contextStrip).toHaveTextContent("> 20 PTS");
    expect(contextStrip).toHaveTextContent("> 10 AST");
  });

  it("renders public context chips and material caveats for placement near the answer", () => {
    const data = makeResponse({
      caveats: ["playoff round data not available before 2001-02"],
      result: {
        query_class: "playoff_history",
        result_status: "ok",
        metadata: {
          team: "LAL",
          season: "2024-25",
          split_type: "home_away",
          applied_filters: [
            { label: "Last N games", value: "10", kind: "window" },
            {
              label: "Date range",
              value: "2026-04-01 \u2013 2026-04-12",
              kind: "date",
            },
          ],
        },
        notes: [],
        caveats: [],
        sections: {},
      },
    });

    render(<ResultContextSummary data={data} />);

    const contextStrip = screen.getByLabelText("Result context");
    // Public context should carry only non-obvious trust/scope info.
    // The answer hero already names team, season, and split type, so
    // those base-scope chips are filtered out (see POST \u00a74).
    expect(contextStrip).not.toHaveTextContent("LAL");
    expect(contextStrip).not.toHaveTextContent("2024-25");
    expect(contextStrip).not.toHaveTextContent("Home/Away");
    expect(contextStrip).toHaveTextContent("Last 10 games");
    expect(contextStrip).toHaveTextContent("Apr 1\u201312, 2026");
    expect(screen.getByText("Caveats")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Round-level data is unavailable before 2001-02, so those seasons are included in totals but not round breakdowns.",
      ),
    ).toBeInTheDocument();
  });

  it("hides the public context strip when only base scope chips would remain", () => {
    // When the answer hero already names everything that would otherwise
    // appear in the public context strip (team + season here), the strip
    // collapses entirely \u2014 no empty chip bar near the hero.
    const data = makeResponse({
      result: {
        query_class: "team_record",
        result_status: "ok",
        metadata: {
          team: "BOS",
          season: "2025-26",
        },
        notes: [],
        caveats: [],
        sections: {},
      },
    });

    const { container } = render(<ResultContextSummary data={data} />);

    expect(container).toBeEmptyDOMElement();
  });

  it("formats opponent-quality filters as opponent-group chips", () => {
    const data = makeResponse({
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {
          applied_filters: [
            { label: "Opponent quality", value: "good teams", kind: "quality" },
          ],
        },
        notes: [],
        caveats: [],
        sections: {},
      },
    });

    render(<ResultEnvelope data={data} displayMode="debug" />);

    expect(screen.getByText("Opponent group")).toBeInTheDocument();
    expect(screen.getAllByText("Good Teams").length).toBeGreaterThan(0);
    expect(screen.queryByText("Opponent quality")).not.toBeInTheDocument();
  });

  it("classifies leaderboard interpretation caveats as context", () => {
    const data = makeResponse({
      caveats: [
        "record by decade leaderboard (wins)",
        "across 2010-11 to 2019-20",
        "playoff round data not available before 2001-02",
      ],
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {},
      },
    });

    render(<ResultEnvelope data={data} displayMode="debug" />);

    expect(screen.getByText("Context")).toBeInTheDocument();
    expect(
      screen.getByText("Record by decade leaderboard (WINS)"),
    ).toBeInTheDocument();
    expect(screen.getByText("2010-11 to 2019-20")).toBeInTheDocument();
    expect(screen.getByText("Caveats")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Round-level data is unavailable before 2001-02, so those seasons are included in totals but not round breakdowns.",
      ),
    ).toBeInTheDocument();
  });

  it("classifies record and matchup range notes as context", () => {
    const data = makeResponse({
      caveats: [
        "record filtered to games vs 20 opponents (ATL, BOS, CHI, ...)",
        "record by decade aggregated across 1996-97 to 2025-26",
        "matchup history: LAL vs BOS by decade",
        "playoff matchup history: MIA vs NYK",
      ],
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {},
      },
    });

    render(<ResultEnvelope data={data} displayMode="debug" />);

    expect(screen.getByText("Context")).toBeInTheDocument();
    expect(screen.getByText("Included opponents:")).toBeInTheDocument();
    expect(screen.getByText("20 teams (ATL, BOS, CHI, ...)")).toBeInTheDocument();
    expect(
      screen.getByText("Record by decade across 1996-97 to 2025-26"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Matchup history: LAL vs BOS by decade"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Playoff matchup history: MIA vs NYK"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Caveats")).not.toBeInTheDocument();
  });

  it("deduplicates range filters and humanizes product-facing notes", () => {
    const data = makeResponse({
      notes: [
        "sample_advanced_metrics: usg_pct, ast_pct, reb_pct, tov_pct recomputed from filtered sample",
        "default: <metric> only \u2192 league-wide leaderboard",
        "leaderboard_source: game-log derived (season-advanced stats excluded in date window)",
      ],
      result: {
        query_class: "leaderboard",
        result_status: "ok",
        metadata: {
          route: "player_stretch_leaderboard",
          stat: "pts",
          start_season: "2023-24",
          end_season: "2025-26",
          applied_filters: [
            {
              label: "Season range",
              value: "2023-24 \u2013 2025-26",
              kind: "season",
            },
            { label: "Last N games", value: "10", kind: "window" },
          ],
        },
        notes: [],
        caveats: [],
        sections: {},
      },
    });

    render(<ResultEnvelope data={data} displayMode="debug" />);

    expect(screen.getByText("Metric:")).toBeInTheDocument();
    expect(screen.getByText("PPG")).toBeInTheDocument();
    expect(screen.getByText("Window:")).toBeInTheDocument();
    expect(screen.getAllByText("Last 10 games").length).toBeGreaterThan(0);
    expect(screen.getAllByText("2023-24 to 2025-26")).toHaveLength(1);
    expect(
      screen.getByText(
        "Advanced rate stats were recalculated using only this filtered sample.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/sample_advanced_metrics/)).not.toBeInTheDocument();
    expect(screen.queryByText(/leaderboard_source/)).not.toBeInTheDocument();
    expect(screen.queryByText(/<metric> only/)).not.toBeInTheDocument();
  });

  it("suppresses notes in the envelope for no-result outcomes", () => {
    const data = makeResponse({
      result_status: "no_result",
      result_reason: "no_match",
      notes: ["No games matched the specified filters"],
      caveats: ["Recent games may not be loaded yet"],
      result: {
        query_class: "summary",
        result_status: "no_result",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {},
      },
    });

    render(<ResultEnvelope data={data} displayMode="debug" />);

    expect(screen.queryByText("Notes")).not.toBeInTheDocument();
    expect(
      screen.queryByText("No games matched the specified filters"),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Caveats")).toBeInTheDocument();
    expect(
      screen.getByText("Recent games may not be loaded yet"),
    ).toBeInTheDocument();
  });
});
