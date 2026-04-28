import type { SectionRow } from "../api/types";
import DataTable from "./DataTable";
import styles from "./ComparisonSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
}

export default function ComparisonSection({ sections }: Props) {
  const summary = sections.summary;
  const comparison = sections.comparison;

  return (
    <>
      {summary && summary.length > 0 && (
        <div className={styles.section}>
          <div className={styles.title}>Players</div>
          <DataTable rows={summary} />
        </div>
      )}
      {comparison && comparison.length > 0 && (
        <div className={styles.section}>
          <div className={styles.title}>Comparison</div>
          <DataTable rows={comparison} highlight />
        </div>
      )}
    </>
  );
}
