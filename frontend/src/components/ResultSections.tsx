import type { QueryResponse, SectionRow } from "../api/types";
import ComparisonSection from "./ComparisonSection";
import DataTable from "./DataTable";
import FinderSection from "./FinderSection";
import LeaderboardSection from "./LeaderboardSection";
import NoResultDisplay from "./NoResultDisplay";
import SplitSummarySection from "./SplitSummarySection";
import StreakSection from "./StreakSection";
import SummarySection from "./SummarySection";

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

function renderByQueryClass(
  queryClass: string,
  sections: Record<string, SectionRow[]>,
): React.ReactNode {
  switch (queryClass) {
    case "summary":
      return <SummarySection sections={sections} />;
    case "comparison":
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
        <div className="section" key={key}>
          <div className="section-title">{sectionLabel(key)}</div>
          <DataTable rows={sections[key]} />
        </div>
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
        />
      );
    }
    return null;
  }

  const queryClass = result.query_class ?? "";
  const hasSections = Object.values(result.sections).some(
    (rows) => rows && rows.length > 0,
  );

  if (!hasSections) {
    if (data.result_status !== "ok") {
      return (
        <NoResultDisplay
          reason={data.result_reason}
          status={data.result_status}
        />
      );
    }
    return null;
  }

  return <>{renderByQueryClass(queryClass, result.sections)}</>;
}
