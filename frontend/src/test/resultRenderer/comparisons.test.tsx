import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResultRenderer from "../../components/results/ResultRenderer";
import { makeResponse } from "./helpers";

describe("ResultRenderer comparison patterns", () => {

  it("renders player comparisons with subject panels and metric edges", () => {
    const data = makeResponse({
      query: "Jokic vs Embiid this season",
      route: "player_compare",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: {
          query_text: "Jokic vs Embiid this season",
          route: "player_compare",
          season: "2025-26",
          season_type: "Regular Season",
          players_context: [
            { player_id: 203999, player_name: "Nikola Jokic" },
            { player_id: 203954, player_name: "Joel Embiid" },
          ],
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              player_name: "Nikola Jokic",
              team_abbr: "DEN",
              games: 72,
              wins: 51,
              losses: 21,
              win_pct: 0.708,
              pts_avg: 26.4,
              reb_avg: 12.1,
              ast_avg: 9.3,
            },
            {
              player_name: "Joel Embiid",
              team_abbr: "PHI",
              games: 68,
              wins: 44,
              losses: 24,
              win_pct: 0.647,
              pts_avg: 30.1,
              reb_avg: 10.8,
              ast_avg: 5.7,
            },
          ],
          comparison: [
            {
              metric: "pts_avg",
              "Nikola Jokic": 26.4,
              "Joel Embiid": 30.1,
            },
            {
              metric: "ast_avg",
              "Nikola Jokic": 9.3,
              "Joel Embiid": 5.7,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    const compared = screen.getByLabelText("Compared players");
    expect(screen.getByLabelText("Comparison result")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Nikola Jokic has 51 wins to Joel Embiid's 44 in the 2025-26 regular season.",
      ),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Nikola Jokic").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Joel Embiid").length).toBeGreaterThan(0);
    expect(within(compared).getByText("51-21")).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Comparison metrics" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Metric" }),
    ).toHaveAttribute("data-mobile-priority", "primary");
    expect(
      screen.getByRole("columnheader", { name: "Nikola Jokic" }),
    ).toHaveAttribute("data-mobile-priority", "primary");
    expect(
      screen.getByRole("columnheader", { name: "Joel Embiid" }),
    ).toHaveAttribute("data-mobile-priority", "primary");
    expect(
      screen.getByRole("columnheader", { name: "Edge / Difference" }),
    ).toHaveAttribute("data-mobile-priority", "primary");
    expect(screen.getByText("PTS Avg")).toBeInTheDocument();
    expect(screen.getAllByText("Joel Embiid +3.7 PTS").length).toBeGreaterThan(
      0,
    );
    expect(screen.getByText("Nikola Jokic +3.6 AST")).toBeInTheDocument();
    expect(screen.queryByText("Player Summary Detail")).not.toBeInTheDocument();
    expect(screen.queryByText("Full Metric Detail")).not.toBeInTheDocument();
  });


  it("renders recent-form comparisons with compact primary metrics and safe differences", () => {
    const data = makeResponse({
      query: "Jokic vs Embiid recent form",
      route: "player_compare",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: {
          query_text: "Jokic vs Embiid recent form",
          route: "player_compare",
          season: "2025-26",
          season_type: "Regular Season",
          applied_filters: [
            { label: "Last N games", value: "10", kind: "window" },
          ],
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              player_name: "Nikola Jokić",
              games: 10,
              wins: 10,
              losses: 0,
              win_pct: 1,
              minutes_avg: 35.2,
              pts_avg: 25.3,
              reb_avg: 14.5,
              ast_avg: 11.9,
              stl_avg: 1.2,
              blk_avg: 0.7,
              tov_avg: 3,
              plus_minus_avg: 11,
              efg_pct_avg: 0.589,
              ts_pct_avg: 0.637,
            },
            {
              player_name: "Joel Embiid",
              games: 10,
              wins: 7,
              losses: 3,
              win_pct: 0.7,
              minutes_avg: 33.2,
              pts_avg: 28.8,
              reb_avg: 8.2,
              ast_avg: 4.2,
              stl_avg: 0.3,
              blk_avg: 1.5,
              tov_avg: 2.3,
              plus_minus_avg: 2.6,
              efg_pct_avg: 0.545,
              ts_pct_avg: 0.623,
            },
          ],
          comparison: [
            { metric: "games", "Nikola Jokić": 10, "Joel Embiid": 10 },
            { metric: "wins", "Nikola Jokić": 10, "Joel Embiid": 7 },
            { metric: "losses", "Nikola Jokić": 0, "Joel Embiid": 3 },
            { metric: "win_pct", "Nikola Jokić": 1, "Joel Embiid": 0.7 },
            { metric: "minutes_avg", "Nikola Jokić": 35.2, "Joel Embiid": 33.2 },
            { metric: "pts_avg", "Nikola Jokić": 25.3, "Joel Embiid": 28.8 },
            { metric: "reb_avg", "Nikola Jokić": 14.5, "Joel Embiid": 8.2 },
            { metric: "ast_avg", "Nikola Jokić": 11.9, "Joel Embiid": 4.2 },
            { metric: "stl_avg", "Nikola Jokić": 1.2, "Joel Embiid": 0.3 },
            { metric: "blk_avg", "Nikola Jokić": 0.7, "Joel Embiid": 1.5 },
            { metric: "tov_avg", "Nikola Jokić": 3, "Joel Embiid": 2.3 },
            { metric: "plus_minus_avg", "Nikola Jokić": 11, "Joel Embiid": 2.6 },
            { metric: "efg_pct_avg", "Nikola Jokić": 0.589, "Joel Embiid": 0.545 },
            { metric: "ts_pct_avg", "Nikola Jokić": 0.637, "Joel Embiid": 0.623 },
            { metric: "usg_pct_avg", "Nikola Jokić": 28.2, "Joel Embiid": 33.1 },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    expect(
      screen.getByText(
        "Over their last 10 games, Nikola Jokić has averaged 25.3 points, 14.5 rebounds and 11.9 assists, while Joel Embiid has averaged 28.8 points, 8.2 rebounds and 4.2 assists.",
      ),
    ).toBeInTheDocument();
    const table = screen.getByRole("table", { name: "Comparison metrics" });
    expect(within(table).getByText("Record")).toBeInTheDocument();
    expect(within(table).queryByText("USG% Avg")).not.toBeInTheDocument();
    expect(screen.getByText("Difference 2.0 MIN")).toBeInTheDocument();
    expect(screen.queryByText("Nikola Jokić +3 losses")).not.toBeInTheDocument();
    const showMore = screen.getByRole("button", { name: "Show more metrics" });
    fireEvent.click(showMore);
    expect(screen.getByText("USG% Avg")).toBeInTheDocument();
    expect(screen.getByText("Nikola Jokić 3 fewer losses")).toBeInTheDocument();
    expect(
      screen.getByText("Nikola Jokić +30.0 percentage points"),
    ).toBeInTheDocument();
  });


  it("renders team comparisons with team identity and metric deltas", () => {
    const data = makeResponse({
      query: "Celtics vs Lakers",
      route: "team_compare",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: {
          query_text: "Celtics vs Lakers",
          route: "team_compare",
          season: "2024-25",
          season_type: "Regular Season",
          teams_context: [
            {
              team_id: 1610612738,
              team_abbr: "BOS",
              team_name: "Boston Celtics",
            },
            {
              team_id: 1610612747,
              team_abbr: "LAL",
              team_name: "Los Angeles Lakers",
            },
          ],
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              team_name: "Boston Celtics",
              games: 82,
              wins: 60,
              losses: 22,
              win_pct: 0.732,
              pts_avg: 120.6,
            },
            {
              team_name: "Los Angeles Lakers",
              games: 82,
              wins: 47,
              losses: 35,
              win_pct: 0.573,
              pts_avg: 116.1,
            },
          ],
          comparison: [
            { metric: "wins", BOS: 60, LAL: 47 },
            { metric: "pts_avg", BOS: 120.6, LAL: 116.1 },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    const compared = screen.getByLabelText("Compared teams");
    expect(
      within(compared).getByLabelText("Boston Celtics (BOS)"),
    ).toBeInTheDocument();
    expect(
      within(compared).getByLabelText("Los Angeles Lakers (LAL)"),
    ).toBeInTheDocument();
    expect(within(compared).getByText("60-22")).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "BOS" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "LAL" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Boston Celtics +13 wins")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Show more metrics" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Team Summary Detail")).not.toBeInTheDocument();
    expect(screen.queryByText("Full Metric Detail")).not.toBeInTheDocument();
  });


  it("renders matchup records as head-to-head comparisons", () => {
    const data = makeResponse({
      query: "Lakers vs Celtics head-to-head",
      route: "team_matchup_record",
      result: {
        query_class: "comparison",
        result_status: "ok",
        metadata: {
          query_text: "Lakers vs Celtics head-to-head",
          route: "team_matchup_record",
          teams_context: [
            {
              team_id: 1610612747,
              team_abbr: "LAL",
              team_name: "Los Angeles Lakers",
            },
            {
              team_id: 1610612738,
              team_abbr: "BOS",
              team_name: "Boston Celtics",
            },
          ],
        },
        notes: [],
        caveats: [],
        sections: {
          summary: [
            {
              team_name: "Los Angeles Lakers",
              games: 4,
              wins: 1,
              losses: 3,
              pts_avg: 109.8,
            },
            {
              team_name: "Boston Celtics",
              games: 4,
              wins: 3,
              losses: 1,
              pts_avg: 118.2,
            },
          ],
          comparison: [
            {
              metric: "wins",
              "Los Angeles Lakers": 1,
              "Boston Celtics": 3,
            },
          ],
        },
        current_through: "2026-04-12",
      },
    });

    render(<ResultRenderer data={data} />);

    const participants = screen.getByLabelText("Head-to-head participants");
    expect(
      screen.getByText(/Boston Celtics lead Los Angeles Lakers/),
    ).toBeInTheDocument();
    expect(within(participants).getByText("1-3")).toBeInTheDocument();
    expect(within(participants).getByText("3-1")).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Comparison metrics" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Participant Detail")).not.toBeInTheDocument();
    expect(screen.queryByText("Metric Detail")).not.toBeInTheDocument();
  });
});
