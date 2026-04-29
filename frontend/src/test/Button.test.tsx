import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Button, IconButton } from "../design-system";
import CopyButton from "../components/CopyButton";
import QueryBar from "../components/QueryBar";
import RawJsonToggle from "../components/RawJsonToggle";
import type { QueryResponse } from "../api/types";

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
