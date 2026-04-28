import type { SectionRow } from "../api/types";
import DataTable from "./DataTable";
import styles from "./StreakSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
}

export default function StreakSection({ sections }: Props) {
  const streak = sections.streak;
  if (!streak || streak.length === 0) return null;

  return (
    <div className={styles.section}>
      <div className={styles.title}>
        Streaks
        <span className={styles.count}>{streak.length} found</span>
      </div>
      <DataTable rows={streak} highlight />
    </div>
  );
}
