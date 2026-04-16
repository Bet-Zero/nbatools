# Result Contracts

This document defines the **target result contracts** for `nbatools`.

It is a design/contracts doc, not a description of what the engine currently produces. Today, result shapes vary across command modules. This doc describes what they should evolve toward so that the CLI, exports, and the React web UI can all consume the same engine.

Related docs:

- [docs/project_conventions.md](project_conventions.md) — engineering conventions (see section 9, UI-readiness)
- [docs/data_contracts.md](data_contracts.md) — dataset-level contracts
- [docs/current_state_guide.md](current_state_guide.md) — currently shipped behavior
- [docs/roadmap.md](roadmap.md) — Phase 5 (product-layer readiness) and Phase 6 (first UI)

---

## 1. Why result contracts matter

### 1.1 CLI and UI share the same engine

The repo has two user surfaces — a CLI that prints pretty text and a React web UI that renders structured results. Both call the same engine and consume the same `QueryResponse` envelope.

Pretty terminal formatting is **not** the core contract. It is one of several presentation layers over a shared structured result. If the engine's source of truth is a formatted string, the UI cannot reuse it without re-parsing terminal output — which is exactly the wrong direction.

### 1.2 Stable engine outputs vs presentation

The engine should produce stable, structured results. Presentation layers then render those results differently:

- CLI pretty text
- CLI exports (CSV / TXT / JSON)
- React web UI components
- API responses

A result contract is the shape the engine guarantees. A presentation layer is a renderer over that shape. The contract must be stable even when renderers change.

### 1.3 Why this matters before a UI exists

Even with no UI on the horizon, result contracts:

- make export behavior predictable across routes
- make test assertions cleaner (assert on fields, not on formatted lines)
- make new query classes cheaper to add (they slot into an existing shape)
- prevent the CLI presentation from quietly becoming load-bearing

---

## 2. Core result classes

