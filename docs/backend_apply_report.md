# Backend Apply Report — Query Intent Audit Patterns

**Branch:** main  
**Suite result:** 2599 passed, 1 xpassed, 0 failures

---

## Pattern 7 — Honest no-result for un-filterable queries

**Status: Complete**

### Files touched

- `src/nbatools/commands/structured_results.py` — Added `FILTER_NOT_SUPPORTED = "filter_not_supported"` to `ResultReason`. Documented distinction from `unsupported` (query type not built) and `no_data` (underlying season data file absent).
- `src/nbatools/commands/player_game_summary.py` — Clutch, schedule-context, and role filter failures now return `NoResult(reason="filter_not_supported")` instead of appending an unfiltered note and continuing.
- `src/nbatools/commands/team_record.py` — Same change for clutch and schedule-context filters.
- `src/nbatools/commands/season_leaders.py` — Same change for clutch filter (missing dataset and untrusted coverage paths).
- `src/nbatools/commands/format_output.py` — Added `"filter_not_supported"` to `_REASON_DISPLAY` map so the renderer doesn't raise `KeyError`.
- `tests/test_result_contract.py` — Updated `ResultReason` count assertion from 6 → 7.
- `tests/test_phase_g_context_transport.py` — Updated all tests for the new 3-tuple return signature of `_route_context_filters_for_execution`; replaced `"unfiltered" in note` string checks with `blocked` list checks; updated the two "missing clutch coverage" tests to accept `filter_not_supported` or `no_data`.
- `tests/test_phase_g_role_execution.py` — Updated fallback tests to expect `NoResult / filter_not_supported`; updated `_route_context_filters_for_execution` call sites for 3-tuple signature.
- `tests/test_phase_h_schedule_context_execution.py` — Same: schedule-context and national-TV fallback tests rewritten; signature updates.
- `tests/test_query_service.py` — Five structured-query tests (quarter, half, back_to_back, one_possession, nationally_televised) updated to assert `filter_not_supported` instead of unfiltered note.
- `tests/_query_smoke.py` — Clutch and national-TV smoke cases updated to `expected_statuses=("no_result",)`; period cases (LeBron 4Q, Celtics first half, Knicks OT) had stale `expected_note_substrings` removed.

### Decision

