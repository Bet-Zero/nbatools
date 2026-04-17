# Glue Layer Scope Audit: `query_service.py` and `format_output.py`

**Date:** 2026-04-17
**Scope:** Code-boundary audit of the two remaining glue-layer files, grounded in current repo state.

---

## 1. Executive Judgment

**Both files are appropriately scoped.** Neither contains responsibilities that urgently need extraction.

`query_service.py` is a clean engine facade — it dispatches, wraps results, and builds metadata. It does not contain business logic, parsing, or formatting.

`format_output.py` is a coherent formatting/serialization layer. It handles pretty rendering, raw/labeled text construction, CSV/JSON export, and the route-to-query-class mapping table. Everything in it relates to "how results are presented or serialized."

**One optional cleanup pass exists** (metadata-building duplication in `query_service.py`), but it is low-risk and low-urgency. It should not block moving to repo/folder architecture.

**Recommendation: proceed to repo/folder architecture.**

---

## 2. `query_service.py` Assessment (660 lines)

### What it does

| Responsibility | Lines (approx) | Verdict |
|---|---|---|
| Module docstring + imports + re-exports | 1–59 | **Clearly belongs** |
| `_build_query_metadata()` — assemble metadata dict from parsed state | 66–145 | **Clearly belongs** |
| `QueryResult` envelope dataclass + convenience accessors | 167–217 | **Clearly belongs** |
| `reason_to_status()` + `_EXPECTED_REASONS` — status normalization | 152–164 | **Clearly belongs** |
| `execute_natural_query()` — grouped-boolean / OR / standard dispatch | 224–492 | **Clearly belongs** (orchestration) |
| Count-intent post-processing (Finder→Count, Leaderboard→Count) | 385–481 | **Borderline but acceptable** — see note below |
| `VALID_ROUTES` + `execute_structured_query()` — structured dispatch | 500–660 | **Clearly belongs** |
| Inline metadata building in `execute_structured_query` | 576–627 | **Borderline** — duplicates `_build_query_metadata` pattern |

### Detailed notes

