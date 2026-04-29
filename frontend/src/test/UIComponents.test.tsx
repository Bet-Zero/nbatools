import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import EmptyState from "../components/EmptyState";
import NoResultDisplay from "../components/NoResultDisplay";
import Loading from "../components/Loading";
import ErrorBox from "../components/ErrorBox";

describe("EmptyState", () => {
  it("renders welcome message", () => {
    render(<EmptyState />);
    expect(screen.getByText("Search the NBA")).toBeInTheDocument();
  });

  it("renders example tips", () => {
    render(<EmptyState />);
    expect(screen.getByText(/Jokic last 10 games/)).toBeInTheDocument();
  });
});

describe("NoResultDisplay", () => {
  it("shows no results for no_result status", () => {
    render(<NoResultDisplay reason="no_match" status="no_result" />);
    expect(screen.getByText("No Results")).toBeInTheDocument();
    expect(
      screen.getByText("No games or records matched your query filters."),
    ).toBeInTheDocument();
  });

  it("shows error variant for error status", () => {
    render(<NoResultDisplay reason="error" status="error" />);
    expect(screen.getByText("Query Error")).toBeInTheDocument();
  });

  it("shows default message when no reason", () => {
    render(<NoResultDisplay reason={null} status="no_result" />);
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
    expect(screen.getByText("Unsupported Query")).toBeInTheDocument();
    expect(
      screen.getByText(
        "This query combination is not supported by the engine.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Cannot use both home_only and away_only/),
    ).toBeInTheDocument();
  });

  it("shows ambiguous variant", () => {
    render(<NoResultDisplay reason="ambiguous" status="no_result" />);
    expect(screen.getByText("Ambiguous Query")).toBeInTheDocument();
    expect(
      screen.getByText(/matched multiple possible entities/),
    ).toBeInTheDocument();
  });

  it("does not show suggestions for unsupported reason", () => {
    render(<NoResultDisplay reason="unsupported" status="no_result" />);
    expect(screen.queryByText("Suggestions")).not.toBeInTheDocument();
  });

  it("shows suggestions for no_match reason", () => {
    render(<NoResultDisplay reason="no_match" status="no_result" />);
    expect(screen.getByText("Suggestions")).toBeInTheDocument();
  });
});

describe("Loading", () => {
  it("renders loading text", () => {
    render(<Loading />);
    expect(screen.getByText("Searching NBA data\u2026")).toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});

describe("ErrorBox", () => {
  it("renders error message", () => {
    render(<ErrorBox message="Connection refused" />);
    expect(screen.getByText("Connection refused")).toBeInTheDocument();
    expect(screen.getByText("Error")).toBeInTheDocument();
  });
});
