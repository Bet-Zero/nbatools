import type { SectionRow } from "../api/types";
import DataTable from "./DataTable";

interface Props {
  sections: Record<string, SectionRow[]>;
}

export default function SummarySection({ sections }: Props) {
  const summary = sections.summary;
  const bySeason = sections.by_season;

  return (
    <>
      {summary && summary.length > 0 && (
        <div className="section">
          <div className="section-title">Summary</div>
          <DataTable rows={summary} />
        </div>
      )}
      {bySeason && bySeason.length > 0 && (
        <div className="section">
          <div className="section-title">By Season</div>
          <DataTable rows={bySeason} />
        </div>
      )}
    </>
  );
}
