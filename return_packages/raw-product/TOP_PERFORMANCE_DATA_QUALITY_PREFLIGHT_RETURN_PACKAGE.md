# Top-Performance Data Quality Preflight Return Package

## 1. Executive summary

- Bam 83 root cause: verified current-season source-backed event, not a route calculation bug. The raw row in `data/raw/player_game_stats/2025-26_regular_season.csv` contains Bam Adebayo's 83-point line, and NBA.com/ESPN external spot checks match the same game, score, and stat line.
- Is it isolated or systemic: isolated for the checked 2025-26 regular-season player-game outlier thresholds. It is the only 70+ and only 80+ player scoring row in the current source file.
- Route logic correct? yes for the scoring query. `top_player_games` reads player game rows, filters the requested season/type, sorts by the selected stat, and exposes the source row. It does strip the leading zero from `game_id` through pandas type inference, which is a traceability issue but not the scoring root cause.
- Source data issue? no for Bam 83. The row is official-source-backed and internally consistent with shooting math, player-team totals, team score, and external public game records.
- Recommended next step: do not patch/suppress Bam. Convert AQ-002 from "suspected bad data" to "verified exceptional outlier" and add QA/data-quality policy so improbable official rows are flagged for review without being capped or hidden.
- Production code changed? no
- Tests changed? no
- Data changed? no

## 2. Bam 83 trace

- Query: `What were the biggest scoring games this season?`
- Route: `top_player_games`
- Source file: `data/raw/player_game_stats/2025-26_regular_season.csv`
- Raw row / summarized raw row: `game_id=0022500938`, `game_date=2026-03-10`, `player_id=1628389`, `player_name=Bam Adebayo`, `team=MIA/Miami Heat`, `opponent=WAS/Washington Wizards`, `is_home=1`, `minutes=42`, `pts=83`, `fgm=20`, `fga=43`, `fg3m=7`, `fg3a=22`, `ftm=36`, `fta=43`, `reb=9`, `ast=3`, `stl=2`, `blk=2`, `tov=5`, `pf=3`, `plus_minus=20`.
- Game/player/team IDs: source `game_id=0022500938`; route output currently serializes it as integer-like `22500938`. `player_id=1628389`; `team_id=1610612748`; `opponent_team_id=1610612764`.
- Related team game evidence: `data/raw/team_game_stats/2025-26_regular_season.csv` has Miami 150, Washington 129, Miami `plus_minus=21`, Washington `plus_minus=-21`. Miami player stat sums match the Miami team row exactly for points, FGM/FGA, 3PM/3PA, FTM/FTA, rebounds, assists, steals, blocks, turnovers, and fouls.
- Does top_player_games transform it incorrectly or expose source data: it exposes source data. Points are not created from a merge or aggregate. The route reads the raw player-game row and sorts by `pts`.
- External spot check: NBA.com game page for `WAS-vs-MIA-0022500938` identifies the same March 10, 2026 game and "Bam. Adebayo. 83 points!": https://www.nba.com/game/WAS-vs-MIA-0022500938/boxscore. ESPN/AP recap matches the 150-129 score and Adebayo stat line: https://www.espn.com/nba/recap/_/gameId/401810793.

## 3. Top-performance route review

- Files inspected: `src/nbatools/commands/top_player_games.py`, `src/nbatools/commands/top_team_games.py`, `src/nbatools/commands/natural_query.py`, `src/nbatools/commands/_natural_query_execution.py`, `src/nbatools/query_service.py`, `qa/raw_query_answer_corpus.yaml`, `tools/raw_query_answer_qa.py`.
- Sorting/stat selection: `top_player_games` maps the requested stat through `ALLOWED_STATS`, then sorts by `[selected_stat, game_date, player_name]` with selected stat descending for normal top queries. For `pts`, Bam's 83 sorts first.
- Row source: `data/raw/player_game_stats/{season}_{season_type_safe}.csv`; `wl` is optionally merged from `team_game_stats` when missing. No team points are merged into the player `pts` column.
- Any route logic issues found: no scoring-stat calculation issue, no duplicate aggregation issue, no season/type mixing for this query, and rows are game-level player rows. Non-scoring natural-language top-performance routing remains unresolved as already tracked by AQ-006; direct structured `top_player_games` supports `ast` and `reb`.
- Traceability issue found: the route does not force `game_id` to string on read, so `0022500938` becomes `22500938` in route/API payloads. This did not cause AQ-002 but makes source tracebacks harder.

## 4. Outlier audit

