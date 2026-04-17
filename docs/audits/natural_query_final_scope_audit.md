# natural_query.py — Final Scope Audit

> Audit date: 2026-04-17
> Audited file: `src/nbatools/commands/natural_query.py` — 1 679 lines, 31 functions
> Previously extracted: 7 helper modules totalling ~2 340 lines

---

## 1. Executive Judgment

**One more targeted extraction pass is clearly warranted.**

`natural_query.py` has improved dramatically. The execution layer, occurrence routing, playoff/record routing, matchup/comparison parsing, date helpers, leaderboard utilities, constants, and season helpers have all been properly pulled out. That was the high-ROI work.

What remains, however, is a file that still mixes two distinct responsibilities:

1. **Parsing helpers** — ~40 small-to-medium functions that extract structured fields from raw query text (stat detection, season extraction, streak parsing, threshold extraction, intent detection, condition detection, etc.). These are pure `text → value` transforms with no routing or orchestration logic.

2. **Routing / orchestration** — `_build_parse_state`, `_finalize_route`, `_merge_inherited_context`, `parse_query`, and `run`. These compose the parsed fields into a routable structure and select the execution path.

Mixing both in one file is the remaining structural problem. It is not catastrophic — the file is readable — but it makes the file larger than necessary and blurs the line between "what does this query say?" and "where does this query go?"

**Verdict:** One final extraction pass — pulling the parsing helpers into a dedicated `_parse_helpers.py` — would bring `natural_query.py` down to ~900 lines of pure routing logic and finish the decomposition cleanly. After that, code-level organization is done enough to move to repo/folder architecture.

---

## 2. Responsibility Inventory

### A. Parsing helpers (text → structured value)

| Function | Lines | What it does |
|---|---|---|
| `extract_top_n` | 17 | Extracts "top N" / "bottom N" / "best N" from text |
| `wants_leaderboard` | 23 | Detects leaderboard intent from text |
| `extract_position_filter` | 20 | Extracts position-group filter ("among guards", etc.) |
| `wants_team_leaderboard` | 16 | Detects team-leaderboard intent |
| `extract_season` | 3 | Extracts single season string |
| `extract_season_range` | 5 | Extracts "from SEASON to SEASON" |
| `detect_career_intent` | 3 | Detects career / all-time keywords |
| `extract_since_season` | 18 | Extracts "since SEASON/YEAR" |
| `extract_last_n_seasons` | 13 | Extracts "last N seasons" |
| `extract_last_n` | 15 | Extracts "last N games" |
| `extract_streak_request` | 75 | Parses player streak conditions |
| `extract_team_streak_request` | 105 | Parses team streak conditions |
| `detect_stat` | 5 | Maps stat text to canonical stat key |
| `detect_season_type` | 4 | Detects playoff vs regular season |
| `default_season_for_context` | 4 | Returns default season based on season type |
| `detect_split_type` | 6 | Detects home/away or win/loss split type |
| `_parse_threshold_match` | 10 | Helper for threshold parsing |
| `extract_threshold_conditions` | 154 | Extracts stat threshold conditions from text |
| `extract_min_value` | 62 | Extracts minimum-value constraints |
| `detect_home_away` | 4 | Detects home/away filter |
| `detect_wins_losses` | 4 | Detects win/loss filter |
| `wants_summary` | 18 | Detects summary intent |
| `wants_finder` | 13 | Detects list/finder intent |
| `wants_count` | 12 | Detects count intent |
| `wants_recent_form` | 2 | Detects "recent form" intent |
| `wants_split_summary` | 2 | Detects split-summary intent |
| `_POSITION_GROUP_PATTERNS` | (dict) | Position name → group mapping |
| `STREAK_SPECIAL_PATTERNS` | (dict) | Special streak pattern definitions |
| `TEAM_STREAK_SPECIAL_PATTERNS` | (dict) | Team streak pattern definitions |

**Total: ~26 functions + 3 data dicts, ~610 lines**

