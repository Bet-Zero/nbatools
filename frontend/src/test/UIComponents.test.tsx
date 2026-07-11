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
      screen.getByText("Ask a basketball question. Get a straight answer."),
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

  it("uses boundary-specific copy for personal-foul leaderboards", () => {
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

    expect(screen.getByText("Unsupported Leaderboard")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Personal-foul leaderboards are not supported yet.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Pf is not available/)).not.toBeInTheDocument();
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
      screen.getByText("Personal-foul leaderboards are not supported yet."),
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

  it("uses boundary-specific copy for rookie leaderboards", () => {
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

    expect(
      screen.getByText("Rookie leaderboards are not supported yet."),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Points is not available for this query."),
    ).not.toBeInTheDocument();
  });

  it("uses boundary-specific copy for role leaderboards", () => {
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

    expect(
      screen.getByText(
        "League-wide starter/bench leaderboards are not supported yet.",
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
        "That concept is not supported yet. Try asking for a specific player, team, game, or stat.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("unsupported_concept")).not.toBeInTheDocument();
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
