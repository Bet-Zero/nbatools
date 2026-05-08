import type { ResultMetadata } from "../../../api/types";

export function hasPinnedEntity(
  metadata: ResultMetadata | undefined,
  kind: "player" | "team",
): boolean {
  if (!metadata) return false;

  if (kind === "player") {
    if (metadata.player_context) return true;
    if (typeof metadata.player === "string" && metadata.player.trim()) return true;
    return Array.isArray(metadata.players) && metadata.players.length === 1;
  }

  if (metadata.team_context) return true;
  if (typeof metadata.team === "string" && metadata.team.trim()) return true;
  return Array.isArray(metadata.teams) && metadata.teams.length === 1;
}