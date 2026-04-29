import type { SectionRow } from "../api/types";
import { SectionHeader } from "../design-system";
import DataTable from "./DataTable";
import styles from "./PlayerSummarySection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
}

export default function PlayerSummarySection({ sections }: Props) {
  const summary = sections.summary;
  const bySeason = sections.by_season;

  return (
    <>
      {summary && summary.length > 0 && (
        <div className={styles.section}>
          <SectionHeader title="Player Summary" />
          <DataTable rows={summary} />
        </div>
      )}
      {bySeason && bySeason.length > 0 && (
        <div className={styles.section}>
          <SectionHeader title="By Season" />
          <DataTable rows={bySeason} />
        </div>
      )}
    </>
  );
}
