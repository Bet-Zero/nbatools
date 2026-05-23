# Opponent-Conference Preview R2 Sync Fix Return Package

## 1. Executive summary

- What was wrong: preview used `DATA_SOURCE=r2`, Vercel excludes `data/**`, and R2 was missing `raw/teams/team_conference_membership.csv`.
- What changed: synced the missing membership CSV to R2; added an opponent-conference deployment smoke assertion; mapped missing membership-file failures to the existing `conference_coverage` no-result guardrail; hardened the frontend API client for empty/non-JSON responses.
- R2 object synced: `raw/teams/team_conference_membership.csv`.
- Production query behavior changed? no.
- Parser behavior changed? no.
- Frontend behavior changed? yes, only API error diagnostics for empty/non-JSON responses. Successful response behavior is unchanged.
- Preview status after rerun: pass on the existing preview after R2 sync. No redeploy was required for the data-path unblock.
- Remaining risk: the new frontend API-client diagnostics require the next frontend deployment before they affect `/visual-qa`; the rerun already showed `/visual-qa` request errors at `0`.

## 2. R2 sync validation

| Check | Result | Evidence |
|---|---|---|
| Dry run includes membership CSV | Pass | `[661/663] would-upload raw/teams/team_conference_membership.csv (4999 bytes)` |
| Dry run summary | Pass | `Files scanned: 663`; `Files that would sync: 10`; `Files failed: 0`; `Bytes that would upload: 57843242` |
| Sync uploads membership CSV | Pass | `[661/663] upload raw/teams/team_conference_membership.csv (4999 bytes)` |
| Sync summary | Pass | `Files scanned: 663`; `Files synced: 10`; `Files failed: 0`; `Bytes uploaded: 57843242` |
| R2 head_object | Pass | `ContentLength=4999`; `LastModified=2026-05-17T09:03:29+00:00`; `nbatools-md5=f9cc9a60c8f659651723a55640966d73` |

Exact command outputs:

```text
$ .venv/bin/nbatools-cli pipeline sync-r2 --dry-run
[661/663] would-upload raw/teams/team_conference_membership.csv (4999 bytes)
R2 sync mode: dry run
Data directory: data
Bucket: nbatools-data
Files scanned: 663
Files that would sync: 10
Files skipped: 653
Files failed: 0
Bytes that would upload: 57843242
```

```text
$ .venv/bin/nbatools-cli pipeline sync-r2
[661/663] upload raw/teams/team_conference_membership.csv (4999 bytes)
R2 sync mode: sync
Data directory: data
Bucket: nbatools-data
Files scanned: 663
Files synced: 10
Files skipped: 653
Files failed: 0
Bytes uploaded: 57843242
```

```text
$ .venv/bin/python -c "<head_object raw/teams/team_conference_membership.csv>"
{'ContentLength': 4999, 'LastModified': '2026-05-17T09:03:29+00:00', 'Metadata': {'nbatools-md5': 'f9cc9a60c8f659651723a55640966d73'}}
```

## 3. DATA_SOURCE=r2 validation

| Query/check | Expected | Actual | Verdict |
|---|---|---|---|
| Celtics record against the East this season | `team_record`, `ok`, 15 opponents, 52 games, 36-16 | `team_record`, `ok`, 15 opponents, 52 games, 36-16 | Pass |
| Lakers record against the West | `team_record`, `ok`, 15 opponents, 52 games, 33-19 | `team_record`, `ok`, 15 opponents, 52 games, 33-19 | Pass |
| Celtics record against east coast teams | unsupported/no-result, no broad fallback | `team_record`, `no_result`, `filter_not_supported`, `unsupported_filters=["opponent_conference"]` | Pass |
| Direct 2025-26 membership counts | East 15, West 15 | East 15, West 15 | Pass |

Exact command outputs:

```text
$ DATA_SOURCE=r2 .venv/bin/python -c "<execute_natural_query probes>"
{"query": "Celtics record against the East this season", "route": "team_record", "status": "ok", "reason": null, "opponent_conference": "East", "opponent_team_abbrs_count": 15, "unsupported_filters": null, "games": 52, "wins": 36, "losses": 16}
{"query": "Lakers record against the West", "route": "team_record", "status": "ok", "reason": null, "opponent_conference": "West", "opponent_team_abbrs_count": 15, "unsupported_filters": null, "games": 52, "wins": 33, "losses": 19}
{"query": "Celtics record against east coast teams", "route": "team_record", "status": "no_result", "reason": "filter_not_supported", "opponent_conference": null, "opponent_team_abbrs_count": 0, "unsupported_filters": ["opponent_conference"], "games": null, "wins": null, "losses": null}
```

