import { type Key, type ReactNode } from "react";
import styles from "./DataTable.module.css";

export type DataTableAlignment = "left" | "right" | "center";

export interface DataTableColumn<Row> {
  key: string;
  header: ReactNode;
  align?: DataTableAlignment;
  className?: string;
  headerClassName?: string;
  cellClassName?: string;
  numeric?: boolean;
  render: (row: Row, rowIndex: number) => ReactNode;
}

export interface DataTableProps<Row> {
  columns: DataTableColumn<Row>[];
  rows: Row[];
  getRowKey?: (row: Row, rowIndex: number) => Key;
  highlight?: boolean;
  emptyState?: ReactNode;
  className?: string;
}

function joinClassNames(...classNames: Array<string | false | undefined>) {
  return classNames.filter(Boolean).join(" ");
}

const ALIGN_CLASS: Record<DataTableAlignment, string> = {
  left: styles.alignLeft,
  right: styles.alignRight,
  center: styles.alignCenter,
};

export function DataTable<Row>({
  columns,
  rows,
  getRowKey,
  highlight = false,
  emptyState = null,
  className,
}: DataTableProps<Row>) {
  if (rows.length === 0) {
    return emptyState ? <div className={styles.empty}>{emptyState}</div> : null;
  }

  return (
    <div className={joinClassNames(styles.tableScroll, className)}>
      <table
        className={joinClassNames(styles.table, highlight && styles.highlight)}
      >
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className={joinClassNames(
                  ALIGN_CLASS[column.align ?? "left"],
                  column.numeric && styles.numeric,
                  column.className,
                  column.headerClassName,
                )}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={getRowKey ? getRowKey(row, rowIndex) : rowIndex}>
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={joinClassNames(
                    ALIGN_CLASS[column.align ?? "left"],
                    column.numeric && styles.numeric,
                    column.className,
                    column.cellClassName,
                  )}
                >
                  {column.render(row, rowIndex)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
