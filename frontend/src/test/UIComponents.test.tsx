import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import EmptyState from "../components/EmptyState";
import NoResultDisplay from "../components/NoResultDisplay";
import Loading from "../components/Loading";
import ErrorBox from "../components/ErrorBox";
import SampleQueries from "../components/SampleQueries";

describe("EmptyState", () => {
  it("renders first-run message", () => {
    render(<EmptyState />);
    expect(
      screen.getByText(
        "Ask a supported NBA stat question. Get a straight answer.",
      ),
    ).toBeInTheDocument();
  });

  it("renders supported query areas", () => {
    render(<EmptyState />);
    expect(screen.getByText("Players")).toBeInTheDocument();
    expect(screen.getByText("Teams")).toBeInTheDocument();
    expect(screen.getByText("History")).toBeInTheDocument();
  });
});

describe("SampleQueries", () => {
  it("renders grouped starter queries", () => {
    render(<SampleQueries onSelect={vi.fn()} />);

    expect(
      screen.getByRole("heading", { name: "Players" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Teams" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Run starter query: Jokic last 10 games",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Run starter query: Lakers playoff history",
      }),
    ).toBeInTheDocument();
    expect(screen.queryByText("entity_summary + game_log")).not.toBeInTheDocument();
  });

  it("shows renderer hints only in debug starter queries", () => {
    render(<SampleQueries onSelect={vi.fn()} displayMode="debug" />);

    expect(screen.getByText("entity_summary + game_log")).toBeInTheDocument();
    expect(
      screen.getByText("entity_summary (lineup_summary)"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("fallback_table (lineup_summary)"),
    ).not.toBeInTheDocument();
  });

  it("submits selected starter query text", () => {
    const onSelect = vi.fn();
    render(<SampleQueries onSelect={onSelect} />);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Run starter query: Celtics record 2024-25",
      }),
    );

    expect(onSelect).toHaveBeenCalledWith("Celtics record 2024-25");
  });
});