```text
$ DATA_SOURCE=r2 .venv/bin/python -c "<get_teams_by_conference counts>"
{"season": "2025-26", "East_count": 15, "West_count": 15}
```

## 4. Deployment monitoring / diagnostics

- Checks added: `default_smoke_cases()` now includes `Celtics record against the East this season` and validates `ok=True`, route `team_record`, result status `ok`, metadata `opponent_conference=East`, and `opponent_team_abbrs` length `15`.
- Tests added/updated: `tests/test_deployment_monitoring.py` now covers the new smoke case and nested JSON path assertions; `tests/test_query_service.py` now covers missing membership-file behavior.
- Missing-data diagnostics changed? yes. A missing `team_conference_membership.csv` during opponent-conference resolution now returns the existing honest no-result boundary `filter_not_supported` with `unsupported_filters=["conference_coverage"]` instead of falling through to generic `no_data`.

Live deployment smoke with the new check:

```text
$ .venv/bin/python tools/deployment_smoke.py --base-url https://nbatools-4vme9ylii-brents-projects-686e97fc.vercel.app --output outputs/deployment_smoke/opponent_conference_r2_sync_fix_preview.json
"ok": true
"case_count": 7
"failure_count": 0
"failures": []
"slug": "query_celtics_record_against_east_current"
"route": "team_record"
"result_status": "ok"
"opponent_conference": "East"
"opponent_team_abbrs_count": 15
```

Full JSON report:

```text
outputs/deployment_smoke/opponent_conference_r2_sync_fix_preview.json
```

## 5. /visual-qa JSON error follow-up

- Reproduced? no.
- Fix/hardening added? yes. `frontend/src/api/client.ts` now reads response text first, reports empty bodies as `HTTP <status>: empty response body`, and reports non-JSON bodies with a body preview.
- Preview rerun result: `/visual-qa` completed 15/15 cases with `Request errors 0`.
- Remaining action if any: deploy the API-client diagnostics with the next frontend build; no extra visual-QA diagnostics wave is needed unless the transient empty response returns.

Browser-level `/visual-qa` output:

```text
{"requestErrors":0,"loaded":15,"backend":"ok 10 / no result 5 / error 0","pageErrors":[]}
```

Note: the browser also reported external `cdn.nba.com` image/logo request failures (`net::ERR_HTTP2_PROTOCOL_ERROR`). These were not `/query` failures and did not affect the rendered `/visual-qa` request-error count.

## 6. Preview smoke rerun

Preview URL: `https://nbatools-4vme9ylii-brents-projects-686e97fc.vercel.app`

| Query/route | Expected | Actual | Verdict |
|---|---|---|---|
| Celtics record against the East this season | `team_record`, `ok`, 15 opponents, 52 games, 36-16 | `team_record`, `ok`, 15 opponents, 52 games, 36-16 | Pass |
| Lakers record against the West | `team_record`, `ok`, 15 opponents, 52 games, 33-19 | `team_record`, `ok`, 15 opponents, 52 games, 33-19 | Pass |
| Lakers road record against West last season | `team_record`, `ok`, 15 opponents, 26 games, 14-12 | `team_record`, `ok`, 15 opponents, 26 games, 14-12 | Pass |
| Knicks record against Eastern Conference teams since January 1 | `team_record`, `ok`, 15 opponents, 26 games, 17-9 | `team_record`, `ok`, 15 opponents, 26 games, 17-9 | Pass |
| Celtics record against east coast teams | unsupported/no-result, no broad fallback | `team_record`, `no_result`, `filter_not_supported`, `unsupported_filters=["opponent_conference"]` | Pass |
| Celtics conference finals record | unsupported/no-result, no broad fallback | `playoff_history`, `no_result`, `filter_not_supported`, `unsupported_filters=["single_team_playoff_round_record"]` | Pass |
| `/visual-qa` | `Request errors 0` | `loaded=15`, `Request errors 0`, backend `ok 10 / no result 5 / error 0` | Pass |

Exact preview query output:

