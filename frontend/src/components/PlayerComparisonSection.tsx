import type { SectionRow } from "../api/types";
import { Card, SectionHeader } from "../design-system";
import DataTable from "./DataTable";
import styles from "./PlayerComparisonSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
}

export default function PlayerComparisonSection({ sections }: Props) {
  const summary = sections.summary;
  const comparison = sections.comparison;

  return (
    <>
      {summary && summary.length > 0 && (
        <Card className={styles.section} depth="card" padding="md">
          <SectionHeader
            title="Player Comparison"
            count={`${summary.length} players`}
          />
          <DataTable rows={summary} />
        </Card>
      )}
      {comparison && comparison.length > 0 && (
        <Card className={styles.section} depth="card" padding="md">
          <SectionHeader title="Metric Comparison" />
          <DataTable rows={comparison} highlight />
        </Card>
      )}
    </>
  );
}
