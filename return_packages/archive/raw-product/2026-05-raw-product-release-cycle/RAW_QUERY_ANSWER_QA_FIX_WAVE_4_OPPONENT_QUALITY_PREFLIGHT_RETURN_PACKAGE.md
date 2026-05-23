# Raw Query Answer QA Fix Wave 4: Opponent-Quality / Playoff-Team Semantics Preflight Return Package

## 1. Executive summary

- Issue confirmed? yes.
- Actual root cause suspected: parser-side season-type detection. `detect_season_type()` returns `Playoffs` for any query containing `playoff`, `playoffs`, or `postseason`, including opponent-quality phrases like `against playoff teams`.
- Is data result wrong, metadata wrong, or both? both. The result is actually loaded and aggregated from playoff game logs, not merely labeled incorrectly.
- Recommended implementation: keep `playoff teams` / `postseason teams` / `teams that made the playoffs` as opponent-quality context unless the query also has explicit playoff-competition wording such as `playoff record`, `in the playoffs`, `playoff history`, `playoff games`, or playoff-round/history intent.
- Production code changed? no.
- Tests changed? no.
- Corpus changed? no.

## 2. AQ-001 reproduction

- Query: `What is the Celtics' record against playoff teams?`
- Route/status: `team_record`, `ok`.
- Parsed season_type: `Playoffs`.
- Parsed season: `2024-25`.
- Applied filters: `Opponent quality=playoff teams`.
- Summary record: Boston Celtics, `2024-25`, `Playoffs`, `11` games, `6` wins, `5` losses, `.545` win pct.
- Caveats: `record filtered to games vs 20 opponents (ATL, BOS, CHI, ...)`.
- Evidence of wrong behavior:
  - `src/nbatools/commands/_parse_helpers.py:493` sets `Playoffs` for any `playoff|playoffs|postseason` token.
  - `src/nbatools/commands/natural_query.py:460` stores that season type before opponent-quality detection.
  - `src/nbatools/commands/natural_query.py:555` defaults the season from that season type, so the query becomes `2024-25` playoffs instead of the latest regular season.
  - `src/nbatools/commands/natural_query.py:606` still detects `playoff teams` as opponent quality.
  - `src/nbatools/commands/natural_query.py:1786` passes the opponent-quality slot into route kwargs.
  - `src/nbatools/commands/_natural_query_execution.py:360` keeps the parsed season type while resolving opponent quality.
  - `src/nbatools/commands/team_record.py:252` loads team games for the passed `season_type`; `src/nbatools/commands/team_record.py:344` writes that same `season_type` into the summary row.
  - `src/nbatools/query_service.py:434` copies parsed `season_type` into payload metadata and `src/nbatools/query_service.py:506` marks the scope as `playoffs`.
- Whether result uses playoff games or regular-season games mislabeled: it uses playoff games. The `11` games, `6-5` record, and `current_through=2025-06-22` align with Boston's 2024-25 playoff sample. A direct regular-season opponent-quality probe for 2025-26 returns `54` games, `33-21`.

## 3. Nearby phrase behavior

