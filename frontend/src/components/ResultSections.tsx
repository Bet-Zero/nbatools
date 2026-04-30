import type { QueryResponse, SectionRow } from "../api/types";
import { Card, SectionHeader } from "../design-system";
import ComparisonSection from "./ComparisonSection";
import CountSection from "./CountSection";
import DataTable from "./DataTable";
import FinderSection from "./FinderSection";
import HeadToHeadSection from "./HeadToHeadSection";
import LeaderboardSection from "./LeaderboardSection";
import NoResultDisplay from "./NoResultDisplay";
import OccurrenceLeaderboardSection from "./OccurrenceLeaderboardSection";
import PlayerComparisonSection from "./PlayerComparisonSection";
import PlayerGameFinderSection from "./PlayerGameFinderSection";
import PlayoffSection from "./PlayoffSection";
import PlayerSummarySection from "./PlayerSummarySection";
import SplitSummaryCardsSection from "./SplitSummaryCardsSection";
import SplitSummarySection from "./SplitSummarySection";
import StreakSection from "./StreakSection";
import SummarySection from "./SummarySection";
import TeamRecordSection from "./TeamRecordSection";
import TeamSummarySection from "./TeamSummarySection";
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

function isPlayerGameFinder(data: QueryResponse): boolean {
  return (
    data.route === "player_game_finder" ||
    data.result?.metadata?.route === "player_game_finder"
  );
}

function isTeamSummary(data: QueryResponse): boolean {
  const route = data.route ?? data.result?.metadata?.route;
  return route === "game_summary";
}

function isTeamRecord(data: QueryResponse): boolean {
  const route = data.route ?? data.result?.metadata?.route;
  return route === "team_record";
}

function isTeamMatchupRecord(data: QueryResponse): boolean {
  const route = data.route ?? data.result?.metadata?.route;
  return route === "team_matchup_record";
}

function isOwnedSplitSummary(data: QueryResponse): boolean {
  const route = data.route ?? data.result?.metadata?.route;
  return route === "team_split_summary" || route === "player_split_summary";
}

function isOwnedStreak(data: QueryResponse): boolean {
  const route = data.route ?? data.result?.metadata?.route;
  return route === "player_streak_finder" || route === "team_streak_finder";
}

function isOccurrenceLeaderboard(data: QueryResponse): boolean {
  const route = data.route ?? data.result?.metadata?.route;
  return (
    route === "player_occurrence_leaders" ||
    route === "team_occurrence_leaders"
  );
}

function isPlayoffRoute(data: QueryResponse): boolean {
  const route = data.route ?? data.result?.metadata?.route;
  return (
    route === "playoff_history" ||
    route === "playoff_appearances" ||
    route === "playoff_matchup_history" ||
    route === "playoff_round_record"
  );
}

function isHeadToHeadComparison(data: QueryResponse): boolean {
  const route = data.route ?? data.result?.metadata?.route;
  if (route === "team_matchup_record" || route === "matchup_by_decade") {
    return true;
  }
  if (route === "player_compare" || route === "team_compare") {
    return data.result?.metadata?.head_to_head_used === true;
  }
  return false;
}

function renderByQueryClass(data: QueryResponse): React.ReactNode {
  const queryClass = data.result?.query_class ?? "";
  const sections = data.result?.sections ?? {};

  switch (queryClass) {
    case "summary":
      if (isPlayoffRoute(data)) {
        return (
          <PlayoffSection
            sections={sections}
            metadata={data.result?.metadata}
            queryClass={queryClass}
            route={data.route}
          />
        );
      }
      if (isPlayerSummary(data)) {
        return (
          <PlayerSummarySection
            sections={sections}
            metadata={data.result?.metadata}
          />
        );
      }
      if (isTeamSummary(data)) {
        return (
          <TeamSummarySection
            sections={sections}
            metadata={data.result?.metadata}
            route={data.route}
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
      if (isPlayoffRoute(data)) {
        return (
          <PlayoffSection
            sections={sections}
            metadata={data.result?.metadata}
            queryClass={queryClass}
            route={data.route}
          />
        );
      }
      if (isHeadToHeadComparison(data)) {
        return (
          <HeadToHeadSection
            sections={sections}
            metadata={data.result?.metadata}
            route={data.route}
          />
        );
      }
      if (isPlayerComparison(data)) {
        return (
          <PlayerComparisonSection
            sections={sections}
            metadata={data.result?.metadata}
          />
        );
      }
      if (isTeamMatchupRecord(data)) {
        return (
          <TeamRecordSection
            sections={sections}
            metadata={data.result?.metadata}
            route={data.route}
          />
        );
      }
      return <ComparisonSection sections={sections} />;
    case "split_summary":
      if (isOwnedSplitSummary(data)) {
        return (
          <SplitSummaryCardsSection
            sections={sections}
            metadata={data.result?.metadata}
            route={data.route}
          />
        );
      }
      return <SplitSummarySection sections={sections} />;
    case "finder":
      if (isPlayerGameFinder(data)) {
        return <PlayerGameFinderSection sections={sections} />;
      }
      return <FinderSection sections={sections} />;
    case "leaderboard":
      if (isOccurrenceLeaderboard(data)) {
        return (
          <OccurrenceLeaderboardSection
            sections={sections}
            metadata={data.result?.metadata}
          />
        );
      }
      if (isPlayoffRoute(data)) {
        return (
          <PlayoffSection
            sections={sections}
            metadata={data.result?.metadata}
            queryClass={queryClass}
            route={data.route}
          />
        );
      }
      return <LeaderboardSection sections={sections} />;
    case "streak":
      if (isOwnedStreak(data)) {
        return (
          <StreakSection
            sections={sections}
            metadata={data.result?.metadata}
            route={data.route}
          />
        );
      }
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
