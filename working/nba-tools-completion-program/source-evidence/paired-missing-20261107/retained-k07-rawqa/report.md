# Raw Query Answer QA Report

## Run Metadata

- Run ID: `r2_validation`
- Started: `2026-11-07T02:19:01.166850+00:00`
- Completed: `2026-11-07T02:19:19.601761+00:00`
- Corpus: `qa/raw_query_answer_corpus.yaml`
- Slices: `[]`
- Cases: `12`

## Summary Counts

- Result statuses: `{'ok': 12}`
- Categories: `{'context_filter': 12}`
- Routes: `{'player_split_summary': 6, 'team_split_summary': 6}`
- Manual review statuses: `{'unreviewed': 12}`
- Manual review tags: `{}`
- Answer text policies: `{'frontend_hero_expected': 12}`
- Answer text statuses: `{'frontend_hero_expected': 12}`
- Suspicious flag cases: `0`
- Suspicious flags: `{}`
- Informational flag cases: `12`
- Informational flags: `{'frontend_hero_expected': 12}`
- Verified outlier cases: `0`
- Verified outliers: `{}`
- Suggested review tags: `{}`
- Expectation cases: `{'pass': 12}`
- Expectation checks: `{'pass': 308}`
- Failed case IDs: `[]`

## Slowest Cases

| Case | Seconds | Status | Route |
|---|---:|---|---|
| k07_a1 | 15.313 | ok | team_split_summary |
| k07_a2 | 2.372 | ok | player_split_summary |
| k07_b2_heldout | 0.163 | ok | player_split_summary |
| k07_a2_heldout | 0.122 | ok | player_split_summary |
| k07_b2 | 0.122 | ok | player_split_summary |
| k07_b1_heldout | 0.071 | ok | team_split_summary |
| k07_c2_heldout | 0.064 | ok | player_split_summary |
| k07_c2 | 0.062 | ok | player_split_summary |
| k07_c1_heldout | 0.045 | ok | team_split_summary |
| k07_b1 | 0.04 | ok | team_split_summary |

## Suspicious / Review Flags

_None._

## Informational Flags

| Case | Flags | Answer text policy | Answer text status |
|---|---|---|---|
| k07_a1 | frontend_hero_expected | frontend_hero_expected | frontend-rendered hero expected |
| k07_a2 | frontend_hero_expected | frontend_hero_expected | frontend-rendered hero expected |
| k07_b1 | frontend_hero_expected | frontend_hero_expected | frontend-rendered hero expected |
| k07_b2 | frontend_hero_expected | frontend_hero_expected | frontend-rendered hero expected |
| k07_c1 | frontend_hero_expected | frontend_hero_expected | frontend-rendered hero expected |
| k07_c2 | frontend_hero_expected | frontend_hero_expected | frontend-rendered hero expected |
| k07_a1_heldout | frontend_hero_expected | frontend_hero_expected | frontend-rendered hero expected |
| k07_a2_heldout | frontend_hero_expected | frontend_hero_expected | frontend-rendered hero expected |
| k07_b1_heldout | frontend_hero_expected | frontend_hero_expected | frontend-rendered hero expected |
| k07_b2_heldout | frontend_hero_expected | frontend_hero_expected | frontend-rendered hero expected |
| k07_c1_heldout | frontend_hero_expected | frontend_hero_expected | frontend-rendered hero expected |
| k07_c2_heldout | frontend_hero_expected | frontend_hero_expected | frontend-rendered hero expected |

## Verified Outliers

_None._

## Failed Expectations

_None._

## Query Review Cards

### k07_a1

#### k07_a1

**Query**  
Celtics record at home against Knicks in 2023-24 and 2025-26 by season

**Answer shown**  
Boston Celtics

**Rendered output**

##### Table — Split Comparison

Mode: team split  
Table type: split_comparison  
Column schema: split_comparison_default  
Rows: 2  

| Games | Wins | Losses | Win Pct | Pts Avg | Reb Avg | Ast Avg | Bucket | Stl Avg | Blk Avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | 2 | 1 | 66.7% | 118.7 | 35.7 | 25.3 | 2023-24 | 6.0 | 6.7 |
| 2 | 1 | 1 | 50.0% | 106.0 | 41.0 | 20.0 | 2025-26 | 5.0 | 3.0 |

