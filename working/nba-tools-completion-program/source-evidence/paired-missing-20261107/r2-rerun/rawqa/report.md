# Raw Query Answer QA Report

## Run Metadata

- Run ID: `composed-core`
- Started: `2026-11-07T02:24:41.956549+00:00`
- Completed: `2026-11-07T02:24:45.272109+00:00`
- Corpus: `qa/raw_query_answer_corpus.yaml`
- Slices: `[]`
- Cases: `8`

## Summary Counts

- Result statuses: `{'no_result': 1, 'ok': 7}`
- Categories: `{'participation_season_split': 4, 'qualified_pair_participation': 4}`
- Routes: `{'game_finder': 1, 'player_game_finder': 1, 'player_split_summary': 2, 'team_record': 2, 'team_split_summary': 2}`
- Manual review statuses: `{'unreviewed': 8}`
- Manual review tags: `{}`
- Answer text policies: `{'<unspecified>': 7, 'no_answer_text_expected': 1}`
- Answer text statuses: `{'backend_answer_text_present': 1, 'missing_backend_answer_text': 5, 'no_answer_text_expected': 1, 'not_required': 1}`
- Suspicious flag cases: `5`
- Suspicious flags: `{'missing_backend_answer_text': 5}`
- Informational flag cases: `0`
- Informational flags: `{}`
- Verified outlier cases: `0`
- Verified outliers: `{}`
- Suggested review tags: `{'backend_answer_text_required': 5}`
- Expectation cases: `{'pass': 8}`
- Expectation checks: `{'pass': 50}`
- Failed case IDs: `[]`

## Slowest Cases

| Case | Seconds | Status | Route |
|---|---:|---|---|
| k08_pair_missing_nonempty | 1.13 | ok | team_record |
| k08_pair_missing_zero | 0.549 | no_result | team_record |
| k08_pair_missing_zero_count | 0.406 | ok | game_finder |
| k08_s4_player_with | 0.357 | ok | player_split_summary |
| k08_s4_player_without | 0.265 | ok | player_split_summary |
| k08_s4_team_with | 0.245 | ok | team_split_summary |
| k08_pair_missing_player_bound | 0.192 | ok | player_game_finder |
| k08_s4_team_without | 0.172 | ok | team_split_summary |

## Suspicious / Review Flags

| Case | Flags | Suggested tags | Manual review |
|---|---|---|---|
| k08_pair_missing_nonempty | missing_backend_answer_text | backend_answer_text_required | unreviewed |
| k08_s4_team_with | missing_backend_answer_text | backend_answer_text_required | unreviewed |
| k08_s4_team_without | missing_backend_answer_text | backend_answer_text_required | unreviewed |
| k08_s4_player_with | missing_backend_answer_text | backend_answer_text_required | unreviewed |
| k08_s4_player_without | missing_backend_answer_text | backend_answer_text_required | unreviewed |

## Informational Flags

_None._

## Verified Outliers

_None._

## Failed Expectations

_None._

## Query Review Cards

### k08_pair_missing_nonempty

#### k08_pair_missing_nonempty

**Query**  
Celtics record with Tatum and Brown missing in 2025-26

**Answer shown**  
The Boston Celtics are 7-1 in 2025-26 Regular Season, a 87.5% win rate.

**Rendered output**

##### Card — Team Record

Subject: Boston Celtics  
Mode: Team record  
Filter: Without player: Jayson Tatum and Jaylen Brown  
Record: 7-1  
Games: 8  
Win %: 87.5%  
PPG: 112.2  
+/-: 18.4  

##### Table — Team record

Subject: Boston Celtics  
Mode: Team record  
Filter: Without player: Jayson Tatum and Jaylen Brown  
Table type: record_summary  
Column schema: team_record_summary_default  
Rows: 1  

| Team | W-L | Games | Win % | PPG | +/- |
| --- | --- | --- | --- | --- | --- |
| Boston Celtics | 7-1 | 8 | 87.5% | 112.2 | 18.4 |

