import type { ReactNode } from "react";
import type { ResultMetadata, SectionRow } from "../api/types";
import ComparisonSection from "./ComparisonSection";
import PlayerComparisonSection from "./PlayerComparisonSection";
import TeamRecordSection from "./TeamRecordSection";

interface Props {
  sections: Record<string, SectionRow[]>;
  metadata?: ResultMetadata;
  route?: string | null;
}

export default function HeadToHeadSection({
  sections,
  metadata,
  route,
}: Props) {
  let content: ReactNode;

  if (
    route === "team_matchup_record" ||
    metadata?.route === "team_matchup_record"
  ) {
    content = (
      <TeamRecordSection sections={sections} metadata={metadata} route={route} />
    );
  } else if (
    route === "player_compare" ||
    metadata?.route === "player_compare"
  ) {
    content = (
      <PlayerComparisonSection sections={sections} metadata={metadata} />
    );
  } else {
    content = <ComparisonSection sections={sections} />;
  }

  return <div aria-label="Head-to-head result">{content}</div>;
}
