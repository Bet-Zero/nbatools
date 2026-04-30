import type { SectionRow } from "../api/types";
import { Card, SectionHeader } from "../design-system";
import DataTable from "./DataTable";
import styles from "./PlayerGameFinderSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
}

export default function PlayerGameFinderSection({ sections }: Props) {
  const finder = sections.finder;
  if (!finder || finder.length === 0) return null;

  return (
    <div className={styles.section}>
      <SectionHeader
        title="Player Games"
        count={`${finder.length} game${finder.length !== 1 ? "s" : ""}`}
      />
      <Card className={styles.detailCard} depth="card" padding="md">
        <SectionHeader title="Player Game Detail" />
        <DataTable rows={finder} />
      </Card>
    </div>
  );
}
