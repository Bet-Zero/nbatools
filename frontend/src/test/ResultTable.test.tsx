import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ResultTable from "../components/results/primitives/ResultTable";

describe("ResultTable", () => {
  it("makes the horizontal scroll area keyboard focusable", () => {
    render(
      <ResultTable
        ariaLabel="Player game log"
        rows={[{ points: 31 }]}
        columns={[
          {
            key: "points",
            header: "PTS",
            numeric: true,
            render: (row) => row.points,
          },
        ]}
      />,
    );

    expect(
      screen.getByRole("region", { name: "Player game log scroll area" }),
    ).toHaveAttribute("tabindex", "0");
    expect(screen.getByRole("table", { name: "Player game log" })).toBeInTheDocument();
  });
});