| Query | Route | Status | Season type | Opponent quality? | Notes |
|---|---|---:|---|---|---|
| `What is the Celtics' record against playoff teams?` | `team_record` | `ok` | `Playoffs` | `playoff teams` | Wrong semantics; returns 2024-25 playoff record, `11`, `6-5`. |
| `What is the Celtics record against good teams?` | `team_record` | `ok` | `Regular Season` | `good teams` | Correct nearby opponent-quality behavior; 2025-26, `52`, `31-21`. |
| `What is the Lakers record against good teams?` | `team_record` | `ok` | `Regular Season` | `good teams` | Correct nearby opponent-quality behavior; 2025-26, `49`, `24-25`. |
| `Lakers record against top-10 defenses 2024-25` | `team_record` | `ok` | `Regular Season` | `top-10 defenses` | Correct explicit-season opponent-quality behavior; `28`, `13-15`. |
| `Lakers playoff history` | `playoff_history` | `ok` | `Playoffs` | no | Correct actual playoff history route; aggregated 1996-97 to 2024-25. |
| `What is the Celtics playoff record?` | `team_record` | `ok` | `Playoffs` | no | Correct actual playoff-game record semantics; 2024-25, `11`, `6-5`. |
| `Celtics record in the playoffs` | `team_record` | `ok` | `Playoffs` | no | Correct actual playoff-game record semantics; 2024-25, `11`, `6-5`. |
| `Celtics record against playoff teams in the regular season` | `team_record` | `ok` | `Playoffs` | `playoff teams` | Wrong: explicit regular-season wording is ignored because `playoff teams` triggers `Playoffs`. |
| `Celtics record against teams that made the playoffs` | `team_record` | `ok` | `Playoffs` | no | Wrong twice: phrase is not recognized as opponent quality, and `playoffs` flips season type. |
| `How has Jayson Tatum played against playoff teams this season?` | `player_game_summary` | `ok` | `Playoffs` | `playoff teams` | Same bug affects player summaries; current result is 2024-25 playoffs, `8` games. |
| `Tatum against teams that made the playoffs` | `player_game_summary` | `ok` | `Playoffs` | no | Same unrecognized phrase plus season-type flip. |

Direct regular-season manual probes show the execution layer already works once season type is regular:

| Manual execution target | Season type | Opponent bucket | Summary |
|---|---|---|---|
| Celtics record vs playoff teams, 2025-26 | `Regular Season` | 20 teams | `54` games, `33-21`, `.611` |
| Celtics record vs playoff teams, 2024-25 | `Regular Season` | 20 teams | `52` games, `33-19`, `.635` |
| Jayson Tatum vs playoff teams, 2025-26 | `Regular Season` | 20 teams | `12` games, `9-3`, `23.083` PPG |
| Jayson Tatum vs playoff teams, 2024-25 | `Regular Season` | 20 teams | `48` games, `31-17`, `26.938` PPG |

## 4. Proposed product semantics

- Opponent-quality phrases:
  - `against playoff teams`
  - `vs playoff teams`
  - `against postseason teams`
  - `vs postseason teams`
  - `against teams that made the playoffs`
  - `against teams that qualified for the playoffs`
  - `against playoff qualifiers`
- These should mean regular-season games by default, with opponent set resolved from latest regular-season standings or qualifying data for the selected season. With the current contract, `playoff teams` is `conference_rank <= 10` from standings snapshots.
- Actual playoff phrases:
  - `playoff record`
  - `postseason record`
  - `in the playoffs`
  - `in postseason`
  - `playoff history`
  - `playoff games`
  - `playoff series`
  - explicit round/history routes such as `Finals appearances`, `best finals record since 1980`
- These should mean `season_type=Playoffs` or a dedicated playoff route.
- Ambiguous phrases:
  - `Celtics vs playoff teams` with no stat/record verb currently routes to `game_finder`; recommended default is still opponent-quality regular-season context, but this is broader than AQ-001 if the execution wave wants to keep scope to summary/record phrases.
  - `Celtics record against playoff teams in the playoffs` is contradictory/redundant. Recommended behavior: explicit `in the playoffs` wins and uses `Playoffs`; the opponent-quality filter may be redundant but should not force a no-result by itself.
  - Entity-specific `Finals record`, such as `Celtics finals record`, is currently not cleanly supported and is already documented as a current boundary in `docs/reference/query_catalog.md`. Do not solve that in Wave 4.
- Explicit regular-season handling:
  - `in the regular season` should force `Regular Season` when paired with opponent-quality playoff-team language.
  - `this season` should follow the regular-season default once the phrase is classified as opponent quality, not playoff mode.

## 5. Recommended implementation plan

- Files to change:
  - `src/nbatools/commands/_parse_helpers.py`
  - `tests/test_natural_query_parser.py`
  - `tests/test_phase_e_opponent_quality_filters.py`
  - `tests/test_ui_failure_coverage.py`
  - `qa/raw_query_answer_corpus.yaml`
  - `docs/reference/query_catalog.md`
  - optionally `docs/reference/query_guide.md` only if adding a short query-guide example is desired
