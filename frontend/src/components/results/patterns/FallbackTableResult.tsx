import type { QueryResponse, SectionRow } from "../../../api/types";
import { Card, SectionHeader } from "../../../design-system";
import DataTable from "../../DataTable";
import styles from "./FallbackTableResult.module.css";

interface Props {
  data: QueryResponse;
}

/**
 * Generic raw-table renderer. Used for any route that has not yet been
 * migrated to a dedicated pattern, and as the safe default when the
 * route lookup fails.
 *
 * Renders one card with a header + DataTable per non-empty section in
 * the response. This is intentionally plain — patterns deliver polish;
 * the fallback's job is to surface the data without losing anything.
 */
export default function FallbackTableResult({ data }: Props) {
  const sections = data.result?.sections ?? {};
  const keys = Object.keys(sections).filter((key) => {
    const rows = sections[key];
    return rows && rows.length > 0;
  });

  if (keys.length === 0) return null;

  return (
    <>
      {keys.map((key) => (
        <Card
          className={styles.section}
          key={key}
          depth="card"
          padding="md"
        >
          <SectionHeader title={sectionLabel(key)} />
          <DataTable rows={sections[key] as SectionRow[]} />
        </Card>
      ))}
    </>
  );
}

const SECTION_LABELS: Record<string, string> = {
  summary: "Summary",
  by_season: "By Season",
  comparison: "Comparison",
  split_comparison: "Split Comparison",
  finder: "Matching Games",
  leaderboard: "Leaderboard",
  streak: "Streaks",
  game_log: "Game Log",
};

function sectionLabel(key: string): string {
  return SECTION_LABELS[key] ?? key.replace(/_/g, " ");
}
