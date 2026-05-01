import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Button, IconButton } from "../design-system";
import CopyButton from "../components/CopyButton";
import QueryBar from "../components/QueryBar";
import RawJsonToggle from "../components/RawJsonToggle";
import type { QueryResponse } from "../api/types";

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: undefined,
  });
  Object.defineProperty(document, "execCommand", {
    configurable: true,
    value: undefined,
  });
});

function makeResponse(): QueryResponse {
  return {
    ok: true,
    query: "lebron points",
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
  };
}

describe("Button primitives", () => {
  it("renders a primary button", () => {
    render(<Button variant="primary">Run</Button>);
    expect(screen.getByRole("button", { name: "Run" })).toBeInTheDocument();
  });

  it("disables and marks loading buttons as busy", () => {
    render(<Button loading>Running...</Button>);
    const button = screen.getByRole("button", { name: "Running..." });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
  });

  it("requires an accessible label for icon-only buttons", () => {
    render(<IconButton aria-label="Clear query" icon="X" />);
    expect(
      screen.getByRole("button", { name: "Clear query" }),
    ).toBeInTheDocument();
  });
});

describe("migrated button controls", () => {
  it("submits QueryBar text and clears the input", () => {
    const onChange = vi.fn();
    const onSubmit = vi.fn();

    render(
      <QueryBar
        value="  Jokic last 10  "
        onChange={onChange}
        onSubmit={onSubmit}
        disabled={false}
      />,
    );

    fireEvent.submit(screen.getByRole("button", { name: "Query" }));
    expect(onSubmit).toHaveBeenCalledWith("Jokic last 10");

    fireEvent.click(screen.getByRole("button", { name: "Clear query" }));
    expect(onChange).toHaveBeenCalledWith("");
  });

  it("preserves QueryBar disabled state", () => {
    render(
      <QueryBar
        value="Jokic"
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        disabled={true}
      />,
    );

    expect(screen.getByRole("button", { name: "Running…" })).toBeDisabled();
    expect(
      screen.queryByRole("button", { name: "Clear query" }),
    ).not.toBeInTheDocument();
  });

  it("copies text and shows copied feedback", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    render(<CopyButton text="share-url" label="Copy Link" variant="share" />);
    fireEvent.click(screen.getByRole("button", { name: "Copy Link" }));

    await waitFor(() => expect(writeText).toHaveBeenCalledWith("share-url"));
    expect(screen.getByRole("button", { name: "✓ Copied" })).toHaveAttribute(
      "title",
      "Copied!",
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "Copy Link copied to clipboard.",
    );
  });

  it("falls back to execCommand when clipboard write fails", async () => {
    const writeText = vi.fn().mockRejectedValue(new Error("blocked"));
    const execCommand = vi.fn().mockReturnValue(true);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    Object.defineProperty(document, "execCommand", {
      configurable: true,
      value: execCommand,
    });

    render(<CopyButton text="fallback-url" label="Copy Link" />);
    fireEvent.click(screen.getByRole("button", { name: "Copy Link" }));

    await waitFor(() => expect(execCommand).toHaveBeenCalledWith("copy"));
    expect(screen.getByRole("button", { name: "✓ Copied" })).toBeInTheDocument();
    expect(document.querySelector("textarea")).not.toBeInTheDocument();
  });

  it("shows copy failure feedback when both copy paths fail", async () => {
    vi.useFakeTimers();
    const writeText = vi.fn().mockRejectedValue(new Error("blocked"));
    const execCommand = vi.fn().mockReturnValue(false);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    Object.defineProperty(document, "execCommand", {
      configurable: true,
      value: execCommand,
    });

    render(<CopyButton text="blocked" label="Copy JSON" />);
    fireEvent.click(screen.getByRole("button", { name: "Copy JSON" }));

    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByRole("button", { name: "Copy Failed" })).toHaveAttribute(
      "title",
      "Copy failed",
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "Copy JSON failed to copy.",
    );

    act(() => {
      vi.advanceTimersByTime(1500);
    });

    expect(screen.getByRole("button", { name: "Copy JSON" })).toBeInTheDocument();
  });

  it("resets copy feedback from the latest click timer", async () => {
    vi.useFakeTimers();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    render(<CopyButton text="share-url" label="Copy Link" />);
    const button = screen.getByRole("button", { name: "Copy Link" });

    fireEvent.click(button);
    await act(async () => {
      await Promise.resolve();
    });
    expect(writeText).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "✓ Copied" }));
    await act(async () => {
      await Promise.resolve();
    });
    expect(writeText).toHaveBeenCalledTimes(2);

    act(() => {
      vi.advanceTimersByTime(1499);
    });
    expect(screen.getByRole("button", { name: "✓ Copied" })).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(screen.getByRole("button", { name: "Copy Link" })).toBeInTheDocument();
  });

  it("toggles raw JSON visibility", () => {
    render(<RawJsonToggle data={makeResponse()} />);

    fireEvent.click(screen.getByRole("button", { name: "Show Raw JSON" }));
    expect(screen.getByText(/"query": "lebron points"/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Hide Raw JSON" }));
    expect(
      screen.queryByText(/"query": "lebron points"/),
    ).not.toBeInTheDocument();
  });
});