- Query: `Celtics record at home against Knicks in 2023-24 and 2025-26 by season`
- Category: `context_filter`
- Priority: `p1`
- Status: `ok`
- Reason: `<none>`
- Route: `team_split_summary`
- Intent: `split_summary`
- Query class: `split_summary`
- Shape hint: `entity_summary`
- Shape source: `backend_approximation`
- Answer text policy: `frontend_hero_expected`
- Answer text status: frontend-rendered hero expected
- Backend answer text: _not backend-provided_
- Answer summary: Boston Celtics -- Regular Season
- Filters: `Opponent=NYK (team)`, `Location=Home (location)`, `Seasons=2023-24, 2025-26 (season)`
- Sections: `summary` 1 row(s), `split_comparison` 2 row(s)
- Expectations: `pass` (24 pass, 0 fail)
- Review notes: Frozen K07 independent raw oracle; exact filtered bucket keys, discrimination, W/L and arithmetic checked in test_k07_split_real_data.py. Original unmet positive baselines retained. No human or deployed acceptance inferred.
- Manual review: `unreviewed`
- Informational flags: `frontend_hero_expected`
- Caveats: `['filtered to games vs NYK']`

Section `summary`

- Rows: `1`
- Columns: team_name, season_start, season_end, season_type, split, games_total

| team_name | season_start | season_end | season_type | split | games_total |
| --- | --- | --- | --- | --- | --- |
| Boston Celtics | 2023-24 | 2025-26 | Regular Season | season | 5 |

Section `split_comparison`

- Rows: `2`
- Columns: bucket, games, wins, losses, win_pct, pts_avg, reb_avg, ast_avg, stl_avg, blk_avg, fg3m_avg, tov_avg, ...

| games | wins | losses | win_pct | pts_avg | reb_avg | ast_avg | bucket | stl_avg | blk_avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | 2 | 1 | 0.667 | 118.667 | 35.667 | 25.333 | 2023-24 | 6 | 6.667 |
| 2 | 1 | 1 | 0.5 | 106 | 41 | 20 | 2025-26 | 5 | 3 |

### k07_a2

#### k07_a2

**Query**  
Stephen Curry averages with at least 25 points against Portland in 2023-24 and 2025-26 by season

**Answer shown**  
Stephen Curry

**Rendered output**

##### Table — Split Comparison

Mode: player split  
Table type: split_comparison  
Column schema: split_comparison_default  
Rows: 2  

| Games | Wins | Losses | Win Pct | Pts Avg | Reb Avg | Ast Avg | Bucket | Minutes Avg | Stl Avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 2 | 0 | 100.0% | 29.0 | 4.0 | 1.5 | 2023-24 | 32.0 | 0.0 |
| 3 | 0 | 3 | 0.0% | 40.3 | 3.7 | 3.0 | 2025-26 | 32.0 | 1.3 |

- Query: `Stephen Curry averages with at least 25 points against Portland in 2023-24 and 2025-26 by season`
- Category: `context_filter`
- Priority: `p1`
- Status: `ok`
- Reason: `<none>`
- Route: `player_split_summary`
- Intent: `split_summary`
- Query class: `split_summary`
- Shape hint: `entity_summary`
- Shape source: `backend_approximation`
- Answer text policy: `frontend_hero_expected`
- Answer text status: frontend-rendered hero expected
- Backend answer text: _not backend-provided_
- Answer summary: Stephen Curry -- Regular Season
- Filters: `Opponent=POR (team)`, `pts min=25.0 (threshold)`, `Seasons=2023-24, 2025-26 (season)`
- Sections: `summary` 1 row(s), `split_comparison` 2 row(s)
- Expectations: `pass` (26 pass, 0 fail)
- Review notes: Frozen K07 independent raw oracle; exact filtered bucket keys, discrimination, W/L and arithmetic checked in test_k07_split_real_data.py. Original unmet positive baselines retained. No human or deployed acceptance inferred.
- Manual review: `unreviewed`
- Informational flags: `frontend_hero_expected`
- Caveats: `['filtered to games vs POR']`

Section `summary`

- Rows: `1`
- Columns: player_name, season_start, season_end, season_type, split, games_total

| player_name | season_start | season_end | season_type | split | games_total |
| --- | --- | --- | --- | --- | --- |
| Stephen Curry | 2023-24 | 2025-26 | Regular Season | season | 5 |

Section `split_comparison`

- Rows: `2`
- Columns: bucket, games, wins, losses, win_pct, minutes_avg, pts_avg, reb_avg, ast_avg, stl_avg, blk_avg, fg3m_avg, ...

| games | wins | losses | win_pct | pts_avg | reb_avg | ast_avg | bucket | minutes_avg | stl_avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 2 | 0 | 1 | 29 | 4 | 1.5 | 2023-24 | 32 | 0 |
| 3 | 0 | 3 | 0 | 40.333 | 3.667 | 3 | 2025-26 | 32 | 1.333 |

### k07_b1

#### k07_b1

**Query**  
Bucks record with at least 45 rebounds in 2023-24 and 2025-26 by season

**Answer shown**  
Milwaukee Bucks

**Rendered output**

