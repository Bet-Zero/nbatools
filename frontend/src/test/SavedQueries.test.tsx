/**
 * Tests for SavedQueries UI components: SavedQueries panel, SaveQueryDialog,
 * and integration with useSavedQueries hook.
 */
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { QueryHistoryEntry } from "../api/types";
import type { SavedQuery } from "../api/savedQueryTypes";
import QueryHistory from "../components/QueryHistory";
import SavedQueries from "../components/SavedQueries";
import {
  addSavedQuery as storageAdd,
  loadSavedQueries as storageLoad,
} from "../storage/savedQueryStorage";

import SaveQueryDialog from "../components/SaveQueryDialog";
import dialogStyles from "../components/SaveQueryDialog.module.css";
function makeSavedQuery(overrides: Partial<SavedQuery> = {}): SavedQuery {
  return {
    id: "test-1",
    label: "Test Query",
    query: "Jokic last 10 games",
    route: null,
    kwargs: null,
    tags: [],
    pinned: false,
    createdAt: Date.now(),
    updatedAt: Date.now(),
    ...overrides,
  };
}

function makeHistoryEntry(
  overrides: Partial<QueryHistoryEntry> = {},
): QueryHistoryEntry {
  return {
    id: 1,
    query: "Jokic last 10 games",
    route: "player_game_summary",
    query_class: "summary",
    result_status: "ok",
    timestamp: Date.now(),
    ...overrides,
  };
}

afterEach(cleanup);

