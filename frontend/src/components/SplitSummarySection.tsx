import type { SectionRow } from "../api/types";
import DataTable from "./DataTable";

interface Props {
  sections: Record<string, SectionRow[]>;
}

export default function SplitSummarySection({ sections }: Props) {
  const summary = sections.summary;
  const splitComparison = sections.split_comparison;

  return (
    <>
      {summary && summary.length > 0 && (
        <div className="section">
          <div className="section-title">Summary</div>
          <DataTable rows={summary} />
        </div>
      )}
      {splitComparison && splitComparison.length > 0 && (
        <div className="section">
          <div className="section-title">Split Comparison</div>
          <DataTable rows={splitComparison} highlight />
        </div>
      )}
    </>
  );
}
