import { useEffect, useId, useState } from "react";
import { fetchFreshness } from "../api/client";
import type { FreshnessResponse, FreshnessStatusValue } from "../api/types";
import { Badge, Card, type BadgeVariant } from "../design-system";
import styles from "./FreshnessStatus.module.css";

type VerificationState = "loading" | "verified" | "unverified";

const STATUS_CONFIG: Record<
  FreshnessStatusValue,
  { dot: string; label: string; className: string }
> = {
  fresh: { dot: "●", label: "Data is current", className: styles.fresh },
  stale: { dot: "●", label: "Data may be stale", className: styles.stale },
  unknown: {
    dot: "○",
    label: "Freshness unknown",
    className: styles.unknown,
  },
  failed: {
    dot: "●",
    label: "Last refresh failed",
    className: styles.failed,
  },
};

const BADGE_VARIANTS: Record<FreshnessStatusValue, BadgeVariant> = {
  fresh: "success",
  stale: "warning",
  unknown: "neutral",
  failed: "danger",
};

const BANNER_MESSAGES: Record<FreshnessStatusValue, string> = {
  fresh: "Ready for a first query.",
  stale: "Stats run through the date shown — new games arrive with the next refresh.",
  unknown: "Freshness is not confirmed.",
  failed: "Refresh needs attention before results are trusted.",
};

const BADGE_LABELS: Record<FreshnessStatusValue, string> = {
  fresh: "current",
  stale: "awaiting refresh",
  unknown: "unknown",
  failed: "refresh failed",
};

const VALID_STATUSES = new Set<FreshnessStatusValue>([
  "fresh",
  "stale",
  "unknown",
  "failed",
]);

function normalizeStatus(value: unknown): FreshnessStatusValue {
  return VALID_STATUSES.has(value as FreshnessStatusValue)
    ? (value as FreshnessStatusValue)
    : "unknown";
}

function normalizeFreshness(data: FreshnessResponse): FreshnessResponse {
  return {
    ...data,
    status: normalizeStatus(data.status),
    seasons: data.seasons.map((season) => ({
      ...season,
      status: normalizeStatus(season.status),
    })),
  };
}

interface Props {
  /** Poll interval in ms — 0 to disable polling. */
  pollInterval?: number;
  variant?: "panel" | "banner";
}

