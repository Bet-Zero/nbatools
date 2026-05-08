# Cosmetic Fixes Pass 2 Report

Date: 2026-05-08

## Scope

This pass fixed three remaining "raw debug output" cosmetic issues identified in the screenshot review.  Pass 1 had already fixed chip wrapping, decimal precision, and date formatting.

- **Pattern E** — Technical `opponent_quality` debug strings leaking into envelope NOTES (e.g. `opponent_quality: good teams -> win_pct >= 0.5`).
- **Pattern F** — Redundant PLAYER column rendered even when the table is explicitly bound to a single player.
- **Pattern H** — No-result note content duplicated in both the orange `ResultEnvelope` NOTES section and the `NoResultDisplay` DETAILS card.

---

## Pattern E — Opponent-quality filter as chips, not notes

### Pattern E: Problem

Backend filter resolution emitted notes like:

```text
opponent_quality: good teams -> win_pct >= 0.5
opponent_quality: playoff teams -> conference rank <= 10
```

These leaked internal column names, comparison operators, and threshold values into the user-facing envelope NOTES block.

### Pattern E: Backend fix

**`src/nbatools/commands/_parse_helpers.py`** — `build_opponent_quality_note` already stripped out note emission in Pass 1.  It now unconditionally returns `None`:

```python
def build_opponent_quality_note(opponent_quality: dict | None = None) -> str | None:
    del opponent_quality
    # Opponent-quality filters are represented as applied-filter chips in
    # result metadata, so repeating them as notes only leaks implementation
    # detail into the user-facing UI.
    return None
```

**`src/nbatools/query_service.py`** — `_build_applied_filters` promotes the opponent-quality dict to a structured chip:

```python
opponent_quality_value = _opponent_quality_surface_term(source.get("opponent_quality"))
if opponent_quality_value:
    applied_filters.append(
        {
            "label": "Opponent quality",
            "value": opponent_quality_value,
            "kind": "quality",
        }
    )
```

`_opponent_quality_surface_term` reads the `surface_term` field (e.g. `"good teams"`, `"playoff teams"`) from the parsed opponent-quality dict.  This is the user-facing natural-language label captured during parsing — it never exposes column names or operators.

**`src/nbatools/commands/_natural_query_execution.py`** — `_resolve_opponent_quality_kwargs` still calls `build_opponent_quality_note` but the function is now a no-op.  The call is retained so the surrounding orchestration logic is unchanged.

### Pattern E: Frontend fix

**`frontend/src/components/ResultEnvelope.tsx`** — `formatAppliedFilter` maps `kind === "quality"` to a `VS` label:

```typescript
if (kind === "quality") {
  return { label: "VS", value: opponentQualityChipValue(value) };
}
```

`opponentQualityChipValue` maps each known surface term to an uppercase display label:

| surface_term | chip value |
| --- | --- |
| `contenders` | `CONTENDERS` |
| `good teams` | `GOOD TEAMS` |
| `playoff teams` | `PLAYOFF TEAMS` |
| `teams over .500` | `WINNING TEAMS` |
| `top teams` | `TOP TEAMS` |
| `top-10 defenses` | `TOP-10 DEFENSES` |
| `winning teams` | `WINNING TEAMS` |

Unknown terms fall back to `.toUpperCase()`.  The label chip reads **VS** / **GOOD TEAMS**, never `opponent_quality: good teams -> win_pct >= 0.5`.

### Pattern E: Label-derivation logic summary

The surface term is captured once during NLP parsing in `detect_opponent_quality` (`_parse_helpers.py`), stored in the parsed intent dict as `{"type": "opponent_quality", "surface_term": "...", "definition": {...}}`, and passed through to `applied_filters` via `_build_applied_filters`.  The `definition` dict (which contains column names and operators) is never serialised into the API response; only `surface_term` travels to the frontend.

### Pattern E: Files touched

- `src/nbatools/commands/_parse_helpers.py`
- `src/nbatools/query_service.py`
- `src/nbatools/commands/_natural_query_execution.py` (structural; function call retained, no-op)
- `tests/test_backend_apply_patterns.py` — `test_opponent_quality_filter_uses_surface_term`
- `tests/test_phase_e_opponent_quality_filters.py` — four integration tests covering propagation to route kwargs, player summary, and team record
- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/test/LayoutPrimitives.test.tsx` — `"formats opponent-quality filters as VS chips"`

---

## Pattern F — PLAYER column hidden for single-entity results

### Pattern F: Problem

Game-log and streak tables bound to a specific player (e.g. "Jokić 5 straight 20+ point games") showed a redundant PLAYER column that repeated the same name on every row.

### Pattern F: Design constraint

The column must be hidden **only** when `applied_filters` (or the equivalent metadata fields) explicitly pin a single player.  Hiding it because all visible rows happen to share a player is prohibited — that logic would silently drop the column from multi-player leaderboards that are filtered to a single result.

### Pattern F: Implementation

**`frontend/src/components/results/patterns/entityBinding.ts`** — shared helper that reads explicit metadata bindings:

```typescript
export function hasPinnedEntity(
  metadata: ResultMetadata | undefined,
  kind: "player" | "team",
): boolean {
  if (!metadata) return false;

  if (kind === "player") {
    if (metadata.player_context) return true;
    if (typeof metadata.player === "string" && metadata.player.trim()) return true;
    return Array.isArray(metadata.players) && metadata.players.length === 1;
  }

  if (metadata.team_context) return true;
  if (typeof metadata.team === "string" && metadata.team.trim()) return true;
  return Array.isArray(metadata.teams) && metadata.teams.length === 1;
}
```

This checks only `metadata.player_context`, `metadata.player`, and singleton `metadata.players` — all fields that the backend explicitly sets when the query is bound to one player.  It never inspects table row contents.

**`frontend/src/components/results/patterns/GameLogResult.tsx`** — `tableColumns` reads the pinned-entity flag before building columns:

```typescript
const hidePinnedPlayerColumn =
  mode === "player" && hasPinnedEntity(data.result?.metadata, "player");