##### Detail — Game Detail

Subject: Boston Celtics  
Mode: Team game log  
Filter: Without player: Jayson Tatum and Jaylen Brown  
Table type: team_game_log  
Column schema: team_game_log_default  
Rows: 8  
Collapsed label: Show game detail  

| # | Date | Team |  | Opp | Score | W/L | PTS | Opp PTS | Margin | REB | AST | 3PM | FG | 3P | FT | TOV | STL | BLK | oreb | dreb |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Dec 4 | BOS |  | WAS | 146-101 | W | 146 | 101 | — | 46 | 35 | 20 | — | — | — | 9 | 14 | 8 | 15 | 31 |
| 2 | Dec 20 | BOS |  | TOR | 112-96 | W | 112 | 96 | — | 55 | 22 | 12 | — | — | — | 9 | 7 | 4 | 17 | 38 |
| 3 | Jan 12 | BOS |  | IND | 96-98 | L | 96 | 98 | — | 46 | 22 | 9 | — | — | — | 12 | 9 | 1 | 10 | 36 |

- Query: `Celtics record with Tatum and Brown missing in 2025-26`
- Category: `qualified_pair_participation`
- Priority: `p0`
- Status: `ok`
- Reason: `<none>`
- Route: `team_record`
- Intent: `summary`
- Query class: `summary`
- Shape hint: `team_record`
- Shape source: `backend_approximation`
- Answer text policy: `<none>`
- Answer text status: backend answer text missing
- Backend answer text: _not backend-provided_
- Answer summary: Boston Celtics -- 7-1 over 8 games, 112.25 PPG, 51.125 RPG, 26.125 APG, Regular Season
- Filters: `Without player=Jayson Tatum and Jaylen Brown (player)`
- Sections: `summary` 1 row(s), `by_season` 1 row(s), `game_log` 8 row(s)
- Expectations: `pass` (8 pass, 0 fail)
- Review notes: Qualified composed stage only; independent explicit Tatum/Brown DNP intersection. Whole-game participation, no medical cause or current-season claim.
- Manual review: `unreviewed`
- Suspicious flags: `missing_backend_answer_text`
- Suggested review tags: `['backend_answer_text_required']`
- Caveats: `['record filtered to games without Jayson Tatum and Jaylen Brown']`

Section `summary`

- Rows: `1`
- Columns: team_name, season_start, season_end, season_type, games, wins, losses, win_pct, pts_avg, reb_avg, ast_avg, fg3m_avg, ...

| team_name | season_start | season_end | games | wins | losses | win_pct | pts_avg | reb_avg | ast_avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Boston Celtics | 2025-26 | 2025-26 | 8 | 7 | 1 | 0.875 | 112.25 | 51.125 | 26.125 |

Section `by_season`

- Rows: `1`
- Columns: season, games, wins, losses, pts_avg, reb_avg, ast_avg, fg3m_avg, tov_avg, plus_minus_avg, efg_pct_avg, ts_pct_avg, ...

| season | games | wins | losses | win_pct | pts_avg | reb_avg | ast_avg | fg3m_avg | tov_avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-26 | 8 | 7 | 1 | 0.875 | 112.25 | 51.125 | 26.125 | 16.25 | 10.625 |

Section `game_log`

- Rows: `8`
- Columns: game_date, game_id, season, season_type, team_id, team_abbr, team_name, opponent_team_id, opponent_team_abbr, opponent_team_name, is_home, is_away, ...

| team_name | team_abbr | season | game_date | opponent_team_abbr | wl | pts | reb | ast | game_id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Boston Celtics | BOS | 2025-26 | 2025-12-04 | WAS | W | 146 | 46 | 35 | 22500334 |
| Boston Celtics | BOS | 2025-26 | 2025-12-20 | TOR | W | 112 | 55 | 22 | 22500388 |
| Boston Celtics | BOS | 2025-26 | 2026-01-12 | IND | L | 96 | 46 | 22 | 22500559 |