export default function FreshnessStatus({
  pollInterval = 120_000,
  variant = "panel",
}: Props) {
  const [info, setInfo] = useState<FreshnessResponse | null>(null);
  const [verification, setVerification] =
    useState<VerificationState>("loading");
  const [expanded, setExpanded] = useState(false);
  const detailsId = useId();

  useEffect(() => {
    let disposed = false;
    let generation = 0;
    let activeController: AbortController | null = null;
    let timerId: ReturnType<typeof setTimeout> | undefined;

    function clearTimer() {
      if (timerId !== undefined) {
        clearTimeout(timerId);
        timerId = undefined;
      }
    }

    function scheduleNext() {
      clearTimer();
      if (
        !disposed &&
        pollInterval > 0 &&
        document.visibilityState !== "hidden"
      ) {
        timerId = setTimeout(() => void load(), pollInterval);
      }
    }

    function cancelActiveRequest() {
      generation += 1;
      activeController?.abort();
      activeController = null;
    }

    async function load() {
      if (
        disposed ||
        activeController !== null ||
        document.visibilityState === "hidden"
      ) {
        return;
      }
      const requestGeneration = ++generation;
      const controller = new AbortController();
      activeController = controller;
      try {
        const data = normalizeFreshness(
          await fetchFreshness({ signal: controller.signal }),
        );
        if (!disposed && requestGeneration === generation) {
          setInfo(data);
          setVerification("verified");
        }
      } catch (error) {
        if (
          !disposed &&
          requestGeneration === generation &&
          !(error instanceof DOMException && error.name === "AbortError")
        ) {
          setVerification("unverified");
        }
      } finally {
        if (requestGeneration === generation) {
          if (activeController === controller) activeController = null;
          scheduleNext();
        }
      }
    }

    function onVisibilityChange() {
      clearTimer();
      if (document.visibilityState === "hidden") {
        cancelActiveRequest();
        setVerification((current) =>
          current === "loading" ? "loading" : "unverified",
        );
        return;
      }
      setVerification((current) =>
        current === "loading" ? "loading" : "unverified",
      );
      void load();
    }

    if (pollInterval > 0) {
      document.addEventListener("visibilitychange", onVisibilityChange);
    }
    void load();

    return () => {
      disposed = true;
      clearTimer();
      document.removeEventListener("visibilitychange", onVisibilityChange);
      cancelActiveRequest();
    };
  }, [pollInterval]);

  if (verification === "loading") return null;

  const status = normalizeStatus(info?.status);
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.unknown;
  const isBanner = variant === "banner";
  const isUnverified = verification === "unverified";
  const canPresentDate = status === "fresh" || status === "stale";
  const label = isUnverified
    ? info?.current_through
      ? `Last known data through ${info.current_through}`
      : "Freshness check unavailable"
    : info?.current_through && canPresentDate
      ? `Data through ${info.current_through}`
      : cfg.label;
  const statusLabel = isUnverified ? "unverified" : BADGE_LABELS[status];
  const message = isUnverified
    ? info
      ? "Current freshness could not be verified. Details below are last known."
      : "Current data freshness could not be verified. Try again soon."
    : BANNER_MESSAGES[status];
  const buttonLabel = isUnverified
    ? `Data freshness unverified: ${label}`
    : `Data freshness: ${label}`;
  const liveMessage = isUnverified || isBanner ? message : null;
  const summaryContent = (
    <>
      <span className={styles.dot} aria-hidden="true">
        {isUnverified ? "○" : cfg.dot}
      </span>
      <span className={styles.labelStack}>
        {isBanner && <span className={styles.kicker}>Data freshness</span>}
        <span className={styles.label}>{label}</span>
        {(isBanner || isUnverified) && (
          <span
            className={
              isUnverified ? styles.verificationMessage : styles.bannerMessage
            }
          >
            {message}
          </span>
        )}
      </span>
      <Badge
        variant={isUnverified ? "warning" : BADGE_VARIANTS[status]}
        size="sm"
        uppercase
      >
        {statusLabel}
      </Badge>
      {info && (
        <span className={styles.expand} aria-hidden="true">
          {expanded ? "▾" : "▸"}
        </span>
      )}
    </>
  );

  return (
    <Card
      className={[
        styles.panel,
        isUnverified ? styles.unverified : cfg.className,
        isBanner ? styles.banner : "",
      ].join(" ")}
      depth="card"
      padding="none"
    >
      <span
        className={styles.liveStatus}
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        {buttonLabel}
        {liveMessage ? `. ${liveMessage}` : ""}
      </span>
      {info ? (
        <button
          type="button"
          className={styles.summary}
          onClick={() => setExpanded((current) => !current)}
          aria-expanded={expanded}
          aria-controls={detailsId}
          title={isUnverified ? "Freshness is unverified" : cfg.label}
          aria-label={buttonLabel}
        >
          {summaryContent}
        </button>
      ) : (
        <div className={[styles.summary, styles.staticSummary].join(" ")}>
          {summaryContent}
        </div>
      )}

      {info && expanded && (
        <div className={styles.details} id={detailsId}>
          <div className={styles.detailsLabel}>
            {isUnverified ? "Last-known season coverage" : "Season coverage"}
          </div>
          {isUnverified && (
            <div className={styles.lastVerified}>
              Last verified: {info.checked_at ?? "time unavailable"}
            </div>
          )}
          {info.seasons.map((s) => (
            <div
              key={`${s.season}-${s.season_type}`}
              className={styles.seasonRow}
            >
              <span className={styles.seasonLabel}>
                {s.season} {s.season_type}
              </span>
              <Badge
                variant={BADGE_VARIANTS[normalizeStatus(s.status)]}
                size="sm"
                uppercase
              >
                {normalizeStatus(s.status)}
              </Badge>
              <span className={styles.seasonCurrentThrough}>
                {s.current_through
                  ? `${isUnverified ? "last known through" : "through"} ${s.current_through}`
                  : "—"}
              </span>
              <span
                className={styles.seasonCurrentThrough}
                title={s.validation_errors.join("; ") || undefined}
              >
                validation {s.validation_state}
                {s.generation_id ? ` · ${s.generation_id.slice(0, 8)}` : ""}
              </span>
            </div>
          ))}

          {info.last_refresh_at && (
            <div className={styles.refreshRow}>
              {isUnverified ? "Last-known refresh" : "Last refresh"}:{" "}
              {info.last_refresh_ok ? "✅" : "❌"} {" "}
              {info.last_refresh_at}
              {info.last_refresh_error && (
                <span className={styles.error}> — details withheld</span>
              )}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
