import { Badge, Card, SkeletonBlock, SkeletonText } from "../design-system";
import styles from "./Loading.module.css";

export default function Loading() {
  return (
    <Card
      className={styles.loading}
      depth="card"
      padding="lg"
      role="status"
      aria-live="polite"
    >
      <div className={styles.header}>
        <div className={styles.spinner} aria-hidden="true" />
        <div className={styles.copy}>
          <Badge variant="accent" size="sm" uppercase>
            Running
          </Badge>
          <div className={styles.message}>Searching NBA data…</div>
          <SkeletonText
            aria-label="Loading query context"
            className={styles.messageSkeleton}
            lines={2}
            width={["72%", "46%"]}
          />
        </div>
      </div>
      <SkeletonBlock
        aria-label="Loading result preview"
        className={styles.preview}
        rows={3}
      />
    </Card>
  );
}