// ...
if (mode === "player") {
  if (!hidePinnedPlayerColumn) {
    columns.push({ key: "player", header: "Player", render: playerCell });
  }
  // date, team columns follow...
}
```

**`frontend/src/components/results/patterns/StreakResult.tsx`** — same guard in `tableColumns`:

```typescript
const hidePinnedPlayerColumn =
  kind === "player" && hasPinnedEntity(data.result?.metadata, "player");
// ...
if (!hidePinnedPlayerColumn) {
  columns.splice(1, 0, {
    key: "entity",
    header: kind === "team" ? "Team" : "Player",
    render: (row) => heroIdentity(kind, entityDisplay(kind, ...)),
  });
}
```

Multi-entity shapes (`TopPerformancesResult`, `LeaderboardResult`, etc.) do not call `hasPinnedEntity` and always show the PLAYER column.

### Pattern F: Files touched

- `frontend/src/components/results/patterns/entityBinding.ts` (new shared helper)
- `frontend/src/components/results/patterns/GameLogResult.tsx`
- `frontend/src/components/results/patterns/StreakResult.tsx`
- `frontend/src/test/ResultRenderer.test.tsx` — tests updated to not expect `Nikola Jokic` in the PLAYER column when metadata pins a single player

---

## Pattern H — No-result envelope NOTES suppressed

### Pattern H: Problem

No-result outcomes showed the same note text twice: once in the orange `ResultEnvelope` NOTES block and once in the `NoResultDisplay` DETAILS card.

### Pattern H: Fix

**`frontend/src/components/ResultEnvelope.tsx`** — `showNotes` gates the NOTES block on the result status:

```typescript
const showNotes = data.result_status !== "no_result" && data.notes.length > 0;
```

Successful results still render NOTES normally.  CAVEATS are always rendered regardless of status (the condition below `showNotes` uses a separate `data.caveats.length > 0` check).

The `NoResultDisplay` component retains its own DETAILS NOTE rendered independently; this change only suppresses the envelope-level duplicate.

### Pattern H: What was not changed

- CAVEATS remain visible in both success and no-result cases.
- `NoResultDisplay` DETAILS NOTE content is unchanged.
- The suppression is unconditional for all no-result shapes (Guided No Result, Message No Result, unrouted) — there is no "sometimes show notes for no-result" exception.

### Pattern H: Files touched

- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/test/LayoutPrimitives.test.tsx` — `"suppresses notes in the envelope for no-result outcomes"`

---

## Validation

### Backend

| Suite | Result |
| --- | --- |
| `make test-query` (`-m query`, 667 tests) | **667 passed** |
| `tests/test_phase_e_opponent_quality_filters.py` (4 tests) | **4 passed** |
| `tests/test_backend_apply_patterns.py` (opponent quality subset) | **2 passed** |
| `make test-preflight` (all non-slow tests) | **2602 passed, 1 xpassed** (6m45s) |

### Frontend

| Suite | Result |
| --- | --- |
| `npm test` (18 test files) | **242 passed** |
| `npm run build` | **passed** |

### Live `/review` verification

Spot-checked the following shapes after the changes were applied:

| Shape | Observation |
| --- | --- |
| Entity Summary "How has Jayson Tatum played against good teams" | `VS` / `GOOD TEAMS` chip present; no `opponent_quality: ...` note |
| Guided no-result card | Note absent from orange envelope; DETAILS NOTE in card visible; CAVEATS visible |
| Message no-result card | Same as above |

Pending live verification (to be confirmed in next review session):

- Team Record "Celtics record against playoff teams" — `VS PLAYOFF TEAMS` chip expected
- Player Game Log "How often has Jokić recorded a triple-double" — PLAYER column expected hidden
- Streak Table "Jokić 5 straight games with 20+ points" — PLAYER column expected hidden
- Top Performances / season leaderboards — PLAYER column expected **visible** (multi-entity)
