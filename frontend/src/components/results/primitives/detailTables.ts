import type { SectionRow } from "../../../api/types";
import type { ResultTableColumn } from "./ResultTable";

const DEFAULT_IGNORED_DETAIL_KEYS = new Set([
  "game_id",
  "player_id",
  "team_id",
  "opponent_team_id",
  "winner_team_id",
  "start_game_id",
  "end_game_id",
  "rank",
  "route",
  "query_text",
  "season_start",
  "season_end",
  "start_season",
  "end_season",
]);

export function resultTableSourceKeys<Row>(
  columns: Array<ResultTableColumn<Row>>,
): Set<string> {
  const keys = new Set<string>();
  for (const column of columns) {
    keys.add(normalizeKey(column.key));
    for (const sourceKey of column.sourceKeys ?? []) {
      keys.add(normalizeKey(sourceKey));
    }
  }
  return keys;
}

export function rowsHaveAdditionalDetailFields(
  rows: SectionRow[],
  displayedKeys: Iterable<string>,
  ignoredKeys: Iterable<string> = [],
): boolean {
  const displayed = new Set(Array.from(displayedKeys, normalizeKey));
  const ignored = new Set(DEFAULT_IGNORED_DETAIL_KEYS);
  for (const key of ignoredKeys) {
    ignored.add(normalizeKey(key));
  }

  for (const row of rows) {
    for (const [key, value] of Object.entries(row)) {
      const normalized = normalizeKey(key);
      if (!hasValue(value)) continue;
      if (ignored.has(normalized)) continue;
      if (displayed.has(normalized)) continue;
      return true;
    }
  }
  return false;
}

function normalizeKey(key: string): string {
  return key.trim().toLowerCase();
}

function hasValue(value: unknown): boolean {
  return value !== null && value !== undefined && value !== "";
}
