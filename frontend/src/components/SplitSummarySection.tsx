import type { SectionRow } from "../api/types";
import DataTable from "./DataTable";
import styles from "./SplitSummarySection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
}

export default function SplitSummarySection({ sections }: Props) {
  const summary = sections.summary;
  const splitComparison = sections.split_comparison;

  return (
    <>
      {summary && summary.length > 0 && (
        <div className={styles.section}>
          <div className={styles.title}>Summary</div>
          <DataTable rows={summary} />
        </div>
      )}
      {splitComparison && splitComparison.length > 0 && (
        <div className={styles.section}>
          <div className={styles.title}>Split Comparison</div>
          <DataTable rows={splitComparison} highlight />
        </div>
      )}
    </>
  );
}
