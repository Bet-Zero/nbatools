import type { QueryResponse } from "../api/types";
import {
  Avatar,
  Badge,
  Button,
  ResultEnvelopeShell,
  TeamBadge,
  type BadgeVariant,
} from "../design-system";
import { resolvePlayerIdentity } from "../lib/identity";
import styles from "./ResultEnvelope.module.css";

interface Props {
  data: QueryResponse;
  onAlternateSelect?: (description: string) => void;
}

function statusLabel(status: string): string {
  switch (status) {
    case "ok":
      return "Success";
    case "no_result":
      return "No Result";
    case "error":
      return "Error";
    default:
      return status;
  }
}

function reasonLabel(reason: string | null): string | null {
  if (!reason) return null;
  switch (reason) {
    case "no_match":
      return "no match";
    case "no_data":
      return "data unavailable";
    case "unrouted":
      return "unrecognized query";
    case "ambiguous":
      return "ambiguous entity";
    case "unsupported":
      return "unsupported";
    case "error":
      return "error";
    default:
      return reason;
  }
}

function routeLabel(route: string): string {
  return route.replace(/_/g, " ");
}

function isTeamAbbreviation(value: string): boolean {
  return /^[A-Z]{2,4}$/.test(value);
}

const STATUS_VARIANTS: Record<string, BadgeVariant> = {
  ok: "success",
  no_result: "warning",
  error: "danger",
};

export default function ResultEnvelope({ data, onAlternateSelect }: Props) {
  const metadata = data.result?.metadata;
  const queryClass = data.result?.query_class;

  // Build context chips from metadata
  const contextChips: {
    label: string;
    value: string;
    identity?: "player" | "team";
    imageUrl?: string | null;
    identityName?: string | null;
  }[] = [];
  if (metadata) {
    if (typeof metadata.player === "string") {
      const playerIdentity = resolvePlayerIdentity({
        playerId: metadata.player_context?.player_id,
        playerName: metadata.player_context?.player_name ?? metadata.player,
      });
      contextChips.push({
        label: "Player",
        value: metadata.player,
        identity: "player",
        imageUrl: playerIdentity.headshotUrl,
        identityName: playerIdentity.playerName,
      });
    }
    if (Array.isArray(metadata.players) && metadata.players.length)
      contextChips.push({
        label: "Players",
        value: metadata.players.join(", "),
      });
    if (typeof metadata.team === "string")
      contextChips.push({
        label: "Team",
        value: metadata.team,
        identity: "team",
      });
    if (Array.isArray(metadata.teams) && metadata.teams.length)
      contextChips.push({
        label: "Teams",
        value: metadata.teams.join(", "),
      });
    if (typeof metadata.season === "string")
      contextChips.push({ label: "Season", value: metadata.season });
    if (typeof metadata.opponent === "string")
      contextChips.push({
        label: "vs",
        value: metadata.opponent,
        identity: "team",
      });
    if (typeof metadata.split_type === "string")
      contextChips.push({ label: "Split", value: metadata.split_type });
  }

  return (
    <ResultEnvelopeShell
      meta={
        <>
          <Badge
            variant={STATUS_VARIANTS[data.result_status] ?? "danger"}
            uppercase
          >
            {statusLabel(data.result_status)}
          </Badge>
          {data.route && (
            <Badge variant="accent" size="sm">
              {routeLabel(data.route)}
            </Badge>
          )}
          {queryClass && queryClass !== data.route && (
            <Badge variant="accent" size="sm">
              {queryClass}
            </Badge>
          )}
          {data.result_reason && (
            <span className={[styles.muted, styles.resultReason].join(" ")}>
              {reasonLabel(data.result_reason)}
            </span>
          )}
          {data.current_through && (
            <>
              <span className={styles.separator} />
              <span className={styles.freshness}>
                Data through <strong>{data.current_through}</strong>
              </span>
            </>
          )}
        </>
      }
      query={<>&ldquo;{data.query}&rdquo;</>}
      context={
        contextChips.length > 0
          ? contextChips.map((chip, i) => (
              <Badge key={i} variant="neutral" size="sm">
                {chip.identity === "player" && (
                  <Avatar
                    name={chip.identityName ?? chip.value}
                    imageUrl={chip.imageUrl}
                    size="sm"
                  />
                )}
                {chip.identity === "team" && (
                  <TeamBadge
                    abbreviation={
                      isTeamAbbreviation(chip.value) ? chip.value : undefined
                    }
                    name={chip.value}
                    size="sm"
                    showName={false}
                  />
                )}
                <span className={styles.contextChipLabel}>{chip.label}</span>
                {chip.value}
              </Badge>
            ))
          : null
      }
      notices={
        data.notes.length > 0 || data.caveats.length > 0 ? (
          <>
            {data.notes.length > 0 && (
              <div className={[styles.infoBlock, styles.notesBlock].join(" ")}>
                <div className={styles.infoBlockLabel}>Notes</div>
                <ul>
                  {data.notes.map((note, i) => (
                    <li key={i}>{note}</li>
                  ))}
                </ul>
              </div>
            )}
            {data.caveats.length > 0 && (
              <div
                className={[styles.infoBlock, styles.caveatsBlock].join(" ")}
              >
                <div className={styles.infoBlockLabel}>Caveats</div>
                <ul>
                  {data.caveats.map((caveat, i) => (
                    <li key={i}>{caveat}</li>
                  ))}
                </ul>
              </div>
            )}
          </>
        ) : null
      }
      alternates={
        data.alternates.length > 0 && onAlternateSelect ? (
          <>
            <span className={styles.alternatesLabel}>Did you mean: </span>
            {data.alternates.map((alt, i) => (
              <Button
                key={i}
                type="button"
                className={styles.alternateChip}
                onClick={() => onAlternateSelect(alt.description)}
                size="sm"
                variant="secondary"
              >
                {alt.description}
              </Button>
            ))}
          </>
        ) : null
      }
    />
  );
}
