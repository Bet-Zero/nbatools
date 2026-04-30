import { Button } from "../design-system";
import styles from "./SampleQueries.module.css";

interface StarterQuery {
  label: string;
  query: string;
  resultHint: string;
}

interface StarterQueryGroup {
  id: string;
  title: string;
  description: string;
  queries: StarterQuery[];
}

export const STARTER_QUERY_GROUPS: StarterQueryGroup[] = [
  {
    id: "players",
    title: "Players",
    description: "Recent form, thresholds, and game logs.",
    queries: [
      {
        label: "Recent form",
        query: "Jokic last 10 games",
        resultHint: "Player summary",
      },
      {
        label: "Game finder",
        query: "Curry 5+ threes",
        resultHint: "Matching games",
      },
    ],
  },
  {
    id: "teams",
    title: "Teams",
    description: "Splits, records, and team streaks.",
    queries: [
      {
        label: "Home/away split",
        query: "Celtics home vs away 2024-25",
        resultHint: "Split summary",
      },
      {
        label: "Team streak",
        query: "Lakers longest winning streak 2024-25",
        resultHint: "Streak cards",
      },
    ],
  },
  {
    id: "comparisons",
    title: "Comparisons",
    description: "Player cards and head-to-head matchups.",
    queries: [
      {
        label: "Player vs player",
        query: "Jokic vs Embiid 2024-25",
        resultHint: "Comparison cards",
      },
      {
        label: "Team matchup",
        query: "Lakers vs Celtics since 2010",
        resultHint: "Head-to-head",
      },
    ],
  },
  {
    id: "records",
    title: "Records",
    description: "Team records and league-wide rankings.",
    queries: [
      {
        label: "Team record",
        query: "Celtics record 2024-25",
        resultHint: "Record card",
      },
      {
        label: "Record leaders",
        query: "best record since 2015",
        resultHint: "Leaderboard",
      },
    ],
  },
  {
    id: "history",
    title: "History",
    description: "Playoff history and rivalry context.",
    queries: [
      {
        label: "Playoff history",
        query: "Lakers playoff history",
        resultHint: "Postseason summary",
      },
      {
        label: "Playoff matchup",
        query: "Lakers vs Celtics playoff history",
        resultHint: "Series detail",
      },
    ],
  },
];

interface Props {
  onSelect: (query: string) => void;
}

export default function SampleQueries({ onSelect }: Props) {
  return (
    <section
      className={styles.sampleQueries}
      aria-labelledby="starter-queries-heading"
    >
      <div className={styles.header}>
        <div>
          <div className={styles.eyebrow}>Starter queries</div>
          <h2 id="starter-queries-heading" className={styles.title}>
            Pick a starting point
          </h2>
        </div>
        <div className={styles.hint}>Runs immediately</div>
      </div>

      <div className={styles.groups}>
        {STARTER_QUERY_GROUPS.map((group) => (
          <section
            key={group.id}
            className={styles.group}
            aria-labelledby={`starter-group-${group.id}`}
          >
            <div className={styles.groupHeader}>
              <h3
                id={`starter-group-${group.id}`}
                className={styles.groupTitle}
              >
                {group.title}
              </h3>
              <p className={styles.groupDescription}>{group.description}</p>
            </div>
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
                  <span className={styles.sampleLabel}>{sample.label}</span>
                  <span className={styles.sampleQuery}>{sample.query}</span>
                  <span className={styles.resultHint}>{sample.resultHint}</span>
                </Button>
              ))}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}