### k08_pair_missing_zero

#### k08_pair_missing_zero

**Query**  
Lakers record with Davis and Reaves missing in 2023-24

**Answer shown**  
No answer returned.

**Rendered output**

##### Message — No result

No answer rows returned; reason=no_match.  

- Query: `Lakers record with Davis and Reaves missing in 2023-24`
- Category: `qualified_pair_participation`
- Priority: `p0`
- Status: `no_result`
- Reason: `no_match`
- Route: `team_record`
- Intent: `summary`
- Query class: `summary`
- Shape hint: `no_result`
- Shape source: `backend_approximation`
- Answer text policy: `no_answer_text_expected`
- Answer text status: no answer text expected
- Backend answer text: _not backend-provided_
- Answer summary: No answer rows returned; reason=no_match
- Filters: `Without player=Anthony Davis and Austin Reaves (player)`
- Sections: _none_
- Expectations: `pass` (3 pass, 0 fail)
- Review notes: Original ID12 fixed historical scope; qualified zero from complete 82-game explicit observations, Reaves played all82. This is not missing data or unsupported interpretation.
- Manual review: `unreviewed`
- Notes: `['No games matched the specified filters']`

### k08_s4_team_with

#### k08_s4_team_with

**Query**  
Celtics record vs Lakers with Jayson Tatum in 2023-24 and 2025-26

**Answer shown**  
Boston Celtics

**Rendered output**

##### Table — Split Comparison

Mode: team split  
Table type: split_comparison  
Column schema: split_comparison_default  
Rows: 1  

| Games | Wins | Losses | Win Pct | Pts Avg | Reb Avg | Ast Avg | Bucket | Stl Avg | Blk Avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 1 | 1 | 50.0% | 115.5 | 49.0 | 30.5 | 2023-24 | 6.0 | 9.5 |

- Query: `Celtics record vs Lakers with Jayson Tatum in 2023-24 and 2025-26`
- Category: `participation_season_split`
- Priority: `p0`
- Status: `ok`
- Reason: `<none>`
- Route: `team_split_summary`
- Intent: `split_summary`
- Query class: `split_summary`
- Shape hint: `entity_summary`
- Shape source: `backend_approximation`
- Answer text policy: `<none>`
- Answer text status: backend answer text missing
- Backend answer text: _not backend-provided_
- Answer summary: Boston Celtics -- Regular Season
- Filters: `Opponent=LAL (team)`, `With player=Jayson Tatum (player)`, `Seasons=2023-24, 2025-26 (season)`
- Sections: `summary` 1 row(s), `split_comparison` 1 row(s)
- Expectations: `pass` (7 pass, 0 fail)
- Review notes: Bound S4 on composed qualified source stage; exact game keys, arithmetic, opposite qualified-empty season and HTTP filter ownership verified by existing S4 helper. No report is downloaded again.
- Manual review: `unreviewed`
- Suspicious flags: `missing_backend_answer_text`
- Suggested review tags: `['backend_answer_text_required']`
- Caveats: `['no games in 2025-26', 'filtered to games vs LAL']`

Section `summary`

- Rows: `1`
- Columns: team_name, season_start, season_end, season_type, split, games_total

| team_name | season_start | season_end | season_type | split | games_total |
| --- | --- | --- | --- | --- | --- |
| Boston Celtics | 2023-24 | 2023-24 | Regular Season | season | 2 |

Section `split_comparison`

- Rows: `1`
- Columns: bucket, games, wins, losses, win_pct, pts_avg, reb_avg, ast_avg, stl_avg, blk_avg, fg3m_avg, tov_avg, ...

| games | wins | losses | win_pct | pts_avg | reb_avg | ast_avg | bucket | stl_avg | blk_avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 1 | 1 | 0.5 | 115.5 | 49 | 30.5 | 2023-24 | 6 | 9.5 |