| Check | Count | Examples | Notes |
|---|---:|---|---|
| Player points >= 70, 2025-26 | 1 | Bam Adebayo, MIA vs WAS, 2026-03-10, 83 points | Verified official outlier; isolated in current season. |
| Player points >= 80, 2025-26 | 1 | Bam Adebayo, 83 | Official-source-backed. |
| Player assists >= 25, 2025-26 | 0 | None | Direct structured top AST row is Ryan Nembhard, 23. |
| Player rebounds >= 30, 2025-26 | 0 | None | Direct structured top REB row is Scottie Barnes, 25. |
| Player blocks >= 12, 2025-26 | 0 | None | Top checked value: Victor Wembanyama, 9. |
| Player steals >= 10, 2025-26 | 0 | None | Top checked value: 8. |
| Player 3PM >= 15, 2025-26 | 0 | None | Top checked values: Stephen Curry and Trey Murphy III, 12. |
| Player minutes > 60, 2025-26 | 0 | None | Top checked value: Tyrese Maxey, 52. |
| Player points != shot formula, 2025-26 | 0 | None | `2*(FGM-3PM)+3*3PM+FTM` matched all checked rows. Bam: 83. |
| Player impossible shooting combos, 2025-26 | 0 | None | Checked FGM>FGA, 3PM>3PA, 3PM>FGM, FTM>FTA. |
| Team points >= 170, 2025-26 | 0 | None | Top team scoring route returns 157 as the high. |
| Team points <= 70, 2025-26 | 1 | BKN 66 at NYK, 2026-01-21 | Low but score/shot math is internally consistent. |
| Team points != shot formula, 2025-26 | 0 | None | Team points match made shots/free throws. |
| Team plus_minus != team pts - opponent pts, 2025-26 | 3 | LAL/CHI 2026-01-26, PHX/MIA 2026-01-13, MIA/TOR 2025-12-15 | Small decimal source values such as `10.6` vs expected `11`; unrelated to Bam and not used to compute his points. |
| Team game row count by game_id, 2025-26 | 0 bad games | 1,230 games, all with two team rows | Pairing is structurally sound. |
| All regular seasons player points >= 70 | 7 | Kobe 81, Bam 83, Luka 73, Donovan Mitchell 71, Damian Lillard 71, Devin Booker 70, Joel Embiid 70 | Bam is extraordinary but not the only historic high-scoring row in the dataset. |
| All regular seasons player points >= 80 | 2 | Kobe Bryant 81 in 2005-06; Bam Adebayo 83 in 2025-26 | The new row is exceptional, not structurally impossible. |

## 5. Data/source policy findings

- Dataset type: production query data is source-backed NBA data pulled through `nba_api` pipeline commands into local/R2 CSV datasets. The checked current file is `2025-26 Regular Season`, last manifested on `2026-05-07T05:25:08`; `data/metadata/last_refresh.json` reports success at `2026-05-07T05:39:39`. Tests and some frontend fixtures use synthetic rows, but this route is not using those fixtures.
- Current data trust assumptions: raw validation checks schema, uniqueness, basic shooting impossibilities, team row counts, and some processed/trust fields. It does not currently enforce high-stat outlier review, player sum vs team total checks, exact point-formula checks, or exact plus-minus/score reconciliation across all datasets.
- Recommended policy: do not cap or suppress official extreme performances. QA should flag improbable outputs for manual review, record verification evidence, and then allowlist/mark them as verified. Data-quality gates should distinguish hard impossibilities from "rare but official" rows.

## 6. Implementation options

| Option | What it does | Files likely touched | Pros | Cons | Recommendation |
|---|---|---|---|---|---|
| Option A - Data correction | Patch or regenerate a bad source row. | `data/raw/player_game_stats/...`, ingestion scripts, manifests | Correct when a row is objectively wrong. | Not appropriate here; would corrupt an official row. Production answer behavior would change incorrectly. | Do not use for Bam 83. |
| Option B - Ingestion validation | Add validation/reporting for point formula, player sums vs team totals, plus-minus reconciliation, and extreme-stat review. | `src/nbatools/commands/pipeline/validate_raw.py`, data-quality helper/tests, possibly docs | Catches real corruption earlier and documents trust checks. | Needs policy for warnings vs failures; hard caps would fail on valid Bam/Kobe-style rows. Could affect pipeline acceptance but not query answers unless made blocking. | Recommended as a follow-up, with warnings/allowlists for rare official rows. |
| Option C - QA outlier guardrails | Keep harness flags but add verified-outlier classification/allowlist so suspicious rows are triaged without implying wrong answers. | `tools/raw_query_answer_qa.py`, optional `qa/*outlier_allowlist*`, `qa/raw_query_answer_corpus.yaml`, findings docs, tests for harness classification | Best match for AQ-002. Preserves production output while improving review signal. | Does not prevent future bad imports by itself. | Recommended next wave. |
| Option D - Product documentation/defer | Mark Bam 83 as accepted official current-data behavior and document that extreme official rows are shown as-is. | `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md`, `qa/raw_query_answer_corpus.yaml`, possibly `docs/reference/query_catalog.md` if behavior wording changes | Low risk and clarifies product trust policy. | Without guardrails, future extreme rows keep looking suspicious. | Pair with Option C. |
| Option E - Route logic fix | Change top-performance route behavior. | `src/nbatools/commands/top_player_games.py`, `top_team_games.py`, route/API tests | Useful only for separate issues such as preserving `game_id` as a string. | No scoring logic bug was found; changing sorting/filtering could cause regressions. | Not recommended for AQ-002, except optional `game_id` string preservation as a separate traceability fix. |

