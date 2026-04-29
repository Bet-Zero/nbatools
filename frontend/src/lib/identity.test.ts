import { describe, expect, it } from "vitest";
import {
  getPlayerHeadshotUrl,
  getTeamColorVars,
  getTeamColors,
  getTeamLogoUrl,
  normalizeIdentityId,
  normalizeTeamAbbreviation,
  resolvePlayerIdentity,
  resolveTeamIdentity,
} from "./identity";

describe("identity helpers", () => {
  it("normalizes stable numeric ids", () => {
    expect(normalizeIdentityId(203999)).toBe("203999");
    expect(normalizeIdentityId(" 1610612747 ")).toBe("1610612747");
    expect(normalizeIdentityId(0)).toBeNull();
    expect(normalizeIdentityId(-1)).toBeNull();
    expect(normalizeIdentityId("abc")).toBeNull();
    expect(normalizeIdentityId(null)).toBeNull();
  });

  it("builds player headshot URLs only from stable ids", () => {
    expect(getPlayerHeadshotUrl(203999)).toBe(
      "https://cdn.nba.com/headshots/nba/latest/1040x760/203999.png",
    );
    expect(getPlayerHeadshotUrl("")).toBeNull();
    expect(getPlayerHeadshotUrl("Nikola Jokic")).toBeNull();
  });

  it("builds team logo URLs only from stable ids", () => {
    expect(getTeamLogoUrl("1610612747")).toBe(
      "https://cdn.nba.com/logos/nba/1610612747/primary/L/logo.svg",
    );
    expect(getTeamLogoUrl(undefined)).toBeNull();
    expect(getTeamLogoUrl("LAL")).toBeNull();
  });

  it("normalizes team abbreviations without accepting arbitrary labels", () => {
    expect(normalizeTeamAbbreviation(" lal ")).toBe("LAL");
    expect(normalizeTeamAbbreviation("NYK")).toBe("NYK");
    expect(normalizeTeamAbbreviation("Lakers")).toBeNull();
    expect(normalizeTeamAbbreviation("")).toBeNull();
  });

  it("looks up team colors from the team color map", () => {
    expect(getTeamColors("lal")).toEqual({
      primary: "#552583",
      secondary: "#FDB927",
    });
    expect(getTeamColors("unknown")).toBeNull();
    expect(getTeamColors(null)).toBeNull();
  });

  it("returns scoped team CSS variable values", () => {
    expect(getTeamColorVars("BOS")).toEqual({
      "--team-primary": "#007A33",
      "--team-secondary": "#BA9653",
    });
    expect(getTeamColorVars("SEA")).toBeNull();
  });

  it("resolves player identity with headshot fallback semantics", () => {
    expect(
      resolvePlayerIdentity({ playerId: " 203999 ", playerName: " Nikola Jokic " }),
    ).toEqual({
      playerId: "203999",
      playerName: "Nikola Jokic",
      headshotUrl:
        "https://cdn.nba.com/headshots/nba/latest/1040x760/203999.png",
    });

    expect(resolvePlayerIdentity({ playerName: "Unknown Player" })).toEqual({
      playerId: null,
      playerName: "Unknown Player",
      headshotUrl: null,
    });
  });

  it("resolves team identity with logo and scoped color fallbacks", () => {
    expect(
      resolveTeamIdentity({
        teamId: 1610612747,
        teamAbbr: "lal",
        teamName: "Los Angeles Lakers",
      }),
    ).toEqual({
      teamId: "1610612747",
      teamAbbr: "LAL",
      teamName: "Los Angeles Lakers",
      logoUrl: "https://cdn.nba.com/logos/nba/1610612747/primary/L/logo.svg",
      colors: {
        primary: "#552583",
        secondary: "#FDB927",
      },
      styleVars: {
        "--team-primary": "#552583",
        "--team-secondary": "#FDB927",
      },
    });

    expect(
      resolveTeamIdentity({ teamAbbr: "SEA", teamName: "Seattle SuperSonics" }),
    ).toEqual({
      teamId: null,
      teamAbbr: "SEA",
      teamName: "Seattle SuperSonics",
      logoUrl: null,
      colors: null,
      styleVars: null,
    });
  });
});
