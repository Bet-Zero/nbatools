# Opponent-Conference Preview Data Path Preflight Return Package

## 1. Executive summary

- Root cause hypothesis: the preview runtime is using `DATA_SOURCE=r2`, but the new trusted team-conference membership file was not synced to the R2 bucket.
- Confirmed root cause if known: confirmed. R2 returns `404` for `raw/teams/team_conference_membership.csv`, while adjacent R2 objects such as `raw/teams/team_history_reference.csv`, `raw/teams/teams_reference.csv`, and the 2024-25 / 2025-26 `team_game_stats` files exist.
- Production code changed? no
- Tests changed? no
- Corpus changed? no
- Recommended execution: sync `data/raw/teams/team_conference_membership.csv` to R2, add a deploy/data availability check for this trusted reference file, then redeploy/rerun the opponent-conference preview smoke. Consider improving missing-membership diagnostics so this failure does not collapse into generic `no_data`.
- Preview status remains: `BLOCKED`

## 2. Local vs preview behavior

| Query | Local behavior | Preview behavior | Difference |
|---|---|---|---|
| Celtics record against the East this season | `team_record`, `ok`; `opponent_team_abbrs` count `15`; `36-16`, 52 games. | `team_record`, `no_result` / `no_data`; `metadata.opponent_conference=East`; `metadata.opponent_team_abbrs=null`. | Local resolves trusted East teams; preview cannot resolve the opponent list. |
| Lakers record against the West | `team_record`, `ok`; `opponent_team_abbrs` count `15`; `33-19`, 52 games. | `team_record`, `no_result` / `no_data`; `metadata.opponent_conference=West`; `metadata.opponent_team_abbrs=null`. | Local resolves trusted West teams; preview cannot resolve the opponent list. |
| Lakers road record against West last season | `team_record`, `ok`; `opponent_team_abbrs` count `15`; `14-12`, 26 games. | `team_record`, `no_result` / `no_data`; season/location metadata preserved. | Local resolves 2024-25 West teams; preview preserves context but has no resolved teams. |
| Knicks record against Eastern Conference teams since January 1 | `team_record`, `ok`; `opponent_team_abbrs` count `15`; `17-9`, 26 games. | `team_record`, `no_result` / `no_data`; date/conference metadata preserved. | Local resolves East teams and date filter; preview preserves context but has no resolved teams. |

## 3. Data source/path investigation

| Area | Finding | Evidence | Impact |
|---|---|---|---|
| Preview data source | Preview is configured for R2, not packaged filesystem data. | `vercel.json` sets `DATA_SOURCE=r2` and `R2_BUCKET_NAME=nbatools-data`; all Vercel function entries exclude `data/**`. | Runtime must fetch data from Cloudflare R2. Committed local CSVs are not present in the function bundle. |
| `DATA_SOURCE=r2` meaning | The app uses `src/nbatools/data_source.py` to map logical paths to R2 keys, lazily downloading objects to a temp cache. | `_R2DataSource.resolve_path()` strips the leading `data/` and requests keys like `raw/teams/team_conference_membership.csv`. | Local path `data/raw/teams/team_conference_membership.csv` must exist in R2 as key `raw/teams/team_conference_membership.csv`. |
| R2 object availability | The membership object is missing from R2. | Read-only R2 `head_object` returned `404` for `raw/teams/team_conference_membership.csv`. | Trusted conference filters cannot resolve in preview. |
| Adjacent R2 objects | Existing small team reference files and team game stats are present. | R2 `head_object` succeeded for `raw/teams/team_history_reference.csv`, `raw/teams/teams_reference.csv`, `raw/team_game_stats/2025-26_regular_season.csv`, and `raw/team_game_stats/2024-25_regular_season.csv`. | This is not a whole-bucket, credentials, team data, or `team_game_stats` outage. |
| R2 sync include logic | There is no separate object manifest for sync; `pipeline sync-r2` walks all files under `data/`, excluding hidden paths only. | `_iter_sync_files(Path("data"))` includes `raw/teams/team_conference_membership.csv`; local scan reported `total_sync_files=663`. | The likely operational fix is to run the existing R2 sync after the new file was committed, not to update a missing sync manifest. |
| Package data | Python package data only includes the UI bundle. | `pyproject.toml` has `nbatools = ["ui/dist/**"]`; `vercel.json` excludes `data/**`. | Package-data rules are not the preview data path for raw CSVs. |
| `.gitignore` | The membership CSV is explicitly allowed and versioned. | `.gitignore` ignores local data by default but allows `!data/raw/teams/team_conference_membership.csv`; `git ls-files` includes the file. | Git ignore rules are not the blocker. |
| Loader path | The loader path is explicit and uses the shared data source abstraction. | `data_utils.py` loads `data/raw/teams/team_conference_membership.csv`; R2 mode maps it to `raw/teams/team_conference_membership.csv`. | No separate hardcoded preview path was found. |

