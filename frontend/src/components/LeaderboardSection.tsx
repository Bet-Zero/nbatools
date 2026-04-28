import type { SectionRow } from "../api/types";
import DataTable from "./DataTable";
import styles from "./LeaderboardSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
}

export default function LeaderboardSection({ sections }: Props) {
  const leaderboard = sections.leaderboard;
  if (!leaderboard || leaderboard.length === 0) return null;

  return (
    <div className={styles.section}>
      <div className={styles.title}>
        Leaderboard
        <span className={styles.count}>{leaderboard.length} entries</span>
      </div>
      <DataTable rows={leaderboard} highlight />
    </div>
  );
}
