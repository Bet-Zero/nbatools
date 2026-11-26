import { Button } from "../design-system";
import { normalizeDisplayMode, type DisplayModeInput } from "../displayMode";
import styles from "./SampleQueries.module.css";

interface StarterQueryGroup {
  id: string;
  title: string;
  scope?: string;
  queries: { query: string; resultHint: string }[];
}

const STARTER_QUERY_GROUPS: StarterQueryGroup[] = [
  {
    id: "players",
    title: "Players",
    queries: [
      { query: "Jokic last 10 games", resultHint: "entity_summary + game_log" },
      { query: "Stephen Curry averages in 2023-24", resultHint: "entity_summary" },
      {
        query: "Top 5 players by three point percentage in 2023-24 minimum 300 attempts",
        resultHint: "leaderboard (season leaders)",
      },
      {
        query: "In 2023-24, how many Jalen Brunson games had 8 or more assists and no turnovers?",
        resultHint: "count (player games)",
      },
    ],
  },
  {
    id: "teams",
    title: "Teams",
    queries: [
      { query: "Celtics record 2024-25", resultHint: "record (team)" },
      {
        query: "Celtics record vs NYK from 2023-11-01 to 2024-03-01",
        resultHint: "record (opponent and dates)",
      },
      {
        query: "Nuggets home vs away splits against Timberwolves with at least 110 points in 2023-24",
        resultHint: "split (team)",
      },
    ],
  },
  {
    id: "participation",
    title: "Player participation",
    scope: "Team records count appearances for the selected team. Games missed while rostered use membership coverage.",
    queries: [
      {
        query: "Cavaliers record without Caris LeVert in 2024-25",
        resultHint: "record (team appearances)",
      },
      {
        query: "How many games did LeBron James miss in 2025-26?",
        resultHint: "count (rostered games missed)",
      },
    ],
  },
  {
    id: "history",
    title: "Streaks and playoffs",
    queries: [
      { query: "Heat longest winning streak in 2012-13", resultHint: "streak (team)" },
      { query: "Warriors playoff record in 2015-16", resultHint: "record (playoffs)" },
    ],
  },
];

interface Props {
  onSelect: (query: string) => void;
  displayMode?: DisplayModeInput;
}

export default function SampleQueries({ onSelect, displayMode }: Props) {
  const isDebugMode = normalizeDisplayMode(displayMode) === "debug";

  return (
    <section
      className={styles.sampleQueries}
      aria-labelledby="starter-queries-heading"
    >
      <header className={styles.panelHeader}>
        <h2 id="starter-queries-heading" className={styles.panelTitle}>
          Starter queries
        </h2>
        <p className={styles.scope}>
          These examples use the served snapshot. Latest-game samples follow its
          data cutoff. Coverage can vary by season and question.
        </p>
      </header>
      <div className={styles.scrollList}>
        {STARTER_QUERY_GROUPS.map((group) => (
          <section
            key={group.id}
            className={styles.group}
            aria-labelledby={`starter-group-${group.id}`}
          >
            <h3
              id={`starter-group-${group.id}`}
              className={styles.groupTitle}
            >
              {group.title}
            </h3>
            {group.scope && <p className={styles.scope}>{group.scope}</p>}
            <div className={styles.samples}>
              {group.queries.map((sample) => (
                <Button
                  key={sample.query}
                  type="button"
                  className={styles.sampleButton}
                  onClick={() => onSelect(sample.query)}
                  size="sm"
                  variant="secondary"
                  aria-label={`Run starter query: ${sample.query}`}
                  fullWidth
                >
                  <span className={styles.sampleQuery}>{sample.query}</span>
                  {isDebugMode && (
                    <span className={styles.resultHint}>
                      {sample.resultHint}
                    </span>
                  )}
                </Button>
              ))}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}
