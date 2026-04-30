import { useEffect, useState } from "react";
import { fetchFreshness } from "../api/client";
import type { FreshnessResponse, FreshnessStatusValue } from "../api/types";
import { Badge, Card, type BadgeVariant } from "../design-system";
import styles from "./FreshnessStatus.module.css";

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
  stale: "Review data age before sharing results.",
  unknown: "Freshness is not confirmed.",
  failed: "Refresh needs attention before results are trusted.",
};

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
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await fetchFreshness();
        if (!cancelled) setInfo(data);
      } catch {
        // API offline — leave info as null
      }
    }

    load();

    if (pollInterval > 0) {
      const id = setInterval(load, pollInterval);
      return () => {
        cancelled = true;
        clearInterval(id);
      };
    }

    return () => {
      cancelled = true;
    };
  }, [pollInterval]);

  if (!info) return null;

  const status = info.status as FreshnessStatusValue;
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.unknown;
  const isBanner = variant === "banner";
  const label = info.current_through
    ? `Data through ${info.current_through}`
    : cfg.label;

  return (
    <Card
      className={[
        styles.panel,
        cfg.className,
        isBanner ? styles.banner : "",
      ].join(" ")}
      depth="card"
      padding="none"
    >
      <button
        type="button"
        className={styles.summary}
        onClick={() => setExpanded((e) => !e)}
        aria-expanded={expanded}
        title={cfg.label}
        aria-label={isBanner ? `Data freshness: ${label}` : undefined}
      >
        <span className={styles.dot}>{cfg.dot}</span>
        <span className={styles.labelStack}>
          {isBanner && (
            <span className={styles.kicker}>Data freshness</span>
          )}
          <span className={styles.label}>{label}</span>
          {isBanner && (
            <span className={styles.bannerMessage}>
              {BANNER_MESSAGES[status] ?? BANNER_MESSAGES.unknown}
            </span>
          )}
        </span>
        <Badge variant={BADGE_VARIANTS[status]} size="sm" uppercase>
          {status}
        </Badge>
        <span className={styles.expand}>{expanded ? "▾" : "▸"}</span>
      </button>

      {expanded && (
        <div className={styles.details}>
          <div className={styles.detailsLabel}>Season coverage</div>
          {info.seasons.map((s) => (
            <div
              key={`${s.season}-${s.season_type}`}
              className={styles.seasonRow}
            >
              <span className={styles.seasonLabel}>
                {s.season} {s.season_type}
              </span>
              <Badge
                variant={BADGE_VARIANTS[s.status as FreshnessStatusValue]}
                size="sm"
                uppercase
              >
                {s.status}
              </Badge>
              <span className={styles.seasonCurrentThrough}>
                {s.current_through ? `through ${s.current_through}` : "—"}
              </span>
            </div>
          ))}

          {info.last_refresh_at && (
            <div className={styles.refreshRow}>
              Last refresh: {info.last_refresh_ok ? "✅" : "❌"}{" "}
              {info.last_refresh_at}
              {info.last_refresh_error && (
                <span
                  className={styles.error}
                  title={info.last_refresh_error}
                >
                  {" "}
                  — {info.last_refresh_error.slice(0, 80)}
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
