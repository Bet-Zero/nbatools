# Raw Query Answer QA Fix Wave 7A: Answer Text Policy Classification Return Package

## 1. Executive summary

- What was wrong: the QA harness treated expected frontend-only hero text as suspicious `missing_backend_answer_text` for 22 P0/P1 summary-style cases.
- What changed: the corpus and harness now support `answer_text_policy`, and expected frontend-rendered hero cases are reported as informational instead of suspicious.
- Production code changed? no. Query execution, frontend rendering, routes, and backend answer metadata were not changed.
- Tests added/updated: focused harness tests for all answer-text policies and summary counting.
- Corpus updated: 22 cases marked `frontend_hero_expected`, 5 backend phrase/count cases marked `requires_backend_answer_text`, and 10 unsupported/no-result boundary cases marked `no_answer_text_expected`.
- Findings updated: AQ-003 is now `partially_addressed / reclassified_expected_limitation`.
- Latest harness run: `outputs/raw_query_answer_qa/20260513T044523Z/report.md`.
- Remaining risk: exact frontend-rendered hero extraction is still deferred; targeted backend answer phrase enrichment remains optional future work.

## 2. Answer text policy

- Allowed values: `requires_backend_answer_text`, `frontend_hero_expected`, `no_answer_text_expected`.
- `requires_backend_answer_text`: requires backend `metadata.answer_phrase` or `metadata.count_phrase`; missing text on an `ok` result creates open `missing_backend_answer_text`.
- `frontend_hero_expected`: missing backend text is informational `frontend_hero_expected`; React result components are expected to build the final hero.
- `no_answer_text_expected`: missing backend text is not flagged.
- Default behavior: cases without the field keep the legacy heuristic; P0/P1 summary-style `ok` results without backend text still become suspicious.
- Informational vs suspicious: expected frontend-only hero cases are informational; missing backend text is suspicious only when the policy requires backend text or legacy heuristic applies.

## 3. Files changed

| File | Change type | Why |
|---|---|---|
| `qa/raw_query_answer_corpus.yaml` | corpus classification | Adds optional `answer_text_policy` and labels the current AQ-003, backend-text, and no-answer boundary cases. |
| `tools/raw_query_answer_qa.py` | harness/reporting | Validates policy, computes `answer_text_status`, separates informational flags from suspicious flags, and emits new counters/Markdown fields. |
| `tests/test_raw_query_answer_qa.py` | tests | Covers frontend hero, required backend text, no-answer, and summary count behavior. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` | findings doc | Reclassifies AQ-003 and records latest run counts. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | plan doc | Adds Fix Wave 7A status and next recommendation. |
| `return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_7A_ANSWER_TEXT_POLICY_CLASSIFICATION_RETURN_PACKAGE.md` | return package | Captures implementation, validation, and remaining recommendations. |

## 4. Behavior after change

- Frontend-hero expected cases: no open suspicious flag; report shows `answer_text_policy: frontend_hero_expected`, `answer_text_status: frontend-rendered hero expected`, and informational `frontend_hero_expected`.
- Backend-answer required cases: `answer_phrase` or `count_phrase` passes cleanly; missing phrase creates open `missing_backend_answer_text`.
- No-answer expected cases: missing backend text is clean.
- Verified outlier behavior: unchanged; Bam Adebayo 83-point row remains a verified `top_performance_high_points` outlier.
- Production query output: unchanged.

## 5. Test coverage

- `test_frontend_hero_policy_is_informational_not_suspicious`: proves frontend hero policy does not create open missing-backend suspicious flags.
- `test_required_backend_answer_text_policy_flags_missing_phrase`: proves required backend text missing still flags.
- `test_required_backend_answer_text_policy_accepts_answer_or_count_phrase`: proves `answer_phrase` and `count_phrase` satisfy required backend text.
- `test_no_answer_text_expected_policy_does_not_flag_missing_phrase`: proves no-answer policy stays clean.
- `test_summary_counts_distinguish_informational_and_suspicious_flags`: proves summary counts separate informational and suspicious families.

## 6. QA harness validation

- Full harness command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml`
- Result: wrote `outputs/raw_query_answer_qa/20260513T044523Z`
- Expectation cases: `pass: 80`
- Expectation checks: `pass: 409`
- Result statuses: `ok: 70`, `no_result: 6`, `error: 4`
- Suspicious flag cases: `0`
- Suspicious flag counts: `{}`
- Informational flag cases: `22`
- Informational flag counts: `frontend_hero_expected: 22`
- Verified outlier cases: `1`
- Verified outlier counts: `top_performance_high_points: 1`
- Targeted harness command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case record_when_jokic_triple_double,jokic_triple_double_count`
- Targeted result: wrote `outputs/raw_query_answer_qa/20260513T044651Z`; 2 cases passed, 0 suspicious, 1 informational.

## 7. Standard validation

Harness:

```text
Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260513T044523Z
Cases: 80
Result statuses: {'error': 4, 'no_result': 6, 'ok': 70}
Expectation cases: {'pass': 80}
Suspicious flag cases: 0
Informational flag cases: 22
Verified outlier cases: 1
Failed case IDs: none
```

Tests:

```text
.venv/bin/pytest tests/test_raw_query_answer_qa.py -n0
8 passed in 1.01s
```

Always:

```text
git diff --check
<no output>
```

Optional:

```text
.venv/bin/ruff check tools/raw_query_answer_qa.py tests/test_raw_query_answer_qa.py
All checks passed!
```

## 8. Updated findings / next recommendation

- AQ-003 status: `partially_addressed / reclassified_expected_limitation`.
- Remaining open suspicious findings: none in the latest full corpus run.
- Recommended next phase: targeted backend `answer_phrase` enrichment for high-value record-style routes if API/CLI direct-answer text is now a priority; otherwise stop this cleanup and move to broader corpus expansion or visual QA.
