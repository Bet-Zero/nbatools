const TIPS = [
  'Try: "Jokic last 10 games"',
  'Try: "top 10 scorers 2024-25"',
  'Try: "Lakers longest winning streak"',
  'Try: "Jokic vs Embiid 2024-25"',
  'Try: "Celtics home vs away"',
];

export default function EmptyState() {
  return (
    <div className="empty-state">
      <div className="empty-icon">🏀</div>
      <h2 className="empty-title">Search the NBA</h2>
      <p className="empty-desc">
        Type a natural language query above to explore player stats, team
        performance, matchups, streaks, and leaderboards.
      </p>
      <div className="empty-tips">
        {TIPS.map((tip) => (
          <div key={tip} className="empty-tip">
            {tip}
          </div>
        ))}
      </div>
    </div>
  );
}
