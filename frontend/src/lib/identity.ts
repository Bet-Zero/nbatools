import teamColorsJson from "../styles/team-colors.json";

const PLAYER_HEADSHOT_BASE_URL =
  "https://cdn.nba.com/headshots/nba/latest/1040x760";
const TEAM_LOGO_BASE_URL = "https://cdn.nba.com/logos/nba";

type IdentityId = number | string | null | undefined;

export interface TeamColors {
  primary: string;
  secondary: string;
}

export type TeamColorVars = {
  "--team-primary": string;
  "--team-secondary": string;
};

export interface PlayerIdentityInput {
  playerId?: IdentityId;
  playerName?: string | null;
}

export interface ResolvedPlayerIdentity {
  playerId: string | null;
  playerName: string | null;
  headshotUrl: string | null;
}

export interface TeamIdentityInput {
  teamId?: IdentityId;
  teamAbbr?: string | null;
  teamName?: string | null;
}

export interface ResolvedTeamIdentity {
  teamId: string | null;
  teamAbbr: string | null;
  teamName: string | null;
  logoUrl: string | null;
  colors: TeamColors | null;
  styleVars: TeamColorVars | null;
}

const TEAM_COLORS: Record<string, TeamColors> = teamColorsJson;

function normalizeOptionalText(value: string | null | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

export function normalizeIdentityId(value: IdentityId): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") {
    return Number.isSafeInteger(value) && value > 0 ? String(value) : null;
  }

  const trimmed = value.trim();
  if (!/^\d+$/.test(trimmed)) return null;

  const asNumber = Number(trimmed);
  return Number.isSafeInteger(asNumber) && asNumber > 0 ? trimmed : null;
}

export function normalizeTeamAbbreviation(
  value: string | null | undefined,
): string | null {
  const normalized = normalizeOptionalText(value)?.toUpperCase() ?? null;
  if (!normalized) return null;
  return /^[A-Z]{2,4}$/.test(normalized) ? normalized : null;
}

export function getPlayerHeadshotUrl(playerId: IdentityId): string | null {
  const normalizedId = normalizeIdentityId(playerId);
  return normalizedId
    ? `${PLAYER_HEADSHOT_BASE_URL}/${normalizedId}.png`
    : null;
}

export function getTeamLogoUrl(teamId: IdentityId): string | null {
  const normalizedId = normalizeIdentityId(teamId);
  return normalizedId
    ? `${TEAM_LOGO_BASE_URL}/${normalizedId}/primary/L/logo.svg`
    : null;
}

export function getTeamColors(
  teamAbbr: string | null | undefined,
): TeamColors | null {
  const normalizedAbbr = normalizeTeamAbbreviation(teamAbbr);
  return normalizedAbbr ? (TEAM_COLORS[normalizedAbbr] ?? null) : null;
}

export function getTeamColorVars(
  teamAbbr: string | null | undefined,
): TeamColorVars | null {
  const colors = getTeamColors(teamAbbr);
  return colors
    ? {
        "--team-primary": colors.primary,
        "--team-secondary": colors.secondary,
      }
    : null;
}

export function resolvePlayerIdentity(
  input: PlayerIdentityInput,
): ResolvedPlayerIdentity {
  const playerId = normalizeIdentityId(input.playerId);
  return {
    playerId,
    playerName: normalizeOptionalText(input.playerName),
    headshotUrl: getPlayerHeadshotUrl(playerId),
  };
}

export function resolveTeamIdentity(
  input: TeamIdentityInput,
): ResolvedTeamIdentity {
  const teamId = normalizeIdentityId(input.teamId);
  const teamAbbr = normalizeTeamAbbreviation(input.teamAbbr);
  const colors = getTeamColors(teamAbbr);

  return {
    teamId,
    teamAbbr,
    teamName: normalizeOptionalText(input.teamName),
    logoUrl: getTeamLogoUrl(teamId),
    colors,
    styleVars: colors
      ? {
          "--team-primary": colors.primary,
          "--team-secondary": colors.secondary,
        }
      : null,
  };
}
