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
    <div className={styles.emptyState}>
      <div className={styles.icon}>🏀</div>
      <h2 className={styles.title}>Search the NBA</h2>
      <p className={styles.description}>
        Type a natural language query above to explore player stats, team
        performance, matchups, streaks, and leaderboards.
      </p>
      <div className={styles.tips}>
        {TIPS.map((tip) => (
          <div key={tip} className={styles.tip}>
            {tip}
          </div>
        ))}
      </div>
    </div>
  );
}
