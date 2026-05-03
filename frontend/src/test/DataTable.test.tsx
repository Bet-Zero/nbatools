import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import DataTable from "../components/DataTable";
import { DataTable as PrimitiveDataTable } from "../design-system";
import styles from "../components/DataTable.module.css";
import primitiveStyles from "../design-system/DataTable.module.css";

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
    expect(screen.getByLabelText("Jokic avatar")).toBeInTheDocument();
  });

  it("renders player headshots when a stable player id is present", () => {
    const rows = [{ player_name: "Nikola Jokic", player_id: 203999, PTS: 25 }];
    const { container } = render(<DataTable rows={rows} />);

    expect(screen.getByLabelText("Nikola Jokic avatar")).toBeInTheDocument();
    expect(container.querySelector("img")).toHaveAttribute(
      "src",
      "https://cdn.nba.com/headshots/nba/latest/1040x760/203999.png",
    );
  });

  it("falls back to player initials when a player id is missing", () => {
    const rows = [{ player_name: "Nikola Jokic", PTS: 25 }];
    const { container } = render(<DataTable rows={rows} />);

    expect(screen.getByLabelText("Nikola Jokic avatar")).toHaveTextContent(
      "NJ",
    );
    expect(container.querySelector("img")).toBeNull();
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

  it("applies rank-cell class for rank column", () => {
    const rows = [{ rank: 1, player_name: "Jokic", team: "DEN", PTS: 25 }];
    const { container } = render(<DataTable rows={rows} />);
    const rankTh = container.getElementsByClassName(styles.rankCell)[0];
    expect(rankTh).not.toBeNull();
    const entityTh = container.getElementsByClassName(styles.entityCell)[0];
    expect(entityTh).not.toBeNull();
    expect(screen.getByLabelText("DEN")).toBeInTheDocument();
  });

  it("renders team logos and colors when stable team identity is present", () => {
    const rows = [
      {
        team_name: "Lakers",
        team_id: 1610612747,
        team_abbr: "LAL",
        wins: 50,
      },
    ];
    const { container } = render(<DataTable rows={rows} />);

    expect(screen.getAllByLabelText("Lakers (LAL)")[0]).toHaveStyle(
      "--team-primary: #552583",
    );
    expect(container.querySelector("img")).toHaveAttribute(
      "src",
      "https://cdn.nba.com/logos/nba/1610612747/primary/L/logo.svg",
    );
  });

  it("hides internal identity columns by default while preserving identity art", () => {
    const rows = [
      {
        player_name: "Nikola Jokic",
        player_id: 203999,
        team_name: "Denver Nuggets",
        team_id: 1610612743,
        team_abbr: "DEN",
        pts: 25,
      },
    ];
    const { container } = render(<DataTable rows={rows} />);

    expect(
      screen.queryByRole("columnheader", { name: "Player Id" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("columnheader", { name: "Team Id" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("columnheader", { name: "Team Abbr" }),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText("Nikola Jokic avatar")).toBeInTheDocument();
    expect(screen.getByLabelText("Denver Nuggets (DEN)")).toBeInTheDocument();
    expect(
      container.getElementsByClassName(styles.stickyIdentity).length,
    ).toBeGreaterThan(0);
  });

  it("falls back to text badges for unknown teams", () => {
    const rows = [
      {
        team_name: "Seattle SuperSonics",
        team_abbr: "SEA",
      },
    ];
    const { container } = render(<DataTable rows={rows} />);

    expect(
      screen.getAllByLabelText("Seattle SuperSonics (SEA)")[0],
    ).toHaveTextContent("SEA");
    expect(container.querySelector("img")).toBeNull();
  });

  it("renders opponent columns with opponent identity", () => {
    const rows = [
      {
        opponent_team_name: "Lakers",
        opponent_team_id: 1610612747,
        opponent_team_abbr: "LAL",
      },
    ];
    const { container } = render(<DataTable rows={rows} />);

    expect(screen.getAllByLabelText("Lakers (LAL)").length).toBeGreaterThan(0);
    expect(container.querySelector("img")).toHaveAttribute(
      "src",
      "https://cdn.nba.com/logos/nba/1610612747/primary/L/logo.svg",
    );
  });

  it("renders abbreviation-only team rows as text badges", () => {
    const rows = [{ team_abbr: "BOS" }];
    const { container } = render(<DataTable rows={rows} />);

    expect(screen.getByLabelText("BOS")).toHaveTextContent("BOS");
    expect(container.querySelector("img")).toBeNull();
  });

  it("applies highlight class when highlight prop is true", () => {
    const rows = [{ a: 1 }];
    const { container } = render(<DataTable rows={rows} highlight />);
    const table = container.querySelector("table");
    expect(table?.classList.contains(primitiveStyles.highlight)).toBe(true);
  });

  it("renders the design-system table without NBA-specific formatting", () => {
    const rows = [{ raw_header: 0.523 }];
    render(
      <PrimitiveDataTable
        rows={rows}
        columns={[
          {
            key: "raw_header",
            header: "raw_header",
            render: (row) => row.raw_header,
          },
        ]}
      />,
    );

    expect(screen.getByText("raw_header")).toBeInTheDocument();
    expect(screen.getByText("0.523")).toBeInTheDocument();
    expect(screen.queryByText("52.3%")).not.toBeInTheDocument();
  });
});
