import type { SectionRow } from "../api/types";
import DataTable from "./DataTable";

interface Props {
  sections: Record<string, SectionRow[]>;
}

export default function FinderSection({ sections }: Props) {
  const finder = sections.finder;
  if (!finder || finder.length === 0) return null;

  return (
    <div className="section">
      <div className="section-title">
        Matching Games
        <span className="section-count">
          {finder.length} game{finder.length !== 1 ? "s" : ""}
        </span>
      </div>
      <DataTable rows={finder} />
    </div>
  );
}
