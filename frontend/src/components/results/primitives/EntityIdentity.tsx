import type { CSSProperties } from "react";
import { Avatar, TeamBadge } from "../../../design-system";
import {
  resolvePlayerIdentity,
  resolveTeamIdentity,
} from "../../../lib/identity";
import styles from "./EntityIdentity.module.css";

type PlayerProps = {
  kind: "player";
  playerId?: number | string | null;
  playerName?: string | null;
  /** Optional team context shown next to the player name. */
  teamAbbr?: string | null;
  teamName?: string | null;
  size?: "sm" | "md";
};

type TeamProps = {
  kind: "team";
  teamId?: number | string | null;
  teamAbbr?: string | null;
  teamName?: string | null;
  size?: "sm" | "md";
};

export type EntityIdentityProps = PlayerProps | TeamProps;

/**
 * Inline entity identity treatment used inside answer-table cells:
 * small headshot/logo + entity name. Falls back gracefully when ids or
 * images are missing.
 *
 * Designed to fit in a table row without dominating row height. Use
 * `size="sm"` for very dense tables (game logs), `size="md"` (default)
 * for leaderboards.
 */
export default function EntityIdentity(props: EntityIdentityProps) {
  const size = props.size ?? "md";

  if (props.kind === "player") {
    const player = resolvePlayerIdentity({
      playerId: props.playerId ?? null,
      playerName: props.playerName ?? null,
    });
    const displayName = player.playerName ?? props.playerName ?? "Player";
    return (
      <span className={`${styles.identity} ${styles[`size_${size}`]}`}>
        <Avatar
          className={styles.mark}
          name={displayName}
          imageUrl={player.headshotUrl}
          size={size}
        />
        <span className={styles.label}>
          <span className={styles.primary}>{displayName}</span>
          {props.teamAbbr && (
            <span className={styles.secondary}>{props.teamAbbr}</span>
          )}
        </span>
      </span>
    );
  }

  const team = resolveTeamIdentity({
    teamId: props.teamId ?? null,
    teamAbbr: props.teamAbbr ?? null,
    teamName: props.teamName ?? null,
  });
  const displayName =
    team.teamName ?? props.teamName ?? team.teamAbbr ?? props.teamAbbr ?? "Team";
  return (
    <span className={`${styles.identity} ${styles[`size_${size}`]}`}>
      <TeamBadge
        className={styles.mark}
        abbreviation={team.teamAbbr ?? undefined}
        name={displayName}
        logoUrl={team.logoUrl}
        size={size}
        showName={false}
        style={(team.styleVars ?? undefined) as CSSProperties | undefined}
      />
      <span className={styles.label}>
        <span className={styles.primary}>{displayName}</span>
      </span>
    </span>
  );
}
