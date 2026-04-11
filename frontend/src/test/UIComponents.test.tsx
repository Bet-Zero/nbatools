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
    expect(screen.getByText("no_match")).toBeInTheDocument();
  });

  it("shows error variant for error status", () => {
    render(<NoResultDisplay reason="Something went wrong" status="error" />);
    expect(screen.getByText("Query Error")).toBeInTheDocument();
  });

  it("shows default message when no reason", () => {
    render(<NoResultDisplay reason={null} status="no_result" />);
    expect(screen.getByText("No matching data found.")).toBeInTheDocument();
  });
});

describe("Loading", () => {
  it("renders loading text", () => {
    render(<Loading />);
    expect(screen.getByText("Running query…")).toBeInTheDocument();
  });
});

describe("ErrorBox", () => {
  it("renders error message", () => {
    render(<ErrorBox message="Connection refused" />);
    expect(screen.getByText("Connection refused")).toBeInTheDocument();
    expect(screen.getByText("Error")).toBeInTheDocument();
  });
});
