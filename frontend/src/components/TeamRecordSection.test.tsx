import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import TeamRecordSection from "./TeamRecordSection";

describe("TeamRecordSection", () => {
  it("renders the single-team record hero with identity and context", () => {
    render(
      <TeamRecordSection
        metadata={{
          route: "team_record",
          season: "2025-26",
          season_type: "Regular Season",
          team_context: {
            team_id: 1610612747,
            team_abbr: "LAL",
            team_name: "Los Angeles Lakers",
          },
        }}
        sections={{
          summary: [
            {
              team_name: "Los Angeles Lakers",
              team_abbr: "LAL",
              wins: 43,
              losses: 28,
              games: 71,
              win_pct: 0.606,
              pts_avg: 118.2,
              reb_avg: 43.1,
              ast_avg: 27.4,
              fg3m_avg: 12.6,
            },
          ],
        }}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Los Angeles Lakers" }),
    ).toBeInTheDocument();
    expect(
      screen.getAllByLabelText("Los Angeles Lakers (LAL)").length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("43-28")).toBeInTheDocument();
    expect(screen.getByText("60.6% win pct")).toBeInTheDocument();

    const context = screen.getByLabelText("Record context");
    expect(within(context).getByText("2025-26")).toBeInTheDocument();
    expect(within(context).getByText("Regular Season")).toBeInTheDocument();
    expect(within(context).getByText("71 games")).toBeInTheDocument();

    expect(screen.getByText("PPG")).toBeInTheDocument();
    expect(screen.getByText("3PM")).toBeInTheDocument();

    const detail = screen.getByRole("region", { name: "Record Detail" });
    expect(within(detail).queryByRole("table")).not.toBeInTheDocument();
  });

  it("adds opponent identity to opponent-scoped records and hides single-season by-season detail", () => {
    render(
      <TeamRecordSection
        metadata={{
          route: "team_record",
          season: "2025-26",
          season_type: "Regular Season",
          team_context: {
            team_id: 1610612738,
            team_abbr: "BOS",
            team_name: "Boston Celtics",
          },
          opponent_context: {
            team_id: 1610612749,
            team_abbr: "MIL",
            team_name: "Milwaukee Bucks",
          },
        }}
        sections={{
          summary: [
            {
              team_name: "Boston Celtics",
              team_abbr: "BOS",
              wins: 3,
              losses: 1,
              games: 4,
              win_pct: 0.75,
            },
          ],
          by_season: [{ season: "2025-26", wins: 3, losses: 1 }],
        }}
      />,
    );

    expect(screen.getByLabelText("Milwaukee Bucks (MIL)")).toBeInTheDocument();
    expect(screen.getByText("vs")).toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Record context")).getByText(
        "vs Milwaukee Bucks",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("region", { name: "By Season" }),
    ).not.toBeInTheDocument();
  });

  it("keeps by-season detail collapsed for multi-season records", async () => {
    const user = userEvent.setup();

    render(
      <TeamRecordSection
        metadata={{
          route: "team_record",
          start_season: "2023-24",
          end_season: "2024-25",
          season_type: "Regular Season",
          team_context: {
            team_id: 1610612738,
            team_abbr: "BOS",
            team_name: "Boston Celtics",
          },
        }}
        sections={{
          summary: [
            {
              team_name: "Boston Celtics",
              team_abbr: "BOS",
              wins: 112,
              losses: 52,
              games: 164,
              win_pct: 0.683,
            },
          ],
          by_season: [
            { season: "2023-24", wins: 64, losses: 18 },
            { season: "2024-25", wins: 48, losses: 34 },
          ],
        }}
      />,
    );

    expect(
      within(screen.getByLabelText("Record context")).getByText(
        "2023-24 to 2024-25",
      ),
    ).toBeInTheDocument();

    const bySeason = screen.getByRole("region", { name: "By Season" });
    expect(within(bySeason).queryByRole("table")).not.toBeInTheDocument();

    await user.click(
      within(bySeason).getByRole("button", { name: "Show raw table" }),
    );
    expect(within(bySeason).getByRole("table")).toBeInTheDocument();
  });
});
