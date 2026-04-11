import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import DataTable from "../components/DataTable";

describe("DataTable", () => {
  it("renders nothing for empty rows", () => {
    const { container } = render(<DataTable rows={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders column headers from row keys", () => {
    const rows = [{ player_name: "Jokic", PTS: 25, REB: 12 }];
    render(<DataTable rows={rows} />);

    expect(screen.getByText("Player Name")).toBeInTheDocument();
    expect(screen.getByText("PTS")).toBeInTheDocument();
    expect(screen.getByText("REB")).toBeInTheDocument();
  });

  it("renders row values", () => {
    const rows = [
      { name: "Jokic", pts: 25.3, reb: 12 },
      { name: "Embiid", pts: 28.1, reb: 11 },
    ];
    render(<DataTable rows={rows} />);

    expect(screen.getByText("Jokic")).toBeInTheDocument();
    expect(screen.getByText("Embiid")).toBeInTheDocument();
    expect(screen.getByText("25.3")).toBeInTheDocument();
  });

  it("formats null/undefined as dash", () => {
    const rows = [{ name: "Test", value: null }];
    render(<DataTable rows={rows} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("formats percentages when column includes 'pct'", () => {
    const rows = [{ fg_pct: 0.523 }];
    render(<DataTable rows={rows} />);
    expect(screen.getByText("52.3%")).toBeInTheDocument();
  });

  it("applies highlight class when highlight prop is true", () => {
    const rows = [{ a: 1 }];
    const { container } = render(<DataTable rows={rows} highlight />);
    const table = container.querySelector("table");
    expect(table?.classList.contains("data-table-highlight")).toBe(true);
  });
});
