import { useEffect, useState } from "react";
import { fetchRoutes } from "../api/client";
import { Badge, Button, Card } from "../design-system";
import styles from "./DevTools.module.css";

interface Props {
  onRun: (route: string, kwargs: string) => void;
}

export default function DevTools({ onRun }: Props) {
  const [routes, setRoutes] = useState<string[]>([]);
  const [selectedRoute, setSelectedRoute] = useState("");
  const [kwargs, setKwargs] = useState("{}");

  useEffect(() => {
    fetchRoutes()
      .then((r) => setRoutes(r.routes))
      .catch(() => setRoutes([]));
  }, []);

  function handleSubmit() {
    if (!selectedRoute) return;
    onRun(selectedRoute, kwargs);
  }

  return (
    <Card
      as="details"
      className={styles.devTools}
      data-shortcut-scope="ignore"
      depth="input"
      padding="md"
    >
      <summary>
        <span>Dev Tools — Structured Query</span>
        <Badge variant="neutral" size="sm" uppercase>
          dev
        </Badge>
      </summary>
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

        <Button type="button" onClick={handleSubmit} size="sm" variant="secondary">
          Run Structured Query
        </Button>
      </div>
    </Card>
  );
}
