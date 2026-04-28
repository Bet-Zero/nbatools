import { useEffect, useState } from "react";
import { fetchRoutes, postStructuredQuery } from "../api/client";
import type { QueryResponse } from "../api/types";
import styles from "./DevTools.module.css";

interface Props {
  onResult: (data: QueryResponse) => void;
  onError: (msg: string) => void;
  onLoading: (loading: boolean) => void;
  onQueryStart?: (route: string, kwargs: string) => void;
}

export default function DevTools({
  onResult,
  onError,
  onLoading,
  onQueryStart,
}: Props) {
  const [routes, setRoutes] = useState<string[]>([]);
  const [selectedRoute, setSelectedRoute] = useState("");
  const [kwargs, setKwargs] = useState("{}");

  useEffect(() => {
    fetchRoutes()
      .then((r) => setRoutes(r.routes))
      .catch(() => setRoutes([]));
  }, []);

  async function handleSubmit() {
    if (!selectedRoute) return;
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(kwargs || "{}");
    } catch (err) {
      onError("Invalid JSON in kwargs: " + (err as Error).message);
      return;
    }
    onQueryStart?.(selectedRoute, kwargs);
    onLoading(true);
    try {
      const data = await postStructuredQuery(selectedRoute, parsed);
      onResult(data);
    } catch (err) {
      onError((err as Error).message);
    } finally {
      onLoading(false);
    }
  }

  return (
    <details className={styles.devTools}>
      <summary>Dev Tools — Structured Query</summary>
      <div className={styles.body}>
        <label htmlFor="route-select">Route</label>
        <select
          id="route-select"
          value={selectedRoute}
          onChange={(e) => setSelectedRoute(e.target.value)}
        >
          <option value="">— select route —</option>
          {routes.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>

        <label htmlFor="kwargs-input">kwargs (JSON)</label>
        <textarea
          id="kwargs-input"
          value={kwargs}
          onChange={(e) => setKwargs(e.target.value)}
          placeholder='{"season": "2024-25", "stat": "pts", "limit": 10}'
        />

        <button type="button" onClick={handleSubmit}>
          Run Structured Query
        </button>
      </div>
    </details>
  );
}