### k08_s4_team_without

#### k08_s4_team_without

**Query**  
Celtics record vs Lakers without Jayson Tatum in 2023-24 and 2025-26

**Answer shown**  
Boston Celtics

**Rendered output**

##### Table — Split Comparison

Mode: team split  
Table type: split_comparison  
Column schema: split_comparison_default  
Rows: 1  

| Games | Wins | Losses | Win Pct | Pts Avg | Reb Avg | Ast Avg | Bucket | Stl Avg | Blk Avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 2 | 0 | 100.0% | 118.5 | 44.0 | 30.0 | 2025-26 | 7.5 | 5.0 |

- Query: `Celtics record vs Lakers without Jayson Tatum in 2023-24 and 2025-26`
- Category: `participation_season_split`
- Priority: `p0`
- Status: `ok`
- Reason: `<none>`
- Route: `team_split_summary`
- Intent: `split_summary`
- Query class: `split_summary`
- Shape hint: `entity_summary`
- Shape source: `backend_approximation`
- Answer text policy: `<none>`
- Answer text status: backend answer text missing
- Backend answer text: _not backend-provided_
- Answer summary: Boston Celtics -- Regular Season
- Filters: `Opponent=LAL (team)`, `Without player=Jayson Tatum (player)`, `Seasons=2023-24, 2025-26 (season)`
- Sections: `summary` 1 row(s), `split_comparison` 1 row(s)
- Expectations: `pass` (7 pass, 0 fail)
- Review notes: Bound S4 on composed qualified source stage; exact game keys, arithmetic, opposite qualified-empty season and HTTP filter ownership verified by existing S4 helper. No report is downloaded again.
- Manual review: `unreviewed`
- Suspicious flags: `missing_backend_answer_text`
- Suggested review tags: `['backend_answer_text_required']`
- Caveats: `['no games in 2023-24', 'filtered to games vs LAL']`

Section `summary`

- Rows: `1`
- Columns: team_name, season_start, season_end, season_type, split, games_total

| team_name | season_start | season_end | season_type | split | games_total |
| --- | --- | --- | --- | --- | --- |
| Boston Celtics | 2025-26 | 2025-26 | Regular Season | season | 2 |

Section `split_comparison`

- Rows: `1`
- Columns: bucket, games, wins, losses, win_pct, pts_avg, reb_avg, ast_avg, stl_avg, blk_avg, fg3m_avg, tov_avg, ...

| games | wins | losses | win_pct | pts_avg | reb_avg | ast_avg | bucket | stl_avg | blk_avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 2 | 0 | 1 | 118.5 | 44 | 30 | 2025-26 | 7.5 | 5 |

### k08_s4_player_with

#### k08_s4_player_with

**Query**  
Jaylen Brown stats vs Lakers with Jayson Tatum in 2023-24 and 2025-26

**Answer shown**  
Jaylen Brown

**Rendered output**

##### Table — Split Comparison

Mode: player split  
Table type: split_comparison  
Column schema: split_comparison_default  
Rows: 1  

| Games | Wins | Losses | Win Pct | Pts Avg | Reb Avg | Ast Avg | Bucket | Minutes Avg | Stl Avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 1 | 1 | 50.0% | 13.5 | 6.5 | 4.5 | 2023-24 | 30.0 | 2.0 |

