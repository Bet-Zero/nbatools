import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { QueryResponse } from "../api/types";

vi.mock("../api/client", () => ({
  fetchDevFixtures: vi.fn(),
  postQuery: vi.fn(),
}));

vi.mock("../lib/reviewScreenshots", () => ({
  downloadReviewScreenshots: vi.fn(),
}));

import ReviewPage from "../ReviewPage";
import { fetchDevFixtures, postQuery } from "../api/client";
import { downloadReviewScreenshots } from "../lib/reviewScreenshots";

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
  window.localStorage.clear();
  vi.mocked(downloadReviewScreenshots).mockResolvedValue();
});

describe("ReviewPage", () => {
  it("fetches fixtures on mount without running queries", async () => {
    vi.mocked(fetchDevFixtures).mockResolvedValue({
      source_path: "docs/architecture/parser/examples.md",
      fixtures: [
        { case_id: "A", query: "First fixture" },
        { case_id: "B", query: "Second fixture" },
      ],
    });

    render(<ReviewPage />);

    expect(await screen.findByText("0 / 2 loaded")).toBeInTheDocument();
    expect(screen.getByText(/2 fixtures available/i)).toBeInTheDocument();
    expect(
      screen.getByText(
        "2 fixtures loaded. Choose a run control to execute review queries.",
      ),
    ).toBeInTheDocument();
    expect(postQuery).not.toHaveBeenCalled();
  });

  it("runs query results manually and renders them as they arrive", async () => {
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
    expect(postQuery).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Run review sweep" }));

    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(2));
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

  it("runs only the first 10 fixtures from the first-10 control", async () => {
    vi.mocked(fetchDevFixtures).mockResolvedValue({
      source_path: "docs/architecture/parser/examples.md",
      fixtures: Array.from({ length: 12 }, (_, index) => ({
        case_id: `Case ${index + 1}`,
        query: `Fixture ${index + 1}`,
      })),
    });
    vi.mocked(postQuery).mockImplementation((query) =>
      Promise.resolve(makeNoResult(query)),
    );

    render(<ReviewPage />);

    await screen.findByText("0 / 12 loaded");
    fireEvent.click(screen.getByRole("button", { name: "Run first 10" }));

    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(10));
    expect(postQuery).not.toHaveBeenCalledWith(
      "Fixture 11",
      expect.anything(),
    );
    expect(await screen.findByText("10 / 12 loaded")).toBeInTheDocument();
  });

  it("uses cached results without calling postQuery", async () => {
    const cached = makeNoResult("Cached fixture");
    window.localStorage.setItem(
      "nbatools.review:v2:A:Cached fixture",
      JSON.stringify({ data: cached }),
    );
    vi.mocked(fetchDevFixtures).mockResolvedValue({
      source_path: "docs/architecture/parser/examples.md",
      fixtures: [{ case_id: "A", query: "Cached fixture" }],
    });

    render(<ReviewPage />);

    await screen.findByText("0 / 1 loaded");
    fireEvent.click(screen.getByRole("button", { name: "Run review sweep" }));

    await screen.findByText("1 / 1 loaded");
    expect(postQuery).not.toHaveBeenCalled();
    expect(
      screen.getByRole("heading", { name: "Cached fixture", level: 3 }),
    ).toBeInTheDocument();
  });

  it("clears cached results and visible review results", async () => {
    window.localStorage.setItem(
      "nbatools.review:v2:A:Cached fixture",
      JSON.stringify({ data: makeNoResult("Cached fixture") }),
    );
    vi.mocked(fetchDevFixtures).mockResolvedValue({
      source_path: "docs/architecture/parser/examples.md",
      fixtures: [{ case_id: "A", query: "Cached fixture" }],
    });

    render(<ReviewPage />);

    await screen.findByText("0 / 1 loaded");
    fireEvent.click(screen.getByRole("button", { name: "Run review sweep" }));
    await screen.findByText("1 / 1 loaded");

    fireEvent.click(
      screen.getByRole("button", { name: "Clear cached results" }),
    );

    expect(window.localStorage.length).toBe(0);
    expect(screen.getByText("0 / 1 loaded")).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Cached fixture", level: 3 }),
    ).not.toBeInTheDocument();
  });

  it("stops queued work after the current concurrency batch", async () => {
    const requests = Array.from({ length: 3 }, () => deferred<QueryResponse>());
    vi.mocked(fetchDevFixtures).mockResolvedValue({
      source_path: "docs/architecture/parser/examples.md",
      fixtures: Array.from({ length: 5 }, (_, index) => ({
        case_id: `Case ${index + 1}`,
        query: `Fixture ${index + 1}`,
      })),
    });
    vi.mocked(postQuery)
      .mockReturnValueOnce(requests[0].promise)
      .mockReturnValueOnce(requests[1].promise)
      .mockReturnValueOnce(requests[2].promise);

    render(<ReviewPage />);

    await screen.findByText("0 / 5 loaded");
    fireEvent.click(screen.getByRole("button", { name: "Run review sweep" }));

    await waitFor(() => expect(postQuery).toHaveBeenCalledTimes(3));
    fireEvent.click(screen.getByRole("button", { name: "Stop" }));

    requests.forEach((request, index) =>
      request.resolve(makeNoResult(`Fixture ${index + 1}`)),
    );

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Run review sweep" }),
      ).not.toBeDisabled(),
    );
    expect(postQuery).toHaveBeenCalledTimes(3);
  });

  it("renders the screenshot download button", async () => {
    vi.mocked(fetchDevFixtures).mockResolvedValue({
      source_path: "docs/architecture/parser/examples.md",
      fixtures: [{ case_id: "A", query: "First fixture" }],
    });
    vi.mocked(postQuery).mockResolvedValue(makeNoResult("First fixture"));

    render(<ReviewPage />);

    await screen.findByText("0 / 1 loaded");
    fireEvent.click(screen.getByRole("button", { name: "Run review sweep" }));

    await waitFor(() =>
      expect(screen.getByText("1 / 1 loaded")).toBeInTheDocument(),
    );

    expect(
      screen.getByRole("button", { name: "Download all screenshots" }),
    ).toBeInTheDocument();
  });

  it("disables the screenshot download button during capture", async () => {
    const capture = deferred<void>();

    vi.mocked(fetchDevFixtures).mockResolvedValue({
      source_path: "docs/architecture/parser/examples.md",
      fixtures: [{ case_id: "A", query: "First fixture" }],
    });
    vi.mocked(postQuery).mockResolvedValue(makeNoResult("First fixture"));
    vi.mocked(downloadReviewScreenshots).mockImplementation(
      async (_targets, onProgress) => {
        onProgress({ current: 1, total: 1 });
        return capture.promise;
      },
    );

    render(<ReviewPage />);

    await screen.findByText("0 / 1 loaded");
    fireEvent.click(screen.getByRole("button", { name: "Run review sweep" }));

    await waitFor(() =>
      expect(screen.getByText("1 / 1 loaded")).toBeInTheDocument(),
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Download all screenshots" }),
    );

    const capturingButton = await screen.findByRole("button", {
      name: "Capturing 1/1...",
    });
    expect(capturingButton).toBeDisabled();

    capture.resolve();

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Download all screenshots" }),
      ).not.toBeDisabled(),
    );
  });

  it("captures one target per shape even when all examples are visible", async () => {
    vi.mocked(fetchDevFixtures).mockResolvedValue({
      source_path: "docs/architecture/parser/examples.md",
      fixtures: [
        { case_id: "A", query: "First fixture" },
        { case_id: "B", query: "Second fixture" },
      ],
    });
    vi.mocked(postQuery)
      .mockResolvedValueOnce(makeNoResult("First fixture"))
      .mockResolvedValueOnce(makeNoResult("Second fixture"));

    render(<ReviewPage />);

    await screen.findByText("0 / 2 loaded");
    fireEvent.click(screen.getByRole("button", { name: "Run review sweep" }));

    await waitFor(() =>
      expect(screen.getByText("2 / 2 loaded")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByLabelText("Show one example per shape"));
    fireEvent.click(
      screen.getByRole("button", { name: "Download all screenshots" }),
    );

    await waitFor(() =>
      expect(downloadReviewScreenshots).toHaveBeenCalledTimes(1),
    );
    const targets = vi.mocked(downloadReviewScreenshots).mock.calls[0]?.[0];
    expect(targets).toHaveLength(1);
  });

  it("shows a capture error when screenshot generation fails", async () => {
    vi.mocked(fetchDevFixtures).mockResolvedValue({
      source_path: "docs/architecture/parser/examples.md",
      fixtures: [{ case_id: "A", query: "First fixture" }],
    });
    vi.mocked(postQuery).mockResolvedValue(makeNoResult("First fixture"));
    vi.mocked(downloadReviewScreenshots).mockRejectedValue(
      new Error("Remote image failed"),
    );

    render(<ReviewPage />);

    await screen.findByText("0 / 1 loaded");
    fireEvent.click(screen.getByRole("button", { name: "Run review sweep" }));

    await waitFor(() =>
      expect(screen.getByText("1 / 1 loaded")).toBeInTheDocument(),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Download all screenshots" }),
    );

    expect(
      await screen.findByText(
        "Screenshot download failed: Remote image failed",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Download all screenshots" }),
    ).not.toBeDisabled();
  });
});
