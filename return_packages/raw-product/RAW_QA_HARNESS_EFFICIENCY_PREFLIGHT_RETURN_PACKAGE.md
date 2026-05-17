# Raw QA Harness Efficiency Preflight Return Package

## 1. Executive summary

- Biggest workflow bottlenecks:
  - Long hand-built `--case` lists for target and adjacent cases.
  - Repeated full 243-case corpus runs after already-localized changes.
  - Manual comparison of current run summaries against previous clean runs.
  - Manual tracking of target, adjacent, and product-boundary case groups across
    return packages.
  - No per-case timing, so slow queries cannot be isolated from the full run.
- Highest-value improvement: saved harness slices plus previous-run failure and
  comparison support. Existing tags are useful, but too broad and not currently
  filterable; saved slices match the actual target/adjacent workflow better.
- Recommended first execution wave: add `--slice`, `--failed-from`,
  `--compare-to`, per-case duration/slowest-case reporting, and 4-6 saved slice
  files for the known Raw QA families.
- Production code changed? no
- Tests changed? no
- Corpus changed? no

## 2. Current harness capabilities

| Capability | Exists today? | Evidence | Notes |
|---|---|---|---|
| `--case` selection | yes | `tools/raw_query_answer_qa.py` defines `parser.add_argument("--case", action="append", default=[])`; `selected_case_ids()` parses values. | Case values can also be comma-separated because `selected_case_ids()` splits each provided value on commas. |
| Multiple `--case` flags | yes | `action="append"` plus `selected_case_ids(args.case)` and `filter_cases(...)`. | Recent return packages use repeated `--case` flags for target and adjacent runs. |
| `--limit` | yes | `parser.add_argument("--limit", type=int, default=None)` and `filter_cases(..., limit=args.limit)`. | Applies after case filtering. |
| Category filter | no | Help output lists only `--corpus`, `--out`, `--run-id`, `--limit`, `--case`, `--top-rows`, `--verified-outliers`, and `--fail-on-expectation-failure`. | Category counts are written to summary, but not selectable. |
| Tag filter | no | No `--tag` argument; corpus tags live under `manual_review.tags`. | Tags are counted in summaries but cannot drive runs. |
| Priority filter | no | No `--priority` argument. | All cases have `priority`, so this would be low-risk to add. |
| Manual-review status filter | no | No `--manual-status` or equivalent. | Summary counts manual statuses, but cannot select them. |
| Answer-text-policy filter | no | No `--answer-text-policy` argument. | Summary counts policies, but cannot select them. |
| `added_in` / wave filter | no | Corpus has 0 `added_in`, `wave`, `slice`, or `slices` fields. | Wave membership is currently implicit in IDs such as `_wave4` and `_wave5`. |
| Select only failed cases from prior run | no | No `--failed-from` option; summary has `failed_case_ids` only as output. | High-value because it turns a failed full run into a small rerun. |
| Compare current run to previous run | no | No `--compare-to` option; no comparison writer. | Manual diffing is currently done from report summaries and return packages. |
| Writes `summary.json` | yes | `summarize_rows()` writes run metadata, counts, failed IDs, flag IDs, and output paths. | Good high-level metadata; not enough by itself for full per-case comparison because it lacks all per-case status/route/flag details. `report.jsonl` has those details. |
| Per-case duration | no | `run_case()` returns result fields but no duration; `main()` uses a list comprehension with only overall start/completed timestamps. | Overall duration can be inferred from timestamps, but not case-level cost. |
| Slowest-case reporting | no | No duration fields or slow-case table in `summary.json` or `report.md`. | Latest 243-case clean run ran from `22:16:55` to `22:20:15`, about 3m20s, but slow cases are invisible. |
| Exposes `added_in` / wave metadata | no | `run_case()` base fields include id, query, category, priority, expected, manual_review, and answer_text_policy only. | Even if added to corpus today, it would not be emitted unless harness code changes. |
| Corpus tags can be filtered today | no | Tags exist under `manual_review.tags`, but the selection layer only accepts case IDs and limit. | Existing tags can support future filters. |

## 3. Current corpus metadata

