import { type ReactNode } from "react";
import type { SectionRow } from "../api/types";
import {
  Avatar,
  DataTable as DataTablePrimitive,
  TeamBadge,
  type DataTableAlignment,
  type DataTableColumn,
} from "../design-system";
import { resolvePlayerIdentity } from "../lib/identity";
import { formatColHeader, formatValue } from "./tableFormatting";
import styles from "./DataTable.module.css";

interface Props {
  rows: SectionRow[];
  highlight?: boolean;
}

/** Column names that indicate a rank column. */
const RANK_COLS = new Set(["rank", "#"]);

/** Column names that indicate an entity (player/team) column. */
const ENTITY_COLS = new Set([
  "player_name",
  "player",
  "team",
  "team_name",
  "opponent",
]);

const PLAYER_COLS = new Set(["player_name", "player"]);
const TEAM_COLS = new Set(["team", "team_name", "opponent"]);

/** Check whether a column contains numeric values (sample first 5 rows). */
function isNumericCol(col: string, rows: SectionRow[]): boolean {
  for (let i = 0; i < Math.min(rows.length, 5); i++) {
    const v = rows[i][col];
    if (v !== null && v !== undefined) return typeof v === "number";
  }
  return false;
}

/** Determine the CSS class for a cell based on column name. */
function cellClass(col: string, rows: SectionRow[]): string {
  const lc = col.toLowerCase();
  if (RANK_COLS.has(lc)) return styles.rankCell;
  if (ENTITY_COLS.has(lc)) return styles.entityCell;
  if (isNumericCol(col, rows)) return styles.num;
  return "";
}

function columnAlignment(col: string, rows: SectionRow[]): DataTableAlignment {
  const lc = col.toLowerCase();
  if (RANK_COLS.has(lc)) return "center";
  if (isNumericCol(col, rows)) return "right";
  return "left";
}

function isTeamAbbreviation(value: string): boolean {
  return /^[A-Z]{2,4}$/.test(value);
}

function rowIdentityId(value: unknown): number | string | null {
  if (typeof value === "number" || typeof value === "string") return value;
  return null;
}

function renderEntityValue(
  value: unknown,
  col: string,
  row: SectionRow,
): ReactNode {
  const formatted = formatValue(value, col);
  if (value === null || value === undefined) return formatted;

  const lc = col.toLowerCase();
  if (PLAYER_COLS.has(lc)) {
    const playerIdentity = resolvePlayerIdentity({
      playerId: rowIdentityId(row.player_id),
      playerName: formatted,
    });
    return (
      <span className={styles.identityValue}>
        <Avatar
          name={playerIdentity.playerName ?? formatted}
          imageUrl={playerIdentity.headshotUrl}
          size="sm"
        />
        <span>{formatted}</span>
      </span>
    );
  }
  if (TEAM_COLS.has(lc)) {
    return (
      <TeamBadge
        abbreviation={isTeamAbbreviation(formatted) ? formatted : undefined}
        name={formatted}
        size="sm"
        showName={!isTeamAbbreviation(formatted)}
      />
    );
  }

  return formatted;
}

export default function DataTable({ rows, highlight = false }: Props) {
  if (!rows.length) return null;
  const columns: DataTableColumn<SectionRow>[] = Object.keys(rows[0]).map(
    (col) => ({
      key: col,
      header: formatColHeader(col),
      align: columnAlignment(col, rows),
      className: cellClass(col, rows),
      numeric: isNumericCol(col, rows),
      render: (row) => renderEntityValue(row[col], col, row),
    }),
  );

  return (
    <DataTablePrimitive
      columns={columns}
      rows={rows}
      highlight={highlight}
      getRowKey={(_, rowIndex) => rowIndex}
    />
  );
}