These are all pure text-parsing functions. None of them reference routes, execute commands, or depend on the routing layer. They depend only on `_constants` (for `STAT_ALIASES`, `STAT_PATTERN`, `normalize_text`).

### B. Parse-state assembly

| Function | Lines | What it does |
|---|---|---|
| `_build_parse_state` | 228 | Calls all parsing helpers, resolves entities, assembles the full parse dict |

This is the bridge between parsing and routing. It calls the helpers from group A plus the already-extracted entity/matchup/occurrence/date/season modules, and produces the structured parse dict.

### C. Route finalization

| Function | Lines | What it does |
|---|---|---|
| `_finalize_route` | 594 | Takes the parse dict and selects the route + builds route_kwargs |

This is the core routing logic. It contains the priority-ordered if/elif chain that maps parsed intent to execution routes. It also contains some inline leaderboard-stat-fallback logic (lower-is-better stats, season-advanced stat blocking).

### D. OR-clause context inheritance

| Function | Lines | What it does |
|---|---|---|
| `_merge_inherited_context` | 58 | Merges base parse state into OR-clause sub-parses |

Used by `_natural_query_execution.py` for boolean OR queries. Tightly coupled to the parse-state schema and `_finalize_route`.

### E. Public API

| Function | Lines | What it does |
|---|---|---|
| `parse_query` | 2 | Composes `_build_parse_state` → `_finalize_route` |
| `run` | 19 | CLI entry point: calls `execute_natural_query` → `render_query_result` |

---

## 3. Belongs Here vs Does Not Belong Here

### Clearly belongs in `natural_query.py`

