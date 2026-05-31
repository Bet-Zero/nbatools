# Public Query Acceptance Wave 2D — Typo-Tolerant Player Decision Return Package

## Product decision

**V1 does not ship fuzzy typo-tolerant player resolution.**

Misspelled first-name fragments must not silently correct to a dominant player when
resolution would happen only through last-name/nickname aliases (`durant`, `curry`).
Exact aliases, full names, and intentional shorthand (`steph`, `durant`, `LeBron`)
remain unchanged.

**Deferred to V2:** edit-distance / fuzzy player matching and an explicit product
policy for intentional typo correction.

## Behavior before / after

| Query | Before | After |
|---|---|---|
| `LeBron vs Kevn Durant comparison` | `player_compare` / `ok` (silent Kevin Durant) | `player_compare` / `no_result` / `filter_not_supported`; `unsupported_filters=["unresolved_player"]`; empty sections |
| `Stephn Curry averages this season` | `player_game_summary` / `ok` (silent Stephen Curry) | `player_game_summary` / `no_result` / `filter_not_supported`; `unsupported_filters=["unresolved_player"]`; empty sections |
| `LeBron James vs Kevin Durant comparison` | `player_compare` / `ok` | unchanged (`player_compare` / `ok`) |
| `Steph Curry averages this season` | `player_game_summary` / `ok` | unchanged (`player_game_summary` / `ok`) |
| `Jokic home vs away this season` | `player_split_summary` / `ok` | unchanged (split guard excludes home/away `vs` phrasing) |
| `LeBron stats vs Kevin Durant` | `player_game_finder` / `ok` | unchanged (opponent-player context excluded) |

## Exact cases resolved

- `pqa_comparison_typo_kevn_durant` — `LeBron vs Kevn Durant comparison`
- `pqa_typo_synonym_stephn_averages` — `Stephn Curry averages this season`

Duplicate preflight ID `pqa_typo_partial_kevn_comparison` remains covered by the
comparison case above; not duplicated in the slice.

## Files changed

| File | Change |
|---|---|
| `src/nbatools/commands/entity_resolution.py` | `allowed_player_reference_tokens()`, `phrase_has_partial_nickname_player_typo()` |
| `src/nbatools/commands/_matchup_utils.py` | Narrow comparison/summary typo detectors; split/on-off/opponent exclusions |
| `src/nbatools/commands/natural_query.py` | `_unresolved_player_typo_boundary()` routing guard |
| `qa/raw_query_answer_corpus.yaml` | Two Wave 2D acceptance cases with metadata |
| `qa/harness_slices/public_query_acceptance.yaml` | Added both case IDs |
| `tests/test_natural_query_parser.py` | Parametrized boundary tests for both queries |
| `docs/planning/raw-product/PUBLIC_QUERY_ACCEPTANCE_COVERAGE_PREFLIGHT.md` | Wave 2D section + matrix updates |
| `docs/reference/query_catalog.md` | V1 typo-correction not supported note |

## Tests / corpus / slices changed

- **Corpus:** `pqa_comparison_typo_kevn_durant`, `pqa_typo_synonym_stephn_averages`
  with `acceptance.family`, `acceptance.variant`, `acceptance.no_broad_fallback=true`
- **Slice:** `public_query_acceptance` (+2 cases → 67 total)
- **Tests:** `test_public_query_bad_fragments_do_not_broad_fallback` (+2 parametrized rows)

## Validation results

| Command | Result |
|---|---|
| `.venv/bin/pytest tests/test_natural_query_parser.py::test_public_query_bad_fragments_do_not_broad_fallback -n0 -q` | 8 passed |
| `.venv/bin/python tools/raw_query_answer_qa.py --slice public_query_acceptance --fail-on-expectation-failure` | `outputs/raw_query_answer_qa/20260528T225801Z`; 67 cases; `pass: 67`; failed none |
| `.venv/bin/python tools/raw_query_answer_qa.py --slice basic_public_availability --fail-on-expectation-failure` | `outputs/raw_query_answer_qa/20260528T224636Z`; 7 cases; `pass: 7`; failed none |
| `.venv/bin/python tools/raw_query_answer_qa.py --slice natural_query_route_priority --slice product_boundaries --fail-on-expectation-failure` | `outputs/raw_query_answer_qa/20260528T225437Z`; 49 cases; `pass: 49`; failed none |
| `make PYTEST=.venv/bin/pytest test-parser` | 788 passed in 726.73s |
| `make PYTEST=.venv/bin/pytest test-query` (initial) | 5 failed, 798 passed — `Jokic vs Embiid since 2021` false positive (trailing `since` not stripped from comparison phrase) |
| `make PYTEST=.venv/bin/pytest test-query` (after fix) | All 5 prior failures pass after `_COMPARISON_TRAILING_CONTEXT` includes `since` |
| `git diff --check` | clean |

## Proof Waves 2A / 2B / 2C stayed green

Wave 2D re-ran the same regression slices used after Waves 2A–2C:

- **`public_query_acceptance` (67 cases):** includes all Wave 2A (6), 2B (3), 2C (3),
  and 2D (2) seeded cases — `pass: 67`
- **`basic_public_availability` (7 cases):** Wave 2B availability shorthand —
  `pass: 7`
- **`natural_query_route_priority` + `product_boundaries` (49 cases):** Wave 2C route
  priority and boundary cases — `pass: 49`

No Wave 2A/2B/2C case IDs were removed or weakened.

## Deferred V2 fuzzy matching notes

- Do not add edit-distance or phonetic matching in `resolve_player()` for V1.
- If V2 adopts typo correction, add explicit confidence thresholds, user-visible
  correction notes, and corpus rows that assert intentional correction — not silent
  nickname-only recovery.
- Partial nickname recovery (`kevn` + `durant` → Kevin Durant) should remain blocked
  unless product policy explicitly ships and tests fuzzy resolution end-to-end.