```text
{"query": "Celtics record against the East this season", "http_ok": true, "ok": true, "route": "team_record", "status": "ok", "reason": null, "opponent_conference": "East", "opponent_team_abbrs_count": 15, "unsupported_filters": null, "games": 52, "wins": 36, "losses": 16}
{"query": "Lakers record against the West", "http_ok": true, "ok": true, "route": "team_record", "status": "ok", "reason": null, "opponent_conference": "West", "opponent_team_abbrs_count": 15, "unsupported_filters": null, "games": 52, "wins": 33, "losses": 19}
{"query": "Lakers road record against West last season", "http_ok": true, "ok": true, "route": "team_record", "status": "ok", "reason": null, "opponent_conference": "West", "opponent_team_abbrs_count": 15, "unsupported_filters": null, "games": 26, "wins": 14, "losses": 12}
{"query": "Knicks record against Eastern Conference teams since January 1", "http_ok": true, "ok": true, "route": "team_record", "status": "ok", "reason": null, "opponent_conference": "East", "opponent_team_abbrs_count": 15, "unsupported_filters": null, "games": 26, "wins": 17, "losses": 9}
{"query": "Celtics record against east coast teams", "http_ok": true, "ok": false, "route": "team_record", "status": "no_result", "reason": "filter_not_supported", "opponent_conference": null, "opponent_team_abbrs_count": 0, "unsupported_filters": ["opponent_conference"], "games": null, "wins": null, "losses": null}
{"query": "Celtics conference finals record", "http_ok": true, "ok": false, "route": "playoff_history", "status": "no_result", "reason": "filter_not_supported", "opponent_conference": null, "opponent_team_abbrs_count": 0, "unsupported_filters": ["single_team_playoff_round_record"], "games": null, "wins": null, "losses": null}
```

## 7. Validation

```text
$ .venv/bin/pytest tests/test_deployment_monitoring.py tests/test_query_service.py::TestOpponentConferenceTeamRecords -q -n0
12 passed in 46.66s
```

```text
$ make PYTEST=.venv/bin/pytest test-query
752 passed in 209.24s (0:03:29)
```

```text
$ npm test -- src/test/client.test.ts
Test Files  1 passed (1)
Tests  10 passed (10)
Duration  5.77s
```

```text
$ npm run lint
/Users/brenthibbitts/nba_tools/frontend/src/ReviewPage.tsx
  159:27  warning  The ref value 'abortControllersRef.current' will likely have changed by the time this effect cleanup function runs. If this ref points to a node rendered by React, copy 'abortControllersRef.current' to a variable inside the effect, and use that variable in the cleanup function  react-hooks/exhaustive-deps

1 problem (0 errors, 1 warning)
```

```text
$ npm run build
../src/nbatools/ui/dist/index.html                   0.77 kB | gzip:   0.41 kB
../src/nbatools/ui/dist/assets/index-CDraH1z9.css   73.64 kB | gzip:  12.63 kB
../src/nbatools/ui/dist/assets/index-DSKZFM-r.js   543.95 kB | gzip: 159.68 kB
✓ built in 940ms
(!) Some chunks are larger than 500 kB after minification.
```

```text
$ .venv/bin/ruff check src/nbatools/deployment_monitoring.py src/nbatools/commands/_natural_query_execution.py tests/test_deployment_monitoring.py tests/test_query_service.py
All checks passed!
```

```text
$ git diff --check
<no output; exit 0>
```

## 8. Files changed

| File | Change type | Why |
|---|---|---|
| `src/nbatools/deployment_monitoring.py` | Deployment smoke hardening | Add opponent-conference R2-sensitive smoke case and nested JSON assertions. |
| `tests/test_deployment_monitoring.py` | Test update | Cover the new smoke case and nested metadata length check. |
| `src/nbatools/commands/_natural_query_execution.py` | Diagnostic guardrail | Treat missing conference membership file as `conference_coverage` unsupported boundary. |
| `tests/test_query_service.py` | Regression test | Prove missing membership file does not broaden to a fake team record or generic no-data. |
| `frontend/src/api/client.ts` | API diagnostics hardening | Preserve success behavior while making empty/non-JSON responses actionable. |
| `frontend/src/test/client.test.ts` | Test update | Cover text-based JSON parsing and empty/non-JSON error diagnostics. |
| `docs/operations/deployment.md` | Docs update | Document the deployment smoke membership-data check. |

## 9. Next recommendation

Mark preview ready with notes and refresh release package.