The engine should think in these result classes. They align with the preferred route classes in [docs/project_conventions.md](project_conventions.md#42-preferred-route-classes).

1. **finder** — list of matching games or entities
2. **summary** — aggregated stats for one entity over a sample
3. **comparison** — side-by-side stats for two or more entities over a sample
4. **split summary** — two or more sub-samples of one entity, compared
5. **leaderboard** — ranked list of entities by one or more metrics
6. **streak** — streak detections or longest-streak results for an entity
7. **no-result / error-style result** — a first-class class, not an unhandled absence

Every query the engine answers should map to one of these. A query that does not fit is a signal that either a new result class needs to be added deliberately or the query should be rephrased to fit an existing one.

---

## 3. Expected conceptual shape per class

Each class below is defined by its conceptual shape. Field names are illustrative — this doc defines the _shape the engine should guarantee_, not a Python class diagram.

Every result class also carries the shared metadata block defined in [section 4](#4-shared-metadata-contract).

### 3.1 finder

**Purpose:** return the list of games (or entities) that match a filter.

Conceptual shape:

- **primary entity/entities:** the player(s) or team(s) being filtered
- **filters/context:** threshold conditions, grouped boolean expression, date window, opponent filter, home/away, W/L
- **tabular data section(s):** one row per matching game with the columns appropriate to the finder (player-game columns for player finders, team-game columns for team finders)
- **summary metrics:** count of matching games; optionally aggregate rollups over the matched set
- **optional metadata:** sort key and direction, max result count if truncated
- **current CLI surfaces that map here:**
  - `player_game_finder`
  - `game_finder` (team game finder)
  - natural-query finder routes (`Jokic under 20 points`, `Jokic last 10 games over 25 and under 15 rebounds`)

### 3.2 summary

**Purpose:** return aggregated stats for one entity over a sample.

Conceptual shape:

- **primary entity:** one player or one team
- **filters/context:** season(s), season type, date window, last-N, opponent filter, split selector, grouped boolean filter
- **tabular data section(s):**
  - overall summary row
  - optional per-season breakdown (maps to the stable `BY_SEASON` label — see [section 6](#6-section-label-guidance))
- **summary metrics:** box-score aggregates plus shooting splits; for player summaries, sample-aware rate metrics (USG%, AST%, REB%) per [docs/data_contracts.md](data_contracts.md#7-sample-aware-metric-contract)
- **optional metadata:** sample size, games played, date range of the actual sample
- **current CLI surfaces that map here:**
  - `player_game_summary`
  - `game_summary` (team summary)
  - `season_leaders` single-entity summary path when applicable
  - natural-query summary routes (`Jokic recent form`, `Celtics last 15 games summary`, `Jokic summary vs Lakers`)

### 3.3 comparison

**Purpose:** return side-by-side stats for two or more entities over a consistent sample definition.

Conceptual shape:

- **primary entities:** two or more players, or two or more teams
- **filters/context:** shared season/window/filter definition applied to each entity; head-to-head flag when the comparison is restricted to games the entities played against each other
- **tabular data section(s):**
  - one comparison table with one column per entity and one row per metric (maps to the stable `COMPARISON` label)
  - optional per-season alignment if requested
- **summary metrics:** the same metric set per entity for an apples-to-apples view; for players, sample-aware rate metrics recomputed from each entity's sample
- **optional metadata:** whether the comparison was head-to-head, whether samples differ in size, any fallback notes
- **current CLI surfaces that map here:**
  - `player_compare`
  - `team_compare`
  - natural-query comparison routes including `vs`, `h2h`, and `head-to-head` phrasing

**Note:** grouped boolean filtering is currently documented for finder/summary/split, **not** for comparisons. The comparison result contract should not assume grouped boolean context until that support is explicitly verified and shipped. See [docs/current_state_guide.md](current_state_guide.md#grouped-boolean-coverage).

### 3.4 split summary

**Purpose:** return two or more sub-samples of one entity, compared against each other.

Conceptual shape:

- **primary entity:** one player or one team
- **filters/context:** base filter (season, window, opponent, etc.) plus a split selector (home vs away, wins vs losses, pre/post All-Star, etc.)
- **tabular data section(s):**
  - one split-comparison table with one column per split and one row per metric (maps to the stable `SPLIT_COMPARISON` label)
- **summary metrics:** same metric set per split; player sample-aware rate metrics recomputed per split sample
- **optional metadata:** split type, sample size per split
- **current CLI surfaces that map here:**
  - `player_split_summary`
  - `team_split_summary`
  - natural-query split routes (`Jokic home vs away in 2025-26`, `Celtics wins vs losses`)

### 3.5 leaderboard

**Purpose:** return a ranked list of entities by one or more metrics.

Conceptual shape:

- **primary entities:** a league-wide set of players or teams
- **filters/context:** season, season type, date window, minimum qualifiers (games played, minutes), metric being ranked, sort direction, top-N
- **tabular data section(s):** one ranked table, ordered by the ranking metric, with identity columns plus the ranking metric plus a reasonable default set of supporting metrics
- **summary metrics:** none beyond the ranked table itself, typically
- **optional metadata:** dataset source used for ranking (season-advanced table vs derived-from-game-logs), any qualifier thresholds applied, any fallback notes when the requested metric is not directly present in the source
- **current CLI surfaces that map here:**
  - `season_leaders`
  - `season_team_leaders`
  - natural-query leaderboard phrasing (`top scorers this season`, `best offensive teams`, `teams with most threes`)

**Note:** leaderboard breadth and phrasing coverage should still be treated as something to verify by tests before broadening claims, per [docs/current_state_guide.md](current_state_guide.md#5-leaderboard-queries). The result _contract_ here is target shape, not a claim that every phrasing works today.

### 3.6 streak

**Purpose:** return streak detections or longest-streak results for an entity.

Conceptual shape:

- **primary entity:** one player or one team
- **filters/context:** threshold definition (e.g. 20+ points, made three, triple-double, team scoring 120+), season/window, opponent filter, streak mode (longest vs "N in a row")
- **tabular data section(s):**
  - one or more streak rows, each with start game, end game, streak length, and the per-game values that satisfied the threshold
- **summary metrics:** longest streak length, count of qualifying streaks when applicable
- **optional metadata:** streak mode, threshold definition, whether streaks are restricted to a date window
- **current CLI surfaces that map here:**
  - `player_streak_finder`
  - `team_streak_finder`
  - natural-query streak phrasing (`Jokic 5 straight games with 20+ points`, `longest Lakers winning streak`)

**Note:** streak surface is present but breadth is still being tightened. The contract defines shape, not exhaustive phrasing coverage.

### 3.7 no-result / error-style result

**Purpose:** represent "no answer" as a first-class result, not as an unhandled absence.

A query that parses but finds nothing, a query that routes successfully but has no data for the requested season/type, and a query that fails parsing are three distinct states. A UI needs to tell them apart. The engine should too.

Conceptual shape:

- **result kind:** one of
  - `no_match` — query was valid and executed, but the filter returned nothing
  - `no_data` — the requested season/type/window is not loaded
  - `unrouted` — parser could not confidently select a route
  - `ambiguous` — parser matched multiple routes with similar confidence
  - `unsupported` — query was understood but the requested combination is not supported (e.g. mutually exclusive filters, invalid stat name)
  - `error` — execution failed for a known reason
- **reason:** a short machine-readable reason code
- **message:** a human-readable explanation suitable for CLI or UI display
- **echoed context:** the query text, detected route (if any), and any partially-resolved filters so the user can see what the engine thought they meant
- **current CLI surfaces that map here:** currently handled ad hoc per command. This result class exists partly to consolidate that.

---

## 4. Shared metadata contract

Every result class should eventually carry a consistent metadata block. These fields are the bridge between "we got an answer" and "here is what that answer is an answer _to_."

Future result objects should carry:

- **query_text** — the original natural query, when applicable
- **route / query_class** — which result class this is (`finder`, `summary`, `comparison`, `split_summary`, `leaderboard`, `streak`, `no_result`)
- **season / season_range** — the season(s) the result covers
- **season_type** — regular season, playoffs, or both
- **date_window** — resolved absolute date range (e.g. `last 10 games` becomes a concrete date range the engine actually used)
- **player_context** — player identity (id + name) where applicable
- **team_context** — team identity (id + abbr + name) where applicable
- **opponent_context** — opponent identity when an opponent filter was applied
- **split_type** — when the result is a split summary
- **grouped_boolean_used** — whether a grouped boolean expression was parsed and applied
- **head_to_head_used** — whether a head-to-head restriction was applied
- **current_through** — freshness marker for the underlying data; should align with the working definition in [docs/data_freshness_plan.md](data_freshness_plan.md#9-current-through--what-users-should-be-able-to-trust). Future-ready — not all results carry this today.
- **notes / caveats** — short, machine-readable notes when the engine applied a semantic fallback. Examples:
  - leaderboard metric not present in season-advanced table, derived from game logs
  - sample-aware player rate recomputed from the filtered sample rather than season-average
  - requested window extended to the nearest available date because the exact window had no games

The purpose of `notes / caveats` is to make semantic fallbacks visible instead of silent. A UI should be able to render these as small badges or footnotes without the engine needing to know anything about the UI.

---

## 5. Raw output, pretty output, exports, and UI

These four layers should relate as renderers over the same underlying result.

- **Raw structured output** is the canonical form. Everything else is derived from it.
- **Pretty CLI output** is a terminal renderer. It may add section headers, column alignment, and color. It must not invent new fields and must not be the place where a value is computed for the first time.
- **Exports (CSV / TXT / JSON)** are additional renderers. JSON export should be the closest to the raw structured output. CSV and TXT are projections suitable for spreadsheet and plain-text consumption.
- **React web UI rendering** is one more renderer. It consumes the same raw structured result that JSON export consumes. If the UI needs a value that only exists in pretty CLI output, that is a signal the value belongs in the raw structured result.

The rule:

> Any value a user sees should exist in the raw structured result first. Presentation layers may reformat it; they should not be the source of it.

---

## 6. Section label guidance

The following section labels are already established as machine-readable output markers and are documented as stable in [docs/project_conventions.md](project_conventions.md#64-output-section-labels):

- `SUMMARY`
- `BY_SEASON`
- `COMPARISON`
- `SPLIT_COMPARISON`

These labels should be understood as **the current naming for sections within specific result classes**, not as a replacement for result classes. In the target contracts:

- `SUMMARY` corresponds to the overall summary block inside a **summary** result
- `BY_SEASON` corresponds to the optional per-season breakdown inside a **summary** result
- `COMPARISON` corresponds to the main table inside a **comparison** result
- `SPLIT_COMPARISON` corresponds to the main table inside a **split summary** result

Rules:

- Do not rename these labels casually — downstream consumers may depend on them.
- New result classes (leaderboard, streak, finder, no-result) will need their own stable section labels over time. Introduce them deliberately and document them when they are added.
- Section labels live inside results. They are not a substitute for the result class itself.

---

## 7. What should not happen

- **UI depending on terminal formatting.** The React UI must not parse pretty CLI output to recover values. If it ever needs to, the engine is producing the wrong shape.
- **Route-specific ad hoc output shapes multiplying without documentation.** New routes should slot into an existing result class. A new shape is a deliberate, documented event, not an accident of implementation.
- **Docs claims outrunning actual result consistency.** This doc describes target contracts. It should not be cited as evidence that the engine already produces fully consistent results across routes. When a route is brought into alignment with a contract, update the current-state guide — not this doc — to reflect the new verified behavior.
- **Silent semantic fallbacks.** If the engine substitutes a different dataset, recomputes a metric from a different sample, or widens a date window to find data, that must surface via the `notes / caveats` metadata, not be hidden inside pretty output.
- **Computing user-visible values in the formatting layer.** If a value appears in pretty output, it must also exist in the raw structured result.

---

## 8. Near-term guidance

This doc is meant to be useful _before_ any UI work begins.

### 8.1 How to use this doc now

- When adding a new route or query feature, identify the result class it belongs to from [section 2](#2-core-result-classes) and shape its output to match [section 3](#3-expected-conceptual-shape-per-class).
- When touching an existing command that already emits raw output, prefer to add missing shared metadata fields from [section 4](#4-shared-metadata-contract) rather than inventing new ad hoc fields.
- When exposing a new section in CLI output, reuse an existing stable label where one applies; only introduce new section labels deliberately.
- When the engine makes a semantic fallback (metric fallback, sample recomputation, window adjustment), surface it as a caveat in the result, not only in pretty output.

### 8.2 How code should move toward these contracts without a rewrite

- **Do not do a broad rewrite.** Per [docs/project_conventions.md](project_conventions.md#82-avoid-architecture-churn), architecture churn without a clear payoff is discouraged.
- **Migrate opportunistically.** When a command is already being edited for another reason, bring its result shape closer to the contract for its class. Over time, this converges without a dedicated refactor pass.
- **Prefer additive changes.** Adding fields to a result is safer than renaming or restructuring them. Presentation layers can ignore new fields.
- **Protect migrations with tests.** When a result shape is tightened, back it with export or structured-output tests, per the testing conventions in [docs/project_conventions.md](project_conventions.md#7-testing-conventions).
- **Update the current-state guide only after verification.** This doc describes the target. [docs/current_state_guide.md](current_state_guide.md) describes what is actually shipped and tested. Keep that distinction strict.

The target is gradual convergence: every route ends up producing a result that fits one of the seven result classes, carries the shared metadata block, and can be rendered by the CLI, exports, and the React UI without any of them needing to know about the others.