describe("SavedQueries panel", () => {
  const noop = () => {};
  const noopExport = () => "[]";

  function renderPanel(queries: SavedQuery[] = [], overrides = {}) {
    const defaultProps = {
      queries,
      onRun: noop,
      onEdit: noop,
      onSave: noop,
      onUpdate: noop,
      onDelete: noop,
      onPin: noop,
      onClearAll: noop,
      onExport: noopExport,
      onImport: noop,
      ...overrides,
    };
    return render(<SavedQueries {...defaultProps} />);
  }

  it("shows empty state when no queries exist", () => {
    renderPanel([]);
    expect(screen.getByText("No saved queries yet")).toBeInTheDocument();
    expect(
      screen.getByText("Save queries you use often for quick access."),
    ).toBeInTheDocument();
  });

  it("renders query count in header", () => {
    renderPanel([makeSavedQuery()]);
    expect(screen.getByText("1 query")).toBeInTheDocument();
  });

  it("renders plural count", () => {
    renderPanel([
      makeSavedQuery({ id: "a" }),
      makeSavedQuery({ id: "b", label: "Second" }),
    ]);
    expect(screen.getByText("2 queries")).toBeInTheDocument();
  });

  it("displays query label and query text", () => {
    renderPanel([makeSavedQuery()]);
    expect(screen.getByText("Test Query")).toBeInTheDocument();
    expect(screen.getByText("Jokic last 10 games")).toBeInTheDocument();
  });

  it("calls onRun when Run button is clicked", () => {
    const onRun = vi.fn();
    renderPanel([makeSavedQuery()], { onRun });
    fireEvent.click(screen.getByTitle("Run query"));
    expect(onRun).toHaveBeenCalledWith("Jokic last 10 games");
  });

  it("calls onRun when label is clicked", () => {
    const onRun = vi.fn();
    renderPanel([makeSavedQuery()], { onRun });
    fireEvent.click(screen.getByText("Test Query"));
    expect(onRun).toHaveBeenCalledWith("Jokic last 10 games");
  });

  it("runs saved query labels from the keyboard", () => {
    const onRun = vi.fn();
    renderPanel([makeSavedQuery()], { onRun });
    const label = screen.getByRole("button", {
      name: "Run saved query from label: Test Query",
    });

    fireEvent.keyDown(label, { key: " " });

    expect(onRun).toHaveBeenCalledWith("Jokic last 10 games");
  });

  it("calls onEdit when Load button is clicked", () => {
    const onEdit = vi.fn();
    renderPanel([makeSavedQuery()], { onEdit });
    fireEvent.click(screen.getByTitle("Load into query bar"));
    expect(onEdit).toHaveBeenCalledWith("Jokic last 10 games");
  });

  it("calls onPin when Pin button is clicked", () => {
    const onPin = vi.fn();
    renderPanel([makeSavedQuery()], { onPin });
    fireEvent.click(screen.getByTitle("Pin"));
    expect(onPin).toHaveBeenCalledWith("test-1");
  });

  it("shows Unpin for pinned queries", () => {
    renderPanel([makeSavedQuery({ pinned: true })]);
    expect(screen.getByTitle("Unpin")).toBeInTheDocument();
  });

  it("calls onDelete when Delete button is clicked", () => {
    const onDelete = vi.fn();
    renderPanel([makeSavedQuery()], { onDelete });
    fireEvent.click(screen.getByTitle("Delete saved query"));
    expect(onDelete).toHaveBeenCalledWith("test-1");
  });

  it("shows pin icon for pinned queries", () => {
    renderPanel([makeSavedQuery({ pinned: true })]);
    expect(screen.getByTitle("Pinned")).toBeInTheDocument();
    expect(screen.getByLabelText("Pinned query")).toBeInTheDocument();
  });

  it("shows tags on a query", () => {
    renderPanel([makeSavedQuery({ tags: ["player", "stats"] })]);
    // "player" and "stats" appear both as tag filter buttons and as tag badges
    const playerElements = screen.getAllByText("player");
    expect(playerElements.length).toBeGreaterThanOrEqual(2);
    const statsElements = screen.getAllByText("stats");
    expect(statsElements.length).toBeGreaterThanOrEqual(2);
  });

  it("keeps long saved labels and tags actionable", () => {
    const longLabel =
      "Jokic playoff matchup history with a very specific saved query label";
    const longTag = "very-long-tag-name-for-mobile-containment";
    renderPanel([makeSavedQuery({ label: longLabel, tags: [longTag] })]);

    expect(
      screen.getByRole("button", {
        name: `Run saved query from label: ${longLabel}`,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: `Filter saved queries by tag: ${longTag}`,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: `Delete saved query: ${longLabel}`,
      }),
    ).toBeInTheDocument();
  });

  it("shows route badge when route is set", () => {
    renderPanel([makeSavedQuery({ route: "player_game_summary" })]);
    expect(screen.getByText("player_game_summary")).toBeInTheDocument();
  });

  it("shows tag filter bar when tags exist", () => {
    renderPanel([makeSavedQuery({ tags: ["player"] })]);
    expect(screen.getByText("All")).toBeInTheDocument();
    // The "player" tag appears both as a filter button and on the query item
    const playerElements = screen.getAllByText("player");
    expect(playerElements.length).toBeGreaterThanOrEqual(2); // filter + tag
  });

  it("filters queries by tag", () => {
    renderPanel([
      makeSavedQuery({ id: "a", label: "Tagged", tags: ["player"] }),
      makeSavedQuery({ id: "b", label: "Untagged", tags: [] }),
    ]);
    // Click the "player" filter (the first one is in the filter bar)
    const filterButtons = screen.getAllByText("player");
    fireEvent.click(filterButtons[0]); // filter button
    expect(screen.getByText("Tagged")).toBeInTheDocument();
    expect(screen.queryByText("Untagged")).not.toBeInTheDocument();
  });

  it("exposes tag filters as pressed controls", () => {
    renderPanel([makeSavedQuery({ tags: ["player"] })]);
    const playerFilter = screen.getByRole("button", {
      name: "Filter saved queries by tag: player",
    });

    expect(playerFilter).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(playerFilter);
    expect(playerFilter).toHaveAttribute("aria-pressed", "true");
  });

  it("shows import button always", () => {
    renderPanel([]);
    expect(
      screen.getByTitle("Import saved queries from JSON"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Import saved queries from JSON" }),
    ).toBeInTheDocument();
  });

  it("shows export button when queries exist", () => {
    renderPanel([makeSavedQuery()]);
    expect(
      screen.getByTitle("Export saved queries as JSON"),
    ).toBeInTheDocument();
  });

  it("requires double-click to clear all", () => {
    const onClearAll = vi.fn();
    renderPanel([makeSavedQuery()], { onClearAll });
    const clearBtn = screen.getByTitle("Delete all saved queries");
    expect(clearBtn.textContent).toBe("Clear All");
    fireEvent.click(clearBtn);
    expect(onClearAll).not.toHaveBeenCalled();
    expect(clearBtn.textContent).toBe("Confirm?");
    fireEvent.click(clearBtn);
    expect(onClearAll).toHaveBeenCalled();
  });

  it("shows visible feedback when import fails", async () => {
    const user = userEvent.setup();
    const onImport = vi.fn(() => {
      throw new Error("bad import");
    });
    renderPanel([], { onImport });
    const fileInput = screen.getByLabelText(
      "Saved query JSON file",
    ) as HTMLInputElement;

    await user.upload(
      fileInput,
      new File(["not json"], "saved-queries.json", {
        type: "application/json",
      }),
    );

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("Import failed"),
    );
  });
});

