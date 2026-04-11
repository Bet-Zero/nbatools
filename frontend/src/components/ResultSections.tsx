import type { QueryResponse } from "../api/types";
import DataTable from "./DataTable";

interface Props {
  data: QueryResponse;
}

/** Preferred section display order by query class. */
const SECTION_ORDER: Record<string, string[]> = {
  summary: ["summary", "by_season"],
  comparison: ["summary", "comparison"],
  split_summary: ["summary", "split_comparison"],
  finder: ["finder"],
  leaderboard: ["leaderboard"],
  streak: ["streak"],
};

/** Human-readable section labels. */
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

function orderedKeys(
  queryClass: string,
  sections: Record<string, unknown>,
): string[] {
  const preferred = SECTION_ORDER[queryClass] ?? [];
  const allKeys = Object.keys(sections);
  const out = [...preferred.filter((k) => k in sections)];
  for (const k of allKeys) {
    if (!out.includes(k)) out.push(k);
  }
  return out;
}

export default function ResultSections({ data }: Props) {
  const result = data.result;
  if (!result?.sections) {
    if (data.result_status === "no_result" || data.result_status === "error") {
      return (
        <div className="no-result">
          {data.result_reason ?? "No matching data found."}
        </div>
      );
    }
    return null;
  }

  const queryClass = result.query_class ?? "";
  const keys = orderedKeys(queryClass, result.sections);
  const rendered = keys.filter(
    (k) => result.sections[k] && result.sections[k].length > 0,
  );

  if (rendered.length === 0) {
    if (data.result_status !== "ok") {
      return (
        <div className="no-result">
          {data.result_reason ?? "No matching data found."}
        </div>
      );
    }
    return null;
  }

  return (
    <>
      {rendered.map((key) => (
        <div className="section" key={key}>
          <div className="section-title">{sectionLabel(key)}</div>
          <DataTable rows={result.sections[key]} />
        </div>
      ))}
    </>
  );
}
