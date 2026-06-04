import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResultRenderer from "../../components/results/ResultRenderer";
import { makeResponse } from "./helpers";

describe("ResultRenderer substrate and empty states", () => {
  it("routes every result through the fallback table by default", () => {
    const data = makeResponse({
      route: "unmapped_route",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          summary: [{ player_name: "Jokic", pts: 27.4, reb: 12.6, ast: 9.2 }],
        },
        current_through: "2025-04-01",
      },
    });

    render(<ResultRenderer data={data} />);

    // Fallback renders one section card per non-empty section.
    expect(screen.getByText("Summary")).toBeInTheDocument();
    // The data inside the section makes it through to the rendered table.
    expect(screen.getByText("Jokic")).toBeInTheDocument();
  });


  it("renders nothing for fully empty results", () => {
    const data = makeResponse({
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {},
        current_through: "2025-04-01",
      },
    });

    const { container } = render(<ResultRenderer data={data} />);
    // NoResultDisplay is the empty-state component; assert at least one
    // child is rendered (i.e. we did not silently render nothing).
    expect(container.firstChild).not.toBeNull();
  });


  it("renders a fallback for every non-empty section", () => {
    const data = makeResponse({
      route: "unmapped_route",
      result: {
        query_class: "summary",
        result_status: "ok",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {
          summary: [{ player_name: "Jokic", pts: 27 }],
          by_season: [{ season: "2025-26", pts_avg: 27 }],
        },
        current_through: "2025-04-01",
      },
    });

    render(<ResultRenderer data={data} />);
    expect(screen.getByText("Summary")).toBeInTheDocument();
    expect(screen.getByText("By Season")).toBeInTheDocument();
  });


  it("renders public ambiguity copy without leaking internal reason labels", () => {
    const data = makeResponse({
      ok: false,
      query: "LeBron vs KD",
      route: "player_compare",
      result_status: "no_result",
      result_reason: "ambiguous_query",
      result: {
        query_class: "comparison",
        result_status: "no_result",
        result_reason: "ambiguous_query",
        metadata: {
          ambiguous_intent: "bare_player_vs_player",
          clarification_options: [
            {
              intent: "player_stat_comparison",
              query: "Compare LeBron James and Kevin Durant this season",
            },
            {
              intent: "player_opponent_games",
              query: "LeBron James stats vs Kevin Durant",
            },
          ],
        },
        notes: [
          "bare player-vs-player queries are ambiguous; add comparison, head-to-head, or stats wording",
        ],
        caveats: [],
        sections: {},
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(screen.getByText("Ambiguous Query")).toBeInTheDocument();
    expect(
      screen.getByText(/This could mean a few different things/),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Suggested queries")).toHaveTextContent(
      "Compare LeBron James and Kevin Durant this season",
    );
    expect(screen.getByLabelText("Suggested queries")).toHaveTextContent(
      "LeBron James stats vs Kevin Durant",
    );
    expect(screen.queryByText("ambiguous_query")).not.toBeInTheDocument();
  });
});
