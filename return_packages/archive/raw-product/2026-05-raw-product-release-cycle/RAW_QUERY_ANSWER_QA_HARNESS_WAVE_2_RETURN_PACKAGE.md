# Raw Query Answer QA Harness Wave 2 Return Package

## 1. Executive summary

- What changed: expanded the Raw Query Answer QA corpus, added manual-review and triage metadata to the harness reports, created a findings inventory, and updated the harness plan with Wave 2 status.
- Production code changed? no
- Tests changed? no
- Corpus size before/after: 12 -> 78 cases
- Latest output directory: `outputs/raw_query_answer_qa/20260511T043039Z/`
- Main finding: the expanded corpus produced no expectation failures, but it grouped review issues around opponent-quality semantics, top-performance data quality, record-when filters, missing-filter policy, date handling, and frontend hero extraction.
- Recommended next step: review and prioritize `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` by fix family before implementation.

## 2. Files changed

| File | Change type | Why |
|---|---|---|
| `qa/raw_query_answer_corpus.yaml` | Modified | Expanded from 12 to 78 curated answer-QA cases and added optional `manual_review` metadata on cases needing triage. |
| `tools/raw_query_answer_qa.py` | Modified | Added manual-review fields, suggested review tags, suspicious flags, and summary/Markdown report sections. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` | Added | Living inventory of manual-review findings grouped by fix family. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | Modified | Added Wave 2 status, latest run, limitations, and next phase. |
| `docs/index.md` | Modified | Indexed the new raw query answer QA findings doc. |
| `return_packages/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_WAVE_2_RETURN_PACKAGE.md` | Added | Captures Wave 2 implementation, validation, and recommended next phase. |

## 3. Corpus expansion summary

| Category | Cases added | Notes |
|---|---:|---|
| Leaderboards | 10 | Added assists, rebounds, steals, blocks, shooting, team offense, team eFG%, team wins, and recent defense boundary coverage. |
| Top performances | 5 | Added team top scoring, named-player best game, single-team top scoring, and non-scoring single-game boundary cases. |
| Player summaries | 5 | Added season shorthand, recent form, opponent no-result, opponent quality, and home split summaries. |
| Team records and summaries | 6 | Added overall, opponent quality, home, opponent-threshold, scoring-threshold, and top-10-defense record cases. |
| Record-when / availability | 4 | Added player scoring/assist/threes conditions plus multi-player availability boundary. |
| Without-player / availability | 5 | Added shorthand, full-question, does-not-play, team-star, and wins-without variants. |
| Finder/count/game log | 6 | Added distinct counts, opponent-under-threshold count, grouped player finder, threes finder, and team multi-condition finder. |
| Streaks | 4 | Added player threshold, active/current, team win, and team scoring-threshold streaks. |
| Rolling stretches | 4 | Added 5-game assists, named-player rebounds/scoring, and team-scope boundary coverage. |
| Playoff/history | 5 | Added Finals appearances, Finals leaderboard, Finals record, playoff appearances leaderboard, and Lakers-Celtics matchup history. |
| Date/date-range | 4 | Added explicit date, since All-Star break, month, and since-January cases. |
| Splits/schedule/clutch | 5 | Added home/away, wins/losses, back-to-back, rest-advantage, and clutch unsupported coverage. |
| Unsupported/ambiguous | 3 | Added subjective best defender, MVP candidates, and vague best-player-lately boundaries. |

## 4. Harness/report changes

- Manual review fields: reports now include `manual_review.status`, `manual_review.tags`, and `manual_review.notes`, defaulting to `unreviewed`.
- Triage flags: report rows can include `suspicious_flags` and `suggested_review_tags`.
- Suspicious flag coverage: missing backend answer text for P0/P1 summary routes, ok result with no sections, unusually high player top-performance point totals, `playoff teams` queries returning `season_type=Playoffs`, expected unsupported/error cases returning ok, and expected-ok cases returning no-result/error.
- Expectation behavior: suspicious flags do not fail cases; hard expectation pass/fail behavior is unchanged.
- Anything intentionally not changed: production query behavior, frontend rendering, parser examples, and broad hard tests.

## 5. Latest run summary

- Run ID: `20260511T043039Z`
- Status counts: `ok: 68`, `no_result: 4`, `error: 6`
- Expectation pass/fail counts: cases `pass: 78`; checks `pass: 375`
- Suspicious/review flags count: 22 flagged cases
- Failed case IDs: `[]`
- Output paths:
  - `outputs/raw_query_answer_qa/20260511T043039Z/report.jsonl`
  - `outputs/raw_query_answer_qa/20260511T043039Z/report.md`
  - `outputs/raw_query_answer_qa/20260511T043039Z/summary.json`

## 6. Findings inventory

| Finding ID | Priority | Finding type | Case/query | Recommended fix family | Status |
|---|---|---|---|---|---|
| AQ-001 | P1 | semantics_issue | `celtics_record_playoff_teams` | opponent-quality semantics | open |
| AQ-002 | P1 | data_quality_question | `biggest_scoring_games` | top-performance data quality | open |
| AQ-003 | P2 | expected limitation | Many P0/P1 summary routes | frontend hero extraction | deferred |
| AQ-004 | P1 | needs_followup | `lakers_held_opponents_under_100_record` | record-when conditions | open |
| AQ-005 | P1 | missing_filter | `lakers_lebron_ad_both_play` | unsupported/no-result policy | open |
| AQ-006 | P2 | needs_product_decision | `most_assists_single_game`, `most_rebounds_single_game` | unsupported/no-result policy | needs_manual_review |
| AQ-007 | P2 | missing_filter | `specific_date_jan_1` | data freshness/date handling | open |
| AQ-008 | P2 | needs_product_decision | `team_5_game_scoring_stretch` | unsupported/no-result policy | needs_manual_review |

## 7. Validation

Command:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --limit 10
```

Output summary:

```text
Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260511T042915Z
Cases: 10
Result statuses: {'ok': 10}
Expectation cases: {'pass': 10}
Suspicious flag cases: 4
Failed case IDs: none
```

Command:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml
```

Output summary:

```text
Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260511T042932Z
Cases: 78
Result statuses: {'error': 6, 'no_result': 4, 'ok': 68}
Expectation cases: {'pass': 78}
Suspicious flag cases: 22
Failed case IDs: none
```

Command:

```bash
make raw-query-answer-qa
```

Output summary:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml
Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260511T043039Z
Cases: 78
Result statuses: {'error': 6, 'no_result': 4, 'ok': 68}
Expectation cases: {'pass': 78}
Suspicious flag cases: 22
Failed case IDs: none
```

Additional check:

```bash
.venv/bin/ruff check tools/raw_query_answer_qa.py
```

Output:

```text
All checks passed!
```

Required final check:

```bash
git diff --check
```

Output:

```text
No output; passed with no whitespace errors.
```

## 8. Recommended next phase

Do not start with one-off fixes. Use the expanded sample to address grouped fix families:

- opponent-quality/playoff-team semantics
- top-performance data quality
- record-when condition variants
- unsupported/no-result policy for unimplemented or missing-filter cases
- frontend hero/rendered answer harness
- date handling for explicit single-date queries
