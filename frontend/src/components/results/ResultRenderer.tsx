import type { QueryResponse } from "../../api/types";
import NoResultDisplay from "../NoResultDisplay";
import { routeToPattern, type PatternConfig } from "./config/routeToPattern";
import FallbackTableResult from "./patterns/FallbackTableResult";
import ResultShell from "./primitives/ResultShell";

interface Props {
  data: QueryResponse;
}

/**
 * The single entry point for rendering a query result. Reads the
 * route, asks `routeToPattern` which patterns to compose, and stacks
 * them vertically inside a `ResultShell`.
 *
 * Replaces `components/ResultSections.tsx`. The old per-route section
 * components are still in the tree but no longer reachable from this
 * renderer; they will be deleted as their routes migrate to dedicated
 * patterns.
 */
export default function ResultRenderer({ data }: Props) {
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

  const patterns = routeToPattern(data);

  return (
    <ResultShell>
      {patterns.map((pattern, index) => (
        <PatternBlock key={`${pattern.type}-${index}`} data={data} pattern={pattern} />
      ))}
    </ResultShell>
  );
}

interface PatternBlockProps {
  data: QueryResponse;
  pattern: PatternConfig;
}

function PatternBlock({ data, pattern }: PatternBlockProps) {
  switch (pattern.type) {
    case "fallback_table":
      return <FallbackTableResult data={data} />;
    default:
      // Exhaustiveness fallback: future PatternConfig variants safely
      // render through the fallback until their pattern is wired in.
      return <FallbackTableResult data={data} />;
  }
}