##### Table — Split Comparison

Mode: team split  
Table type: split_comparison  
Column schema: split_comparison_default  
Rows: 2  

| Games | Wins | Losses | Win Pct | Pts Avg | Reb Avg | Ast Avg | Bucket | Stl Avg | Blk Avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 36 | 28 | 8 | 77.8% | 122.2 | 49.7 | 27.1 | 2023-24 | 6.3 | 5.2 |
| 23 | 14 | 9 | 60.9% | 112.5 | 48.4 | 25.2 | 2025-26 | 7.0 | 4.2 |

- Query: `Bucks record with at least 45 rebounds in 2023-24 and 2025-26 by season`
- Category: `context_filter`
- Priority: `p1`
- Status: `ok`
- Reason: `<none>`
- Route: `team_split_summary`
- Intent: `split_summary`
- Query class: `split_summary`
- Shape hint: `entity_summary`
- Shape source: `backend_approximation`
- Answer text policy: `frontend_hero_expected`
- Answer text status: frontend-rendered hero expected
- Backend answer text: _not backend-provided_
- Answer summary: Milwaukee Bucks -- Regular Season
- Filters: `reb min=45.0 (threshold)`, `Seasons=2023-24, 2025-26 (season)`
- Sections: `summary` 1 row(s), `split_comparison` 2 row(s)
- Expectations: `pass` (26 pass, 0 fail)
- Review notes: Frozen K07 independent raw oracle; exact filtered bucket keys, discrimination, W/L and arithmetic checked in test_k07_split_real_data.py. Original unmet positive baselines retained. No human or deployed acceptance inferred.
- Manual review: `unreviewed`
- Informational flags: `frontend_hero_expected`

Section `summary`

- Rows: `1`
- Columns: team_name, season_start, season_end, season_type, split, games_total

| team_name | season_start | season_end | season_type | split | games_total |
| --- | --- | --- | --- | --- | --- |
| Milwaukee Bucks | 2023-24 | 2025-26 | Regular Season | season | 59 |

Section `split_comparison`

- Rows: `2`
- Columns: bucket, games, wins, losses, win_pct, pts_avg, reb_avg, ast_avg, stl_avg, blk_avg, fg3m_avg, tov_avg, ...

| games | wins | losses | win_pct | pts_avg | reb_avg | ast_avg | bucket | stl_avg | blk_avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 36 | 28 | 8 | 0.778 | 122.222 | 49.667 | 27.139 | 2023-24 | 6.333 | 5.167 |
| 23 | 14 | 9 | 0.609 | 112.478 | 48.435 | 25.174 | 2025-26 | 7 | 4.217 |

### k07_b2

#### k07_b2

**Query**  
Devin Booker averages with at least 6 assists in 2023-24 and 2025-26 by season

**Answer shown**  
Devin Booker

**Rendered output**

##### Table — Split Comparison

Mode: player split  
Table type: split_comparison  
Column schema: split_comparison_default  
Rows: 2  

| Games | Wins | Losses | Win Pct | Pts Avg | Reb Avg | Ast Avg | Bucket | Minutes Avg | Stl Avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 46 | 31 | 15 | 67.4% | 26.0 | 4.8 | 8.3 | 2023-24 | 36.7 | 0.8 |
| 36 | 21 | 15 | 58.3% | 25.1 | 4.2 | 7.9 | 2025-26 | 34.9 | 0.8 |

- Query: `Devin Booker averages with at least 6 assists in 2023-24 and 2025-26 by season`
- Category: `context_filter`
- Priority: `p1`
- Status: `ok`
- Reason: `<none>`
- Route: `player_split_summary`
- Intent: `split_summary`
- Query class: `split_summary`
- Shape hint: `entity_summary`
- Shape source: `backend_approximation`
- Answer text policy: `frontend_hero_expected`
- Answer text status: frontend-rendered hero expected
- Backend answer text: _not backend-provided_
- Answer summary: Devin Booker -- Regular Season
- Filters: `ast min=6.0 (threshold)`, `Seasons=2023-24, 2025-26 (season)`
- Sections: `summary` 1 row(s), `split_comparison` 2 row(s)
- Expectations: `pass` (26 pass, 0 fail)
- Review notes: Frozen K07 independent raw oracle; exact filtered bucket keys, discrimination, W/L and arithmetic checked in test_k07_split_real_data.py. Original unmet positive baselines retained. No human or deployed acceptance inferred.
- Manual review: `unreviewed`
- Informational flags: `frontend_hero_expected`

Section `summary`

- Rows: `1`
- Columns: player_name, season_start, season_end, season_type, split, games_total

| player_name | season_start | season_end | season_type | split | games_total |
| --- | --- | --- | --- | --- | --- |
| Devin Booker | 2023-24 | 2025-26 | Regular Season | season | 82 |

