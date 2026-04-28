import type { SectionRow } from "../api/types";
import DataTable from "./DataTable";
import styles from "./SummarySection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
}

export default function SummarySection({ sections }: Props) {
  const summary = sections.summary;
  const bySeason = sections.by_season;

  return (
    <>
      {summary && summary.length > 0 && (
        <div className={styles.section}>
          <div className={styles.title}>Summary</div>
          <DataTable rows={summary} />
        </div>
      )}
      {bySeason && bySeason.length > 0 && (
        <div className={styles.section}>
          <div className={styles.title}>By Season</div>
          <DataTable rows={bySeason} />
        </div>
      )}
    </>
  );
}
