import type { QueryResponse } from "../../api/types";
import NoResultDisplay from "../NoResultDisplay";
import { routeToPattern, type PatternConfig } from "./config/routeToPattern";
import ComparisonResult from "./patterns/ComparisonResult";
import EntitySummaryResult from "./patterns/EntitySummaryResult";
import FallbackTableResult from "./patterns/FallbackTableResult";
import GameLogResult from "./patterns/GameLogResult";
import LeaderboardResult from "./patterns/LeaderboardResult";
import PlayoffHistoryResult from "./patterns/PlayoffHistoryResult";
import RecordResult from "./patterns/RecordResult";
import RollingStretchResult from "./patterns/RollingStretchResult";
import SplitResult from "./patterns/SplitResult";
import StreakResult from "./patterns/StreakResult";
import TopPerformancesResult from "./patterns/TopPerformancesResult";
import ResultShell from "./primitives/ResultShell";

type ResultDisplayMode = "product" | "review";

interface Props {
  data: QueryResponse;
  displayMode?: ResultDisplayMode;
}

/**
 * The single entry point for rendering a query result. Reads the
 * route, asks `routeToPattern` which patterns to compose, and stacks
 * them vertically inside a `ResultShell`.
 *
 * This is the only route-aware result display entry point; route-specific
 * presentation lives in reusable pattern components under `patterns/`.
 */
export default function ResultRenderer({
  data,
  displayMode = "product",
}: Props) {
  const result = data.result;
  const noResultNotes = [...data.notes, ...(data.result?.notes ?? [])];
  const noResultCaveats = [...data.caveats, ...(data.result?.caveats ?? [])];

  if (!result?.sections || Object.keys(result.sections).length === 0) {
    if (data.result_status === "no_result" || data.result_status === "error") {
      return (
        <NoResultDisplay
          reason={data.result_reason}
          status={data.result_status}
          metadata={data.result?.metadata}
          notes={noResultNotes}
          caveats={noResultCaveats}
        />
      );
    }
    if (data.result_status === "ok") {
      return (
        <NoResultDisplay
          reason="empty_sections"
          status={data.result_status}
          metadata={data.result?.metadata}
          notes={noResultNotes}
          caveats={noResultCaveats}
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
          metadata={data.result?.metadata}
          notes={noResultNotes}
          caveats={noResultCaveats}
        />
      );
    }
    return (
      <NoResultDisplay
        reason="empty_sections"
        status={data.result_status}
        metadata={data.result?.metadata}
        notes={noResultNotes}
        caveats={noResultCaveats}
      />
    );
  }

  const patterns = routeToPattern(data);

  return (
    <ResultShell>
      {patterns.map((pattern, index) => (
        <PatternBlock
          key={`${pattern.type}-${index}`}
          data={data}
          pattern={pattern}
          displayMode={displayMode}
        />
      ))}
    </ResultShell>
  );
}

interface PatternBlockProps {
  data: QueryResponse;
  pattern: PatternConfig;
  displayMode: ResultDisplayMode;
}

function PatternBlock({ data, pattern, displayMode }: PatternBlockProps) {
  switch (pattern.type) {
    case "entity_summary":
      return (
        <EntitySummaryResult data={data} sectionKey={pattern.sectionKey} />
      );
    case "game_log":
      return (
        <GameLogResult
          data={data}
          sectionKey={pattern.sectionKey}
          summaryKey={pattern.summaryKey}
          fallbackSectionKey={pattern.fallbackSectionKey}
          mode={pattern.mode}
          metricKey={pattern.metricKey}
          preserveOrder={pattern.preserveOrder}
          showSummaryStrip={pattern.showSummaryStrip}
          rawDetailTitle={pattern.rawDetailTitle}
          detailSectionKeys={pattern.detailSectionKeys}
          displayMode={displayMode}
        />
      );
    case "leaderboard":
      return (
        <LeaderboardResult
          data={data}
          sectionKey={pattern.sectionKey}
          metricKey={pattern.metricKey}
          metricLabel={pattern.metricLabel}
          sentenceMetricLabel={pattern.sentenceMetricLabel}
          valueSuffix={pattern.valueSuffix}
          verb={pattern.verb}
        />
      );
    case "top_performances":
      return (
        <TopPerformancesResult
          data={data}
          sectionKey={pattern.sectionKey}
          subject={pattern.subject}
        />
      );
    case "rolling_stretch":
      return (
        <RollingStretchResult data={data} sectionKey={pattern.sectionKey} />
      );
    case "split":
      return (
        <SplitResult
          data={data}
          sectionKey={pattern.sectionKey}
          summaryKey={pattern.summaryKey}
          subject={pattern.subject}
          bucketKey={pattern.bucketKey}
          splitLabelOverride={pattern.splitLabelOverride}
          primaryDetailTitle={pattern.primaryDetailTitle}
          summaryDetailTitle={pattern.summaryDetailTitle}
        />
      );
    case "streak":
      return <StreakResult data={data} sectionKey={pattern.sectionKey} />;
    case "playoff_history":
      return <PlayoffHistoryResult data={data} mode={pattern.mode} />;
    case "comparison":
      return (
        <ComparisonResult
          data={data}
          subject={pattern.subject}
          headToHead={pattern.headToHead}
        />
      );
    case "record":
      return <RecordResult data={data} mode={pattern.mode} />;
    case "fallback_table":
      return <FallbackTableResult data={data} />;
    default:
      // Exhaustiveness fallback: future PatternConfig variants safely
      // render through the fallback until their pattern is wired in.
      return <FallbackTableResult data={data} />;
  }
}