Section `split_comparison`

- Rows: `2`
- Columns: bucket, games, wins, losses, win_pct, minutes_avg, pts_avg, reb_avg, ast_avg, stl_avg, blk_avg, fg3m_avg, ...

| games | wins | losses | win_pct | pts_avg | reb_avg | ast_avg | bucket | minutes_avg | stl_avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 46 | 31 | 15 | 0.674 | 25.957 | 4.826 | 8.348 | 2023-24 | 36.717 | 0.804 |
| 36 | 21 | 15 | 0.583 | 25.111 | 4.25 | 7.889 | 2025-26 | 34.944 | 0.75 |

### k07_c1

#### k07_c1

**Query**  
Nuggets home vs away splits against Timberwolves with at least 110 points in 2023-24

**Answer shown**  
Denver Nuggets

**Rendered output**

##### Table — Split Comparison

Mode: team split  
Table type: split_comparison  
Column schema: split_comparison_default  
Rows: 2  

| Games | Wins | Losses | Win Pct | Pts Avg | Reb Avg | Ast Avg | Bucket | Stl Avg | Blk Avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 0 | 100.0% | 116.0 | 44.0 | 31.0 | home | 7.0 | 8.0 |
| 1 | 1 | 0 | 100.0% | 115.0 | 49.0 | 26.0 | away | 5.0 | 1.0 |

- Query: `Nuggets home vs away splits against Timberwolves with at least 110 points in 2023-24`
- Category: `context_filter`
- Priority: `p1`
- Status: `ok`
- Reason: `<none>`
- Route: `team_split_summary`
- Intent: `split_summary`
- Query class: `split_summary`
- Shape hint: `entity_summary`
- Shape source: `backend_approximation`
- Answer text policy: `frontend_hero_expected`
- Answer text status: frontend-rendered hero expected
- Backend answer text: _not backend-provided_
- Answer summary: Denver Nuggets -- Regular Season
- Filters: `Opponent=MIN (team)`, `Location=Home (location)`, `Location=Away (location)`, `pts min=110.0 (threshold)`
- Sections: `summary` 1 row(s), `split_comparison` 2 row(s)
- Expectations: `pass` (26 pass, 0 fail)
- Review notes: Frozen K07 independent raw oracle; exact filtered bucket keys, discrimination, W/L and arithmetic checked in test_k07_split_real_data.py. Original unmet positive baselines retained. No human or deployed acceptance inferred.
- Manual review: `unreviewed`
- Informational flags: `frontend_hero_expected`
- Caveats: `['filtered to games vs MIN']`

Section `summary`

- Rows: `1`
- Columns: team_name, season_start, season_end, season_type, split, games_total

| team_name | season_start | season_end | season_type | split | games_total |
| --- | --- | --- | --- | --- | --- |
| Denver Nuggets | 2023-24 | 2023-24 | Regular Season | home_away | 2 |

Section `split_comparison`

- Rows: `2`
- Columns: bucket, games, wins, losses, win_pct, pts_avg, reb_avg, ast_avg, stl_avg, blk_avg, fg3m_avg, tov_avg, ...

| games | wins | losses | win_pct | pts_avg | reb_avg | ast_avg | bucket | stl_avg | blk_avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 0 | 1 | 116 | 44 | 31 | home | 7 | 8 |
| 1 | 1 | 0 | 1 | 115 | 49 | 26 | away | 5 | 1 |

### k07_c2

#### k07_c2

**Query**  
Jalen Brunson home vs away averages against Celtics with at least 20 points in 2023-24

**Answer shown**  
Jalen Brunson

**Rendered output**

##### Table — Split Comparison

Mode: player split  
Table type: split_comparison  
Column schema: split_comparison_default  
Rows: 2  

| Games | Wins | Losses | Win Pct | Pts Avg | Reb Avg | Ast Avg | Bucket | Minutes Avg | Stl Avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0 | 1 | 0.0% | 34.0 | 3.0 | 9.0 | home | 38.0 | 1.0 |
| 3 | 1 | 2 | 33.3% | 29.3 | 2.0 | 4.0 | away | 34.3 | 0.7 |

