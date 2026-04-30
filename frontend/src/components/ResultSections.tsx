import type { QueryResponse, SectionRow } from "../api/types";
import { Card, SectionHeader } from "../design-system";
import ComparisonSection from "./ComparisonSection";
import DataTable from "./DataTable";
import FinderSection from "./FinderSection";
import LeaderboardSection from "./LeaderboardSection";
import NoResultDisplay from "./NoResultDisplay";
import PlayerComparisonSection from "./PlayerComparisonSection";
import PlayerSummarySection from "./PlayerSummarySection";
import SplitSummarySection from "./SplitSummarySection";
import StreakSection from "./StreakSection";
import SummarySection from "./SummarySection";
import styles from "./ResultSections.module.css";

interface Props {
  data: QueryResponse;
}

/** Human-readable section labels for fallback rendering. */
const SECTION_LABELS: Record<string, string> = {
  summary: "Summary",
  by_season: "By Season",
  comparison: "Comparison",
  split_comparison: "Split Comparison",
  finder: "Matching Games",
  leaderboard: "Leaderboard",
  streak: "Streaks",
};

function sectionLabel(key: string): string {
  return SECTION_LABELS[key] ?? key.replace(/_/g, " ");
}

function isPlayerSummary(data: QueryResponse): boolean {
  return (
    data.route === "player_game_summary" ||
    data.result?.metadata?.route === "player_game_summary"
  );
}

function isPlayerComparison(data: QueryResponse): boolean {
  return (
    data.route === "player_compare" ||
    data.result?.metadata?.route === "player_compare"
  );
}

function renderByQueryClass(data: QueryResponse): React.ReactNode {
  const queryClass = data.result?.query_class ?? "";
  const sections = data.result?.sections ?? {};

  switch (queryClass) {
    case "summary":
      if (isPlayerSummary(data)) {
        return (
          <PlayerSummarySection
            sections={sections}
            metadata={data.result?.metadata}
          />
        );
      }
      return <SummarySection sections={sections} />;
    case "comparison":
      if (isPlayerComparison(data)) {
        return <PlayerComparisonSection sections={sections} />;
      }
      return <ComparisonSection sections={sections} />;
    case "split_summary":
      return <SplitSummarySection sections={sections} />;
    case "finder":
      return <FinderSection sections={sections} />;
    case "leaderboard":
      return <LeaderboardSection sections={sections} />;
    case "streak":
      return <StreakSection sections={sections} />;
    default:
      return renderFallback(sections);
  }
}

function renderFallback(
  sections: Record<string, SectionRow[]>,
): React.ReactNode {
  const keys = Object.keys(sections).filter(
    (k) => sections[k] && sections[k].length > 0,
  );
  if (keys.length === 0) return null;
  return (
    <>
      {keys.map((key) => (
        <Card className={styles.section} key={key} depth="card" padding="md">
          <SectionHeader title={sectionLabel(key)} />
          <DataTable rows={sections[key]} />
        </Card>
      ))}
    </>
  );
}

export default function ResultSections({ data }: Props) {
  const result = data.result;

  if (!result?.sections || Object.keys(result.sections).length === 0) {
    if (data.result_status === "no_result" || data.result_status === "error") {
      return (
        <NoResultDisplay
          reason={data.result_reason}
          status={data.result_status}
          notes={data.notes}
        />
      );
    }
    return null;
  }

  const hasSections = Object.values(result.sections).some(
    (rows) => rows && rows.length > 0,
  );

  if (!hasSections) {
    if (data.result_status !== "ok") {
      return (
        <NoResultDisplay
          reason={data.result_reason}
          status={data.result_status}
          notes={data.notes}
        />
      );
    }
    return null;
  }

  return <>{renderByQueryClass(data)}</>;
}