describe("QueryHistory panel", () => {
  it("names history actions and supports keyboard activation", () => {
    const onSelect = vi.fn();
    const onEdit = vi.fn();
    const onSave = vi.fn();
    render(
      <QueryHistory
        entries={[makeHistoryEntry()]}
        onSelect={onSelect}
        onEdit={onEdit}
        onClear={vi.fn()}
        onSave={onSave}
      />,
    );

    const label = screen.getByRole("button", {
      name: "Run history query from label: Jokic last 10 games",
    });
    fireEvent.keyDown(label, { key: " " });
    expect(onSelect).toHaveBeenCalledWith("Jokic last 10 games");

    fireEvent.click(
      screen.getByRole("button", {
        name: "Edit history query: Jokic last 10 games",
      }),
    );
    expect(onEdit).toHaveBeenCalledWith("Jokic last 10 games");

    fireEvent.click(
      screen.getByRole("button", {
        name: "Save history query: Jokic last 10 games",
      }),
    );
    expect(onSave).toHaveBeenCalledWith("Jokic last 10 games");
  });
});

describe("SaveQueryDialog", () => {
  afterEach(cleanup);

  it("renders save form with default values", () => {
    render(
      <SaveQueryDialog
        defaultQuery="test query"
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText("Save Query")).toBeInTheDocument();
    const queryInput = screen.getByPlaceholderText("Natural language query");
    expect(queryInput).toHaveValue("test query");
  });

  it("renders edit form with existing values", () => {
    const query = makeSavedQuery({
      label: "Edit Me",
      query: "existing query",
      tags: ["a", "b"],
      pinned: true,
    });
    render(
      <SaveQueryDialog
        editing={query}
        onSave={vi.fn()}
        onUpdate={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText("Edit Saved Query")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Edit Me")).toBeInTheDocument();
    expect(screen.getByDisplayValue("existing query")).toBeInTheDocument();
    expect(screen.getByDisplayValue("a, b")).toBeInTheDocument();
  });

  it("calls onSave with input data", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(
      <SaveQueryDialog
        defaultQuery="my query"
        onSave={onSave}
        onCancel={vi.fn()}
      />,
    );
    const labelInput = screen.getByPlaceholderText("e.g. Jokic recent stats");
    await user.type(labelInput, "My Label");
    fireEvent.click(screen.getByText("Save"));
    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        label: "My Label",
        query: "my query",
      }),
    );
  });

  it("calls onCancel when Cancel is clicked", () => {
    const onCancel = vi.fn();
    render(
      <SaveQueryDialog defaultQuery="" onSave={vi.fn()} onCancel={onCancel} />,
    );
    fireEvent.click(screen.getByText("Cancel"));
    expect(onCancel).toHaveBeenCalled();
  });

  it("disables Submit when label is empty", () => {
    render(
      <SaveQueryDialog
        defaultQuery="query"
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    const submitBtn = screen.getByText("Save");
    expect(submitBtn).toBeDisabled();
  });

  it("calls onUpdate when editing", async () => {
    const user = userEvent.setup();
    const onUpdate = vi.fn();
    const query = makeSavedQuery({ label: "Old Label" });
    render(
      <SaveQueryDialog
        editing={query}
        onSave={vi.fn()}
        onUpdate={onUpdate}
        onCancel={vi.fn()}
      />,
    );
    const labelInput = screen.getByDisplayValue("Old Label");
    await user.clear(labelInput);
    await user.type(labelInput, "New Label");
    fireEvent.click(screen.getByText("Update"));
    expect(onUpdate).toHaveBeenCalledWith(
      "test-1",
      expect.objectContaining({ label: "New Label" }),
    );
  });

  it("calls onCancel when overlay is clicked", () => {
    const onCancel = vi.fn();
    render(
      <SaveQueryDialog defaultQuery="" onSave={vi.fn()} onCancel={onCancel} />,
    );
    // Click the overlay (outermost div)
    const overlay = document.getElementsByClassName(dialogStyles.overlay)[0];
    fireEvent.click(overlay!);
    expect(onCancel).toHaveBeenCalled();
  });
});

describe("useSavedQueries hook integration", () => {
  // This tests the hook indirectly through the storage layer
  // since the hook is a thin wrapper. Direct hook testing would
  // require renderHook which is covered by the storage tests.

  const storage: Record<string, string> = {};

  beforeEach(() => {
    vi.stubGlobal("localStorage", {
      getItem: (key: string) => storage[key] ?? null,
      setItem: (key: string, value: string) => {
        storage[key] = value;
      },
      removeItem: (key: string) => {
        delete storage[key];
      },
    });
  });

  afterEach(() => {
    for (const key of Object.keys(storage)) delete storage[key];
    vi.restoreAllMocks();
  });

  it("round-trips through add + load", () => {
    storageAdd({ label: "Hook Test", query: "q" });
    const loaded = storageLoad();
    expect(loaded).toHaveLength(1);
    expect(loaded[0].label).toBe("Hook Test");
  });
});