- Query: `Jalen Brunson home vs away averages against Celtics with at least 20 points in 2023-24`
- Category: `context_filter`
- Priority: `p1`
- Status: `ok`
- Reason: `<none>`
- Route: `player_split_summary`
- Intent: `split_summary`
- Query class: `split_summary`
- Shape hint: `entity_summary`
- Shape source: `backend_approximation`
- Answer text policy: `frontend_hero_expected`
- Answer text status: frontend-rendered hero expected
- Backend answer text: _not backend-provided_
- Answer summary: Jalen Brunson -- Regular Season
- Filters: `Opponent=BOS (team)`, `Location=Home (location)`, `Location=Away (location)`, `pts min=20.0 (threshold)`
- Sections: `summary` 1 row(s), `split_comparison` 2 row(s)
- Expectations: `pass` (26 pass, 0 fail)
- Review notes: Frozen K07 independent raw oracle; exact filtered bucket keys, discrimination, W/L and arithmetic checked in test_k07_split_real_data.py. Original unmet positive baselines retained. No human or deployed acceptance inferred.
- Manual review: `unreviewed`
- Informational flags: `frontend_hero_expected`
- Caveats: `['filtered to games vs BOS']`

Section `summary`

- Rows: `1`
- Columns: player_name, season_start, season_end, season_type, split, games_total

| player_name | season_start | season_end | season_type | split | games_total |
| --- | --- | --- | --- | --- | --- |
| Jalen Brunson | 2023-24 | 2023-24 | Regular Season | home_away | 4 |

Section `split_comparison`

- Rows: `2`
- Columns: bucket, games, wins, losses, win_pct, minutes_avg, pts_avg, reb_avg, ast_avg, stl_avg, blk_avg, fg3m_avg, ...

| games | wins | losses | win_pct | pts_avg | reb_avg | ast_avg | bucket | minutes_avg | stl_avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0 | 1 | 0 | 34 | 3 | 9 | home | 38 | 1 |
| 3 | 1 | 2 | 0.333 | 29.333 | 2 | 4 | away | 34.333 | 0.667 |

### k07_a1_heldout

#### k07_a1_heldout

**Query**  
For 2023-24 and 2025-26 separately, what was Boston's home record versus New York Knicks?

**Answer shown**  
Boston Celtics

**Rendered output**

##### Table — Split Comparison

Mode: team split  
Table type: split_comparison  
Column schema: split_comparison_default  
Rows: 2  

| Games | Wins | Losses | Win Pct | Pts Avg | Reb Avg | Ast Avg | Bucket | Stl Avg | Blk Avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | 2 | 1 | 66.7% | 118.7 | 35.7 | 25.3 | 2023-24 | 6.0 | 6.7 |
| 2 | 1 | 1 | 50.0% | 106.0 | 41.0 | 20.0 | 2025-26 | 5.0 | 3.0 |

- Query: `For 2023-24 and 2025-26 separately, what was Boston's home record versus New York Knicks?`
- Category: `context_filter`
- Priority: `p1`
- Status: `ok`
- Reason: `<none>`
- Route: `team_split_summary`
- Intent: `split_summary`
- Query class: `split_summary`
- Shape hint: `entity_summary`
- Shape source: `backend_approximation`
- Answer text policy: `frontend_hero_expected`
- Answer text status: frontend-rendered hero expected
- Backend answer text: _not backend-provided_
- Answer summary: Boston Celtics -- Regular Season
- Filters: `Opponent=NYK (team)`, `Location=Home (location)`, `Seasons=2023-24, 2025-26 (season)`
- Sections: `summary` 1 row(s), `split_comparison` 2 row(s)
- Expectations: `pass` (24 pass, 0 fail)
- Review notes: Frozen K07 independent raw oracle; exact filtered bucket keys, discrimination, W/L and arithmetic checked in test_k07_split_real_data.py. Original unmet positive baselines retained. No human or deployed acceptance inferred.
- Manual review: `unreviewed`
- Informational flags: `frontend_hero_expected`
- Caveats: `['filtered to games vs NYK']`

Section `summary`

- Rows: `1`
- Columns: team_name, season_start, season_end, season_type, split, games_total

| team_name | season_start | season_end | season_type | split | games_total |
| --- | --- | --- | --- | --- | --- |
| Boston Celtics | 2023-24 | 2025-26 | Regular Season | season | 5 |

Section `split_comparison`

- Rows: `2`
- Columns: bucket, games, wins, losses, win_pct, pts_avg, reb_avg, ast_avg, stl_avg, blk_avg, fg3m_avg, tov_avg, ...

| games | wins | losses | win_pct | pts_avg | reb_avg | ast_avg | bucket | stl_avg | blk_avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | 2 | 1 | 0.667 | 118.667 | 35.667 | 25.333 | 2023-24 | 6 | 6.667 |
| 2 | 1 | 1 | 0.5 | 106 | 41 | 20 | 2025-26 | 5 | 3 |

### k07_a2_heldout

#### k07_a2_heldout

**Query**  
Break Stephen Curry's averages against the Trail Blazers into 2023-24 and 2025-26, using only appearances with 25 or more points.

**Answer shown**  
Stephen Curry

**Rendered output**

##### Table — Split Comparison

