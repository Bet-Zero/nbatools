import type { QueryResponse, SectionRow } from "../api/types";
import { Card, SectionHeader } from "../design-system";
import CountSection from "./CountSection";
import DataTable from "./DataTable";
import FinderSection from "./FinderSection";
import LineupSection from "./LineupSection";
import NoResultDisplay from "./NoResultDisplay";
import SummarySection from "./SummarySection";
import TeamRecordSection from "./TeamRecordSection";
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

function isTeamRecord(data: QueryResponse): boolean {
  const route = data.route ?? data.result?.metadata?.route;
  return route === "team_record";
}

function isLineupSummary(data: QueryResponse): boolean {
  const route = data.route ?? data.result?.metadata?.route;
  return route === "lineup_summary";
}

function isTeamMatchupRecord(data: QueryResponse): boolean {
  const route = data.route ?? data.result?.metadata?.route;
  return route === "team_matchup_record";
}

function renderByQueryClass(data: QueryResponse): React.ReactNode {
  const queryClass = data.result?.query_class ?? "";
  const sections = data.result?.sections ?? {};

  switch (queryClass) {
    case "summary":
      if (isLineupSummary(data)) {
        return (
          <LineupSection
            sections={sections}
            metadata={data.result?.metadata}
            mode="summary"
          />
        );
      }
      if (isTeamRecord(data)) {
        return (
          <TeamRecordSection
            sections={sections}
            metadata={data.result?.metadata}
            route={data.route}
          />
        );
      }
      return <SummarySection sections={sections} />;
    case "comparison":
      if (isTeamMatchupRecord(data)) {
        return (
          <TeamRecordSection
            sections={sections}
            metadata={data.result?.metadata}
            route={data.route}
          />
        );
      }
      return renderFallback(sections);
    case "split_summary":
      return renderFallback(sections);
    case "finder":
      return <FinderSection sections={sections} />;
    case "leaderboard":
      return renderFallback(sections);
    case "streak":
      return renderFallback(sections);
    case "count":
      return (
        <CountSection
          sections={sections}
          metadata={data.result?.metadata}
          route={data.route}
        />
      );
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
          caveats={data.caveats}
        />
      );
    }
    if (data.result_status === "ok") {
      return (
        <NoResultDisplay
          reason="empty_sections"
          status={data.result_status}
          notes={data.notes}
          caveats={data.caveats}
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
          caveats={data.caveats}
        />
      );
    }
    return (
      <NoResultDisplay
        reason="empty_sections"
        status={data.result_status}
        notes={data.notes}
        caveats={data.caveats}
      />
    );
  }

  return <>{renderByQueryClass(data)}</>;
}