- Query: `Jaylen Brown stats vs Lakers with Jayson Tatum in 2023-24 and 2025-26`
- Category: `participation_season_split`
- Priority: `p0`
- Status: `ok`
- Reason: `<none>`
- Route: `player_split_summary`
- Intent: `split_summary`
- Query class: `split_summary`
- Shape hint: `entity_summary`
- Shape source: `backend_approximation`
- Answer text policy: `<none>`
- Answer text status: backend answer text missing
- Backend answer text: _not backend-provided_
- Answer summary: Jaylen Brown -- Regular Season
- Filters: `Opponent=LAL (team)`, `With player=Jayson Tatum (player)`, `Seasons=2023-24, 2025-26 (season)`
- Sections: `summary` 1 row(s), `split_comparison` 1 row(s)
- Expectations: `pass` (7 pass, 0 fail)
- Review notes: Bound S4 on composed qualified source stage; exact game keys, arithmetic, opposite qualified-empty season and HTTP filter ownership verified by existing S4 helper. No report is downloaded again.
- Manual review: `unreviewed`
- Suspicious flags: `missing_backend_answer_text`
- Suggested review tags: `['backend_answer_text_required']`
- Caveats: `['no games in 2025-26', 'filtered to games vs LAL']`

Section `summary`

- Rows: `1`
- Columns: player_name, season_start, season_end, season_type, split, games_total

| player_name | season_start | season_end | season_type | split | games_total |
| --- | --- | --- | --- | --- | --- |
| Jaylen Brown | 2023-24 | 2023-24 | Regular Season | season | 2 |

Section `split_comparison`

- Rows: `1`
- Columns: bucket, games, wins, losses, win_pct, minutes_avg, pts_avg, reb_avg, ast_avg, stl_avg, blk_avg, fg3m_avg, ...

| games | wins | losses | win_pct | pts_avg | reb_avg | ast_avg | bucket | minutes_avg | stl_avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 1 | 1 | 0.5 | 13.5 | 6.5 | 4.5 | 2023-24 | 30 | 2 |

### k08_s4_player_without

#### k08_s4_player_without

**Query**  
Jaylen Brown stats vs Lakers without Jayson Tatum in 2023-24 and 2025-26

**Answer shown**  
Jaylen Brown

**Rendered output**

##### Table — Split Comparison

Mode: player split  
Table type: split_comparison  
Column schema: split_comparison_default  
Rows: 1  

| Games | Wins | Losses | Win Pct | Pts Avg | Reb Avg | Ast Avg | Bucket | Minutes Avg | Stl Avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 2 | 0 | 100.0% | 31.0 | 8.0 | 7.5 | 2025-26 | 35.0 | 2.0 |

- Query: `Jaylen Brown stats vs Lakers without Jayson Tatum in 2023-24 and 2025-26`
- Category: `participation_season_split`
- Priority: `p0`
- Status: `ok`
- Reason: `<none>`
- Route: `player_split_summary`
- Intent: `split_summary`
- Query class: `split_summary`
- Shape hint: `entity_summary`
- Shape source: `backend_approximation`
- Answer text policy: `<none>`
- Answer text status: backend answer text missing
- Backend answer text: _not backend-provided_
- Answer summary: Jaylen Brown -- Regular Season
- Filters: `Opponent=LAL (team)`, `Without player=Jayson Tatum (player)`, `Seasons=2023-24, 2025-26 (season)`
- Sections: `summary` 1 row(s), `split_comparison` 1 row(s)
- Expectations: `pass` (7 pass, 0 fail)
- Review notes: Bound S4 on composed qualified source stage; exact game keys, arithmetic, opposite qualified-empty season and HTTP filter ownership verified by existing S4 helper. No report is downloaded again.
- Manual review: `unreviewed`
- Suspicious flags: `missing_backend_answer_text`
- Suggested review tags: `['backend_answer_text_required']`
- Caveats: `['no games in 2023-24', 'filtered to games vs LAL']`

Section `summary`

- Rows: `1`
- Columns: player_name, season_start, season_end, season_type, split, games_total

| player_name | season_start | season_end | season_type | split | games_total |
| --- | --- | --- | --- | --- | --- |
| Jaylen Brown | 2025-26 | 2025-26 | Regular Season | season | 2 |

Section `split_comparison`

- Rows: `1`
- Columns: bucket, games, wins, losses, win_pct, minutes_avg, pts_avg, reb_avg, ast_avg, stl_avg, blk_avg, fg3m_avg, ...

