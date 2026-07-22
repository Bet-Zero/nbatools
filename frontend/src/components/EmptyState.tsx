import { Card } from "../design-system";
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
        <h2 className={styles.title}>
          Ask a supported NBA stat question. Get a straight answer.
        </h2>
        <p className={styles.description}>
          Players, teams, records, streaks, matchups, playoff history — type a
          question the way you&apos;d say it, or pick a starter query to see
          how it answers.
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