## 7. Recommended execution scope

- Exact goal: close AQ-002 as a verified official top-performance outlier, keep the production answer intact, and improve QA/data-quality review so rare official rows are not confused with corrupted source data.
- Files to change: `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md`, `qa/raw_query_answer_corpus.yaml`, `tools/raw_query_answer_qa.py` if implementing a verified-outlier allowlist/classification, optional new QA allowlist file under `qa/`.
- Tests to add: focused harness/unit coverage for high-points suspicious classification, including one verified allowlisted row and one unverified high-points row. If adding ingestion validation, add tests for point formula, player-team stat sums, plus-minus reconciliation, and warning vs hard-fail policy.
- Harness/corpus updates: mark `biggest_scoring_games` manual review as pass/verified official outlier after adding verification notes; keep or reclassify the high-points flag so it is not reported as an open data-quality question once verified.
- Data/docs updates: no data correction. Update findings and, if policy is formalized, data contracts or operations docs with "rare official outliers are displayed, not capped" and "hard impossibilities are validation failures."
- Stop conditions: do not suppress Bam, do not cap high points, do not route non-scoring natural-language top-performance queries in this wave, and do not broaden production route behavior beyond optional `game_id` string preservation if that is explicitly included.

## 8. Validation performed

- Read QA and context docs: `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md`, latest QA report, corpus, harness, query catalog, result contracts, and the Wave 1-4 return packages.
- Inspected route/source files: `src/nbatools/commands/top_player_games.py`, `src/nbatools/commands/top_team_games.py`, `src/nbatools/commands/natural_query.py`, `src/nbatools/commands/_natural_query_execution.py`, `src/nbatools/query_service.py`, `src/nbatools/data_source.py`, pipeline pull/validation files.
- Located data files with `find data -maxdepth 3 -type f | sort` and inspected current source headers with `head`.
- Trace probe: read `data/raw/player_game_stats/2025-26_regular_season.csv`, selected Bam's 83-point row, joined/compared `data/raw/team_game_stats/2025-26_regular_season.csv`, `data/raw/games/2025-26_regular_season.csv`, `data/processed/player_game_features/2025-26_regular_season.csv`, and `data/processed/team_game_features/2025-26_regular_season.csv`.
- Team/player consistency probe: summed Miami and Washington player rows for `0022500938`; player sums matched team rows for points, shooting, rebounds, assists, steals, blocks, turnovers, and fouls.
- Outlier probe: checked current-season player thresholds for points, assists, rebounds, blocks, steals, 3PM, minutes, point-formula mismatches, and impossible shooting combos; checked team scoring extremes, shot-formula mismatches, plus-minus/score mismatches, and game pair counts.
- Historical context probe: scanned all regular-season `data/raw/player_game_stats/*_regular_season.csv` and `data/raw/team_game_stats/*_regular_season.csv` for high-scoring and low/high team-point outliers.
- Route probes: executed natural queries for `What were the biggest scoring games this season?`, `top team scoring games this season`, `most assists single game this season`, and `most rebounds single game this season`; executed direct structured `top_player_games` builds for `pts`, `ast`, `reb`, `fg3m`, `minutes`, `plus_minus`, and `top_team_games` builds for several team stats.
- QA report probe: read `outputs/raw_query_answer_qa/20260512T124917Z/report.jsonl` for `biggest_scoring_games`; confirmed the only suspicious flag is `top_performance_high_points`.
- External spot check: opened NBA.com game page `WAS-vs-MIA-0022500938` and ESPN/AP recap for Heat 150-129 Wizards on March 10, 2026; both match the local source row.
- Worktree check before writing: `git status --short` was clean. Only this return package was added.