| games | wins | losses | win_pct | pts_avg | reb_avg | ast_avg | bucket | minutes_avg | stl_avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 2 | 0 | 1 | 31 | 8 | 7.5 | 2025-26 | 35 | 2 |

### k08_pair_missing_zero_count

#### k08_pair_missing_zero_count

**Query**  
How many Lakers games with Davis and Reaves missing in 2023-24?

**Answer shown**  
The LAL have recorded 0 games in the 2023-24 regular season.

**Rendered output**

_No rendered blocks._
- Query: `How many Lakers games with Davis and Reaves missing in 2023-24?`
- Category: `qualified_pair_participation`
- Priority: `p0`
- Status: `ok`
- Reason: `<none>`
- Route: `game_finder`
- Intent: `count`
- Query class: `count`
- Shape hint: `game_log_team_table`
- Shape source: `backend_approximation`
- Answer text policy: `<none>`
- Answer text status: backend answer text present
- Backend answer text: The LAL have recorded 0 games in the 2023-24 regular season.
- Answer summary: Count: 0
- Filters: `Without player=Anthony Davis and Austin Reaves (player)`
- Sections: `count` 1 row(s)
- Expectations: `pass` (5 pass, 0 fail)
- Review notes: Same qualified complete historical ID12 pair-zero sample; numeric count0 is distinct from no_data.
- Manual review: `unreviewed`

Section `count`

- Rows: `1`
- Columns: count

| count |
| --- |
| 0 |

### k08_pair_missing_player_bound

#### k08_pair_missing_player_bound

**Query**  
Austin Reaves games with 20 points with LeBron James and Anthony Davis missing against Boston in 2023-24

**Answer shown**  
Austin Reaves had 1 game matching in 2023-24.

**Rendered output**

##### Table — Player Game Detail

Subject: Austin Reaves  
Mode: Player game log  
Filter: Opponent: BOS; Without player: LeBron James and Anthony Davis; pts min: 20.0  
Table type: player_game_log  
Column schema: player_game_log_default  
Rows: 1  

| # | Date | TM |  | Opp | W/L | MIN | PTS | REB | AST | FG | 3P | FT | STL | BLK | TOV | +/- | TS% | eFG% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Feb 1 | LAL |  | BOS | W | 35 | 32 | 2 | 3 | — | — | — | 0 | 0 | 0 | 16 | 75.9% | 75.0% |

- Query: `Austin Reaves games with 20 points with LeBron James and Anthony Davis missing against Boston in 2023-24`
- Category: `qualified_pair_participation`
- Priority: `p0`
- Status: `ok`
- Reason: `<none>`
- Route: `player_game_finder`
- Intent: `finder`
- Query class: `finder`
- Shape hint: `game_log_table`
- Shape source: `backend_approximation`
- Answer text policy: `<none>`
- Answer text status: not required
- Backend answer text: _not backend-provided_
- Answer summary: Top row: Austin Reaves -- 32 PTS, 2024-02-01 LAL vs BOS
- Filters: `Opponent=BOS (team)`, `Without player=LeBron James and Anthony Davis (player)`, `pts min=20.0 (threshold)`
- Sections: `finder` 1 row(s)
- Expectations: `pass` (6 pass, 0 fail)
- Review notes: Independently qualified official report pair plus own player bound and named opponent; exactReaves32/2/3 line remains retained.
- Manual review: `unreviewed`

Section `finder`

- Rows: `1`
- Columns: rank, game_date, game_id, season, season_type, player_name, player_id, team_name, team_abbr, opponent_team_name, opponent_team_abbr, is_home, ...

| rank | player_name | team_name | team_abbr | season | game_date | opponent_team_abbr | wl | pts | reb |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Austin Reaves | Los Angeles Lakers | LAL | 2023-24 | 2024-02-01T00:00:00 | BOS | W | 32 | 2 |
