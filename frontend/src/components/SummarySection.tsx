import type { SectionRow } from "../api/types";
import {
  SectionHeader,
  StatBlock,
  type StatProps,
} from "../design-system";
import DataTable from "./DataTable";
import { formatColHeader, formatValue } from "./tableFormatting";
import styles from "./SummarySection.module.css";

interface Props {
  sections: Record<string, SectionRow[]>;
}

const SUMMARY_STAT_LIMIT = 4;
const NON_STAT_SUMMARY_COLS = new Set([
  "#",
  "rank",
  "player",
  "player_name",
  "team",
  "team_name",
  "opponent",
  "season",
  "season_type",
  "game_date",
  "date",
]);

function summaryStats(rows: SectionRow[]): StatProps[] {
  if (rows.length !== 1) return [];
  const row = rows[0];
  return Object.keys(row)
    .filter((col) => {
      const key = col.toLowerCase();
      return (
        !NON_STAT_SUMMARY_COLS.has(key) &&
        typeof row[col] === "number"
      );
    })
    .slice(0, SUMMARY_STAT_LIMIT)
    .map((col, index) => ({
      label: formatColHeader(col),
      value: formatValue(row[col], col),
      semantic: index === 0 ? "accent" : "neutral",
    }));
}

export default function SummarySection({ sections }: Props) {
  const summary = sections.summary;
  const bySeason = sections.by_season;
  const stats = summary ? summaryStats(summary) : [];

  return (
    <>
      {summary && summary.length > 0 && (
        <div className={styles.section}>
          <SectionHeader title="Summary" />
          {stats.length > 0 && (
            <StatBlock stats={stats} columns={4} className={styles.stats} />
          )}
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