| Metadata field | Present? | Consistency | Useful for filtering? | Notes |
|---|---|---|---|---|
| `id` | yes | 243/243 | yes | Stable case IDs are the only current precise selection mechanism. |
| `query` | yes | 243/243 | limited | Useful for report review, not ideal for selection. |
| `category` | yes | 243/243 | yes | 20 categories exist. Useful for broad slices, but too coarse for target/adjacent fix runs. |
| `priority` | yes | 243/243 | yes | Counts: `p0: 3`, `p1: 79`, `p2: 161`. |
| `answer_text_policy` | partial | 200/243 present; 43 unspecified | yes | Counts: `frontend_hero_expected: 149`, `no_answer_text_expected: 41`, `requires_backend_answer_text: 10`, missing/unspecified: 43. |
| `manual_review` | partial | 179/243 present; missing cases normalize to unreviewed in harness output | yes | Status counts from corpus probe: `expected_unsupported: 27`, `pass: 35`, `verified_outlier: 1`, explicit `unreviewed: 116`, missing: 64. |
| `manual_review.tags` | partial | 179 cases have tags; 39 unique tags | yes | Useful tags include `context_filter`, `stat_mapping`, `stat_alias`, `unsupported_boundary`, `playoff`, `date_filter`, `comparison`, `defensive_stat`, `record_when`, and `top_performance`. |
| Top-level `tags` | no | 0/243 | not today | Current tag location is nested under manual review. That is acceptable if the filter knows where to look. |
| `added_in` | no | 0/243 | not today | Would be useful for new-cases-only runs and expansion wave review. |
| `slices` | no | 0/243 | not today | Useful, but saved slice files avoid touching every case and better preserve target/adjacent group intent. |
| Wave markers | implicit only | 50 IDs contain `wave4`; 48 IDs contain `wave5`; no normalized field | fragile | Wave 5 cases do not have wave tags or `added_in`; they are identifiable only by ID suffixes and occasional notes. |
| Expected fields | yes, varied by case | Required fields are consistent; optional expectation fields vary by route shape | yes | `expected_route` present in 241 cases, `expected_shape` in 217, `expected_sections` in 226, `hard_assertions` in 104. |

Minimal schema addition that would help most:

- Add optional `added_in` for new cases going forward, for example
  `added_in: raw_wave_6` or `added_in: fix_wave_8d`.
- Do not require a full historical backfill before adding harness value.
- Prefer saved slice files for target/adjacent groups because they can capture
  hand-picked case sets without mutating corpus expectations or overloading
  tags.

Adding `added_in` or `slices` is low-risk if optional and ignored by existing
expectation semantics. `added_in` is lower-risk than per-case `slices` because
it is descriptive metadata. Saved slice files are lower-risk still because they
avoid editing `qa/raw_query_answer_corpus.yaml` for workflow-only grouping.

## 4. Workflow pain points

| Pain point | Current cost | Proposed improvement | Expected benefit |
|---|---|---|---|
| Manually typing long `--case` lists | High attention cost; easy to omit adjacent cases or mistype IDs. | Saved slices such as `--slice defensive_aliases` and `--slice product_boundaries`. | Converts repeated 5-10 case command strings into stable names. |
| Rerunning full 243-case corpus | About 3m20s for the latest clean run, plus report review time. | Keep full runs as final safety, but use slices and failed-reruns during iteration. | Saves minutes per iteration while preserving final full-corpus gate. |
| Rerunning only prior failures | Manual extraction from `summary.json` or `report.md`. | `--failed-from outputs/.../summary.json` or `report.jsonl`. | Turns a failing corpus run into a focused rerun with no copy/paste. |
| Comparing current and previous runs | Manual summary comparison in docs and return packages. | `--compare-to outputs/.../report.jsonl` or `summary.json`. | Surfaces newly failing/passing cases, status deltas, flag deltas, and route drift automatically. |
| Finding previous run paths | Manual lookup in output folders and docs. | Document "latest clean run" convention and compare commands; optionally add a later `--compare-to latest`. | Reduces handoff friction; `latest` can be deferred. |
| Keeping target and adjacent cases organized | Case lists live in return packages, not executable artifacts. | Saved slice files under `qa/harness_slices/`. | Makes wave knowledge reusable. |
| Knowing which cases are slow | Impossible today. | Per-case duration plus slowest-case table. | Helps separate harness overhead from expensive query families. |
| Deciding parser/query test scope | Repeated manual judgment in return packages. | Docs-only validation presets tied to change type. | Faster, more consistent safety decisions without removing gates. |
| Updating checkpoint/findings docs | Manual and still necessary. | Defer auto-updating docs; improve run summaries first. | Avoids risky doc automation while lowering data collection cost. |

Estimated biggest time savers:

1. Saved slices: highest repeated-command savings and lowest cognitive load.
2. `--failed-from`: highest value when a full run has a small set of failures.
3. `--compare-to`: highest review-quality improvement, especially before return
   packages.
4. Per-case timing: helps once the corpus grows or a route becomes slow.
5. Broad tag/category filters: useful, but less precise than saved slices for
   recent fix waves.

## 5. Improvement options

