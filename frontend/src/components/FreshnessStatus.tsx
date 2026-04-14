import { useEffect, useState } from "react";
import { fetchFreshness } from "../api/client";
import type { FreshnessResponse, FreshnessStatusValue } from "../api/types";

const STATUS_CONFIG: Record<
  FreshnessStatusValue,
  { dot: string; label: string; className: string }
> = {
  fresh: { dot: "●", label: "Data is current", className: "freshness-fresh" },
  stale: { dot: "●", label: "Data may be stale", className: "freshness-stale" },
  unknown: {
    dot: "○",
    label: "Freshness unknown",
    className: "freshness-unknown",
  },
  failed: {
    dot: "●",
    label: "Last refresh failed",
    className: "freshness-failed",
  },
};

interface Props {
  /** Poll interval in ms — 0 to disable polling. */
  pollInterval?: number;
}

export default function FreshnessStatus({ pollInterval = 120_000 }: Props) {
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

  return (
    <div className={`freshness-panel ${cfg.className}`}>
      <button
        type="button"
        className="freshness-summary"
        onClick={() => setExpanded((e) => !e)}
        aria-expanded={expanded}
        title={cfg.label}
      >
        <span className="freshness-dot">{cfg.dot}</span>
        <span className="freshness-label">
          {info.current_through
            ? `Data through ${info.current_through}`
            : cfg.label}
        </span>
        <span className={`freshness-badge freshness-badge-${status}`}>
          {status}
        </span>
        <span className="freshness-expand">{expanded ? "▾" : "▸"}</span>
      </button>

      {expanded && (
        <div className="freshness-details">
          {info.seasons.map((s) => (
            <div
              key={`${s.season}-${s.season_type}`}
              className="freshness-season-row"
            >
              <span className="freshness-season-label">
                {s.season} {s.season_type}
              </span>
              <span className={`freshness-badge freshness-badge-${s.status}`}>
                {s.status}
              </span>
              <span className="freshness-season-ct">
                {s.current_through ? `through ${s.current_through}` : "—"}
              </span>
            </div>
          ))}

          {info.last_refresh_at && (
            <div className="freshness-refresh-row">
              Last refresh: {info.last_refresh_ok ? "✅" : "❌"}{" "}
              {info.last_refresh_at}
              {info.last_refresh_error && (
                <span
                  className="freshness-error"
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
    </div>
  );
}
