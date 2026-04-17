# Structured Result Layer

Internal architecture doc for the structured result layer introduced in the
summary / comparison / split-summary result classes.

## What changed

Six commands now produce **structured result objects** before rendering any
text output:

| Command                | Result type          | Module                             |
| ---------------------- | -------------------- | ---------------------------------- |
| `player_game_summary`  | `SummaryResult`      | `commands/player_game_summary.py`  |
| `game_summary`         | `SummaryResult`      | `commands/game_summary.py`         |
| `player_compare`       | `ComparisonResult`   | `commands/player_compare.py`       |
| `team_compare`         | `ComparisonResult`   | `commands/team_compare.py`         |
| `player_split_summary` | `SplitSummaryResult` | `commands/player_split_summary.py` |
| `team_split_summary`   | `SplitSummaryResult` | `commands/team_split_summary.py`   |

When there are no matching games, `build_result()` returns a `NoResult`
sentinel instead.

## Where it lives

`src/nbatools/commands/structured_results.py`

Defines four dataclasses:

- **`NoResult`** — empty result sentinel
- **`SummaryResult`** — holds `summary` (DataFrame) + optional `by_season` (DataFrame)
- **`ComparisonResult`** — holds `summary` (DataFrame, 2 rows) + `comparison` (DataFrame, metric table)
- **`SplitSummaryResult`** — holds `summary` (DataFrame) + `split_comparison` (DataFrame, per-bucket rows)

## How it works

Each refactored command now exposes two functions:

```
build_result(**kwargs) -> SummaryResult | ComparisonResult | SplitSummaryResult | NoResult
run(**kwargs) -> None   # prints to stdout, delegates to build_result()
```

`run()` is unchanged externally — same signature, same stdout output.
Internally it calls `build_result()` and prints `result.to_labeled_text()`.

### Rendering methods

Every result object has three rendering methods:

| Method               | Returns          | Purpose                                                                                                                     |
| -------------------- | ---------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `to_labeled_text()`  | `str`            | Labeled CSV sections (SUMMARY / BY_SEASON / COMPARISON / SPLIT_COMPARISON) — identical to the old `print()` output          |
| `to_dict()`          | `dict`           | Machine-readable structure with `query_class`, `result_status`, `metadata`, `notes`, `sections` (list-of-dicts per section) |
| `to_sections_dict()` | `dict[str, str]` | Section-label → CSV-text mapping, for the pretty formatter                                                                  |

### Data flow

```
build_result()
  └─> SummaryResult / ComparisonResult / SplitSummaryResult / NoResult
        ├─ .to_labeled_text()  →  stdout (CLI raw output)
        ├─ .to_dict()          →  JSON export / future API
        └─ .to_sections_dict() →  pretty formatter input
```

## What is now structured-first

- **summary** (player_game_summary, game_summary)
- **comparison** (player_compare, team_compare)
- **split_summary** (player_split_summary, team_split_summary)

These commands produce real DataFrames in structured containers. All output
is derived from that structure.

## What remains text-first

- **finder** (player_game_finder, game_finder)
- **leaderboard** (season_leaders, season_team_leaders, top_player_games, top_team_games)
- **streak** (player_streak_finder, team_streak_finder)

These still print CSV text directly to stdout. They are candidates for future
structured-result passes.

## Compatibility

- `run()` functions have the same signature and produce identical stdout output
- All 313 pre-existing tests still pass
- Labeled section labels are preserved: SUMMARY, BY_SEASON, COMPARISON, SPLIT_COMPARISON
- The `format_output.py` pretty formatter, `wrap_raw_output()`, and export
  plumbing all work unchanged because `to_labeled_text()` matches the old format

## Tests

`tests/test_structured_results.py` — 39 tests covering:

- Unit tests for each result class (shape, labeled text, dict output, NaN handling)
- Integration tests proving `build_result()` returns the correct type for each command
- Round-trip tests proving `build_result().to_labeled_text() == run()` stdout output
- `to_dict()` contract tests (correct sections, correct data values)
- Pretty-output-from-structured tests
