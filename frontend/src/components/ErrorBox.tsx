import { Badge, Button, Card } from "../design-system";
import styles from "./ErrorBox.module.css";

interface Props {
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
  apiOnline?: boolean | null;
}

export default function ErrorBox({
  message,
  onRetry,
  retryLabel = "Retry",
  apiOnline,
}: Props) {
  const offline = apiOnline === false;

  return (
    <Card
      className={[styles.errorBox, offline ? styles.offline : ""]
        .filter(Boolean)
        .join(" ")}
      depth="card"
      padding="lg"
      role="alert"
    >
      <div className={styles.header}>
        <div className={styles.titleGroup}>
          <span className={styles.eyebrow}>
            {offline ? "Connection status" : "Request status"}
          </span>
          <div className={styles.title}>
            {offline ? "API offline" : "Request failed"}
          </div>
        </div>
        <Badge variant={offline ? "danger" : "warning"} size="sm" uppercase>
          {offline ? "offline" : "error"}
        </Badge>
      </div>
      <div className={styles.message}>
        {offline
          ? "The API status check is failing, so query results may not be reachable right now."
          : "The request did not complete. No result data was changed."}
      </div>
      <div className={styles.details} aria-label="Failure details">
        <div className={styles.detailsTitle}>Details</div>
        <div className={styles.detailText}>{message}</div>
      </div>
      {onRetry && (
        <div className={styles.actions}>
          <Button type="button" variant="primary" size="sm" onClick={onRetry}>
            {retryLabel}
          </Button>
        </div>
      )}
    </Card>
  );
}
