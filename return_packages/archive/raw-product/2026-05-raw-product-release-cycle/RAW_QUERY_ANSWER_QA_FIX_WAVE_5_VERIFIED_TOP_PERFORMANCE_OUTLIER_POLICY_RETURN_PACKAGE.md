# Raw Query Answer QA Fix Wave 5: Verified Top-Performance Outlier Policy Return Package

## 1. Executive summary

- What was wrong: AQ-002 treated Bam Adebayo's 83-point top-performance result as an open suspicious data-quality question.
- What preflight proved: the row is source-backed and official, with local player/team source agreement and external NBA.com plus ESPN/AP spot checks.
- What changed: the QA harness now loads a verified-outlier allowlist and separates open suspicious flags from verified official outliers.
- Production code changed? no
- Tests added/updated: added focused harness-unit tests in `tests/test_raw_query_answer_qa.py`.
- Corpus updated: `biggest_scoring_games` is now `verified_outlier` with `top_performance` and `verified_outlier` tags.
- Findings updated: AQ-002 is `closed_verified` / `verified_official_outlier`.
- Latest harness run: `outputs/raw_query_answer_qa/20260513T025137Z/report.md`
- Remaining risk: future extreme-but-unverified rows still need manual review or later ingestion validation policy.

## 2. Verified outlier policy

- Policy: official-source-backed rare outliers are displayed as-is; QA records verification instead of suppressing or capping the row.
- Allowlist file: `qa/verified_outliers.yaml`
- Matching rules: category, stat, value, date, game ID with leading-zero / zero-stripped normalization, and player identity by `player_id` when present or `player_name` fallback.
- What remains suspicious: new high-point top-performance rows at or above the QA threshold that do not match the allowlist.
- What is not suppressed: Bam Adebayo's 83-point row remains in `top_player_games` and stays visible in the QA report.

## 3. Files changed

| File | Change type | Why |
|---|---|---|
| `qa/verified_outliers.yaml` | Added | QA-only allowlist for verified official outliers. |
| `tools/raw_query_answer_qa.py` | Updated | Loads allowlist, classifies verified high-point rows separately, and reports verified-outlier counts. |
| `tests/test_raw_query_answer_qa.py` | Added | Covers verified, unverified, and game-ID-normalized high-point classification. |
| `qa/raw_query_answer_corpus.yaml` | Updated | Marks `biggest_scoring_games` as a verified outlier case. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` | Updated | Closes AQ-002 as verified official outlier and records latest counts. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | Updated | Adds Fix Wave 5 status and remaining fix families. |
| `docs/reference/result_contracts/core_result_table_contracts.md` | Updated | Adds short QA/data-quality policy for extreme top-performance rows. |

## 4. Behavior after change

- Biggest scoring games: still returns `top_player_games` with Bam Adebayo first at 83 points.
- Bam 83 report classification: `verified_outliers: top_performance_high_points`, not an open `suspicious_flags` item.
- New unverified high-point rows: remain open `top_performance_high_points` suspicious flags.
- Production query output: unchanged.

## 5. Test coverage

- `test_verified_high_point_outlier_is_not_open_suspicious`: proves an allowlisted high-point row moves to `verified_outliers` and leaves no open suspicious flag.
- `test_unverified_high_point_outlier_stays_open_suspicious`: proves a non-allowlisted high-point row remains an open suspicious flag.
- `test_verified_outlier_game_id_matching_handles_leading_zero_forms`: proves `0022500938` matches zero-stripped/integer-like `22500938`.

## 6. QA harness validation

- Targeted harness command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case biggest_scoring_games`
- Targeted result: run `20260513T025121Z`; cases `1`; result statuses `ok: 1`; expectation cases `pass: 1`; expectation checks `pass: 5`; suspicious flag cases `0`; verified outlier cases `1`; failed case IDs `none`.
- Full harness command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml`
- Full result: run `20260513T025137Z`; cases `80`; result statuses `ok: 69`, `no_result: 5`, `error: 6`; expectation cases `pass: 80`; expectation checks `pass: 401`; failed case IDs `[]`.
- Latest output path: `outputs/raw_query_answer_qa/20260513T025137Z/report.md`
- Expectation pass/fail counts: `pass: 401`, `fail: 0`
- Suspicious flags count: `missing_backend_answer_text: 22`
- Verified outlier count: `top_performance_high_points: 1`

## 7. Standard validation

Harness:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case biggest_scoring_games
Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260513T025121Z
Cases: 1
Result statuses: {'ok': 1}
Expectation cases: {'pass': 1}
Suspicious flag cases: 0
Verified outlier cases: 1
Failed case IDs: none

.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml
Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260513T025137Z
Cases: 80
Result statuses: {'error': 6, 'no_result': 5, 'ok': 69}
Expectation cases: {'pass': 80}
Suspicious flag cases: 22
Verified outlier cases: 1
Failed case IDs: none
```

Tests:

```text
.venv/bin/pytest tests/test_raw_query_answer_qa.py -n0
3 passed in 2.80s
```

Always:

```text
git diff --check
<no output>
```

Optional if touched:

```text
.venv/bin/ruff check tools/raw_query_answer_qa.py tests/test_raw_query_answer_qa.py
All checks passed!
```

## 8. Updated findings / next fix family recommendation

- AQ-002 status: `closed_verified`
- Remaining highest-priority findings: AQ-003 backend answer text / frontend hero extraction remains deferred; AQ-006 non-scoring top-performance routing still needs product decision; AQ-008 team-scoped rolling-stretch routing still needs product decision.
- Recommended next fix family: unsupported/no-result policy for remaining product boundaries, then frontend-rendered answer extraction or explicit product decisions for non-scoring top-performance and team rolling-stretch surfaces.
