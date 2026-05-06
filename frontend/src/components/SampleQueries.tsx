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

// One preset per implemented result pattern variant in
// `routeToPattern.ts`. The `resultHint` mirrors the pattern config so it
// is obvious which renderer each preset will exercise. Most queries are
// drawn from existing parser/router tests so they should route as
// expected; the two flagged with ⚠️ are educated guesses for routes
// that lack verified natural-language test coverage.
const STARTER_QUERY_GROUPS: StarterQueryGroup[] = [
  {
    id: "players",
    title: "Players",
    description: "Player summaries, finders, top games, and leaders.",
    queries: [
      {
        label: "Recent form (last-N)",
        query: "Jokic last 10 games",
        resultHint: "entity_summary + game_log",
      },
      {
        label: "Season summary",
        query: "Jokic 2025-26",
        resultHint: "entity_summary",
      },
      {
        label: "Player game finder",
        query: "Curry 5+ threes",
        resultHint: "game_log (player)",
      },
      {
        label: "Top player games",
        query: "highest scoring games this season",
        resultHint: "game_log (top player games)",
      },
      {
        label: "Season leaders",
        query: "top scorers this season",
        resultHint: "leaderboard (season leaders)",
      },
      {
        label: "Player occurrence leaders",
        query: "most 40 point games since 2020",
        resultHint: "leaderboard (occurrence)",
      },
    ],
  },
  {
    id: "teams",
    title: "Teams",
    description: "Team finders, top games, records, and rankings.",
    queries: [
      {
        label: "Team game finder",
        query: "Lakers over 120 points",
        resultHint: "game_log (team)",
      },
      {
        // ⚠️ unverified — no natural-query test for top_team_games.
        label: "Top team games",
        query: "highest scoring team games this season",
        resultHint: "game_log (top team games)",
      },
      {
        // ⚠️ unverified — no natural-query test for team_occurrence_leaders.
        label: "Team occurrence leaders",
        query: "most 120 point games this season",
        resultHint: "leaderboard (team occurrence)",
      },
      {
        label: "Team record",
        query: "Celtics record 2024-25",
        resultHint: "record (team)",
      },
      {
        label: "Team record leaderboard",
        query: "best record since 2015",
        resultHint: "leaderboard (team record)",
      },
    ],
  },
  {
    id: "splits",
    title: "Splits & On/Off",
    description: "Player and team splits, plus on-court / off-court.",
    queries: [
      {
        label: "Player split",
        query: "Jokic home vs away in 2025-26",
        resultHint: "split (player)",
      },
      {
        label: "Team split",
        query: "Celtics home vs away 2024-25",
        resultHint: "split (team)",
      },
      {
        label: "Player on/off",
        query: "Jokic on/off",
        resultHint: "split (on-off)",
      },
    ],
  },
  {
    id: "streaks",
    title: "Streaks & Stretches",
    description: "Player streaks, team streaks, and rolling stretches.",
    queries: [
      {
        label: "Player streak",
        query: "Jokic 5 straight games with 20+ points",
        resultHint: "streak (player)",
      },
      {
        label: "Team streak",
        query: "Lakers longest winning streak 2024-25",
        resultHint: "streak (team)",
      },
      {
        label: "Player stretch leaderboard",
        query: "Booker hottest 4-game scoring stretch",
        resultHint: "leaderboard (stretch)",
      },
    ],
  },
  {
    id: "lineups",
    title: "Lineups",
    description: "Single lineup summaries and lineup leaderboards.",
    queries: [
      {
        label: "Lineup summary",
        query: "lineup with Tatum and Jaylen Brown",
        resultHint: "fallback_table (lineup_summary)",
      },
      {
        label: "Lineup leaderboard",
        query: "best 5-man lineups this season",
        resultHint: "leaderboard (lineup)",
      },
    ],
  },
  {
    id: "comparisons",
    title: "Comparisons",
    description: "Player cards, team cards, and head-to-head matchups.",
    queries: [
      {
        label: "Player vs player",
        query: "Jokic vs Embiid 2024-25",
        resultHint: "comparison (player)",
      },
      {
        label: "Team vs team",
        query: "Celtics vs Bucks from 2021-22 to 2023-24",
        resultHint: "comparison (team)",
      },
      {
        label: "Team head-to-head",
        query: "Lakers vs Celtics since 2010",
        resultHint: "comparison (team h2h)",
      },
    ],
  },
  {
    id: "decades",
    title: "Records by decade",
    description: "Decade splits and decade-aware leaderboards.",
    queries: [
      {
        label: "Record by decade",
        query: "lakers playoff summary by decade",
        resultHint: "record (by decade)",
      },
      {
        label: "Record by decade leaderboard",
        query: "most wins by decade since 1980",
        resultHint: "record (decade leaderboard)",
      },
      {
        label: "Matchup by decade",
        query: "lakers vs celtics by decade",
        resultHint: "record (matchup by decade)",
      },
    ],
  },
  {
    id: "playoffs",
    title: "Playoff history",
    description: "Playoff histories, round records, and appearances.",
    queries: [
      {
        label: "Playoff history",
        query: "Lakers playoff history",
        resultHint: "playoff_history",
      },
      {
        label: "Playoff round record",
        query: "best finals record since 1980",
        resultHint: "playoff_history (round)",
      },
      {
        label: "Playoff matchup history",
        query: "Lakers vs Celtics playoff history",
        resultHint: "playoff_history (matchup)",
      },
      {
        label: "Playoff appearances",
        query: "most finals appearances since 2000",
        resultHint: "leaderboard (appearances)",
      },
    ],
  },
  {
    id: "single_game",
    title: "Single game",
    description: "Specific-game lookups (game_summary route).",
    queries: [
      {
        label: "Game summary",
        query: "Boston home wins vs Milwaukee from 2021-22 to 2023-24",
        resultHint: "game_log (single game)",
      },
    ],
  },
];

interface Props {
  onSelect: (query: string) => void;
}

export default function SampleQueries({ onSelect }: Props) {
  return (
    <section className={styles.sampleQueries} aria-label="Starter queries">
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
              >
                <span className={styles.sampleQuery}>{sample.query}</span>
                <span className={styles.resultHint}>· {sample.resultHint}</span>
              </Button>
            ))}
          </div>
        </section>
      ))}
    </section>
  );
}
