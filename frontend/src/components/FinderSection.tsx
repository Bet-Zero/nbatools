import type { SectionRow } from "../api/types";
import { SectionHeader } from "../design-system";
import DataTable from "./DataTable";
import styles from "./FinderSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
}

export default function FinderSection({ sections }: Props) {
  const finder = sections.finder;
  if (!finder || finder.length === 0) return null;

  return (
    <div className={styles.section}>
      <SectionHeader
        title="Matching Games"
        count={`${finder.length} game${finder.length !== 1 ? "s" : ""}`}
      />
      <DataTable rows={finder} />
    </div>
  );
}
