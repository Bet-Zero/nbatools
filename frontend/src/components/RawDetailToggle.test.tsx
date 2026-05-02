import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import RawDetailToggle from "./RawDetailToggle";

describe("RawDetailToggle", () => {
  const rows = [
    { player_name: "Nikola Jokic", pts: 31, internal_id: "hidden" },
  ];

  it("renders nothing for empty rows", () => {
    const { container } = render(<RawDetailToggle title="Raw" rows={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("hides the table when closed", () => {
    render(<RawDetailToggle title="Full Summary" rows={rows} />);

    expect(
      screen.getByRole("button", { name: "Show raw table" }),
    ).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByText("Full Summary")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("shows the table when opened", async () => {
    const user = userEvent.setup();
    render(<RawDetailToggle title="Full Summary" rows={rows} />);

    await user.click(screen.getByRole("button", { name: "Show raw table" }));

    expect(
      screen.getByRole("button", { name: "Hide raw table" }),
    ).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("Nikola Jokic")).toBeInTheDocument();
  });

  it("respects hidden columns when open", () => {
    render(
      <RawDetailToggle
        title="Full Summary"
        rows={rows}
        hiddenColumns={new Set(["internal_id"])}
        defaultOpen
      />,
    );

    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.queryByText("Internal Id")).not.toBeInTheDocument();
    expect(screen.queryByText("hidden")).not.toBeInTheDocument();
  });
});
