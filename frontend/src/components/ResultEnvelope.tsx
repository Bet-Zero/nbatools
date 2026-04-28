import type { QueryResponse } from "../api/types";
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

const STATUS_STYLES: Record<string, string> = {
  ok: styles.statusOk,
  no_result: styles.statusNoResult,
  error: styles.statusError,
};

export default function ResultEnvelope({ data, onAlternateSelect }: Props) {
  const metadata = data.result?.metadata;
  const queryClass = data.result?.query_class;

  // Build context chips from metadata
  const contextChips: { label: string; value: string }[] = [];
  if (metadata) {
    if (typeof metadata.player === "string")
      contextChips.push({ label: "Player", value: metadata.player });
    if (Array.isArray(metadata.players) && metadata.players.length)
      contextChips.push({
        label: "Players",
        value: metadata.players.join(", "),
      });
    if (typeof metadata.team === "string")
      contextChips.push({ label: "Team", value: metadata.team });
    if (Array.isArray(metadata.teams) && metadata.teams.length)
      contextChips.push({
        label: "Teams",
        value: metadata.teams.join(", "),
      });
    if (typeof metadata.season === "string")
      contextChips.push({ label: "Season", value: metadata.season });
    if (typeof metadata.opponent === "string")
      contextChips.push({ label: "vs", value: metadata.opponent });
    if (typeof metadata.split_type === "string")
      contextChips.push({ label: "Split", value: metadata.split_type });
  }

  return (
    <div className={styles.envelope}>
      {/* Status + Route + Freshness row */}
      <div className={styles.top}>
        <span
          className={[
            styles.statusBadge,
            STATUS_STYLES[data.result_status] ?? styles.statusError,
          ].join(" ")}
        >
          {statusLabel(data.result_status)}
        </span>
        {data.route && <span className={styles.pill}>{routeLabel(data.route)}</span>}
        {queryClass && queryClass !== data.route && (
          <span className={styles.pill}>{queryClass}</span>
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
      </div>

      {/* Query text */}
      <div className={styles.queryText}>&ldquo;{data.query}&rdquo;</div>

      {/* Context chips */}
      {contextChips.length > 0 && (
        <div className={styles.context}>
          {contextChips.map((chip, i) => (
            <span key={i} className={styles.contextChip}>
              <span className={styles.contextChipLabel}>{chip.label}</span>
              {chip.value}
            </span>
          ))}
        </div>
      )}

      {/* Notes */}
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

      {/* Caveats */}
      {data.caveats.length > 0 && (
        <div className={[styles.infoBlock, styles.caveatsBlock].join(" ")}>
          <div className={styles.infoBlockLabel}>Caveats</div>
          <ul>
            {data.caveats.map((caveat, i) => (
              <li key={i}>{caveat}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Did you mean? — alternate interpretations */}
      {data.alternates.length > 0 && onAlternateSelect && (
        <div className={[styles.infoBlock, styles.alternatesBlock].join(" ")}>
          <span className={styles.alternatesLabel}>Did you mean: </span>
          {data.alternates.map((alt, i) => (
            <button
              key={i}
              type="button"
              className={styles.alternateChip}
              onClick={() => onAlternateSelect(alt.description)}
            >
              {alt.description}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