- Logic to change:
  - Add a small helper in `_parse_helpers.py` to identify playoff-team opponent-quality phrases.
  - Update `detect_season_type()` so these phrases do not imply `Playoffs` unless explicit playoff-competition wording is also present.
  - Extend `detect_opponent_quality()` to recognize `postseason teams`, `teams that made the playoffs`, and likely `teams that qualified for the playoffs`, mapping them to the existing `playoff teams` policy.
  - Keep the existing `playoff teams` glossary policy unchanged for this wave; the current policy already says latest regular-season standings, conference rank <= 10.
- Guardrails:
  - Preserve `Playoffs` for `playoff record`, `postseason record`, `in the playoffs`, `playoff history`, `playoff series`, and playoff matchup/history routes.
  - Do not change `team_record` aggregation; it is behaving correctly for the season type it receives.
  - Do not change opponent-quality resolution data placement or definitions in this wave.
  - Do not touch top-performance data quality, non-scoring top performances, team rolling stretches, or frontend hero extraction.
- Tests to add:
  - Parser:
    - `parse_query("Jokic against playoff teams")` has `opponent_quality.surface_term == "playoff teams"` and `season_type == "Regular Season"`.
    - `parse_query("Celtics record against playoff teams")` routes `team_record` with `route_kwargs.season_type == "Regular Season"`.
    - `parse_query("Celtics record against playoff teams in the regular season")` stays `Regular Season`.
    - `parse_query("Celtics record against teams that made the playoffs")` maps to `opponent_quality.surface_term == "playoff teams"` and stays `Regular Season`.
    - `parse_query("Celtics playoff record")`, `parse_query("Celtics record in the playoffs")`, and `parse_query("Lakers playoff history")` still use playoff semantics.
  - Execution/data-backed:
    - Exact AQ-001 natural query returns `team_record`, `ok`, metadata `season_type == "Regular Season"`, quality applied filter, and summary `games == 54`, `wins == 33`, `losses == 21` for current default 2025-26 data.
    - Player companion query, `How has Jayson Tatum played against playoff teams this season?`, returns `player_game_summary`, metadata `Regular Season`, quality applied filter, and a regular-season sample.
    - Existing top-10 defense and good-team tests continue to pass.
- Corpus expectations to update:
  - Update `celtics_record_playoff_teams` hard assertions to the new regular-season result after implementation verification.
  - Add at least one explicit playoff-record corpus guard so the change cannot accidentally de-playoff `playoff record` / `in the playoffs`.
  - Add a phrase-variant case for `teams that made the playoffs` if that phrase is shipped in Wave 4.

## 6. Risks

- Possible playoff-route regressions:
  - A broad `detect_season_type()` exemption could accidentally turn `playoff record` or `playoff history` into regular-season queries. Guard with explicit tests for actual playoff phrases and route helpers.
  - `Celtics vs Heat playoff record since 2020` should remain `playoff_matchup_history`, not regular-season matchup record.
- Possible opponent-quality regressions:
  - If `detect_opponent_quality()` patterns become too broad, they could swallow specific team opponents or route history phrases incorrectly. Keep patterns anchored to `against|vs|versus`.
  - `teams that made the playoffs` currently lacks a precise source-of-truth data contract beyond the existing `conference_rank <= 10` policy. If the product wants strict playoff-bracket qualifiers instead of play-in/top-10 qualifiers, that is a separate data-definition decision.
- Data dependency risks:
  - Existing `resolve_opponent_quality_teams()` explicitly ignores incoming `season_type` and resolves from regular-season standings/ratings. That is consistent with the recommended semantics, but it should be documented in tests and corpus expectations.
  - Default-season behavior will change from `2024-25` playoffs to `2025-26` regular season for AQ-001. This is expected, but it changes exact row counts.
- Open product decisions:
  - Whether `playoff teams` should mean top 10 by conference, top 8 playoff bracket teams, or teams that qualified after play-in. The current shipped glossary says top 10 by conference.
  - Whether generic fragments like `Celtics vs playoff teams` should be included in Wave 4 or left to a later query-surface expansion.
  - Whether entity-specific `Finals record` should become supported. Do not bundle this into AQ-001.

## 7. Validation performed

Read-only context and findings inspection:

```bash
git status --short
sed -n '1,240p' docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md
sed -n '1,260p' outputs/raw_query_answer_qa/20260512T105201Z/report.md
rg -n "celtics_record_playoff_teams|playoff teams|good teams|top-10 defenses|playoff record|playoff history|teams that made" qa/raw_query_answer_corpus.yaml docs/reference/query_catalog.md docs/reference/query_guide.md docs/reference/result_contracts/core_result_table_contracts.md tools/raw_query_answer_qa.py
sed -n '80,130p' qa/raw_query_answer_corpus.yaml
sed -n '450,590p' qa/raw_query_answer_corpus.yaml
sed -n '520,610p' docs/reference/query_catalog.md
sed -n '110,145p' docs/reference/query_catalog.md
sed -n '1,220p' return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_1_FILTERED_RECORD_CORRECTNESS_RETURN_PACKAGE.md
sed -n '1,220p' return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_2_UNSUPPORTED_MISSING_FILTER_POLICY_RETURN_PACKAGE.md
sed -n '1,220p' return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_3_DATE_FILTER_DROP_PREVENTION_RETURN_PACKAGE.md
find outputs/raw_query_answer_qa/20260512T105201Z -maxdepth 2 -type f
```

Summary:

- Worktree was clean before this package.
- Latest raw QA report confirms AQ-001 as the only `playoff_teams_playoff_season_type` suspicious flag.
- Corpus currently expects only route/filter/section shape for `celtics_record_playoff_teams`; it does not yet assert the desired regular-season record.
- Prior waves intentionally left AQ-001 untouched.

Read-only report extraction:

```bash
.venv/bin/python -c "import json; p='outputs/raw_query_answer_qa/20260512T105201Z/report.jsonl'; ids=set('celtics_record_playoff_teams,tatum_good_teams,lakers_good_teams_record,lakers_top_10_defenses_record,lakers_playoff_history'.split(',')); [print(json.dumps({k:obj.get(k) for k in ['id','query','result_status','result_reason','route','intent','query_class','metadata','applied_filters','caveats','notes','section_summaries','suspicious_flags']}, ensure_ascii=False, default=str)) for line in open(p) for obj in [json.loads(line)] if obj['id'] in ids]"
```

Summary:

- `celtics_record_playoff_teams`: metadata `season_type=Playoffs`, `current_through=2025-06-22`, summary `11`, `6-5`.
- `tatum_good_teams`, `lakers_good_teams_record`, and `lakers_top_10_defenses_record`: all stay `Regular Season`.
- `lakers_playoff_history`: correctly uses `Playoffs` on the dedicated playoff route.

Read-only parse and execution probe:

```bash
.venv/bin/python -c "exec('''import json
from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query
queries = [
    \"What is the Celtics' record against playoff teams?\",
    \"What is the Celtics record against good teams?\",
    \"What is the Lakers record against good teams?\",
    \"Lakers record against top-10 defenses 2024-25\",
    \"Lakers playoff history\",
    \"What is the Celtics playoff record?\",
    \"Celtics record in the playoffs\",
    \"Celtics record against playoff teams in the regular season\",
    \"Celtics record against teams that made the playoffs\",
    \"How has Jayson Tatum played against playoff teams this season?\",
    \"Tatum against teams that made the playoffs\",
]
def compact(row):
    if row is None:
        return None
    keys = [\"team_name\", \"player_name\", \"season_start\", \"season_end\", \"season_type\", \"games\", \"wins\", \"losses\", \"win_pct\", \"pts_avg\", \"reb_avg\", \"ast_avg\", \"seasons_appeared\"]
    return {k: row.get(k) for k in keys if k in row}
for q in queries:
    parsed = parse_query(q)
    qr = execute_natural_query(q)
    summary_row = None
    by_row = None
    if hasattr(qr.result, \"summary\") and qr.result.summary is not None and not qr.result.summary.empty:
        summary_row = qr.result.summary.iloc[0].to_dict()
    if hasattr(qr.result, \"by_season\") and qr.result.by_season is not None and not qr.result.by_season.empty:
        by_row = qr.result.by_season.iloc[0].to_dict()
    print(json.dumps({
        \"query\": q,
        \"parse_route\": parsed.get(\"route\"),
        \"parse_season\": parsed.get(\"season\"),
        \"parse_season_type\": parsed.get(\"season_type\"),
        \"parse_opp_quality\": parsed.get(\"opponent_quality\"),
        \"result_route\": qr.route,
        \"result_status\": qr.result_status,
        \"metadata_season\": qr.metadata.get(\"season\"),
        \"metadata_season_type\": qr.metadata.get(\"season_type\"),
        \"applied_filters\": qr.metadata.get(\"applied_filters\"),
        \"summary\": compact(summary_row),
        \"by_season\": compact(by_row),
    }, ensure_ascii=False, default=str))
''')"
```

