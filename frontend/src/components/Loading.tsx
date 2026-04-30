import {
  Badge,
  Card,
  Skeleton,
  SkeletonBlock,
  SkeletonText,
} from "../design-system";
import styles from "./Loading.module.css";

export default function Loading() {
  return (
    <Card
      className={styles.loading}
      depth="card"
      padding="lg"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className={styles.statusRow}>
        <div className={styles.spinner} aria-hidden="true" />
        <div className={styles.copy}>
          <div className={styles.badgeRow}>
            <Badge variant="accent" size="sm" uppercase>
              Running
            </Badge>
            <span className={styles.context}>Query request</span>
          </div>
          <div className={styles.message}>Searching NBA data…</div>
          <div className={styles.detail}>
            Preparing the result view while the API checks the request.
          </div>
        </div>
      </div>
      <div className={styles.preview} aria-label="Loading result preview">
        <div className={styles.previewHeader}>
          <Skeleton width="34%" height="var(--space-5)" />
          <SkeletonText
            aria-label="Loading result metadata"
            className={styles.previewMeta}
            lines={2}
            width={["72%", "48%"]}
          />
        </div>
        <div className={styles.previewGrid}>
          <div
            className={styles.summaryPreview}
            aria-label="Loading summary preview"
          >
            <Skeleton width="48%" height="var(--space-4)" />
            <div className={styles.metricGrid}>
              <Skeleton height="var(--space-10)" radius="lg" />
              <Skeleton height="var(--space-10)" radius="lg" />
              <Skeleton height="var(--space-10)" radius="lg" />
            </div>
          </div>
          <SkeletonBlock
            aria-label="Loading result rows"
            className={styles.tablePreview}
            rows={4}
          />
        </div>
      </div>
    </Card>
  );
}