| Option | Value | Complexity | Risk | Recommendation |
|---|---|---|---|---|
| A - Harness tag/category filters | High for exploratory runs and broad families. | Low to medium. Selection already normalizes case metadata. | Low if filters are additive and fail on unknown filter values only when appropriate. | Do after first slice/failure wave, or include only `--category`/`--priority` if implementation remains small. |
| B - Saved harness slices | Very high for current target/adjacent workflow. | Medium. Needs slice schema, path/name resolution, unknown ID validation, and selection composition. | Low. Workflow-only files do not change expectations. | Do now. This is the best first improvement. |
| C - Previous-run failure rerun | Very high after any failing full run. | Low to medium. Read `failed_case_ids` from `summary.json`; optionally support `report.jsonl` expectation failures. | Low. It only narrows selection. | Do now. |
| D - Run comparison summaries | High for return packages and release gates. | Medium. Best comparison needs per-case data from `report.jsonl`; summary-only compare is useful but limited. | Low to medium. Must not redefine pass/fail; only report deltas. | Do now with conservative output. |
| E - Runtime/slow-case reporting | Medium now, higher as corpus grows. | Low. Wrap each `run_case()` call with monotonic timing and summarize slowest cases. | Low. Adds report metadata only. | Do now if touching the harness. |
| F - Validation preset docs/scripts | Medium. Helps standardize decisions. | Low for docs, medium for Makefile because dynamic args are awkward. | Low. Risk is over-prescribing and creating stale targets. | Do docs now; defer Makefile targets beyond maybe `raw-query-answer-qa`. |
| G - Corpus schema wave tags | Medium. Helps expansion waves and new-cases-only runs. | Low for forward-only `added_in`; medium for historical backfill. | Low if optional; higher if backfilling many cases in same wave. | Add `added_in` going forward later. Do not backfill in the first execution wave. |

## 6. Recommended execution scope

- Exact goal:
  - Make Raw QA iteration faster without weakening the final full-corpus safety
    gate or changing any production behavior, tests, or existing corpus
    expectations.
- Features to implement:
  - `--slice <name-or-path>` loading from `qa/harness_slices/<name>.yaml` or a
    direct path.
  - Multiple `--slice` flags, composable with `--case`.
  - `--failed-from <summary.json-or-report.jsonl>` to rerun failed expectation
    cases from a prior run.
  - `--compare-to <summary.json-or-report.jsonl>` to write comparison metadata
    into `summary.json` and `report.md`.
  - Per-case `duration_seconds` in `report.jsonl`.
  - `slowest_cases` in `summary.json` and a small slowest-case table in
    `report.md`.
  - Docs for tiered validation presets and examples.
- Files likely to change:
  - `tools/raw_query_answer_qa.py`
  - `qa/harness_slices/*.yaml`
  - `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`
  - Possibly `Makefile` only if adding fixed convenience targets is still
    useful after docs examples.
- Slice files to add, if any:
  - `qa/harness_slices/defensive_aliases.yaml`
  - `qa/harness_slices/playoff_phrasing.yaml`
  - `qa/harness_slices/team_date_context.yaml`
  - `qa/harness_slices/player_entity_stat_context.yaml`
  - `qa/harness_slices/product_boundaries.yaml`
  - Optional: `qa/harness_slices/preview_smoke.yaml` for the six preview smoke
    cases, if it stays backend-only and does not claim visual coverage.
- Docs to update:
  - Harness plan usage examples for target, adjacent, failed-rerun, compare,
    and release-final validation.
  - Do not update current-state product docs unless behavior changes in a later
    wave.
- Tests to add:
  - Add small, query-free tests for slice loading, selection composition,
    failed-from parsing, and comparison summarization if the helper functions
    are factored cleanly.
  - Do not add tests that execute the full NBA query engine just to test harness
    selection mechanics.
- Validation commands:
  - `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case record_when_jokic_triple_double --case points_per_game_leader`
  - `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice product_boundaries`
  - `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --failed-from <known-prior-failing-summary-or-jsonl>`
  - `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --compare-to outputs/raw_query_answer_qa/20260516T221654Z/report.jsonl --case record_when_jokic_triple_double`
  - `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml`
  - `.venv/bin/ruff check tools/raw_query_answer_qa.py`
  - `git diff --check`
  - No frontend tests unless frontend files change.
- Stop conditions:
  - Any selection mode silently drops unknown case IDs.
  - `--slice`, `--case`, or `--failed-from` semantics conflict or are ambiguous.
  - Comparison output starts affecting pass/fail exit status.
  - Full corpus no longer passes 243/243 expectations.
  - Any production query behavior, tests, or existing corpus expectations need
    to change to make the harness feature work.

## 7. Deferred ideas

