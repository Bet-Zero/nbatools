import type { SectionRow } from "../api/types";
import DataTable from "./DataTable";

interface Props {
  sections: Record<string, SectionRow[]>;
}

export default function LeaderboardSection({ sections }: Props) {
  const leaderboard = sections.leaderboard;
  if (!leaderboard || leaderboard.length === 0) return null;

  return (
    <div className="section">
      <div className="section-title">
        Leaderboard
        <span className="section-count">{leaderboard.length} entries</span>
      </div>
      <DataTable rows={leaderboard} highlight />
    </div>
  );
}
