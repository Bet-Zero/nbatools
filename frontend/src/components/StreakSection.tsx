import type { SectionRow } from "../api/types";
import DataTable from "./DataTable";

interface Props {
  sections: Record<string, SectionRow[]>;
}

export default function StreakSection({ sections }: Props) {
  const streak = sections.streak;
  if (!streak || streak.length === 0) return null;

  return (
    <div className="section">
      <div className="section-title">
        Streaks
        <span className="section-count">{streak.length} found</span>
      </div>
      <DataTable rows={streak} />
    </div>
  );
}