- **`_build_parse_state`** — This is the orchestrator that assembles parsing results into a query state dict. It is the bridge between parsing and routing and belongs with the routing layer.
- **`_finalize_route`** — This is the core routing decision tree. It is the reason `natural_query.py` exists.
- **`_merge_inherited_context`** — Coupled to the parse-state schema and `_finalize_route`. Belongs here.
- **`parse_query`** — Public API that composes the above two. Belongs here.
- **`run`** — Thin CLI wrapper. Acceptable here (could live in CLI layer, but it's 19 lines and not worth moving).

### Should be extracted

- **All parsing helpers (group A above)** — These are pure `text → value` transforms. They have no dependency on routing, execution, or the parse-state schema. They are the single remaining cohesive cluster that clearly does not belong in a routing/orchestration module.

  Extracting them would:
  - Reduce `natural_query.py` from ~1 679 lines to ~900 lines
  - Make the file purely about routing/orchestration
  - Make the parsing helpers independently testable and reusable
  - Follow the same pattern as every previous extraction (`_constants.py`, `_date_utils.py`, `_matchup_utils.py`, etc.)

### Borderline but acceptable — should stay

- **`default_season_for_context`** — Could go in `_seasons.py` but it's 4 lines and tightly used by `_build_parse_state`. Not worth the import churn.
- **Leaderboard stat-fallback logic inside `_finalize_route`** (lines ~1270-1370) — This is routing-level policy ("if this stat isn't available in this context, fall back to pts"). It's 80+ lines of inline logic that could theoretically be a helper, but it's deeply interwoven with the route-selection branches. Extracting it would create a helper that's hard to name and only called from one place. Leave it.

---

## 4. One Final Recommended Extraction Pass

### Target: Extract parsing helpers into `_parse_helpers.py`

**What moves:**
All 26 functions and 3 data dicts from group A above (~610 lines). Specifically:

- `extract_top_n`
- `wants_leaderboard`
- `_POSITION_GROUP_PATTERNS` + `extract_position_filter`
- `wants_team_leaderboard`
- `extract_season`, `extract_season_range`
- `detect_career_intent`, `extract_since_season`, `extract_last_n_seasons`, `extract_last_n`
- `STREAK_SPECIAL_PATTERNS` + `extract_streak_request`
- `TEAM_STREAK_SPECIAL_PATTERNS` + `extract_team_streak_request`
- `detect_stat`
- `detect_season_type`
- `default_season_for_context`
- `detect_split_type`
- `_parse_threshold_match` + `extract_threshold_conditions`
- `extract_min_value`
- `detect_home_away`, `detect_wins_losses`
- `wants_summary`, `wants_finder`, `wants_count`, `wants_recent_form`, `wants_split_summary`

**What stays in `natural_query.py`:**
- `_build_parse_state` (~228 lines)
- `_finalize_route` (~594 lines)
- `_merge_inherited_context` (~58 lines)
- `parse_query` (2 lines)
- `run` (19 lines)
- Import block and re-exports

**Why this is high-value:**
1. It is the single largest remaining cohesive cluster that violates the module's stated purpose
2. The functions are pure and self-contained — zero coupling to routing logic
3. It follows the exact pattern of every previous successful extraction
4. It brings `natural_query.py` to a clean ~900-line routing module
5. The extraction is mechanical (move + add imports) — low risk

**Why now instead of later:**
These helpers are imported by tests that currently reach into `natural_query.py` for parsing functions. Extracting them now gives tests a clean import path before repo/folder restructuring, which would otherwise have to deal with re-export chains.

---

## 5. Stop Line

After extracting the parsing helpers, **do not split further**. Specifically:

- **Do not split `_finalize_route` into per-route helper functions.** The if/elif chain is long but linear and readable. Breaking it into sub-functions would scatter the priority order across files and make routing harder to trace.
- **Do not extract the leaderboard stat-fallback logic.** It's routing-level policy, not a reusable parsing helper.
- **Do not move `_build_parse_state` to a separate file.** It is the natural bridge between parsing and routing and belongs with the router.
- **Do not move `_merge_inherited_context` to `_natural_query_execution.py`.** It depends on `_finalize_route` and the parse-state schema — it belongs with the routing layer.
- **Do not move `run` to `cli.py`.** It's 19 lines and a standard thin wrapper pattern used across the codebase.
- **Do not create a `_route_helpers.py`** or similar for fragments of `_finalize_route`. The function is long but it is one decision tree, not a bag of reusable helpers.

The goal after this pass is a `natural_query.py` that contains exactly: parse-state assembly, route selection, context inheritance, and the public API. Everything else should already live in a helper module.

---

## 6. Summary

| Question | Answer |
|---|---|
| Is `natural_query.py` appropriately scoped today? | Almost — one cluster remains misplaced |
| Is another decomposition pass warranted? | Yes — one final targeted pass |
| What is the extraction target? | ~610 lines of pure parsing helpers → `_parse_helpers.py` |
| What is the risk? | Low — mechanical move, no logic changes |
| What is the post-extraction state? | ~900-line routing module — clean enough to move on |
| Is code-level decomposition done after that? | Yes |

---

## Appendix: Ready-to-Run Prompt for Final Extraction

> **Task:** Extract all pure parsing helper functions from `natural_query.py` into a new `_parse_helpers.py` module.
>
> **Scope:**
> - Move all functions and data dicts listed in group A of the audit (see §2.A) into `src/nbatools/commands/_parse_helpers.py`
> - Update `natural_query.py` to import them from `_parse_helpers`
> - Update any external imports that reference these functions via `natural_query` to either: (a) import from `_parse_helpers` directly, or (b) keep working via re-export from `natural_query` — prefer (b) for tests to minimize test churn
> - `normalize_text` stays in `_constants.py` where it is defined; `_parse_helpers.py` imports it from there
> - `detect_stat` depends on `STAT_ALIASES` from `_constants` — that stays as-is
> - Run `make test-impacted` then `make test-parser` to verify
>
> **Do not:**
> - Change any function signatures or behavior
> - Move `_build_parse_state`, `_finalize_route`, `_merge_inherited_context`, `parse_query`, or `run`
> - Introduce new abstractions or refactor any logic
> - Touch test assertions
