import { Badge, Card } from "../design-system";
import styles from "./EmptyState.module.css";

const CAPABILITIES = [
  {
    title: "Players",
    detail: "recent form, game logs, thresholds, and streaks",
  },
  {
    title: "Teams",
    detail: "records, splits, matchups, and team-level trends",
  },
  {
    title: "History",
    detail: "playoff runs, rivalry records, and era comparisons",
  },
];

export default function EmptyState() {
  return (
    <Card className={styles.emptyState} depth="card" padding="lg">
      <div className={styles.content}>
        <Badge variant="accent" size="sm" uppercase>
          First run
        </Badge>
        <h2 className={styles.title}>
          Ask a basketball question. Get a structured answer.
        </h2>
        <p className={styles.description}>
          nbatools turns natural-language NBA searches into answer-first cards,
          rankings, and detail tables for players, teams, records, streaks,
          matchups, and playoff history.
        </p>
      </div>

      <div className={styles.capabilities} aria-label="Supported query areas">
        {CAPABILITIES.map((item) => (
          <div key={item.title} className={styles.capability}>
            <div className={styles.capabilityTitle}>{item.title}</div>
            <div className={styles.capabilityDetail}>{item.detail}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}
