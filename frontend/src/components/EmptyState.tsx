import { Badge, Card } from "../design-system";
import styles from "./EmptyState.module.css";

const TIPS = [
  'Try: "Jokic last 10 games"',
  'Try: "top 10 scorers 2024-25"',
  'Try: "Lakers longest winning streak"',
  'Try: "Jokic vs Embiid 2024-25"',
  'Try: "Celtics home vs away"',
];

export default function EmptyState() {
  return (
    <Card className={styles.emptyState} depth="card" padding="lg">
      <div className={styles.iconWrap}>
        <div className={styles.icon}>🏀</div>
      </div>
      <div className={styles.copy}>
        <Badge variant="accent" size="sm" uppercase>
          Ready
        </Badge>
        <h2 className={styles.title}>Search the NBA</h2>
        <p className={styles.description}>
          Type a natural language query above to explore player stats, team
          performance, matchups, streaks, and leaderboards.
        </p>
      </div>
      <div className={styles.tips}>
        {TIPS.map((tip) => (
          <div key={tip} className={styles.tip}>
            {tip}
          </div>
        ))}
      </div>
    </Card>
  );
}
