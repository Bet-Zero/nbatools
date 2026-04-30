import type { ReactNode } from "react";
import type { SectionRow } from "../api/types";
import ComparisonSection from "./ComparisonSection";
import LeaderboardSection from "./LeaderboardSection";
import SummarySection from "./SummarySection";

interface Props {
  sections: Record<string, SectionRow[]>;
  queryClass: string;
}

export default function PlayoffSection({ sections, queryClass }: Props) {
  let content: ReactNode = null;

  if (queryClass === "summary") {
    content = <SummarySection sections={sections} />;
  } else if (queryClass === "comparison") {
    content = <ComparisonSection sections={sections} />;
  } else if (queryClass === "leaderboard") {
    content = <LeaderboardSection sections={sections} />;
  }

  return <div aria-label="Playoff result">{content}</div>;
}