**Count-intent post-processing (lines 385–481):**
The Finder→CountResult conversion (lines 385–396) is clean and small. The LeaderboardResult→CountResult path (lines 397–474) is the longest single block in the file — it inspects DataFrame columns to extract an entity count. This is not domain logic in the traditional sense (it doesn't compute stats), but it does reach into DataFrame internals. It is acceptable here because:
- It is a service-layer concern: "transform the result shape based on detected query intent."
- Moving it elsewhere (e.g., into `CountResult` or a helper) would just shift the complexity without reducing it.
- It only runs when `count_intent` is active, which is a query-service routing decision.

**Metadata duplication:**
`execute_structured_query` (lines 576–627) builds its own metadata dict inline rather than calling `_build_query_metadata`. The logic is nearly identical (player/team coalescing, current_through computation, season extraction). This is the only real boundary smell in the file. A future pass could unify this into `_build_query_metadata` with an optional `parsed` or `kwargs` input. But the duplication is stable and tested — it does not cause bugs or maintenance confusion today.

### What does NOT belong here — confirmed absent

- ❌ No parsing logic — delegated to `natural_query.py`
- ❌ No formatting logic — delegated to `format_output.py`
- ❌ No data loading — delegated to command modules
- ❌ No CLI concerns — no print statements, no Typer references
- ❌ No API concerns — no FastAPI references

---

## 3. `format_output.py` Assessment (1166 lines)

### What it does

| Responsibility | Lines (approx) | Verdict |
|---|---|---|
| Constants: section labels, metadata field order, route-to-query-class map | 1–96 | **Clearly belongs** |
| `route_to_query_class()` | 92–95 | **Clearly belongs** — used by both `query_service.py` and `_natural_query_execution.py` |
| `build_metadata_block()` / `parse_metadata_block()` | 98–167 | **Clearly belongs** — metadata serialization |
| `wrap_raw_output()` / `build_no_result_output()` / `build_error_output()` | 170–240 | **Clearly belongs** — raw text envelope construction |
| `strip_metadata_section()` / `parse_labeled_sections()` | 121–261 | **Clearly belongs** — section parsing for the labeled-text format |
| `_read_csv_block()` / `_extract_sections()` | 264–304 | **Clearly belongs** — internal helpers for pretty formatter |
| Number/record/label formatting helpers | 307–466 | **Clearly belongs** — pure presentation |
| `_format_comparison()` / `_format_split_summary()` | 473–648 | **Clearly belongs** — pretty rendering |
| `format_pretty_output()` (from raw text) | 701–877 | **Clearly belongs** — the original text-based pretty renderer |
| `format_pretty_from_result()` (from structured result) | 915–937 | **Clearly belongs** — newer structured-result pretty renderer |
| `_format_count_pretty()` | 940–956 | **Clearly belongs** |
| `_format_pretty_from_sections()` | 959–1033 | **Clearly belongs** — internal dispatch |
| `write_csv_from_result()` / `write_json_from_result()` | 1036–1122 | **Clearly belongs** — export serialization |
| `_json_default()` / `_prepare_metadata_for_json()` | 1125–1152 | **Clearly belongs** |
| `wrap_result_with_metadata()` | 1155–1166 | **Clearly belongs** — convenience bridge |

### Detailed notes

**Dual pretty-formatting paths:**
The file has two entry points for pretty formatting: `format_pretty_output()` (from raw labeled text) and `format_pretty_from_result()` (from structured result objects). Both exist intentionally — the text-based path is still used for backward compatibility, and the structured path is the preferred newer path. The structured path (`format_pretty_from_result`) sometimes falls back to the text path for summary recomposition (line 992). This is acceptable — it avoids duplicating the full summary formatter.

**`ROUTE_TO_QUERY_CLASS` map:**
This is a data mapping, not logic. It lives in `format_output.py` because the query class directly drives output section labeling. `query_service.py` imports `route_to_query_class()` from here, which is the correct dependency direction (service imports from format, not the reverse).

**File size:**
At 1166 lines, this is a large file. But the content is cohesive — it is all formatting, serialization, and presentation helpers. Splitting it (e.g., `_pretty_renderers.py` + `_export_writers.py`) would be a folder-architecture decision, not a scope-boundary issue. The responsibilities are correct; only the physical file size could warrant splitting.

### What does NOT belong here — confirmed absent

- ❌ No query routing or parsing logic
- ❌ No data loading or computation
- ❌ No CLI framework references (no Typer, no argparse)
- ❌ No API references (no FastAPI, no Pydantic)
- ❌ No compatibility shims that should be retired — the dual-path formatting is intentional

---

## 4. Belongs Here vs Should Move

### `query_service.py`

| Cluster | Classification |
|---|---|
| Natural query dispatch (grouped-bool / OR / standard) | Clearly belongs |
| Structured query dispatch | Clearly belongs |
| `QueryResult` envelope + accessors | Clearly belongs |
| Metadata building (`_build_query_metadata`) | Clearly belongs |
| Inline metadata in `execute_structured_query` | Borderline but acceptable — minor duplication of `_build_query_metadata` |
| Count-intent Finder→Count conversion | Clearly belongs |
| Count-intent Leaderboard→Count entity extraction | Borderline but acceptable — service-layer result transformation |
| `reason_to_status()` normalization | Clearly belongs |
| Result type re-exports | Clearly belongs |

### `format_output.py`

| Cluster | Classification |
|---|---|
| Section label constants + route-to-query-class map | Clearly belongs |
| Metadata block build/parse | Clearly belongs |
| Raw text envelope helpers (wrap, build_no_result, build_error) | Clearly belongs |
| Section parsing (parse_labeled_sections, _extract_sections) | Clearly belongs |
| Number/record/label formatting helpers | Clearly belongs |
| Pretty renderers (summary, comparison, split, count, leaderboard/finder/streak) | Clearly belongs |
| `format_pretty_output()` — text-based entry | Clearly belongs (backward compat, still used) |
| `format_pretty_from_result()` — structured entry | Clearly belongs (preferred path) |
| CSV/JSON export writers | Clearly belongs |
| JSON serialization helpers | Clearly belongs |

**Nothing in either file should be extracted.**

---

## 5. Recommended Next Action

**Proceed to repo/folder architecture.** The glue-layer code organization is done enough.

If a tiny opportunistic cleanup is desired before that, the single highest-value one is:

> **Unify metadata building in `query_service.py`** — refactor `execute_structured_query` (lines 576–627) to call `_build_query_metadata()` with a kwargs-based input path instead of duplicating the player/team/season coalescing logic inline. This is ~50 lines of duplication removal with zero behavioral change.

This is optional. It does not block repo/folder architecture, and the duplication is stable. Do it only if someone is already touching `query_service.py` for another reason.

---

## 6. Stop Line

**Do not refactor further:**

- **Do not split `format_output.py` into multiple files yet.** It is large (1166 lines) but cohesive. Splitting it is a folder-architecture decision (e.g., `formatting/pretty.py`, `formatting/export.py`), not a code-scope problem. Doing it now would create churn without improving boundaries.

- **Do not extract the count-intent post-processing** from `query_service.py` into a separate module. It is 80 lines of conditional result transformation that runs in one place. Extraction adds indirection without benefit.

- **Do not collapse the dual pretty-formatting paths** (`format_pretty_output` vs `format_pretty_from_result`). Both exist for valid reasons (backward compat vs structured path), and the structured path already delegates to the text path where needed.

- **Do not move `ROUTE_TO_QUERY_CLASS`** out of `format_output.py`. The map drives output labeling, and both consumers (`query_service.py`, `_natural_query_execution.py`) already import it from there. The dependency direction is correct.

- **Do not attempt to unify `QueryResult.to_dict()` with the API layer's `_query_result_to_response()`**. These serve different consumers (JSON dict vs Pydantic model) and should stay separate.

The glue layer is clean. Further decomposition at this stage would be over-engineering.
