import type { SectionRow } from "../api/types";
import { SectionHeader } from "../design-system";
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
      <SectionHeader
        title="Leaderboard"
        count={`${leaderboard.length} entries`}
      />
      <DataTable rows={leaderboard} highlight />
    </div>
  );
}
