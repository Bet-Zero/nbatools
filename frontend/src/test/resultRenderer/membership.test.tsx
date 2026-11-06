import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResultRenderer from "../../components/results/ResultRenderer";
import { makeResponse } from "./helpers";

describe("Dated membership rendering", () => {
  it.each([
    ["member", "did_not_play", "Explicitly did not play"],
    ["member", "unknown", "Unknown — insufficient participation evidence"],
    ["not_member", "not_member", "Not a member of the requested team"],
    ["unknown", "unknown", "Unknown — insufficient participation evidence"],
  ])(
    "preserves membership %s and participation %s",
    (membership, participation, text) => {
      const data = makeResponse({ route: "player_membership" });
      data.result!.sections.summary = [
        {
          date: "2023-12-29",
          player_name: "Controlled Player",
          membership_state: membership,
          participation_state: participation,
          member_team_id: membership === "unknown" ? null : 1610612761,
          member_team_abbr: membership === "unknown" ? null : "TOR",
        },
      ];
      render(<ResultRenderer data={data} />);
      const table = screen.getByRole("table", {
        name: "Membership and participation",
      });
      expect(within(table).getByText(text)).toBeVisible();
      expect(
        within(table).getByText(membership === "unknown" ? "Unknown" : "TOR"),
      ).toBeVisible();
      expect(
        screen.getByText(
          "Membership alone does not establish participation or an absence reason.",
        ),
      ).toBeVisible();
      expect(
        screen.queryByText(/0 games|healthy|injured|0\.0/),
      ).not.toBeInTheDocument();
    },
  );
});
