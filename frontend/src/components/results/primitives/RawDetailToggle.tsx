import { useId, useState } from "react";
import type { SectionRow } from "../../../api/types";
import { Button } from "../../../design-system";
import DataTable from "../../DataTable";
import styles from "./RawDetailToggle.module.css";

interface Props {
  title: string;
  rows: SectionRow[];
  highlight?: boolean;
  hiddenColumns?: Set<string>;
  defaultOpen?: boolean;
  collapsedLabel?: string;
  expandedLabel?: string;
}

export default function RawDetailToggle({
  title,
  rows,
  highlight = false,
  hiddenColumns,
  defaultOpen = false,
  collapsedLabel = "Show raw table",
  expandedLabel = "Hide raw table",
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();

  if (rows.length === 0) return null;

  return (
    <section className={styles.rawDetail} aria-label={title}>
      <div className={styles.header}>
        <div className={styles.titleGroup}>
          <h3 className={styles.title}>{title}</h3>
          <span className={styles.count}>
            {rows.length} {rows.length === 1 ? "row" : "rows"}
          </span>
        </div>
        <Button
          type="button"
          onClick={() => setOpen((value) => !value)}
          size="sm"
          variant="secondary"
          aria-expanded={open}
          aria-controls={panelId}
        >
          {open ? expandedLabel : collapsedLabel}
        </Button>
      </div>
      {open && (
        <div className={styles.tablePanel} id={panelId}>
          <DataTable
            rows={rows}
            highlight={highlight}
            hiddenColumns={hiddenColumns}
          />
        </div>
      )}
    </section>
  );
}