Summary:

- The target and explicit `regular season` variant both parse as `Playoffs`.
- `teams that made the playoffs` currently does not set opponent quality and still parses as `Playoffs`.
- `Celtics playoff record`, `Celtics record in the playoffs`, and `Lakers playoff history` are legitimate playoff semantics.
- Player summaries are affected by the same parser issue.

Read-only manual regular-season execution probe:

```bash
.venv/bin/python -c "exec('''import json
from nbatools.commands.natural_query import parse_query
from nbatools.commands.data_utils import resolve_opponent_quality_teams
from nbatools.commands.team_record import build_team_record_result
from nbatools.commands.player_game_summary import build_result as build_player_summary_result
probes = [
    (\"team\", \"What is the Celtics' record against playoff teams?\", \"2025-26\", \"Regular Season\"),
    (\"team\", \"What is the Celtics' record against playoff teams?\", \"2024-25\", \"Regular Season\"),
    (\"player\", \"How has Jayson Tatum played against playoff teams this season?\", \"2025-26\", \"Regular Season\"),
    (\"player\", \"How has Jayson Tatum played against playoff teams this season?\", \"2024-25\", \"Regular Season\"),
]
for kind, q, season, season_type in probes:
    parsed = parse_query(q)
    opponents = resolve_opponent_quality_teams(parsed[\"opponent_quality\"], [season], season_type)
    if kind == \"team\":
        result = build_team_record_result(team=parsed[\"team\"], season=season, season_type=season_type, opponent=opponents)
    else:
        result = build_player_summary_result(player=parsed[\"player\"], season=season, season_type=season_type, opponent=opponents)
    row = result.summary.iloc[0].to_dict()
    print(json.dumps({\"kind\": kind, \"season\": season, \"season_type\": season_type, \"opponents\": len(opponents), \"summary\": {k: row.get(k) for k in [\"team_name\", \"player_name\", \"season_type\", \"games\", \"wins\", \"losses\", \"win_pct\", \"pts_avg\"] if k in row}}, ensure_ascii=False, default=str))
''')"
```

Summary:

- Confirms the execution layer can produce the desired regular-season opponent-quality results without changing `team_record` or `player_game_summary`.
- Current default target after the parser fix should be 2025-26 Regular Season, Celtics `54`, `33-21`, `.611`.

Code-path inspection:

```bash
rg -n "def detect_season_type|def detect_opponent_quality|OPPONENT|playoff teams|good teams|teams that made" src/nbatools/commands/_parse_helpers.py
nl -ba src/nbatools/commands/_parse_helpers.py | sed -n '488,842p'
nl -ba src/nbatools/commands/natural_query.py | sed -n '430,720p'
nl -ba src/nbatools/commands/natural_query.py | sed -n '1758,1790p'
nl -ba src/nbatools/commands/_natural_query_execution.py | sed -n '344,370p'
nl -ba src/nbatools/commands/team_record.py | sed -n '207,350p'
nl -ba src/nbatools/query_service.py | sed -n '414,516p'
nl -ba src/nbatools/commands/data_utils.py | sed -n '449,456p'
nl -ba src/nbatools/commands/_glossary.py | sed -n '80,145p'
```

Summary:

- Root cause is isolated enough for implementation: parser season-type detection must distinguish opponent-quality playoff-team language from actual playoff competition language.
- No production code, tests, or corpus files were changed during preflight.