- Playwright visual automation.
- Frontend-copy full-corpus expansion.
- GitHub Actions artifacts for raw QA reports.
- CI caching or persistent output indexing.
- Auto-updating findings/checkpoint docs.
- Full report dashboards.
- `--tag`, `--category`, `--priority`, `--manual-status`,
  `--answer-text-policy`, and `--added-in` filters if saved slices are not
  enough.
- Historical `added_in` backfill for Wave 4 and Wave 5 cases.
- `latest-clean` run alias or symlink management.
- Makefile targets with environment-variable arguments, if the CLI examples
  still feel too long after slices land.

## 8. Validation performed

Files inspected:

- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md`
- `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md`
- `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`
- `qa/raw_query_answer_corpus.yaml`
- `tools/raw_query_answer_qa.py`
- `outputs/raw_query_answer_qa/20260516T221654Z/report.md`
- `outputs/raw_query_answer_qa/20260516T221654Z/report.jsonl`
- `outputs/raw_query_answer_qa/20260516T221654Z/summary.json`
- `return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_8D_PRODUCT_BOUNDARY_FINALIZATION_RETURN_PACKAGE.md`
- `return_packages/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST_RETURN_PACKAGE.md`
- `return_packages/raw-product/RAW_PRODUCT_PREVIEW_MANUAL_QA_RERUN_RETURN_PACKAGE.md`
- `Makefile`
- `pyproject.toml`
- `frontend/package.json`
- Root `package.json` check: no root `package.json` exists.

Commands and probes run:

```text
git status --short
sed -n '1,240p' tools/raw_query_answer_qa.py
sed -n '241,520p' tools/raw_query_answer_qa.py
sed -n '521,920p' tools/raw_query_answer_qa.py
sed -n '921,1280p' tools/raw_query_answer_qa.py
sed -n '1281,1680p' tools/raw_query_answer_qa.py
sed -n '1681,2100p' tools/raw_query_answer_qa.py
sed -n '1,220p' qa/raw_query_answer_corpus.yaml
sed -n '1,220p' docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md
sed -n '221,520p' docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md
sed -n '1,220p' docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md
sed -n '220,520p' docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md
sed -n '1,240p' docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md
sed -n '240,520p' docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md
sed -n '1,220p' return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_8D_PRODUCT_BOUNDARY_FINALIZATION_RETURN_PACKAGE.md
sed -n '1,240p' return_packages/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST_RETURN_PACKAGE.md
sed -n '1,240p' return_packages/raw-product/RAW_PRODUCT_PREVIEW_MANUAL_QA_RERUN_RETURN_PACKAGE.md
sed -n '1,220p' Makefile
sed -n '1,220p' pyproject.toml
sed -n '1,220p' package.json
sed -n '1,240p' frontend/package.json
ls outputs/raw_query_answer_qa/20260516T221654Z
sed -n '1,180p' outputs/raw_query_answer_qa/20260516T221654Z/report.md
sed -n '1,220p' outputs/raw_query_answer_qa/20260516T221654Z/summary.json
head -n 1 outputs/raw_query_answer_qa/20260516T221654Z/report.jsonl
.venv/bin/python tools/raw_query_answer_qa.py --help
```

Structured corpus metadata probe:

```text
.venv/bin/python - <<'PY'
import collections
from pathlib import Path
import yaml
path=Path('qa/raw_query_answer_corpus.yaml')
data=yaml.safe_load(path.read_text())
cases=data['cases']
print('total', len(cases))
...
PY
```

Search probes:

```text
rg -n "raw-query|raw_query|qa:frontend|frontend-copy|visual-qa|slice|failed-from|compare-to" Makefile frontend/package.json docs/planning/raw-product return_packages/raw-product tools qa
rg -n "Targeted|Adjacent|Full corpus|make PYTEST|make test-parser|make test-query|ruff check|git diff --check|--case" return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_8*.md
rg -n "20260516T221654Z|Failed case IDs|Run ID|Started|Completed|case_count|manual_review_tag_counts|output_file_paths|duration|slow" outputs/raw_query_answer_qa/20260516T221654Z/summary.json outputs/raw_query_answer_qa/20260516T221654Z/report.md
rg -n "manual_review:|tags:|added_in:|slices:|answer_text_policy:|priority:|category:|_wave5" qa/raw_query_answer_corpus.yaml
rg -n "summary.json|failed_case_ids|manual_review_tag_counts|duration|slowest|compare|failed-from|--case|--limit|--tag|--category|--priority|manual_review|answer_text_policy" tools/raw_query_answer_qa.py docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md outputs/raw_query_answer_qa/20260516T221654Z/summary.json
```

No raw harness execution, tests, production build, or frontend QA run was
performed for this preflight because the task was investigation/design only.