Mode: player split  
Table type: split_comparison  
Column schema: split_comparison_default  
Rows: 2  

| Games | Wins | Losses | Win Pct | Pts Avg | Reb Avg | Ast Avg | Bucket | Minutes Avg | Stl Avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 2 | 0 | 100.0% | 29.0 | 4.0 | 1.5 | 2023-24 | 32.0 | 0.0 |
| 3 | 0 | 3 | 0.0% | 40.3 | 3.7 | 3.0 | 2025-26 | 32.0 | 1.3 |

- Query: `Break Stephen Curry's averages against the Trail Blazers into 2023-24 and 2025-26, using only appearances with 25 or more points.`
- Category: `context_filter`
- Priority: `p1`
- Status: `ok`
- Reason: `<none>`
- Route: `player_split_summary`
- Intent: `split_summary`
- Query class: `split_summary`
- Shape hint: `entity_summary`
- Shape source: `backend_approximation`
- Answer text policy: `frontend_hero_expected`
- Answer text status: frontend-rendered hero expected
- Backend answer text: _not backend-provided_
- Answer summary: Stephen Curry -- Regular Season
- Filters: `Opponent=POR (team)`, `pts min=25.0 (threshold)`, `Seasons=2023-24, 2025-26 (season)`
- Sections: `summary` 1 row(s), `split_comparison` 2 row(s)
- Expectations: `pass` (26 pass, 0 fail)
- Review notes: Frozen K07 independent raw oracle; exact filtered bucket keys, discrimination, W/L and arithmetic checked in test_k07_split_real_data.py. Original unmet positive baselines retained. No human or deployed acceptance inferred.
- Manual review: `unreviewed`
- Informational flags: `frontend_hero_expected`
- Caveats: `['filtered to games vs POR']`

Section `summary`

- Rows: `1`
- Columns: player_name, season_start, season_end, season_type, split, games_total

| player_name | season_start | season_end | season_type | split | games_total |
| --- | --- | --- | --- | --- | --- |
| Stephen Curry | 2023-24 | 2025-26 | Regular Season | season | 5 |

Section `split_comparison`

- Rows: `2`
- Columns: bucket, games, wins, losses, win_pct, minutes_avg, pts_avg, reb_avg, ast_avg, stl_avg, blk_avg, fg3m_avg, ...

| games | wins | losses | win_pct | pts_avg | reb_avg | ast_avg | bucket | minutes_avg | stl_avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 2 | 0 | 1 | 29 | 4 | 1.5 | 2023-24 | 32 | 0 |
| 3 | 0 | 3 | 0 | 40.333 | 3.667 | 3 | 2025-26 | 32 | 1.333 |

### k07_b1_heldout

#### k07_b1_heldout

**Query**  
Show Milwaukee's record for each of 2023-24 and 2025-26 in games where the Bucks grabbed at least 45 rebounds.

**Answer shown**  
Milwaukee Bucks

**Rendered output**

##### Table — Split Comparison

Mode: team split  
Table type: split_comparison  
Column schema: split_comparison_default  
Rows: 2  

| Games | Wins | Losses | Win Pct | Pts Avg | Reb Avg | Ast Avg | Bucket | Stl Avg | Blk Avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 36 | 28 | 8 | 77.8% | 122.2 | 49.7 | 27.1 | 2023-24 | 6.3 | 5.2 |
| 23 | 14 | 9 | 60.9% | 112.5 | 48.4 | 25.2 | 2025-26 | 7.0 | 4.2 |

- Query: `Show Milwaukee's record for each of 2023-24 and 2025-26 in games where the Bucks grabbed at least 45 rebounds.`
- Category: `context_filter`
- Priority: `p1`
- Status: `ok`
- Reason: `<none>`
- Route: `team_split_summary`
- Intent: `split_summary`
- Query class: `split_summary`
- Shape hint: `entity_summary`
- Shape source: `backend_approximation`
- Answer text policy: `frontend_hero_expected`
- Answer text status: frontend-rendered hero expected
- Backend answer text: _not backend-provided_
- Answer summary: Milwaukee Bucks -- Regular Season
- Filters: `reb min=45.0 (threshold)`, `Seasons=2023-24, 2025-26 (season)`
- Sections: `summary` 1 row(s), `split_comparison` 2 row(s)
- Expectations: `pass` (26 pass, 0 fail)
- Review notes: Frozen K07 independent raw oracle; exact filtered bucket keys, discrimination, W/L and arithmetic checked in test_k07_split_real_data.py. Original unmet positive baselines retained. No human or deployed acceptance inferred.
- Manual review: `unreviewed`
- Informational flags: `frontend_hero_expected`

Section `summary`

- Rows: `1`
- Columns: team_name, season_start, season_end, season_type, split, games_total

