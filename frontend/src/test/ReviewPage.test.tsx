import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { QueryResponse } from "../api/types";

vi.mock("../api/client", () => ({
  fetchDevFixtures: vi.fn(),
  postQuery: vi.fn(),
}));

import ReviewPage from "../ReviewPage";
import { fetchDevFixtures, postQuery } from "../api/client";

function deferred<T>() {
  let resolve: (value: T) => void = () => {};
  let reject: (reason?: unknown) => void = () => {};
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function makeNoResult(query: string): QueryResponse {
  return {
    ok: false,
    query,
    route: null,
    result_status: "no_result",
    result_reason: "unsupported",
    current_through: null,
    confidence: null,
    intent: null,
    alternates: [],
    notes: [],
    caveats: [],
    result: {
      query_class: "summary",
      result_status: "no_result",
      result_reason: "unsupported",
      metadata: {},
      notes: [],
      caveats: [],
      sections: {},
    },
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ReviewPage", () => {
  it("fetches query results in parallel and renders them as they arrive", async () => {
    const first = deferred<QueryResponse>();
    const second = deferred<QueryResponse>();

    vi.mocked(fetchDevFixtures).mockResolvedValue({
      source_path: "docs/architecture/parser/examples.md",
      fixtures: [
        { case_id: "A", query: "First fixture" },
        { case_id: "B", query: "Second fixture" },
      ],
    });
    vi.mocked(postQuery)
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);

    render(<ReviewPage />);

    expect(await screen.findByText("0 / 2 loaded")).toBeInTheDocument();
    expect(
      screen.getByText("2 fixtures are still loading."),
    ).toBeInTheDocument();

    second.resolve(makeNoResult("Second fixture"));

    await waitFor(() =>
      expect(screen.getByText("1 / 2 loaded")).toBeInTheDocument(),
    );
    await screen.findByRole("button", { name: /Message No Result/i });
    expect(
      screen.getByRole("heading", { name: "Second fixture", level: 3 }),
    ).toBeInTheDocument();
    expect(screen.getByText("1 fixture is still loading.")).toBeInTheDocument();

    first.resolve(makeNoResult("First fixture"));

    await waitFor(() =>
      expect(screen.getByText("2 / 2 loaded")).toBeInTheDocument(),
    );
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /Message No Result/i }),
      ).toHaveTextContent("2 fixtures"),
    );
    expect(
      screen.getByRole("heading", { name: "First fixture", level: 3 }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Second fixture", level: 3 }),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Show one example per shape"));

    expect(
      screen.getByRole("heading", { name: "First fixture", level: 3 }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Second fixture", level: 3 }),
    ).toBeInTheDocument();
  });
});