describe("NoResultDisplay", () => {
  function openDetails() {
    fireEvent.click(screen.getByText("Details"));
  }

  it("shows no results for no_result status", () => {
    render(<NoResultDisplay reason="no_match" status="no_result" />);
    expect(screen.getByText("No Matching Results")).toBeInTheDocument();
    expect(
      screen.getByText("No games or records matched the query filters."),
    ).toBeInTheDocument();
  });

  it("uses readable date copy and date-specific guidance for date no-matches", () => {
    render(
      <NoResultDisplay
        reason="no_match"
        status="no_result"
        notes={["No games matched the specified filters"]}
        metadata={{
          route: "season_leaders",
          stat: "pts",
          start_date: "2026-04-11",
          end_date: "2026-04-11",
        }}
      />,
    );

    expect(
      screen.getByText("No NBA games matched Apr 11, 2026."),
    ).toBeInTheDocument();
    expect(screen.queryByText(/2026-04-11/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("Suggested next steps")).toHaveTextContent(
      "Try the previous NBA game day",
    );
    expect(screen.getByLabelText("Suggested next steps")).toHaveTextContent(
      "Try the next NBA game day",
    );
    expect(screen.getByLabelText("Suggested queries")).toHaveTextContent(
      "Who leads the NBA in points per game this season?",
    );
    expect(
      screen.queryByText(/Check player or team spelling/),
    ).not.toBeInTheDocument();
  });

  it("formats date ranges in no-match copy without raw ISO dates", () => {
    render(
      <NoResultDisplay
        reason="no_match"
        status="no_result"
        notes={["No games matched the specified filters"]}
        metadata={{
          route: "season_leaders",
          stat: "pts",
          start_date: "2026-04-01",
          end_date: "2026-04-12",
        }}
      />,
    );

    expect(
      screen.getByText("No NBA games matched Apr 1\u201312, 2026."),
    ).toBeInTheDocument();
    expect(screen.queryByText(/2026-04-01/)).not.toBeInTheDocument();
    expect(screen.queryByText(/2026-04-12/)).not.toBeInTheDocument();
  });

  it("shows error variant for error status", () => {
    render(<NoResultDisplay reason="error" status="error" />);
    expect(screen.getByText("Query Error")).toBeInTheDocument();
  });

  it("uses clearer copy for unsupported cooled-off phrasing", () => {
    render(
      <NoResultDisplay
        reason="unrouted"
        status="error"
        metadata={{
          query_text: "Which scorers have cooled off over their last 10 games?",
        }}
      />,
    );

    expect(screen.getByText("Can't answer that one yet")).toBeInTheDocument();
    expect(
      screen.getByText(
        'I couldn\'t interpret "cooled off" as a supported stat query yet.',
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("Query Error")).not.toBeInTheDocument();
  });

  it("shows default message when no reason", () => {
    render(<NoResultDisplay reason={null} status="no_result" />);
    expect(screen.getByText("No Results")).toBeInTheDocument();
    expect(screen.getByText("No matching data found.")).toBeInTheDocument();
  });

  it("shows unsupported variant", () => {
    render(
      <NoResultDisplay
        reason="unsupported"
        status="no_result"
        notes={["Cannot use both home_only and away_only"]}
      />,
    );
    expect(screen.getByText("Can't answer that one yet")).toBeInTheDocument();
    expect(
      screen.getByText(
        "That combination isn't supported yet. Try simplifying the question or removing a filter.",
      ),
    ).toBeInTheDocument();
    openDetails();
    expect(
      screen.getByText(/Cannot use both home_only and away_only/),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Result details")).toHaveTextContent("Note");
  });

  it("humanizes backend column names in primary unsupported copy", () => {
    render(
      <NoResultDisplay
        reason="Column 'def_rating' not available"
        status="no_result"
      />,
    );

    expect(
      screen.getByText(
        "Defensive rating is not available in the current dataset.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Column 'def_rating' not available"),
    ).not.toBeInTheDocument();
  });

  it("uses supported recovery copy for legacy personal-foul leaderboard boundaries", () => {
    render(
      <NoResultDisplay
        reason="filter_not_supported"
        status="no_result"
        metadata={{
          route: "season_leaders",
          stat: "pf",
          unsupported_filters: ["personal_foul_leaderboard"],
        }}
      />,
    );

    expect(screen.getByText("Unavailable Filter")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Personal-foul leaderboards are supported. Try asking for personal fouls or PF and include the season you want ranked.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Pf is not available/)).not.toBeInTheDocument();
  });

  it("keeps fouls-drawn concepts distinct from supported personal-foul totals", () => {
    render(
      <NoResultDisplay
        reason="filter_not_supported"
        status="no_result"
        metadata={{
          query_text: "players best at drawing fouls",
          unsupported_filters: ["unsupported_concept"],
        }}
      />,
    );

    expect(screen.getByText("Unsupported Question")).toBeInTheDocument();
    expect(
      screen.getByText(
        "That concept is not supported yet. Try a starter query or one of the supported areas on the start screen.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/Personal-foul leaderboards are supported/),
    ).not.toBeInTheDocument();
  });

  it("explains the player playoff-appearance grain boundary", () => {
    render(
      <NoResultDisplay
        reason="filter_not_supported"
        status="no_result"
        route="playoff_appearances"
        queryClass="count"
        metadata={{
          route: "playoff_appearances",
          player: "LeBron James",
          unsupported_filters: ["player_playoff_appearances"],
        }}
      />,
    );

    expect(screen.getByText("Unsupported Question")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Player playoff-appearance counts are not supported yet. Try asking about a team or the league leaderboard.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/0 appearances/i)).not.toBeInTheDocument();
    expect(screen.queryByText("filter_not_supported")).not.toBeInTheDocument();
  });

  it("keeps raw unsupported diagnostics out of the public no-result message", () => {
    render(
      <NoResultDisplay
        reason="filter_not_supported"
        status="no_result"
        route="season_leaders"
        queryClass="leaderboard"
        metadata={{
          route: "season_leaders",
          stat: "pf",
          unsupported_filters: ["personal_foul_leaderboard"],
        }}
        feedbackAction={<button type="button">Submit for review</button>}
      />,
    );

    expect(
      screen.getByText(
        "Personal-foul leaderboards are supported. Try asking for personal fouls or PF and include the season you want ranked.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("filter_not_supported")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Submit for review" })).toBeInTheDocument();
    expect(screen.queryByText("Details")).not.toBeInTheDocument();
  });

  it("keeps raw unsupported diagnostics available in debug no-result details", () => {
    render(
      <NoResultDisplay
        reason="filter_not_supported"
        status="no_result"
        route="season_leaders"
        queryClass="leaderboard"
        metadata={{
          route: "season_leaders",
          stat: "pf",
          unsupported_filters: ["personal_foul_leaderboard"],
        }}
        displayMode="debug"
      />,
    );

    expect(screen.getByText("filter_not_supported")).toBeInTheDocument();
    expect(screen.getByText("personal_foul_leaderboard")).toBeInTheDocument();
    expect(screen.getByText("season_leaders")).toBeInTheDocument();
  });

  it("uses supported recovery copy for legacy rookie leaderboard boundaries", () => {
    render(
      <NoResultDisplay
        reason="filter_not_supported"
        status="no_result"
        metadata={{
          route: "season_leaders",
          stat: "pts",
          unsupported_filters: ["rookie_leaderboard"],
        }}
      />,
    );

    expect(screen.getByText("Unavailable Filter")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Rookie leaderboards are supported. Try specifying the stat and season you want ranked.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Points is not available for this query."),
    ).not.toBeInTheDocument();
  });

  it("uses supported recovery copy for unresolved role leaderboards", () => {
    render(
      <NoResultDisplay
        reason="filter_not_supported"
        status="no_result"
        metadata={{
          route: "season_leaders",
          stat: "ast",
          unsupported_filters: ["role_leaderboard"],
        }}
      />,
    );

    expect(screen.getByText("Unavailable Filter")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Starter and bench leaderboards are supported. Specify either starter or bench and include the stat you want ranked.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Assists is not available for this query."),
    ).not.toBeInTheDocument();
  });

  it("uses boundary-specific copy for team bench scoring", () => {
    render(
      <NoResultDisplay
        reason="filter_not_supported"
        status="no_result"
        metadata={{
          route: "game_finder",
          stat: "pts",
          unsupported_filters: ["team_bench_scoring"],
        }}
      />,
    );

    expect(screen.getByText("Unsupported Summary")).toBeInTheDocument();
    expect(
      screen.getByText("Team bench-scoring summaries are not supported yet."),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Points is not available for this query."),
    ).not.toBeInTheDocument();
  });

  it("uses typed public copy for unsupported concepts", () => {
    render(
      <NoResultDisplay
        reason="filter_not_supported"
        status="no_result"
        metadata={{
          query_text: "Jokic salary and contract",
          unsupported_filters: ["unsupported_concept"],
        }}
      />,
    );

    expect(screen.getByText("Unsupported Question")).toBeInTheDocument();
    expect(
      screen.getByText(
        "That concept is not supported yet. Try a starter query or one of the supported areas on the start screen.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("unsupported_concept")).not.toBeInTheDocument();
  });

  it("asks which stat when a ranking names none", () => {
    // "best NBA teams this season" used to return a points-per-game
    // leaderboard. The card must ask for a stat, and must never name one the
    // user did not ask for.
    render(
      <NoResultDisplay
        reason="filter_not_supported"
        status="no_result"
        metadata={{
          route: "season_team_leaders",
          query_text: "best NBA teams this season",
          unsupported_filters: ["leaderboard_metric_required"],
        }}
      />,
    );

    expect(screen.getByText("Which Stat?")).toBeInTheDocument();
    expect(
      screen.getByText(/League rankings need a stat to rank by/),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Points is not available for this query."),
    ).not.toBeInTheDocument();
  });

  it("says season totals are unsupported rather than showing per-game", () => {
    render(
      <NoResultDisplay
        reason="filter_not_supported"
        status="no_result"
        metadata={{
          route: "season_leaders",
          // No `stat`: nothing ran. The metric the refusal is *about* travels
          // in `requested_stat`, which is what the backend now publishes.
          requested_stat: "reb",
          requested_aggregation: "total",
          available_aggregation: "per_game",
          query_text: "players with the most total rebounds",
          unsupported_filters: ["leaderboard_aggregation_unsupported"],
        }}
      />,
    );

    expect(screen.getByText("Unsupported Ranking")).toBeInTheDocument();
    // Metric-scoped and direction-specific: rebounds is ranked per game, so
    // the season-total board is the one that does not exist.
    expect(
      screen.getByText(/Rebounds is ranked per game here/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/a season-total rebounds leaderboard is not available/),
    ).toBeInTheDocument();
    // It must not claim every leaderboard is per-game.
    expect(
      screen.queryByText(/League leaderboards rank per-game figures/),
    ).not.toBeInTheDocument();
  });

  it("says per-game is unsupported for a total-backed stat, not the reverse", () => {
    // `minutes per game leaders` executed minutes_total and presented it as
    // the answer. The copy must name this direction, not the opposite one.
    render(
      <NoResultDisplay
        reason="filter_not_supported"
        status="no_result"
        metadata={{
          route: "season_leaders",
          requested_stat: "minutes",
          requested_aggregation: "per_game",
          available_aggregation: "total",
          query_text: "minutes per game leaders",
          unsupported_filters: ["leaderboard_aggregation_unsupported"],
        }}
      />,
    );

    expect(screen.getByText("Unsupported Ranking")).toBeInTheDocument();
    expect(
      screen.getByText(/Minutes is ranked by season total here/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/a per-game minutes leaderboard is not available/),
    ).toBeInTheDocument();
    // The opposite claim, and any suggestion that the total board ran.
    expect(
      screen.queryByText(/Minutes is ranked per game/),
    ).not.toBeInTheDocument();
  });

  it("says only what is certain when no aggregation direction was recorded", () => {
    render(
      <NoResultDisplay
        reason="filter_not_supported"
        status="no_result"
        metadata={{
          route: "season_leaders",
          requested_stat: "pts",
          query_text: "combined scoring leaders",
          unsupported_filters: ["leaderboard_aggregation_unsupported"],
        }}
      />,
    );

    expect(
      screen.getByText(
        /Points is not ranked by the aggregation this asks for, and no other aggregation was substituted for it\./,
      ),
    ).toBeInTheDocument();
  });

  it("says a ranking orders by one stat when several were asked for", () => {
    render(
      <NoResultDisplay
        reason="filter_not_supported"
        status="no_result"
        metadata={{
          route: "season_leaders",
          query_text: "points and rebounds leaders this season",
          requested_metrics: ["pts", "reb"],
          unsupported_filters: ["leaderboard_multiple_metrics_unsupported"],
        }}
      />,
    );

    expect(screen.getByText("Unsupported Ranking")).toBeInTheDocument();
    expect(
      screen.getByText(/only be ordered by one stat/),
    ).toBeInTheDocument();
  });

  it("says a stat is unavailable for the window without naming a substitute", () => {
    // This used to return a points leaderboard with a "using pts" note.
    render(
      <NoResultDisplay
        reason="filter_not_supported"
        status="no_result"
        metadata={{
          route: "season_team_leaders",
          requested_stat: "off_rating",
          query_text: "best offensive teams from 2022-23 to 2024-25",
          unsupported_filters: ["leaderboard_metric_unavailable_for_scope"],
        }}
      />,
    );

    expect(screen.getByText("Unsupported Ranking")).toBeInTheDocument();
    expect(
      screen.getByText(/Offensive rating is not available for that time range/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/no other stat was substituted for it/),
    ).toBeInTheDocument();
    expect(screen.queryByText(/using pts/)).not.toBeInTheDocument();
  });

  it("does not name a metric for a ranking it could not fully read", () => {
    // "top three point shooters" resolved to pts at the base. The card must
    // not announce anything about points.
    render(
      <NoResultDisplay
        reason="filter_not_supported"
        status="no_result"
        metadata={{
          route: "season_leaders",
          // Neither `stat` nor `requested_stat`: the product could not read
          // the whole question, so it has no metric it can honestly report.
          query_text: "top three point shooters",
          unsupported_filters: ["leaderboard_request_unclear"],
        }}
      />,
    );

    expect(screen.getByText("Which Stat?")).toBeInTheDocument();
    expect(
      screen.getByText(/does not say enough to rank on its own/),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Points is not available for this query."),
    ).not.toBeInTheDocument();
  });

  // Opening Details is the only way to see these notes: the disclosure body is
  // not rendered while it is closed, so a collapsed-card assertion cannot see
  // what a reader sees after one click. Every case below opens it.
  describe("opened Details never shows an internal blocker id", () => {
    // The exact shapes the backend publishes for each boundary refusal: the
    // human boundary note, then the generic "<id> filter is not supported"
    // fallback that rendered the identifier verbatim.
    const BOUNDARY_CASES = [
      {
        id: "leaderboard_metric_required",
        boundaryNote:
          "unsupported_boundary: this asks for a ranking without naming a stat to rank by, and there is no default metric; no substituted leaderboard was returned",
        query: "best players this season",
      },
      {
        id: "leaderboard_multiple_metrics_unsupported",
        boundaryNote:
          "unsupported_boundary: this asks for more than one stat, and a ranking orders by exactly one; no substituted leaderboard was returned",
        query: "points and rebounds leaders this season",
      },
      {
        id: "leaderboard_aggregation_unsupported",
        boundaryNote:
          "unsupported_boundary: this asks for a season total of a stat the leaderboard ranks per game; no substituted leaderboard was returned",
        query: "total points leaders this season",
      },
      {
        id: "leaderboard_metric_unavailable_for_scope",
        boundaryNote:
          "unsupported_boundary: the requested stat is not available for that window; no substituted leaderboard was returned",
        query: "best offensive teams from 2022-23 to 2024-25",
      },
      {
        id: "leaderboard_request_unclear",
        boundaryNote:
          "unsupported_boundary: part of this request is outside what a ranking can express; no substituted leaderboard was returned",
        query: "top three point shooters this season",
      },
    ];

    it.each(BOUNDARY_CASES)(
      "$id is never rendered as text",
      ({ id, boundaryNote, query }) => {
        const genericNote = `${id} filter is not supported with current data; try removing this filter or asking for standard player, team, or game stats (blocked: ${id})`;
        const { container } = render(
          <NoResultDisplay
            reason="filter_not_supported"
            status="no_result"
            notes={[boundaryNote, genericNote]}
            metadata={{
              route: "season_leaders",
              query_text: query,
              unsupported_filters: [id],
              notes: [genericNote],
            }}
          />,
        );

        const summary = screen.queryByText("Details");
        if (summary) fireEvent.click(summary);

        expect(container.textContent).not.toContain(id);
        expect(container.textContent).not.toContain("blocked:");
        expect(container.textContent).not.toContain("unsupported_boundary");
      },
    );

    it("keeps ordinary notes that are not the blocker record", () => {
      // Suppression is scoped to the boundary's own duplicate notes. A real
      // caveat about the data still has to reach the reader.
      const { container } = render(
        <NoResultDisplay
          reason="filter_not_supported"
          status="no_result"
          notes={[
            "unsupported_boundary: this asks for a ranking without naming a stat to rank by, and there is no default metric; no substituted leaderboard was returned",
          ]}
          caveats={["Rookie experience coverage is incomplete before 2015-16."]}
          metadata={{
            route: "season_leaders",
            query_text: "best rookies",
            unsupported_filters: ["leaderboard_metric_required"],
          }}
        />,
      );

      fireEvent.click(screen.getByText("Details"));

      expect(
        screen.getByText(
          "Rookie experience coverage is incomplete before 2015-16.",
        ),
      ).toBeInTheDocument();
      expect(container.textContent).not.toContain("leaderboard_metric_required");
    });
  });

  it("asks for a subject and a stat for a bare context fragment", () => {
    // "clutch stats" used to be handed stat="pts" so the leaderboard had
    // something to rank. The card must not mention points, and must ask for
    // the two things actually missing.
    render(
      <NoResultDisplay
        reason="filter_not_supported"
        status="no_result"
        metadata={{
          route: "season_leaders",
          query_text: "clutch stats",
          clutch: true,
          unsupported_filters: ["leaderboard_request_unclear"],
        }}
      />,
    );

    expect(screen.getByText("Which Stat?")).toBeInTheDocument();
    expect(
      screen.getByText(/Name the player or team you mean and the stat you want/),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Points is not available for this query."),
    ).not.toBeInTheDocument();
  });

  it("guides recent defensive-rating unsupported queries to safe alternatives", () => {
    render(
      <NoResultDisplay
        reason="unsupported"
        status="no_result"
        notes={["Column 'def_rating' not available"]}
        metadata={{
          route: "season_team_leaders",
          stat: "def_rating",
          applied_filters: [
            { label: "Last N games", value: "10", kind: "window" },
          ],
        }}
      />,
    );

    expect(
      screen.getByText(
        "Defensive rating is not available for recent team leaderboards in the current dataset.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Suggested queries")).toHaveTextContent(
      "Which teams have the best record recently?",
    );
    expect(screen.getByLabelText("Suggested queries")).toHaveTextContent(
      "Lakers held opponents under 100 points this season",
    );
    openDetails();
    expect(screen.getByLabelText("Result details")).toHaveTextContent(
      "Column 'def_rating' not available",
    );
  });

  it("hides internal parser notes from no-result details", () => {
    render(
      <NoResultDisplay
        reason="no_match"
        status="no_result"
        notes={[
          "No games matched the specified filters",
          "default: <metric> only \u2192 league-wide leaderboard",
          "leaderboard_source: game-log derived (season-advanced stats excluded in date window)",
        ]}
        metadata={{
          route: "season_leaders",
          stat: "pts",
          start_date: "2026-04-11",
          end_date: "2026-04-11",
      }}
      />,
    );

    openDetails();
    expect(screen.getByLabelText("Result details")).toHaveTextContent(
      "No games matched the specified filters",
    );
    expect(screen.queryByText(/<metric> only/)).not.toBeInTheDocument();
    expect(screen.queryByText(/leaderboard_source/)).not.toBeInTheDocument();
  });

  it("shows ambiguous variant", () => {
    render(<NoResultDisplay reason="ambiguous" status="no_result" />);
    expect(screen.getByText("Ambiguous Query")).toBeInTheDocument();
    expect(
      screen.getByText(/matched multiple possible entities/),
    ).toBeInTheDocument();
  });

  it("shows public copy and scoped suggestions for bare player comparison ambiguity", () => {
    render(
      <NoResultDisplay
        reason="ambiguous_query"
        status="no_result"
        metadata={{
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
        }}
        query="LeBron vs KD"
      />,
    );

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

  it("uses specific copy for combined player availability filters", () => {
    render(
      <NoResultDisplay
        reason="filter_not_supported"
        status="no_result"
        notes={[
          "multi-player availability filters are not supported with current data; try a single-player absence query such as 'Lakers record without LeBron' (blocked: multi_player_availability)",
        ]}
      />,
    );

    expect(
      screen.getByText(
        "This version does not support combining with-player and without-player filters yet. Try one availability filter at a time.",
      ),
    ).toBeInTheDocument();
  });

  it("shows entity disambiguation candidates when provided", () => {
    render(
      <NoResultDisplay
        reason="ambiguous"
        status="no_result"
        metadata={{
          candidates: [
            { display_name: "Jaylen Brown", team_abbr: "BOS" },
            { display_name: "Bruce Brown", team_abbr: "NOP" },
            { display_name: "Anthony Brown", team_abbr: null },
          ],
        }}
      />,
    );

    expect(
      screen.getByLabelText("Disambiguation suggestions"),
    ).toHaveTextContent(
      "Did you mean: Jaylen Brown (BOS), Bruce Brown (NOP), or Anthony Brown (free agent)?",
    );
  });

  it("shows suggested query text for fragment ambiguity", () => {
    render(
      <NoResultDisplay
        reason="ambiguous"
        status="no_result"
        metadata={{
          suggested_queries: [
            "how many triple doubles has Jokic had this season",
            "list Jokic triple doubles this season",
          ],
        }}
      />,
    );

    expect(screen.getByLabelText("Suggested queries")).toHaveTextContent(
      "Try one of these:",
    );
    expect(
      screen.getByText("how many triple doubles has Jokic had this season"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("list Jokic triple doubles this season"),
    ).toBeInTheDocument();
  });

  it("does not show suggestions for unsupported reason", () => {
    render(<NoResultDisplay reason="unsupported" status="no_result" />);
    expect(
      screen.queryByLabelText("Suggested next steps"),
    ).not.toBeInTheDocument();
  });

  it("does not show suggestions for ambiguous or unrouted reasons", () => {
    const { rerender } = render(
      <NoResultDisplay reason="ambiguous" status="no_result" />,
    );
    expect(
      screen.queryByLabelText("Suggested next steps"),
    ).not.toBeInTheDocument();

    rerender(<NoResultDisplay reason="unrouted" status="no_result" />);
    expect(screen.getByText("Can't answer that one yet")).toBeInTheDocument();
    expect(
      screen.queryByLabelText("Suggested next steps"),
    ).not.toBeInTheDocument();
  });

  it("shows suggestions for no_match reason", () => {
    render(<NoResultDisplay reason="no_match" status="no_result" />);
    expect(screen.getByLabelText("Suggested next steps")).toBeInTheDocument();
  });

  it("shows supplied caveats in details", () => {
    render(
      <NoResultDisplay
        reason="no_data"
        status="no_result"
        caveats={["Recent games may not be loaded yet"]}
      />,
    );
    openDetails();
    expect(screen.getByLabelText("Result details")).toHaveTextContent("Caveat");
    expect(
      screen.getByText(/Recent games may not be loaded yet/),
    ).toBeInTheDocument();
  });

  it("shows neutral empty-section state for ok responses without rows", () => {
    render(<NoResultDisplay reason="empty_sections" status="ok" />);
    expect(screen.getByText("No Displayable Rows")).toBeInTheDocument();
    expect(
      screen.queryByLabelText("Suggested next steps"),
    ).not.toBeInTheDocument();
  });
});

describe("Loading", () => {
  it("renders loading text", () => {
    render(<Loading />);
    expect(screen.getByText("Searching NBA data\u2026")).toBeInTheDocument();
    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-live", "polite");
    expect(status).toHaveAttribute("aria-busy", "true");
  });

  it("renders a compact result-preview skeleton", () => {
    render(<Loading />);
    expect(screen.getByLabelText("Loading result preview")).toBeInTheDocument();
    expect(
      screen.getByLabelText("Loading result metadata"),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText("Loading summary preview"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Loading result rows")).toBeInTheDocument();
  });
});

describe("ErrorBox", () => {
  it("renders error message", () => {
    render(<ErrorBox message="Connection refused" />);
    expect(screen.getByText("Connection refused")).toBeInTheDocument();
    expect(screen.getByText("Request failed")).toBeInTheDocument();
    expect(screen.getByLabelText("Failure details")).toBeInTheDocument();
  });

  it("renders retry action when provided", () => {
    const onRetry = vi.fn();
    render(
      <ErrorBox
        message="Network request failed"
        onRetry={onRetry}
        retryLabel="Retry query"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Retry query" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("renders API offline messaging distinctly", () => {
    render(<ErrorBox message="Failed to fetch" apiOnline={false} />);
    expect(screen.getByText("API offline")).toBeInTheDocument();
    expect(screen.getByText("offline")).toBeInTheDocument();
  });
});
