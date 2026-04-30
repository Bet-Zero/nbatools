import type { SectionRow } from "../api/types";
import { SectionHeader } from "../design-system";
import DataTable from "./DataTable";
import styles from "./CountSection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
}

const DETAIL_LABELS: Record<string, string> = {
  finder: "Matching Games",
  leaderboard: "Leaderboard Detail",
  streak: "Streak Detail",
};

function sectionTitle(key: string): string {
  return DETAIL_LABELS[key] ?? key.replace(/_/g, " ");
}

export default function CountSection({ sections }: Props) {
  const count = sections.count;
  const detailKeys = Object.keys(sections).filter(
    (key) => key !== "count" && sections[key] && sections[key].length > 0,
  );

  return (
    <>
      {count && count.length > 0 && (
        <div className={styles.section}>
          <SectionHeader title="Count" />
          <DataTable rows={count} />
        </div>
      )}
      {detailKeys.map((key) => (
        <div className={styles.section} key={key}>
          <SectionHeader title={sectionTitle(key)} />
          <DataTable rows={sections[key]} />
        </div>
      ))}
    </>
  );
}