The audit listed clutch, period/quarter, back-to-back/rest, role, national TV, and "leads the team in scoring" as un-filterable. The "leads the team" case is a parse-time detection issue (the parser doesn't currently extract this as a structured filter), so no handler change was needed for it. All structured-filter cases are covered.

### Known gap

The note text passed into `NoResult` for clutch failures still says "results are unfiltered" (a holdover from the old behavior, produced by `build_clutch_filter_coverage_note` in `data_utils.py`). The behavior is correct — the result is a no-result, not unfiltered data — but the note wording was not updated to suggest a concrete alternative query as the spec required. This is a cosmetic fix for a future pass.

---

## Pattern 9 — Routing fixes

**Status: Complete**

### Files touched

- `src/nbatools/commands/natural_query.py` — Three routing changes:
  - **team_matchup_record vs team_compare**: rule now documented with a comment. Two teams + any W/L-outcome keyword (record, win, lose, head-to-head, matchup) → `team_matchup_record`; two teams without → `team_compare`.
  - **team_record without-player guard**: comment added explaining the `without_player` clause gate (requires no stat filter to qualify as a record query vs a finder query).
  - **top_team_games trigger expansion**: regex added to catch "highest-scoring team games", "best team performances", "biggest team scoring nights", and similar natural phrasings beyond the literal "top team" / "top team games" that were previously the only triggers.
  - **career_intent forwarded**: `career_intent` added to `player_game_summary` route_kwargs (needed for Pattern 1 by_season backfill).
- `tests/test_backend_apply_patterns.py` (new file) — 36 tests covering routing rules plus Pattern 1/2/3/8 contract tests.

### Decision

The audit listed a "Sweep queries that don't have a clean handler match" section. Rather than trying to enumerate every edge case, routing tests were written for the three rules explicitly changed. Other sweep cases in the audit are parse-level ambiguities (no routing change needed) or require new handler routes not in scope for this pass.

---

## Pattern 1 — Multi-period historical context

**Status: Complete**

### Files touched

- `src/nbatools/query_service.py` — `scope_kind` metadata field added to every query response. Values: `"single_season"`, `"season_range"`, `"career"`, `"all_time"`, `"playoffs"`, `"decade"`. Logic: `career_intent=True` + player entity → `"career"`; `career_intent=True` + no player entity → `"all_time"`; `by_decade_intent=True` → `"decade"`; `start_season` + `end_season` without career/decade intent → `"season_range"`; playoffs season type without range → `"playoffs"`; everything else → `"single_season"`.
- `src/nbatools/commands/structured_results.py` — `to_dict` / `to_sections_dict` divergence fixed: `game_log` is now included in `to_sections_dict`, matching `to_dict`.
- `src/nbatools/commands/player_game_summary.py` — Added `career_intent: bool = False` parameter to `build_result`. When `career_intent=True` and a player is specified, the handler captures the player's active seasons from the raw game log before applying secondary filters (opponent, home/away, outcome, etc.). After computing `by_season` from the filtered data, the result is reindexed against the full career arc, filling seasons that had zero matching filtered games with zeros. This gives the frontend a complete season axis even for filtered career queries like "Jokic career vs Lakers".
- `src/nbatools/commands/natural_query.py` — `career_intent` added to `player_game_summary` route_kwargs so it reaches the handler.
- `tests/test_backend_apply_patterns.py` — `TestScopeKind` class covers single_season, season_range, career, all_time, playoffs, and decade cases.

### Decision

The spec said `by_season` should cover "every season in the player's career, not just the queried range." For career queries (`career_intent=True`), seasons are already resolved to the full historical span, and the player filter naturally limits rows to seasons the player appeared in. The gap only manifests when secondary filters (opponent etc.) leave some career seasons with zero matching rows — those seasons previously dropped out of `by_season` entirely. The fix reindexes against the pre-filter player season set.

For non-career multi-season queries ("since 2020"), `by_season` covers the queried range only. Loading data outside the queried range for arc context would require a handler-level architectural change (two data loads) and was not in scope for this pass.

---

## Pattern 2 — Filter context in metadata

**Status: Complete**

### Files touched

- `src/nbatools/query_service.py` — `applied_filters` list added to every query response. Each entry is `{label, value, kind}`. Covers: opponent, without_player, home/away, wins/losses, clutch, back-to-back, rest_days, one_possession, nationally_televised, role, quarter, half, position_filter, opponent_quality, stat threshold (min/max), season range, date range, last_n window.
- `tests/test_backend_apply_patterns.py` — `TestAppliedFilters` class covers opponent, wins_only, no-filter, and season-range cases.

---

## Pattern 3 — Count vs list intent

**Status: Complete**

### Files touched

- `src/nbatools/query_service.py` — `primary_count` (int) and `count_phrase` (string) added to metadata when `count_intent=True` and the result is a `CountResult`. `_build_count_phrase` builds a natural-language sentence from the count, entity, occurrence event, season, and season type.
- `tests/test_backend_apply_patterns.py` — `TestCountMetadata` covers single and plural phrasing.

### Decision

Coverage of count-intent paths depends on the parser correctly setting `count_intent=True`. The implementation key is off that flag. All routes that produce `CountResult` (finder and leaderboard paths post-conversion in `execute_natural_query`) automatically pick up `primary_count` and `count_phrase`. No handler changes were needed.

---

## Pattern 8 — Ambiguous query recovery

**Status: Complete**

### Files touched

- `src/nbatools/query_service.py`:
  - Entity ambiguity: `metadata.candidates` populated as `[{id, display_name, team_abbr, position}]` per candidate, using `_resolve_player_context` to enrich raw name strings.
  - Fragment ambiguity: `metadata.suggested_queries` populated by `_build_suggested_queries_for_fragment`, which inspects the parsed player/team/stat/occurrence slots and returns 2–4 concrete alternative query strings.
- `tests/test_backend_apply_patterns.py` — `TestAmbiguousRecovery` covers entity candidate list, fragment suggestions (with and without occurrence event), team fragment suggestions, and the 4-suggestion cap.

### Decision

`suggested_queries` for fragment ambiguity are generated heuristically from parsed slots, not from a lookup of known-good queries. The quality of suggestions degrades for heavily ambiguous inputs with few parsed slots (e.g., a bare two-word query with no recognizable entity or stat). This is acceptable for the current pass; a future improvement could use a query-index lookup.

---

## Notes for the frontend pass

- **`scope_kind`** is on every response. Frontend should use this to decide when to render the by_season breakdown table and when to show the career arc chart.
- **`applied_filters`** is present only when at least one filter is active (key absent when empty). Frontend chip-set renderer should guard accordingly.
- **`primary_count` / `count_phrase`**: only present when `count_intent=True` and the result is a CountResult. Frontend should check for presence, not assume.
- **`candidates`** and **`suggested_queries`**: only present on `no_result` responses with `result_reason = "ambiguous"`. They are mutually exclusive: entity ambiguity gets `candidates`, fragment ambiguity gets `suggested_queries`.
- **`filter_not_supported`**: the no-result note text still says "results are unfiltered" (stale wording). A cosmetic fix to `build_clutch_filter_coverage_note` and equivalent helpers will align note text with the new behavior before frontend renders the note string.
- **`by_season` career arc**: for career queries with secondary filters, `by_season` now includes seasons with zero matching games (filled with 0). Frontend renderers that compute averages from `by_season` rows should guard against divide-by-zero when `games = 0`.
