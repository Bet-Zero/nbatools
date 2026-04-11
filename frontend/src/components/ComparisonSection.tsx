import type { SectionRow } from "../api/types";
import DataTable from "./DataTable";

interface Props {
  sections: Record<string, SectionRow[]>;
}

export default function ComparisonSection({ sections }: Props) {
  const summary = sections.summary;
  const comparison = sections.comparison;

  return (
    <>
      {summary && summary.length > 0 && (
        <div className="section">
          <div className="section-title">Players</div>
          <DataTable rows={summary} />
        </div>
      )}
      {comparison && comparison.length > 0 && (
        <div className="section">
          <div className="section-title">Comparison</div>
          <DataTable rows={comparison} highlight />
        </div>
      )}
    </>
  );
}
