import type { SectionRow } from "../api/types";
import LeaderboardSection from "./LeaderboardSection";

interface Props {
  sections: Record<string, SectionRow[]>;
}

export default function OccurrenceLeaderboardSection({ sections }: Props) {
  return (
    <LeaderboardSection
      sections={sections}
      title="Occurrence Leaderboard"
      detailTitle="Occurrence Detail"
    />
  );
}