## 4. Membership file availability

- Local file exists: yes, `data/raw/teams/team_conference_membership.csv`.
- Committed/versioned: yes, `git ls-files data/raw/teams/team_conference_membership.csv` returns the file.
- Included in package/deploy: no as local filesystem data; Vercel excludes `data/**`, and Python package data only includes `ui/dist/**`.
- Included in R2/upload: not currently present in R2. The existing sync walker would include it, but the bucket key is missing.
- Loader path: `data/raw/teams/team_conference_membership.csv` through `data_exists()` / `data_read_csv()` in `src/nbatools/commands/data_utils.py`; in R2 this becomes `raw/teams/team_conference_membership.csv`.
- Failure mode when missing: `load_team_conference_membership()` raises `FileNotFoundError`. `execute_natural_query()` catches `FileNotFoundError` around execution and converts it to `NoResult(reason="no_data")`, leaving `metadata.opponent_conference` present but `metadata.opponent_team_abbrs` null. `get_teams_by_conference()` itself does not silently return an empty list when the file is missing.

## 5. /visual-qa JSON error investigation

- Failing request/case if identified: request path identified as `POST /query`; exact visual case not identified because Vercel request logs do not include the request body/query text.
- Response status/body: Vercel logs for the earlier `/visual-qa` run include one `POST /query` request id `cgt79-1779006270415-a7f06adda198` with `responseStatusCode=0`, while the function log line says `POST /query HTTP/1.1" 200`. This is consistent with an empty/aborted response reaching the browser, causing `Response.json()` to throw `Unexpected end of JSON input`.
- Likely cause: transient empty/aborted Vercel response during live `/visual-qa` concurrent query loading, not a stable backend JSON payload error. A serial replay of all 15 visual QA queries returned HTTP `200` with valid JSON for every case. A concurrency-3 replay, matching `VisualQaPage.tsx`, also returned HTTP `200` with valid JSON for every case, although several cases were slow.
- Recommended fix: add safer API client response handling so empty/non-JSON responses produce a useful request error that includes HTTP status/body preview when available. Separately, keep the API/Vercel handlers returning JSON on caught exceptions. For diagnosis, add temporary query/case id logging or a visual-QA replay harness that records case id, status, body length, and parse error.

## 6. Recommended execution scope

- Files likely to change:
  - `docs/operations/deployment.md` or release checklist docs: document that new small reference data must be synced to R2 before preview smoke.
  - `src/nbatools/deployment_monitoring.py` and `tests/test_deployment_monitoring.py`: add an opponent-conference smoke case or a deployment data availability assertion.
  - Optional: `src/nbatools/query_service.py` / `src/nbatools/commands/_natural_query_execution.py`: map missing conference-membership file to `conference_coverage` or add a diagnostic note/log without changing query semantics.
  - Optional visual QA hardening: `frontend/src/api/client.ts` and matching tests to avoid raw `Response.json()` failures on empty/non-JSON responses.
- Data/deploy artifacts likely to update:
  - R2 bucket key `raw/teams/team_conference_membership.csv`.
  - A fresh preview deployment after R2 sync.
- Tests/checks to add:
  - Deployment smoke assertion that `Celtics record against the East this season` returns `ok`, route `team_record`, and 15 resolved opponent teams.
  - Optional R2/data-source unit coverage that missing membership yields a specific diagnostic boundary, not a broad fallback.
  - Optional frontend API client test for empty error responses.
- Validation commands:
  - `nbatools-cli pipeline sync-r2 --dry-run`
  - `nbatools-cli pipeline sync-r2`
  - R2 read-only `head_object` for `raw/teams/team_conference_membership.csv`.
  - `DATA_SOURCE=r2 .venv/bin/python -c '<opponent-conference query probe>'`
  - `./.venv/bin/python tools/deployment_smoke.py --base-url <preview-url> --output outputs/deployment_smoke/<run>.json`
  - Preview smoke rerun for the four opponent-conference queries plus guardrails and `/visual-qa`.
