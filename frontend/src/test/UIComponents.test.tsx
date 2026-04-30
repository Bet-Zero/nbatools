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
      screen.getByText("Ask a basketball question. Get a structured answer."),
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
    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-live", "polite");
    expect(status).toHaveAttribute("aria-busy", "true");
  });

  it("renders a compact result-preview skeleton", () => {
    render(<Loading />);
    expect(screen.getByLabelText("Loading result preview")).toBeInTheDocument();
    expect(screen.getByLabelText("Loading result metadata")).toBeInTheDocument();
    expect(screen.getByLabelText("Loading summary preview")).toBeInTheDocument();
    expect(screen.getByLabelText("Loading result rows")).toBeInTheDocument();
  });
});

describe("ErrorBox", () => {
  it("renders error message", () => {
    render(<ErrorBox message="Connection refused" />);
    expect(screen.getByText("Connection refused")).toBeInTheDocument();
    expect(screen.getByText("Error")).toBeInTheDocument();
  });
});
