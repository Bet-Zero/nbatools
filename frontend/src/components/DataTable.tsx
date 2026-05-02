import { type CSSProperties, type ReactNode } from "react";
import type { SectionRow } from "../api/types";
import {
  Avatar,
  DataTable as DataTablePrimitive,
  TeamBadge,
  type DataTableAlignment,
  type DataTableColumn,
} from "../design-system";
import { resolvePlayerIdentity, resolveTeamIdentity } from "../lib/identity";
import { formatColHeader, formatValue } from "./tableFormatting";
import styles from "./DataTable.module.css";

interface Props {
  rows: SectionRow[];
  highlight?: boolean;
  hiddenColumns?: Iterable<string>;
}

/** Column names that indicate a rank column. */
const RANK_COLS = new Set(["rank", "#"]);

const PLAYER_COLS = new Set(["player_name", "player"]);
const TEAM_COLS = new Set([
  "team",
  "team_name",
  "team_abbr",
  "opponent",
  "opponent_team_name",
  "opponent_team_abbr",
]);

/** Column names that indicate an entity (player/team) column. */
const ENTITY_COLS = new Set([...PLAYER_COLS, ...TEAM_COLS]);

const PRIMARY_ENTITY_COL_PREFERENCE = [
  "player_name",
  "player",
  "team_name",
  "team",
  "team_abbr",
  "entity",
  "name",
  "lineup",
  "lineup_members",
  "members",
];

const COLLAPSIBLE_IDENTITY_GROUPS = [
  ["player_name", "player"],
  ["team_name", "team", "team_abbr"],
];

function normalizeColumnName(column: string): string {
  return column.toLowerCase();
}

function selectVisibleColumns(
  columns: string[],
  hiddenColumns: Iterable<string> | undefined,
): string[] {
  if (!hiddenColumns) return columns;

  const hidden = new Set(
    Array.from(hiddenColumns, (column) => normalizeColumnName(column)),
  );
  const selected = new Set(
    columns.filter((column) => !hidden.has(normalizeColumnName(column))),
  );

  for (const group of COLLAPSIBLE_IDENTITY_GROUPS) {
    const visibleGroupColumns = columns.filter(
      (column) =>
        selected.has(column) && group.includes(normalizeColumnName(column)),
    );
    if (visibleGroupColumns.length <= 1) continue;

    const preferred = group.find((columnName) =>
      visibleGroupColumns.some(
        (column) => normalizeColumnName(column) === columnName,
      ),
    );
    if (!preferred) continue;

    for (const column of visibleGroupColumns) {
      if (normalizeColumnName(column) !== preferred) {
        selected.delete(column);
      }
    }
  }

  const hasVisiblePrimaryEntityColumn = columns.some(
    (column) =>
      selected.has(column) &&
      PRIMARY_ENTITY_COL_PREFERENCE.includes(normalizeColumnName(column)),
  );

  if (!hasVisiblePrimaryEntityColumn) {
    const fallback = PRIMARY_ENTITY_COL_PREFERENCE.find((columnName) =>
      columns.some((column) => normalizeColumnName(column) === columnName),
    );
    if (fallback) {
      const fallbackColumn = columns.find(
        (column) => normalizeColumnName(column) === fallback,
      );
      if (fallbackColumn) selected.add(fallbackColumn);
    }
  }

  return columns.filter((column) => selected.has(column));
}

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

function rowText(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function teamIdentityForColumn(
  col: string,
  row: SectionRow,
  formatted: string,
) {
  const lc = col.toLowerCase();
  const isOpponent = lc.startsWith("opponent");
  const teamId = rowIdentityId(
    isOpponent ? row.opponent_team_id : row.team_id,
  );
  const teamAbbr =
    rowText(isOpponent ? row.opponent_team_abbr : row.team_abbr) ??
    (isTeamAbbreviation(formatted) ? formatted : null);
  const teamName =
    rowText(isOpponent ? row.opponent_team_name : row.team_name) ?? formatted;

  return resolveTeamIdentity({
    teamId,
    teamAbbr,
    teamName,
  });
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
    const teamIdentity = teamIdentityForColumn(col, row, formatted);
    return (
      <TeamBadge
        abbreviation={
          teamIdentity.teamAbbr ??
          (isTeamAbbreviation(formatted) ? formatted : undefined)
        }
        name={teamIdentity.teamName ?? formatted}
        logoUrl={teamIdentity.logoUrl}
        size="sm"
        showName={!isTeamAbbreviation(formatted)}
        style={(teamIdentity.styleVars ?? undefined) as
          | CSSProperties
          | undefined}
      />
    );
  }

  return formatted;
}

export default function DataTable({
  rows,
  highlight = false,
  hiddenColumns,
}: Props) {
  if (!rows.length) return null;
  const visibleColumns = selectVisibleColumns(Object.keys(rows[0]), hiddenColumns);
  const columns: DataTableColumn<SectionRow>[] = visibleColumns.map((col) => ({
    key: col,
    header: formatColHeader(col),
    align: columnAlignment(col, rows),
    className: cellClass(col, rows),
    numeric: isNumericCol(col, rows),
    render: (row) => renderEntityValue(row[col], col, row),
  }));

  return (
    <DataTablePrimitive
      columns={columns}
      rows={rows}
      highlight={highlight}
      getRowKey={(_, rowIndex) => rowIndex}
    />
  );
}