- Preview rerun requirements:
  - Confirm `metadata.opponent_team_abbrs` has 15 teams for East/West supported cases.
  - Confirm `result_status=ok` and records match local QA.
  - Confirm geography and Conference Finals guardrails still refuse without broad fallback.
  - Confirm `/visual-qa` reports `Request errors 0`, or capture the failing request with case id/status/body length.
- Stop conditions:
  - R2 object still missing after sync.
  - Opponent-conference preview result remains `no_data` with null `opponent_team_abbrs`.
  - Any supported query broadens to an unfiltered full-season record.
  - `/visual-qa` still has an empty/non-JSON request without enough diagnostics to identify the case.

## 7. Validation performed

- Read handoff/source files:
  - `return_packages/raw-product/OPPONENT_CONFERENCE_PREVIEW_SMOKE_RERUN_RETURN_PACKAGE.md`
  - `return_packages/raw-product/OPPONENT_CONFERENCE_PROMOTION_RETURN_PACKAGE.md`
  - `return_packages/raw-product/TEAM_CONFERENCE_MEMBERSHIP_DATA_CONTRACT_RETURN_PACKAGE.md`
  - `data/raw/teams/team_conference_membership.csv`
  - `src/nbatools/commands/data_utils.py`
  - `src/nbatools/commands/_natural_query_execution.py`
  - `src/nbatools/commands/team_record.py`
  - `src/nbatools/query_service.py`
  - `src/nbatools/data_source.py`
  - `src/nbatools/commands/pipeline/sync_r2.py`
  - `src/nbatools/vercel_functions.py`
  - `src/nbatools/vercel_http.py`
  - `src/nbatools/api_handlers.py`
  - `src/nbatools/deployment_monitoring.py`
  - `api/query.py`
  - `vercel.json`
  - `.gitignore`
  - `pyproject.toml`
  - `docs/operations/deployment.md`
  - `frontend/src/VisualQaPage.tsx`
  - `frontend/src/api/client.ts`
  - `qa/frontend_visual_qa_corpus.json`
- Local direct probes:
  - `.venv/bin/python -c '<execute_natural_query probes for the four opponent-conference queries>'`
  - Results: all four local probes returned `team_record` / `ok` with `opponent_team_abbrs` count `15`.
- R2 object probes:
  - Read-only R2 `head_object` for `raw/teams/team_conference_membership.csv` returned `404`.
  - Read-only R2 `head_object` for adjacent known objects succeeded:
    - `raw/teams/team_history_reference.csv`
    - `raw/teams/teams_reference.csv`
    - `raw/team_game_stats/2025-26_regular_season.csv`
    - `raw/team_game_stats/2024-25_regular_season.csv`
- Sync include check:
  - `.venv/bin/python -c '<_iter_sync_files(Path("data")) membership include check>'`
  - Result: `raw/teams/team_conference_membership.csv True`; total local sync files `663`.
- Preview direct probes:
  - `curl -sS -i -X POST <preview>/query ... Celtics record against the East this season`
  - `curl -sS -i -X POST <preview>/query ... Lakers record against the West`
  - Results: HTTP `200`, JSON `no_result` / `no_data`, `metadata.opponent_team_abbrs=null`.
- Current-code R2 failure-mode probe:
  - `DATA_SOURCE=r2 .venv/bin/python -c '<execute_natural_query Celtics record against the East this season>'`
  - Result: `team_record` / `no_result` / `no_data`, `opponent_conference=East`, `opponent_team_abbrs=None`.
  - `DATA_SOURCE=r2 .venv/bin/python -c '<get_teams_by_conference probes>'`
  - Result: missing file raises `FileNotFoundError`.
- Visual QA probes:
  - Serial Node replay of all 15 `qa/frontend_visual_qa_corpus.json` cases against preview `/query`: all returned HTTP `200` with valid JSON.
  - Concurrency-3 Node replay matching `VisualQaPage.tsx`: all returned HTTP `200` with valid JSON.
  - `npx vercel logs <preview> --since 2h --limit 100 --json --no-color --no-branch`
  - `npx vercel logs <preview> --request-id cgt79-1779006270415-a7f06adda198 --expand --json --no-color --no-branch`
  - Evidence: one earlier `/visual-qa`-era `POST /query` log had `responseStatusCode=0`, consistent with the browser's empty JSON parse failure.