| team_name | season_start | season_end | season_type | split | games_total |
| --- | --- | --- | --- | --- | --- |
| Milwaukee Bucks | 2023-24 | 2025-26 | Regular Season | season | 59 |

Section `split_comparison`

- Rows: `2`
- Columns: bucket, games, wins, losses, win_pct, pts_avg, reb_avg, ast_avg, stl_avg, blk_avg, fg3m_avg, tov_avg, ...

| games | wins | losses | win_pct | pts_avg | reb_avg | ast_avg | bucket | stl_avg | blk_avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 36 | 28 | 8 | 0.778 | 122.222 | 49.667 | 27.139 | 2023-24 | 6.333 | 5.167 |
| 23 | 14 | 9 | 0.609 | 112.478 | 48.435 | 25.174 | 2025-26 | 7 | 4.217 |

### k07_b2_heldout

#### k07_b2_heldout

**Query**  
Compare Devin Booker's 2023-24 and 2025-26 season averages only in games with 6 or more assists.

**Answer shown**  
Devin Booker

**Rendered output**

##### Table — Split Comparison

Mode: player split  
Table type: split_comparison  
Column schema: split_comparison_default  
Rows: 2  

| Games | Wins | Losses | Win Pct | Pts Avg | Reb Avg | Ast Avg | Bucket | Minutes Avg | Stl Avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 46 | 31 | 15 | 67.4% | 26.0 | 4.8 | 8.3 | 2023-24 | 36.7 | 0.8 |
| 36 | 21 | 15 | 58.3% | 25.1 | 4.2 | 7.9 | 2025-26 | 34.9 | 0.8 |

- Query: `Compare Devin Booker's 2023-24 and 2025-26 season averages only in games with 6 or more assists.`
- Category: `context_filter`
- Priority: `p1`
- Status: `ok`
- Reason: `<none>`
- Route: `player_split_summary`
- Intent: `split_summary`
- Query class: `split_summary`
- Shape hint: `entity_summary`
- Shape source: `backend_approximation`
- Answer text policy: `frontend_hero_expected`
- Answer text status: frontend-rendered hero expected
- Backend answer text: _not backend-provided_
- Answer summary: Devin Booker -- Regular Season
- Filters: `ast min=6.0 (threshold)`, `Seasons=2023-24, 2025-26 (season)`
- Sections: `summary` 1 row(s), `split_comparison` 2 row(s)
- Expectations: `pass` (26 pass, 0 fail)
- Review notes: Frozen K07 independent raw oracle; exact filtered bucket keys, discrimination, W/L and arithmetic checked in test_k07_split_real_data.py. Original unmet positive baselines retained. No human or deployed acceptance inferred.
- Manual review: `unreviewed`
- Informational flags: `frontend_hero_expected`

Section `summary`

- Rows: `1`
- Columns: player_name, season_start, season_end, season_type, split, games_total

| player_name | season_start | season_end | season_type | split | games_total |
| --- | --- | --- | --- | --- | --- |
| Devin Booker | 2023-24 | 2025-26 | Regular Season | season | 82 |

Section `split_comparison`

- Rows: `2`
- Columns: bucket, games, wins, losses, win_pct, minutes_avg, pts_avg, reb_avg, ast_avg, stl_avg, blk_avg, fg3m_avg, ...

| games | wins | losses | win_pct | pts_avg | reb_avg | ast_avg | bucket | minutes_avg | stl_avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 46 | 31 | 15 | 0.674 | 25.957 | 4.826 | 8.348 | 2023-24 | 36.717 | 0.804 |
| 36 | 21 | 15 | 0.583 | 25.111 | 4.25 | 7.889 | 2025-26 | 34.944 | 0.75 |

### k07_c1_heldout

#### k07_c1_heldout

**Query**  
Split Denver's 2023-24 games against Minnesota into home and road records, including only games where Denver scored 110 or more.

**Answer shown**  
Denver Nuggets

**Rendered output**

##### Table — Split Comparison

Mode: team split  
Table type: split_comparison  
Column schema: split_comparison_default  
Rows: 2  

| Games | Wins | Losses | Win Pct | Pts Avg | Reb Avg | Ast Avg | Bucket | Stl Avg | Blk Avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 0 | 100.0% | 116.0 | 44.0 | 31.0 | home | 7.0 | 8.0 |
| 1 | 1 | 0 | 100.0% | 115.0 | 49.0 | 26.0 | away | 5.0 | 1.0 |

- Query: `Split Denver's 2023-24 games against Minnesota into home and road records, including only games where Denver scored 110 or more.`
- Category: `context_filter`
- Priority: `p1`
- Status: `ok`
- Reason: `<none>`
- Route: `team_split_summary`
- Intent: `split_summary`
- Query class: `split_summary`
- Shape hint: `entity_summary`
- Shape source: `backend_approximation`
- Answer text policy: `frontend_hero_expected`
- Answer text status: frontend-rendered hero expected
- Backend answer text: _not backend-provided_
- Answer summary: Denver Nuggets -- Regular Season
- Filters: `Opponent=MIN (team)`, `Location=Home (location)`, `Location=Away (location)`, `pts min=110.0 (threshold)`
- Sections: `summary` 1 row(s), `split_comparison` 2 row(s)
- Expectations: `pass` (26 pass, 0 fail)
- Review notes: Frozen K07 independent raw oracle; exact filtered bucket keys, discrimination, W/L and arithmetic checked in test_k07_split_real_data.py. Original unmet positive baselines retained. No human or deployed acceptance inferred.
- Manual review: `unreviewed`
- Informational flags: `frontend_hero_expected`
- Caveats: `['filtered to games vs MIN']`

Section `summary`

- Rows: `1`
- Columns: team_name, season_start, season_end, season_type, split, games_total

| team_name | season_start | season_end | season_type | split | games_total |
| --- | --- | --- | --- | --- | --- |
| Denver Nuggets | 2023-24 | 2023-24 | Regular Season | home_away | 2 |

Section `split_comparison`

- Rows: `2`
- Columns: bucket, games, wins, losses, win_pct, pts_avg, reb_avg, ast_avg, stl_avg, blk_avg, fg3m_avg, tov_avg, ...

| games | wins | losses | win_pct | pts_avg | reb_avg | ast_avg | bucket | stl_avg | blk_avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 0 | 1 | 116 | 44 | 31 | home | 7 | 8 |
| 1 | 1 | 0 | 1 | 115 | 49 | 26 | away | 5 | 1 |

### k07_c2_heldout

#### k07_c2_heldout

**Query**  
Against Boston in 2023-24, split Jalen Brunson's averages by home versus away after keeping only his games with at least 20 points.

**Answer shown**  
Jalen Brunson

**Rendered output**

##### Table — Split Comparison

Mode: player split  
Table type: split_comparison  
Column schema: split_comparison_default  
Rows: 2  

| Games | Wins | Losses | Win Pct | Pts Avg | Reb Avg | Ast Avg | Bucket | Minutes Avg | Stl Avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0 | 1 | 0.0% | 34.0 | 3.0 | 9.0 | home | 38.0 | 1.0 |
| 3 | 1 | 2 | 33.3% | 29.3 | 2.0 | 4.0 | away | 34.3 | 0.7 |

- Query: `Against Boston in 2023-24, split Jalen Brunson's averages by home versus away after keeping only his games with at least 20 points.`
- Category: `context_filter`
- Priority: `p1`
- Status: `ok`
- Reason: `<none>`
- Route: `player_split_summary`
- Intent: `split_summary`
- Query class: `split_summary`
- Shape hint: `entity_summary`
- Shape source: `backend_approximation`
- Answer text policy: `frontend_hero_expected`
- Answer text status: frontend-rendered hero expected
- Backend answer text: _not backend-provided_
- Answer summary: Jalen Brunson -- Regular Season
- Filters: `Opponent=BOS (team)`, `Location=Home (location)`, `Location=Away (location)`, `pts min=20.0 (threshold)`
- Sections: `summary` 1 row(s), `split_comparison` 2 row(s)
- Expectations: `pass` (26 pass, 0 fail)
- Review notes: Frozen K07 independent raw oracle; exact filtered bucket keys, discrimination, W/L and arithmetic checked in test_k07_split_real_data.py. Original unmet positive baselines retained. No human or deployed acceptance inferred.
- Manual review: `unreviewed`
- Informational flags: `frontend_hero_expected`
- Caveats: `['filtered to games vs BOS']`

Section `summary`

- Rows: `1`
- Columns: player_name, season_start, season_end, season_type, split, games_total

| player_name | season_start | season_end | season_type | split | games_total |
| --- | --- | --- | --- | --- | --- |
| Jalen Brunson | 2023-24 | 2023-24 | Regular Season | home_away | 4 |

Section `split_comparison`

- Rows: `2`
- Columns: bucket, games, wins, losses, win_pct, minutes_avg, pts_avg, reb_avg, ast_avg, stl_avg, blk_avg, fg3m_avg, ...

| games | wins | losses | win_pct | pts_avg | reb_avg | ast_avg | bucket | minutes_avg | stl_avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0 | 1 | 0 | 34 | 3 | 9 | home | 38 | 1 |
| 3 | 1 | 2 | 0.333 | 29.333 | 2 | 4 | away | 34.333 | 0.667 |
