# Public Query Acceptance Coverage Preflight

Date: 2026-05-28

Status: preflight complete; Wave 1 probe/seed complete; Wave 2A and 2B fixes complete.

This document designs a public-query acceptance coverage system for obvious
real-user phrasings across the advertised Raw Product query surface. The
initial preflight did not change production code, parser/routing behavior,
frontend rendering, QA corpus expectations, saved harness slices, or release
status. Wave 1 added only safe passing raw QA cases, acceptance metadata, and a
saved harness slice; it did not change production code, parser/routing behavior,
frontend rendering, or release status.

## 1. Goal

Manual public usage found basic failures that the raw QA corpus did not catch:
canonical examples passed, but obvious sibling and inverse phrasings were not
systematically required for every public feature family.

The acceptance system should prove this for every advertised family:

- a canonical phrase works
- a short search-bar phrase works
- a natural sentence phrase works
- a common synonym phrase works
- an inverse or sibling phrase routes to the right adjacent family when one
  exists
- a nearby unsupported phrase does not broad-fallback
- typo or partial-entity phrasing does not silently drop requested filters or
  answer a broader question

## 2. Inputs Reviewed

- `docs/reference/query_catalog.md`
- `docs/reference/query_guide.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md`
- `qa/raw_query_answer_corpus.yaml`
- `qa/harness_slices/*.yaml`
- `docs/planning/raw-product/PARSER_ROUTING_GROWTH_GUARDRAILS.md`
- `docs/planning/raw-product/NATURAL_QUERY_DECISION_MAP_AND_TEST_MATRIX.md`
- `docs/planning/raw-product/BASIC_PUBLIC_QUERY_FAILURE_SWEEP_TEAM_RECORD_AVAILABILITY_PREFLIGHT.md`

Current raw QA corpus size observed in this preflight: 260 cases.

Current saved harness slices observed:

- `basic_public_availability`
- `defensive_aliases`
- `natural_query_route_priority`
- `player_entity_stat_context`
- `playoff_phrasing`
- `product_boundaries`
- `team_date_context`

Wave 1 added:

- `public_query_acceptance`

## 3. Advertised Public Feature Families

The public Raw Product surface advertises these families:

| Family | Main routes / behavior |
|---|---|
| Player stats this season | `player_game_summary` |
| Team records | `team_record`, `team_matchup_record`, `team_record_leaderboard` |
| Team record with/without player | `team_record` with whole-game `with_player` / `without_player`; compound availability unsupported |
| Player summaries / recent form | `player_game_summary`, some finder forms when a stat-only context is requested |
| Leaderboards | `season_leaders`, `season_team_leaders`, occurrence leaderboards |
| Top single-game performances | `top_player_games`, `top_team_games`, named-player best-game finder forms |
| Count queries | `player_game_finder`, `game_finder`, occurrence leaderboards with count semantics |
| Game finders | `player_game_finder`, `game_finder` |
| Splits | `player_split_summary`, `team_split_summary` |
| Streaks | `player_streak_finder`, `team_streak_finder` |
| Rolling stretches | `player_stretch_leaderboard`; team rolling stretches unsupported |
| Comparisons | `player_compare`, `team_compare`, `team_matchup_record` |
| Playoff history | `playoff_history`, `playoff_matchup_history`, `playoff_appearances`, `playoff_round_record`, era/decade routes |
| Date/window filters | date, month, since-date, last-N, last-season, current-season, no-match behavior |
| Unsupported subjective/narrative questions | unrouted/error or explicit unsupported/no-result |
| Typo/partial entity behavior | explicit no-result or ambiguity; no dropped filters or broad fallback |

## 4. Current Coverage Findings

| Family | Current coverage | Classification | Main public-acceptance gap |
|---|---|---|---|
| Player stats this season | `Jokic this season`, `Luka stats this season` | Mostly canonical / short | Needs sentence, synonym, sibling, and typo coverage in one acceptance matrix. |
| Team records | Overall, home/away, road, dates, opponent quality, conference, division guards | Strong phrasing variants and no-broad-fallback guards | Needs a public matrix tying canonical, short, sentence, synonym, matchup sibling, unsupported division, and typo cases together. |
| Team record with/without player | New `basic_public_availability` slice covers the recent issue | Focused variants for one failure family | Needs additional public variants such as `when PLAYER plays`, `w/ PLAYER`, `without PLAYER`, mixed availability, and typo/partial names. |
| Player summaries / recent form | Recent form, last-N, opponent quality, role, rest, player-vs-player context | Good route breadth | Needs explicit sibling guards against comparison/finder routes and typo handling. |
| Leaderboards | Many stat aliases, position leaderboards, team leaderboards, unsupported role/rookie/PF boundaries | Strong variants and some inverse coverage | Needs a fixed public matrix linking season leaderboards to top-single-game sibling phrases and stat-typo fallback guards. |
| Top single-game performances | Scoring, assists, rebounds, threes, blocks, steals, plus-minus; user exact rebound variant | Good canonical/stat variants | Needs explicit inverse guard against per-game season leaderboards and unsupported team-single-game threes. |
| Count queries | Player event counts, team counts, distinct player counts | Moderate | Needs canonical/short/sentence/synonym coverage plus unsupported no-threshold count and typo cases. |
| Game finders | Player/team threshold finders and some count-adjacent cases | Moderate | Needs more real-user sentence/synonym coverage and unsupported nearby boundaries. |
| Splits | Player/team home-away, wins-losses, recent split contexts | Good supported variants | Needs split-specific unsupported route-combo guard and typo coverage. |
| Streaks | Player/team streaks, current/completed, special events | Good supported variants | Needs explicit sibling guard against finder/count phrasing and trend/subjective no-broad-fallback cases. |
| Rolling stretches | Player stretches and team rolling unsupported cases | Strong supported/unsupported pair | Needs typo and Game Score sentence variant in public acceptance. |
| Comparisons | Player/team comparisons, head-to-head, player-as-opponent sibling | Strong collision coverage | Needs public acceptance cases for subjective comparison and partial entity behavior. |
| Playoff history | Playoff history, matchup history, appearances, round records, unsupported single-team round records | Strong variants and unsupported boundaries | Needs typo/partial team guard and explicit opponent-quality sibling. |
| Date/window filters | Specific dates, month windows, since-date, last-N, no-match dates | Good route breadth | Needs malformed/vague date no-broad-fallback coverage. |
| Unsupported subjective/narrative | Defender, MVP, best player lately, cooled off, clutch, duo | Strong unsupported inventory | Needs to be pulled into the public acceptance suite as required guardrails for adjacent supported families. |
| Typo/partial entity behavior | Availability typo is covered; broader entity typo cases are sparse | Narrow | Needs dedicated cross-family typo/partial acceptance rows. |

High-level finding: the corpus has breadth, but the acceptance requirement is
implicit. The missing system is not "more examples somewhere"; it is a required
variant grid for every public family.

## 5. Strategy Decision

Use the existing raw QA corpus as the single expectation source, add acceptance
metadata to relevant cases, and add one saved harness slice for the public
acceptance suite.

Chosen strategy:

- Keep cases in `qa/raw_query_answer_corpus.yaml`.
- Add a saved slice named `qa/harness_slices/public_query_acceptance.yaml`.
- Add optional per-case metadata inside existing raw corpus cases:

```yaml
acceptance:
  surface: public_query_acceptance
  family: team_record_availability
  variant: inverse_sibling
  no_broad_fallback: true
  sibling_of: lakers_record_with_luka_public_sweep
```

Do not create a separate public acceptance corpus.

Rationale:

- A separate corpus would duplicate expectations and invite drift from the raw
  QA product contract.
- A saved slice alone is runnable today, but it cannot explain why a case is in
  the suite or whether every family has every required variant.
- Tags/metadata alone are not currently runnable without new harness selection
  logic; the saved slice gives immediate execution.
- The combined approach keeps one source of truth, preserves current harness
  behavior, and leaves room for future tag filtering if it becomes worthwhile.

The next execution wave should add the metadata and slice only after deciding
which proposed new cases are behavior-preserving and which reveal product bugs
that need fixes first.

## 6. Matrix Rules

Each family should have these variant types:

| Variant | Meaning |
|---|---|
| `canonical` | The doc-facing representative phrase. |
| `short` | Search-bar or fragment phrasing. |
| `sentence` | Full natural-language question. |
| `synonym` | Common alternate wording or stat/entity alias. |
| `inverse_sibling` | Adjacent supported route or inverse filter that must not be confused with the family. |
| `nearby_unsupported` | Plausible adjacent phrase that must return unsupported/no-result instead of a broad answer. |
| `typo_partial` | Misspelled or partial entity/stat/date phrase where relevant. |

No-broad-fallback assertions:

- Supported cases must assert exact route, status, and at least one distinctive
  route kwarg, applied filter, metadata field, section, row count, or top-row
  value that proves the requested scope was honored.
- Unsupported cases must assert the expected non-ok status/reason, empty
  sections when the result is no-result, and stable `metadata.unsupported_filters`
  when the route uses one.
- Route-preserving unsupported boundaries are valid, but the case must prove no
  wider table, leaderboard, record, or summary rows were returned.
- Typo/partial cases must prove the typo was not silently dropped.

Case ID convention for new cases:

```text
pqa_<family>_<variant>_<short_slug>
```

Existing raw QA case IDs should be reused and tagged rather than duplicated.

## 7. Proposed Public Acceptance Matrix

The following cases are proposed. Existing IDs can be reused; new `pqa_*` IDs
should be added only in a future execution wave.

### 7.1 Player Stats This Season

| Variant | Case ID | Query | Expected route / status / reason | Support | No-broad-fallback assertion |
|---|---|---|---|---|---|
| Canonical | `luka_stats_this_season_public_sweep` | `Luka stats this season` | `player_game_summary` / `ok` / `-` | Supported | Summary subject is Luka Doncic; no team-record or leaderboard answer. |
| Short | `jokic_season_summary` | `Jokic this season` | `player_game_summary` / `ok` / `-` | Supported | One player summary row for Nikola Jokic. |
| Sentence | `pqa_player_stats_sentence_luka_played` | `How has Luka Doncic played this season?` | `player_game_summary` / `ok` / `-` | Supported | Summary subject is Luka Doncic and section includes `summary`. |
| Synonym | `pqa_player_stats_synonym_luka_averages` | `Luka averages this year` | `player_game_summary` / `ok` / `-` | Supported | Player summary route with current-season default; no finder-only rows. |
| Inverse/sibling | `lakers_record_with_luka_public_sweep` | `Lakers record with Luka` | `team_record` / `ok` / `-` | Supported sibling | Must remain a team-record availability answer, not Luka stats. |
| Nearby unsupported | `mvp_candidates_subjective` | `Who are the MVP candidates?` | `None` / `error` / `unrouted` | Unsupported | No player leaderboard or player summary fallback. |
| Typo/partial | `pqa_player_stats_typo_jokc` | `Jokc stats this season` | `None` / `error` / `unrouted` | Unsupported until resolved | No Nikola Jokic summary unless resolver confidence is explicit and tested. |

Missing user-obvious variants: `How has PLAYER played this season?`,
`PLAYER averages this year`, and general player-name typo handling outside the
availability route.

### 7.2 Team Records

| Variant | Case ID | Query | Expected route / status / reason | Support | No-broad-fallback assertion |
|---|---|---|---|---|---|
| Canonical | `celtics_overall_record` | `What is the Celtics record this season?` | `team_record` / `ok` / `-` | Supported | Summary row is BOS; no league record leaderboard. |
| Short | `pqa_team_record_short_celtics_record` | `Celtics record` | `team_record` / `ok` / `-` | Supported | Single-team record, latest regular-season default. |
| Sentence | `lakers_how_did_road_last_season_wave5` | `How did the Lakers do on the road last season?` | `team_record` / `ok` / `-` | Supported | Applies road and last-season filters. |
| Synonym | `lakers_road_record_last_season` | `Lakers road record last season` | `team_record` / `ok` / `-` | Supported | Same filter shape as sentence form. |
| Inverse/sibling | `warriors_lakers_record_this_season_wave5` | `Warriors vs Lakers record this season` | `team_matchup_record` / `ok` / `-` | Supported sibling | Two-team record does not collapse to single-team Warriors or Lakers record. |
| Nearby unsupported | `celtics_atlantic_division_guard` | `Celtics record vs Atlantic Division` | `team_record` / `no_result` / `filter_not_supported` | Unsupported | `unsupported_filters=["opponent_division"]`; empty sections; no full Celtics record. |
| Typo/partial | `pqa_team_record_typo_celtcs` | `Celtcs record this season` | `None` / `error` / `unrouted` | Unsupported until resolved | No Celtics record unless typo resolution is explicitly supported. |

Missing user-obvious variants: bare `TEAM record`, typo/partial team names, and
a single acceptance table that ties team-record route priority to matchup and
division boundaries.

### 7.3 Team Record With/Without Player

| Variant | Case ID | Query | Expected route / status / reason | Support | No-broad-fallback assertion |
|---|---|---|---|---|---|
| Canonical | `lakers_record_with_luka_public_sweep` | `Lakers record with Luka` | `team_record` / `ok` / `-` | Supported | `With player=Luka Doncic`; Lakers subject; game log included. |
| Short | `pqa_availability_short_lakers_w_luka` | `Lakers w/ Luka record` | `team_record` / `ok` / `-` | Supported | Same with-player filter; no Luka player summary. |
| Sentence | `pqa_availability_sentence_luka_plays` | `What is the Lakers record when Luka Doncic plays?` | `team_record` / `ok` / `-` | Supported | Team-record subject; applied filter is whole-game presence. |
| Synonym | `pqa_availability_synonym_reaves_available` | `Lakers wins with Austin Reaves` | `team_record` / `ok` / `-` | Supported | With-player filter for Austin Reaves; not an Austin Reaves summary. |
| Inverse/sibling | `lakers_record_without_luka_public_sweep` | `Lakers record without Luka` | `team_record` / `ok` / `-` | Supported inverse | `Without player=Luka Doncic`; no broad full-season record. |
| Nearby unsupported | `lakers_record_with_reaves_without_luka_public_sweep` | `Lakers record with Reaves without Luka` | `team_record` / `no_result` / `filter_not_supported` | Unsupported | `unsupported_filters=["multi_player_availability"]`; empty sections. |
| Typo/partial | `lakers_record_without_luk_public_sweep` | `Lakers record without Luk` | `team_record` / `no_result` / `filter_not_supported` | Unsupported | `unsupported_filters=["unresolved_player_availability"]`; no 82-game Lakers record. |

Missing user-obvious variants: `when PLAYER plays`, `w/ PLAYER`, and more
absence synonyms in the same acceptance family as presence.

### 7.4 Player Summaries / Recent Form

| Variant | Case ID | Query | Expected route / status / reason | Support | No-broad-fallback assertion |
|---|---|---|---|---|---|
| Canonical | `tatum_recent_form` | `Jayson Tatum recent form` | `player_game_summary` / `ok` / `-` | Supported | Player summary route with recent/default window context. |
| Short | `luka_last_10_summary_wave5` | `Luka last 10 games summary` | `player_game_summary` / `ok` / `-` | Supported | Last-N context is preserved. |
| Sentence | `tatum_good_teams` | `How has Jayson Tatum played against good teams this season?` | `player_game_summary` / `ok` / `-` | Supported | Opponent-quality filter is applied; no broad Tatum season summary. |
| Synonym | `kd_ts_top_defenses_missing_filters` | `KD TS% vs top defenses` | `player_game_summary` / `ok` / `-` | Supported | Stat context and opponent-quality bucket are preserved. |
| Inverse/sibling | `lebron_durant_comparison_wave4` | `LeBron James vs Kevin Durant comparison` | `player_compare` / `ok` / `-` | Supported sibling | Comparison wording does not route as player-vs-opponent summary. |
| Nearby unsupported | `best_player_lately_ambiguous` | `Who is the best player lately?` | `None` / `error` / `unrouted` | Unsupported | No points leaderboard or recent-form fallback. |
| Typo/partial | `pqa_player_recent_typo_tatm` | `Tatm recent form` | `None` / `error` / `unrouted` | Unsupported until resolved | No Tatum summary unless partial-name support is explicit. |

Missing user-obvious variants: `How has PLAYER played recently?`, typo/partial
names, and explicit comparison-vs-opponent sibling assertions inside the public
acceptance slice.

### 7.5 Leaderboards

| Variant | Case ID | Query | Expected route / status / reason | Support | No-broad-fallback assertion |
|---|---|---|---|---|---|
| Canonical | `points_per_game_leader` | `Who leads the NBA in points per game this season?` | `season_leaders` / `ok` / `-` | Supported | Player season leaderboard, stat is points/PPG. |
| Short | `leaders_in_steals_wave5` | `leaders in steals this season` | `season_leaders` / `ok` / `-` | Supported | Stat is steals; no default points leaderboard. |
| Sentence | `centers_rebound_leaders_wave4` | `Which centers have the most rebounds this season?` | `season_leaders` / `ok` / `-` | Supported | Position filter is centers and stat is rebounds. |
| Synonym | `true_shooting_leaders_phrase_wave5` | `true shooting leaders this season` | `season_leaders` / `ok` / `-` | Supported | Stat alias resolves to `ts_pct`. |
| Inverse/sibling | `most_assists_single_game` | `What were the most assists in a game this season?` | `top_player_games` / `ok` / `-` | Supported sibling | Single-game wording does not route to assist-per-game leaders. |
| Nearby unsupported | `rookie_scoring_leaders_wave4` | `rookie scoring leaders this season` | `season_leaders` / `no_result` / `filter_not_supported` | Unsupported | `unsupported_filters=["rookie_leaderboard"]`; no broad scoring leaders. |
| Typo/partial | `pqa_leaderboard_stat_typo_pionts` | `Who leads the NBA in pionts per game this season?` | `None` / `error` / `unrouted` | Unsupported until stat typo support exists | No silent correction to points without explicit support. |

Missing user-obvious variants: stat-typo behavior and a required inverse check
for every high-risk leaderboard/top-game collision.

### 7.6 Top Single-Game Performances

| Variant | Case ID | Query | Expected route / status / reason | Support | No-broad-fallback assertion |
|---|---|---|---|---|---|
| Canonical | `biggest_scoring_games` | `What were the biggest scoring games this season?` | `top_player_games` / `ok` / `-` | Supported | Top-player-games route; not PPG leaders. |
| Short | `most_rebounds_single_game` | `most rebounds in a game this season` | `top_player_games` / `ok` / `-` | Supported | Stat is rebounds. |
| Sentence | `most_rebounds_single_game_this_year_public_sweep` | `Who had the most rebounds in a game this year?` | `top_player_games` / `ok` / `-` | Supported | `this year` resolves to current season; stat is rebounds. |
| Synonym | `pqa_top_games_synonym_single_game_rebounds` | `single-game rebound leaders this season` | `top_player_games` / `ok` / `-` | Supported | Single-game wording preserved. |
| Inverse/sibling | `rebound_leaders_this_season` | `Who leads the NBA in rebounds this season?` | `season_leaders` / `ok` / `-` | Supported sibling | Season leaderboard does not route to top single-game rebounds. |
| Nearby unsupported | `biggest_team_three_point_games_boundary` | `biggest team three-point games this season` | `None` / `error` / `unrouted` | Unsupported | No top-team-game threes fallback until support is approved. |
| Typo/partial | `pqa_top_games_stat_typo_rebunds` | `most rebunds in a game this season` | `None` / `error` / `unrouted` | Unsupported until stat typo support exists | No broad scoring-games answer. |

Missing user-obvious variants: `single-game <stat> leaders` and typo handling
for stat names in top-game phrasing.

### 7.7 Count Queries

| Variant | Case ID | Query | Expected route / status / reason | Support | No-broad-fallback assertion |
|---|---|---|---|---|---|
| Canonical | `jokic_triple_double_count` | `How often has Nikola Jokic recorded a triple-double this season?` | `player_game_finder` / `ok` / `-` | Supported | Count section is present; special-event filter applied. |
| Short | `pqa_count_short_lebron_triple_doubles` | `count LeBron triple doubles since 2020` | `player_game_finder` / `ok` / `-` | Supported | Count semantics; no raw finder-only answer. |
| Sentence | `celtics_120_15_threes_count_missing_filter` | `how many Celtics games with 120+ points and 15+ threes since 2022` | `team_occurrence_leaders` / `ok` / `-` | Supported | Team count/occurrence semantics preserved. |
| Synonym | `players_10_assist_count` | `number of players with 10 assists this season` | `player_occurrence_leaders` / `ok` / `-` | Supported | Distinct-player count semantics; threshold required. |
| Inverse/sibling | `jokic_30_points_10_assists_finder_misparsed` | `Jokic games with 30 points and 10 assists` | `player_game_finder` / `ok` / `-` | Supported sibling | Finder rows returned; no count section unless count phrasing exists. |
| Nearby unsupported | `pqa_count_unsupported_players_played` | `how many players played this season` | `player_occurrence_leaders` / `no_result` / `filter_not_supported` | Unsupported | No broad player leaderboard; missing threshold is explicit. |
| Typo/partial | `pqa_count_typo_jokc_triple_doubles` | `how many Jokc triple doubles this season` | `None` / `error` / `unrouted` | Unsupported until resolved | No Jokic count unless entity typo resolution is explicit. |

Missing user-obvious variants: `count`, `number of`, and no-threshold
unsupported count coverage in one matrix.

### 7.8 Game Finders

| Variant | Case ID | Query | Expected route / status / reason | Support | No-broad-fallback assertion |
|---|---|---|---|---|---|
| Canonical | `jokic_30_points_10_assists_finder_misparsed` | `Jokic games with 30 points and 10 assists` | `player_game_finder` / `ok` / `-` | Supported | Finder rows for Jokic; no summary-only answer. |
| Short | `curry_5_threes_finder` | `Curry 5+ threes this season` | `player_game_finder` / `ok` / `-` | Supported | Stat threshold is 5+ threes. |
| Sentence | `pqa_finder_sentence_tatum_35_5_threes` | `What games did Tatum have over 35 points and 5+ threes?` | `player_game_finder` / `ok` / `-` | Supported | Player finder route with both thresholds. |
| Synonym | `pqa_finder_synonym_show_lakers_home_losses` | `show me Lakers home losses` | `game_finder` / `ok` / `-` | Supported | Team finder with home and loss filters. |
| Inverse/sibling | `luka_last_10_summary_wave5` | `Luka last 10 games summary` | `player_game_summary` / `ok` / `-` | Supported sibling | Summary wording does not return only finder rows. |
| Nearby unsupported | `celtics_bench_scoring_boundary_wave4` | `Celtics bench scoring this season` | `game_finder` / `no_result` / `filter_not_supported` | Unsupported | `unsupported_filters=["team_bench_scoring"]`; no Celtics scoring finder fallback. |
| Typo/partial | `pqa_finder_typo_curr_5_threes` | `Curr 5+ threes this season` | `None` / `error` / `unrouted` | Unsupported until resolved | No Stephen Curry finder unless partial-name support is explicit. |

Missing user-obvious variants: `show me`, `find`, and typo handling for
entity-led finder fragments.

### 7.9 Splits

| Variant | Case ID | Query | Expected route / status / reason | Support | No-broad-fallback assertion |
|---|---|---|---|---|---|
| Canonical | `jokic_home_away_split` | `Jokic home vs away this season` | `player_split_summary` / `ok` / `-` | Supported | Split buckets are home and away. |
| Short | `celtics_wins_losses_split` | `Celtics wins vs losses` | `team_split_summary` / `ok` / `-` | Supported | Team split buckets are wins and losses. |
| Sentence | `anthony_edwards_wins_losses_split_no_match` | `How does Anthony Edwards shoot in wins versus losses?` | `player_split_summary` / `ok` / `-` | Supported | Player split route with wins/losses buckets. |
| Synonym | `curry_home_away_last_20_split_wave4` | `Stephen Curry home away split last 20 games` | `player_split_summary` / `ok` / `-` | Supported | Last-N context preserved. |
| Inverse/sibling | `knicks_road_record` | `What is the Knicks road record this season?` | `team_record` / `ok` / `-` | Supported sibling | Road record does not become home/away split. |
| Nearby unsupported | `pqa_split_unsupported_celtics_bench_home_away` | `Celtics bench scoring home vs away` | `game_finder` / `no_result` / `filter_not_supported` | Unsupported | Team bench-scoring boundary; no broad Celtics home/away split. |
| Typo/partial | `pqa_split_typo_jokc_home_away` | `Jokc home vs away this season` | `None` / `error` / `unrouted` | Unsupported until resolved | No Jokic split unless partial-name support is explicit. |

Missing user-obvious variants: split-specific unsupported adjacency and typo
coverage.

### 7.10 Streaks

| Variant | Case ID | Query | Expected route / status / reason | Support | No-broad-fallback assertion |
|---|---|---|---|---|---|
| Canonical | `jokic_5_straight_20_points` | `Jokic 5 straight games with 20+ points` | `player_streak_finder` / `ok` / `-` | Supported | Streak route; threshold preserved. |
| Short | `lakers_win_streak` | `longest Lakers winning streak` | `team_streak_finder` / `ok` / `-` | Supported | Team streak route; no team record summary. |
| Sentence | `pqa_streak_sentence_curry_3_threes` | `What is Curry's longest streak with at least 3 threes?` | `player_streak_finder` / `ok` / `-` | Supported | Player streak route with threes threshold. |
| Synonym | `thunder_110_point_streak` | `Thunder consecutive games with 110+ points` | `team_streak_finder` / `ok` / `-` | Supported | `consecutive games` maps to streak. |
| Inverse/sibling | `curry_5_threes_finder` | `Curry 5+ threes this season` | `player_game_finder` / `ok` / `-` | Supported sibling | No streak route without streak/consecutive wording. |
| Nearby unsupported | `cooled_off_lately_wave5` | `who has cooled off lately` | `None` / `error` / `unrouted` | Unsupported | No trend-to-streak or trend-to-leaderboard fallback. |
| Typo/partial | `pqa_streak_typo_jok_longest` | `Jok longest 30 point streak` | `None` / `error` / `unrouted` | Unsupported until resolved | No Jokic streak unless partial-name support is explicit. |

Missing user-obvious variants: sentence forms and trend-adjacent unsupported
coverage in the public acceptance slice.

### 7.11 Rolling Stretches

| Variant | Case ID | Query | Expected route / status / reason | Support | No-broad-fallback assertion |
|---|---|---|---|---|---|
| Canonical | `hottest_3_game_scoring_stretch` | `Which players have the hottest 3-game scoring stretch this year?` | `player_stretch_leaderboard` / `ok` / `-` | Supported | Window size is 3; stat is scoring/points. |
| Short | `booker_4_game_scoring_stretch` | `Booker hottest 4-game scoring stretch` | `player_stretch_leaderboard` / `ok` / `-` | Supported | Named-player stretch; window size is 4. |
| Sentence | `pqa_stretch_sentence_game_score` | `Who has the best 5-game stretch by Game Score?` | `player_stretch_leaderboard` / `ok` / `-` | Supported | Stat is Game Score; window size is 5. |
| Synonym | `efficient_10_game_stretch` | `most efficient 10-game rolling stretch` | `player_stretch_leaderboard` / `ok` / `-` | Supported | Efficiency stat context preserved. |
| Inverse/sibling | `team_5_game_scoring_stretch` | `best 5-game team scoring stretch this season` | `player_stretch_leaderboard` / `no_result` / `filter_not_supported` | Unsupported sibling | `unsupported_filters=["team_rolling_stretch"]`; no player stretch rows. |
| Nearby unsupported | `team_net_rating_stretch_unsupported` | `best 5-game team net rating stretch` | `player_stretch_leaderboard` / `no_result` / `filter_not_supported` | Unsupported | Team rolling-stretch unsupported; empty sections. |
| Typo/partial | `pqa_stretch_typo_bookr` | `Bookr hottest 4-game scoring stretch` | `None` / `error` / `unrouted` | Unsupported until resolved | No Devin Booker stretch unless partial-name support is explicit. |

Missing user-obvious variants: Game Score sentence form and typo/partial names.

### 7.12 Comparisons

| Variant | Case ID | Query | Expected route / status / reason | Support | No-broad-fallback assertion |
|---|---|---|---|---|---|
| Canonical | `lebron_durant_comparison_wave4` | `LeBron James vs Kevin Durant comparison` | `player_compare` / `ok` / `-` | Supported | Two-player comparison route. |
| Short | `jokic_embiid_recent_comparison` | `Jokic vs Embiid recent form` | `player_compare` / `ok` / `-` | Supported | Two-player recent comparison; not two separate summaries. |
| Sentence | `compare_lebron_durant_wave5` | `Compare LeBron James and Kevin Durant` | `player_compare` / `ok` / `-` | Supported | Compare wording maps to player comparison. |
| Synonym | `celtics_bucks_comparison_this_season_wave5` | `Celtics vs Bucks comparison this season` | `team_compare` / `ok` / `-` | Supported | Team comparison route. |
| Inverse/sibling | `lebron_stats_vs_durant_wave5` | `LeBron stats vs Kevin Durant` | `player_game_finder` / `ok` / `-` | Supported sibling | Stats-vs-player context does not route to player comparison. |
| Nearby unsupported | `pqa_comparison_subjective_better_jokic_embiid` | `Who is better, Jokic or Embiid?` | `None` / `error` / `unrouted` | Unsupported | No invented comparison winner or broad comparison table. |
| Typo/partial | `pqa_comparison_typo_kevn_durant` | `LeBron vs Kevn Durant comparison` | `None` / `error` / `unrouted` | Unsupported until resolved | No player comparison unless partial-name support is explicit. |

Missing user-obvious variants: subjective comparison boundary and typo/partial
opponent names.

### 7.13 Playoff History

| Variant | Case ID | Query | Expected route / status / reason | Support | No-broad-fallback assertion |
|---|---|---|---|---|---|
| Canonical | `lakers_playoff_history` | `Lakers playoff history` | `playoff_history` / `ok` / `-` | Supported | Single-team playoff history route. |
| Short | `lakers_finals_appearances` | `Lakers Finals appearances` | `playoff_appearances` / `ok` / `-` | Supported | Finals appearances route; no regular-season record. |
| Sentence | `lakers_celtics_playoff_matchup_history_wave5` | `Lakers Celtics playoff matchup history` | `playoff_matchup_history` / `ok` / `-` | Supported | Team-pair playoff matchup route. |
| Synonym | `heat_knicks_playoff_series_record_wave4` | `Heat Knicks playoff series record` | `playoff_matchup_history` / `ok` / `-` | Supported | Adjacent team names bind only in playoff series context. |
| Inverse/sibling | `celtics_record_playoff_teams` | `What is the Celtics' record against playoff teams?` | `team_record` / `ok` / `-` | Supported sibling | Opponent-quality phrase remains regular-season team record. |
| Nearby unsupported | `bulls_finals_record_wave4` | `Bulls Finals record` | `playoff_history` / `no_result` / `filter_not_supported` | Unsupported | `unsupported_filters=["single_team_playoff_round_record"]`; no regular-season Bulls record. |
| Typo/partial | `pqa_playoff_typo_lakeers_history` | `Lakeers playoff history` | `None` / `error` / `unrouted` | Unsupported until resolved | No Lakers playoff history unless typo support is explicit. |

Missing user-obvious variants: typo/partial team names and explicit
opponent-quality-vs-playoff-history sibling grouping in the acceptance slice.

### 7.14 Date / Window Filters

| Variant | Case ID | Query | Expected route / status / reason | Support | No-broad-fallback assertion |
|---|---|---|---|---|---|
| Canonical | `top_scorers_in_march` | `top scorers in March` | `season_leaders` / `ok` / `-` | Supported | Month filter is applied; no full-season leaderboard. |
| Short | `luka_last_5_summary` | `Luka last 5` | `player_game_summary` / `ok` / `-` | Supported | Last-N context is 5 games. |
| Sentence | `specific_date_jan_1` | `Who scored the most points on January 1 2026?` | `top_player_games` / `ok` / `-` | Supported | Explicit date filter; top-game route. |
| Synonym | `jokic_since_all_star_break` | `Jokic since All-Star break` | `player_game_finder` / `ok` / `-` | Supported | Since-All-Star window preserved. |
| Inverse/sibling | `most_points_last_night` | `Who scored the most points last night?` | `season_leaders` / `no_result` / `no_match` | Supported no-match boundary | No fallback to latest full-season scoring leaders. |
| Nearby unsupported | `pqa_date_unsupported_since_trade_deadline` | `best offensive teams since the trade deadline` | `season_team_leaders` / `no_result` / `filter_not_supported` | Unsupported until date anchor exists | No full-season team leaderboard. |
| Typo/partial | `pqa_date_typo_marhc` | `top scorers in Marhc` | `None` / `error` / `unrouted` | Unsupported until date typo support exists | No March or full-season leaderboard unless typo support is explicit. |

Missing user-obvious variants: unsupported vague anchors such as trade deadline
and malformed month names.

### 7.15 Unsupported Subjective / Narrative Questions

| Variant | Case ID | Query | Expected route / status / reason | Support | No-broad-fallback assertion |
|---|---|---|---|---|---|
| Canonical unsupported | `best_defender_subjective` | `Who is the best defender in the NBA?` | `None` / `error` / `unrouted` | Unsupported | No defensive rating or blocks leaderboard fallback. |
| Short | `pqa_subjective_short_mvp_candidates` | `MVP candidates` | `None` / `error` / `unrouted` | Unsupported | No points leaderboard or player summary fallback. |
| Sentence | `cooled_off_lately_wave5` | `who has cooled off lately` | `None` / `error` / `unrouted` | Unsupported | No trend-to-recent-form fallback. |
| Synonym | `most_clutch_player_wave5` | `Who is the most clutch player this season?` | `season_leaders` / `no_result` / `filter_not_supported` | Unsupported | No broad points leaderboard; unsupported subjective clutch is explicit. |
| Inverse/sibling | `tatum_clutch_stats` | `Tatum clutch stats` | `player_game_summary` / `no_result` / `filter_not_supported` | Unsupported-data sibling | Concrete player clutch stats route may preserve route, but no broad Tatum stats. |
| Nearby unsupported | `best_duo_unsupported` | `Who is the best duo this season?` | `None` / `error` / `unrouted` | Unsupported | No lineup or comparison fallback without a supported definition. |
| Typo/partial | `pqa_subjective_typo_defnder` | `best defnder in NBA` | `None` / `error` / `unrouted` | Unsupported | No broad fallback despite typo. |

Missing user-obvious variants: short fragments like `MVP candidates` and
typo-laden subjective questions.

### 7.16 Typo / Partial Entity Behavior

This family is a cross-cutting guardrail, not a product feature to support by
itself. It should reuse typo rows from other families and include a few
route-preserving filter typos.

| Variant | Case ID | Query | Expected route / status / reason | Support | No-broad-fallback assertion |
|---|---|---|---|---|---|
| Canonical typo guard | `lakers_record_without_luk_public_sweep` | `Lakers record without Luk` | `team_record` / `no_result` / `filter_not_supported` | Unsupported | Unresolved availability filter preserved; no full Lakers record. |
| Short | `pqa_typo_short_jokc_stats` | `Jokc stats` | `None` / `error` / `unrouted` | Unsupported until resolved | No Nikola Jokic summary unless resolver support is explicit. |
| Sentence | `pqa_typo_sentence_tatm_recent` | `How has Tatm played recently?` | `None` / `error` / `unrouted` | Unsupported until resolved | No Tatum recent-form fallback. |
| Synonym | `pqa_typo_synonym_stephn_averages` | `Stephn Curry averages this season` | `None` / `error` / `unrouted` | Unsupported until resolved | No Stephen Curry summary unless typo support is explicit. |
| Inverse/sibling | `luka_stats_this_season_public_sweep` | `Luka stats this season` | `player_game_summary` / `ok` / `-` | Supported sibling | Confirms correctly spelled short name still resolves. |
| Nearby unsupported | `pqa_typo_team_lakeers_record` | `Lakeers record this season` | `None` / `error` / `unrouted` | Unsupported until resolved | No Lakers record unless typo support is explicit. |
| Typo/partial | `pqa_typo_partial_kevn_comparison` | `LeBron vs Kevn Durant comparison` | `None` / `error` / `unrouted` | Unsupported until resolved | No comparison table with one unresolved entity. |

Missing user-obvious variants: typo/partial coverage across player, team,
comparison, and filter contexts.

## 8. Cases To Add Or Retag

Existing cases to include in `public_query_acceptance` should be tagged rather
than duplicated. The matrix above names the exact existing IDs.

New proposed cases:

- `pqa_player_stats_sentence_luka_played`
- `pqa_player_stats_synonym_luka_averages`
- `pqa_player_stats_typo_jokc`
- `pqa_team_record_short_celtics_record`
- `pqa_team_record_typo_celtcs`
- `pqa_availability_short_lakers_w_luka`
- `pqa_availability_sentence_luka_plays`
- `pqa_availability_synonym_reaves_available`
- `pqa_player_recent_typo_tatm`
- `pqa_leaderboard_stat_typo_pionts`
- `pqa_top_games_synonym_single_game_rebounds`
- `pqa_top_games_stat_typo_rebunds`
- `pqa_count_short_lebron_triple_doubles`
- `pqa_count_unsupported_players_played`
- `pqa_count_typo_jokc_triple_doubles`
- `pqa_finder_sentence_tatum_35_5_threes`
- `pqa_finder_synonym_show_lakers_home_losses`
- `pqa_finder_typo_curr_5_threes`
- `pqa_split_unsupported_celtics_bench_home_away`
- `pqa_split_typo_jokc_home_away`
- `pqa_streak_sentence_curry_3_threes`
- `pqa_streak_typo_jok_longest`
- `pqa_stretch_sentence_game_score`
- `pqa_stretch_typo_bookr`
- `pqa_comparison_subjective_better_jokic_embiid`
- `pqa_comparison_typo_kevn_durant`
- `pqa_playoff_typo_lakeers_history`
- `pqa_date_unsupported_since_trade_deadline`
- `pqa_date_typo_marhc`
- `pqa_subjective_short_mvp_candidates`
- `pqa_subjective_typo_defnder`
- `pqa_typo_short_jokc_stats`
- `pqa_typo_sentence_tatm_recent`
- `pqa_typo_synonym_stephn_averages`
- `pqa_typo_team_lakeers_record`
- `pqa_typo_partial_kevn_comparison`

Before adding any new case, probe current behavior. If a proposed supported
case fails, do not weaken the expected behavior to match the failure. Split it
into a behavior-fix wave or mark it as intentionally unsupported by product
decision.

## 9. Execution Plan

Future execution wave:

1. Probe every proposed new query through `execute_natural_query()` and
   `query_result_to_payload()`.
2. Classify each new case as one of:
   - current behavior already matches expected acceptance target
   - product bug requiring parser/routing/execution fix
   - intentionally unsupported boundary requiring no-broad-fallback expectation
   - needs product decision
3. Add or retag raw QA cases in `qa/raw_query_answer_corpus.yaml`.
4. Add `qa/harness_slices/public_query_acceptance.yaml` with all matrix case IDs.
5. For route families whose new cases fail, fix behavior in PR-sized units
   before landing the corpus expectation.
6. Run targeted acceptance validation:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice public_query_acceptance --fail-on-expectation-failure
```

7. Run adjacent route-priority and product-boundary slices:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice natural_query_route_priority --slice product_boundaries --fail-on-expectation-failure
```

8. If production parser/routing or execution changed, run:

```bash
make test-parser
make test-query
make test-preflight
```

9. Always finish with:

```bash
git diff --check
```

## 10. Stop Conditions

Stop and re-plan if the future execution wave:

- needs a separate public corpus to pass
- changes release status
- changes frontend rendering to mask backend answer gaps
- weakens an unsupported boundary into a broad successful answer
- changes expected route/status/reason to match a known wrong route
- adds typo autocorrection without explicit product approval and no-broad-
  fallback tests
- adds public docs that advertise behavior before raw QA acceptance passes

## 11. Preflight Validation

This preflight created only planning and return-package documentation. No code,
QA corpus, harness slice, frontend, or release-status files were changed.

Required validation for this preflight:

```bash
git diff --check
```

## 12. Wave 1 Probe And Seed Results

Wave 1 probed all 36 proposed new `pqa_*` cases from section 8 through
`execute_natural_query()` and `query_result_to_payload()`.

Wave 1 corpus/slice result:

| Metric | Count |
|---|---:|
| Proposed new `pqa_*` cases probed | 36 |
| New safe `pqa_*` cases added | 21 |
| Existing cases reused and retagged | 33 |
| Total `public_query_acceptance` slice cases | 54 |
| Slice cases with `acceptance` metadata | 54 |
| Slice cases with `acceptance.no_broad_fallback=true` | 35 |
| Proposed new cases deferred as behavior failures | 11 |
| Proposed new cases requiring product decision | 2 |
| Proposed new cases not added as duplicates | 2 |

Wave 1 added `qa/harness_slices/public_query_acceptance.yaml` and tagged
included raw QA cases with:

- `acceptance.family`
- `acceptance.variant`
- `acceptance.no_broad_fallback` where the case is a sibling, unsupported, or
  typo/partial guard

Wave 1 did not add any expected-ok case that currently fails. It also did not
encode broad fallback behavior as acceptable.

### 12.1 Family Coverage In Seed Slice

| Family | Slice cases | Notes |
|---|---:|---|
| `player_stats_this_season` | 6 | Includes canonical, short, sentence, synonym, nearby unsupported, and typo guard. |
| `team_records` | 5 | Includes canonical, short, sentence, matchup sibling, and division unsupported guard. |
| `team_record_availability` | 6 | Includes the full recent `basic_public_availability` supported/unsupported set plus sentence-form presence. |
| `player_summaries_recent_form` | 3 | Includes recent-form canonical, comparison sibling, and typo guard. |
| `leaderboards` | 2 | Includes canonical leaderboard and unsupported rookie-boundary guard. |
| `top_single_game_performances` | 4 | Includes canonical, sentence, synonym, and stat-typo guard. |
| `count_queries` | 3 | Includes canonical count, no-threshold unsupported guard, and typo guard. |
| `game_finders` | 4 | Includes canonical finder, sentence-form route/no-match, synonym, and typo guard. |
| `splits` | 2 | Includes canonical split and typo guard. |
| `streaks` | 3 | Includes canonical streak, trend-adjacent unsupported guard, and typo guard. |
| `rolling_stretches` | 3 | Includes canonical, sentence Game Score, and team-stretch unsupported sibling. |
| `comparisons` | 1 | Includes subjective better-than unsupported guard. |
| `playoff_history` | 4 | Includes canonical history, opponent-quality sibling, round-record unsupported guard, and typo guard. |
| `date_window_filters` | 2 | Includes month filter and last-night no-match guard. |
| `unsupported_subjective_narrative` | 5 | Includes subjective, awards, clutch, duo, and typo/narrative guards. |
| `typo_partial_entity_behavior` | 1 | Includes cross-family unresolved player shorthand guard. |

### 12.2 New Cases Added In Wave 1

| Case ID | Classification |
|---|---|
| `pqa_player_stats_sentence_luka_played` | Safe supported expectation. |
| `pqa_player_stats_synonym_luka_averages` | Safe supported expectation. |
| `pqa_player_stats_typo_jokc` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_team_record_short_celtics_record` | Safe supported expectation. |
| `pqa_availability_sentence_luka_plays` | Safe supported expectation. |
| `pqa_player_recent_typo_tatm` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_top_games_synonym_single_game_rebounds` | Safe supported expectation. |
| `pqa_top_games_stat_typo_rebunds` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_count_unsupported_players_played` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_count_typo_jokc_triple_doubles` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_finder_sentence_tatum_35_5_threes` | Safe supported route with `no_match`; no broad fallback. |
| `pqa_finder_synonym_show_lakers_home_losses` | Safe supported expectation. |
| `pqa_finder_typo_curr_5_threes` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_split_typo_jokc_home_away` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_streak_typo_jok_longest` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_stretch_sentence_game_score` | Safe supported expectation. |
| `pqa_comparison_subjective_better_jokic_embiid` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_playoff_typo_lakeers_history` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_subjective_short_mvp_candidates` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_subjective_typo_defnder` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_typo_short_jokc_stats` | Safe unsupported/no-broad-fallback expectation. |

### 12.3 Proposed Cases Not Added

| Case ID | Probe result | Classification | Next action |
|---|---|---|---|
| `pqa_team_record_typo_celtcs` | `team_record_leaderboard` / `ok` | Behavior failure | Add team/entity typo guard so unresolved team-like record fragments do not become broad record leaderboards. |
| `pqa_availability_short_lakers_w_luka` | `player_game_summary` / `ok` | Behavior failure | Extend whole-game presence parsing to `w/ PLAYER` team-record phrasing. |
| `pqa_availability_synonym_reaves_available` | `player_game_summary` / `ok` | Behavior failure | Extend team availability routing for `TEAM wins with PLAYER` without crossing into player summaries. |
| `pqa_leaderboard_stat_typo_pionts` | `season_leaders` / `ok` | Behavior failure | Guard misspelled stat words so they do not default to broad points leaderboards. |
| `pqa_count_short_lebron_triple_doubles` | `player_occurrence_leaders` / `ok` | Behavior failure | Route player-specific `count PLAYER triple doubles` to player count/finder semantics, not occurrence leaderboard semantics. |
| `pqa_split_unsupported_celtics_bench_home_away` | `team_split_summary` / `ok` | Behavior failure | Preserve team bench-scoring unsupported boundary before split routing. |
| `pqa_streak_sentence_curry_3_threes` | `player_game_finder` / `ok` | Behavior failure | Preserve sentence-form `longest streak` wording on streak route. |
| `pqa_stretch_typo_bookr` | `player_stretch_leaderboard` / `ok` | Behavior failure | Do not drop unresolved named-player fragments and return broad stretch leaderboards. |
| `pqa_comparison_typo_kevn_durant` | `player_compare` / `ok` | Product decision required | Decide whether typo-tolerant player resolution is an intentional supported behavior and document/test it. |
| `pqa_date_unsupported_since_trade_deadline` | `season_team_leaders` / `ok` | Behavior failure | Unsupported date anchors must not be ignored into full-scope leaderboards. |
| `pqa_date_typo_marhc` | `season_leaders` / `ok` | Behavior failure | Misspelled date/month filters must not be ignored into broad leaderboards. |
| `pqa_typo_sentence_tatm_recent` | `None` / `error` / `unrouted` | Duplicate of existing sufficient case | Covered by `pqa_player_recent_typo_tatm`. |
| `pqa_typo_synonym_stephn_averages` | `player_game_summary` / `ok` | Product decision required | Decide whether typo-tolerant player resolution is supported; if yes, add explicit contract coverage. |
| `pqa_typo_team_lakeers_record` | `team_record_leaderboard` / `ok` | Behavior failure | Add unresolved team typo guard for record phrasing. |
| `pqa_typo_partial_kevn_comparison` | `player_compare` / `ok` | Duplicate of product-decision case | Covered by `pqa_comparison_typo_kevn_durant` decision path. |

### 12.4 Wave 1 Validation

Passed:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice public_query_acceptance --fail-on-expectation-failure
```

Result: `outputs/raw_query_answer_qa/20260528T073054Z`; 54 cases,
expectation cases `pass: 54`, failed case IDs none, suspicious flag cases 0.

Passed:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice basic_public_availability --fail-on-expectation-failure
```

Result: `outputs/raw_query_answer_qa/20260528T073305Z`; 7 cases, expectation
cases `pass: 7`, failed case IDs none, suspicious flag cases 0.

Passed:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice natural_query_route_priority --slice product_boundaries --fail-on-expectation-failure
```

Result: `outputs/raw_query_answer_qa/20260528T073305Z`; 49 cases, expectation
cases `pass: 49`, failed case IDs none, suspicious flag cases 0.

Parser/query/preflight test slices were not run because Wave 1 did not change
production parser, routing, or execution behavior.

### 12.5 Recommended Fix Waves

1. Typo/partial no-broad-fallback guards for unresolved team/stat/date/named
   player fragments.
2. Availability phrase expansion for `w/ PLAYER` and `TEAM wins with PLAYER`.
3. Count route fix for player-specific shorthand special-event counts.
4. Route-priority fixes for bench-scoring split phrasing and sentence-form
   streak wording.
5. Product decision on whether typo-tolerant player resolution is intentionally
   supported for cases such as `Kevn Durant` and `Stephn Curry`.

## 13. Wave 2A No-Broad-Fallback Guard Results

Wave 2A fixed the highest-priority unresolved/bad-fragment fallback failures
from section 12.3. The implementation added narrow parser guards only; it did
not add typo correction, new feature support, frontend changes, release-status
changes, or broad fallback expectations.

### 13.1 Cases Fixed And Seeded

| Case ID | Query | Before | After | Unsupported filter |
|---|---|---|---|---|
| `pqa_team_record_typo_celtcs` | `Celtcs record this season` | `team_record_leaderboard` / `ok` | `team_record_leaderboard` / `no_result` / `filter_not_supported` | `unresolved_team` |
| `pqa_typo_team_lakeers_record` | `Lakeers record this season` | `team_record_leaderboard` / `ok` | `team_record_leaderboard` / `no_result` / `filter_not_supported` | `unresolved_team` |
| `pqa_leaderboard_stat_typo_pionts` | `Who leads the NBA in pionts per game this season?` | `season_leaders` / `ok` | `season_leaders` / `no_result` / `filter_not_supported` | `unresolved_stat` |
| `pqa_date_typo_marhc` | `top scorers in Marhc` | `season_leaders` / `ok` | `season_leaders` / `no_result` / `filter_not_supported` | `unresolved_date` |
| `pqa_date_unsupported_since_trade_deadline` | `best offensive teams since the trade deadline` | `season_team_leaders` / `ok` | `season_team_leaders` / `no_result` / `filter_not_supported` | `unsupported_date_anchor` |
| `pqa_stretch_typo_bookr` | `Bookr hottest 4-game scoring stretch` | `player_stretch_leaderboard` / `ok` | `player_stretch_leaderboard` / `no_result` / `filter_not_supported` | `unresolved_player` |

Wave 2A added these six cases to `qa/raw_query_answer_corpus.yaml` with
`acceptance.family`, `acceptance.variant`, and
`acceptance.no_broad_fallback=true`, then added the case IDs to
`qa/harness_slices/public_query_acceptance.yaml`.

Current public acceptance slice totals after Wave 2A:

| Metric | Count |
|---|---:|
| Total `public_query_acceptance` slice cases | 60 |
| Cases added in Wave 2A | 6 |
| Wave 1 deferred behavior failures fixed in Wave 2A | 6 |
| Remaining Wave 1 behavior failures intentionally left for later waves | 5 |
| Product-decision cases still open | 2 |

### 13.2 Root Cause

The parser already had an unsupported-filter execution path, but several route
families only checked for positive supported matches. If a user supplied an
unresolved fragment that looked like a public filter or subject, the remaining
tokens still satisfied a broad leaderboard route:

- unresolved team-like prefixes before `record`
- stat-like misspellings before `per game`
- month-like misspellings in date-window phrasing
- unsupported named date anchors such as `trade deadline`
- unresolved player-like prefixes before rolling-stretch phrasing

Wave 2A added guard detection before the broad record, metric-leaderboard, and
rolling-stretch defaults.

### 13.3 Behavior Preserved

The guards are intentionally narrow. Supported sibling examples still route as
supported behavior:

| Query | Preserved route/status |
|---|---|
| `Booker hottest 4-game scoring stretch` | `player_stretch_leaderboard` / `ok` |
| `hottest 3-game scoring stretch this year` | `player_stretch_leaderboard` / `ok` |
| `best record this season` | `team_record_leaderboard` / `ok` |
| `top scorers in March` | `season_leaders` / `ok` with March date window |

### 13.4 Validation

Passed:

```bash
.venv/bin/pytest tests/test_natural_query_parser.py::test_public_query_bad_fragments_do_not_broad_fallback -n0
.venv/bin/pytest tests/test_ui_failure_coverage.py::TestP2BoundaryRoutingCleanup::test_public_query_bad_fragment_guards_return_no_result -n0
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice public_query_acceptance --fail-on-expectation-failure
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice basic_public_availability --fail-on-expectation-failure
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice natural_query_route_priority --slice product_boundaries --fail-on-expectation-failure
```

Raw QA results:

- `public_query_acceptance`: `outputs/raw_query_answer_qa/20260528T101541Z`,
  60 cases, expectation cases `pass: 60`, failed case IDs none.
- `basic_public_availability`: `outputs/raw_query_answer_qa/20260528T101716Z`,
  7 cases, expectation cases `pass: 7`, failed case IDs none.
- `natural_query_route_priority` + `product_boundaries`:
  `outputs/raw_query_answer_qa/20260528T101716Z`, 49 cases, expectation cases
  `pass: 49`, failed case IDs none.

Full parser/query slice and whitespace validation results are recorded in the
Wave 2A return package.

### 13.5 Remaining Later Waves

Wave 2A intentionally left these Wave 1 failures for later work:

- availability shorthand: `pqa_availability_short_lakers_w_luka`
- availability synonym: `pqa_availability_synonym_reaves_available`
- player-specific count shorthand: `pqa_count_short_lebron_triple_doubles`
- bench split boundary: `pqa_split_unsupported_celtics_bench_home_away`
- streak sentence route priority: `pqa_streak_sentence_curry_3_threes`

The product-decision items for typo-tolerant player resolution also remain
open:

- `pqa_comparison_typo_kevn_durant`
- `pqa_typo_synonym_stephn_averages`

## 14. Wave 2B Availability Shorthand And Synonym Results

Wave 2B fixed the two remaining team-record player-availability public-query
acceptance failures. The implementation stayed inside the existing
single-player whole-game availability contract:

- `w/ PLAYER` is now a with-player presence marker for team-record availability.
- `with PLAYER available` plus team win intent now routes to team-record
  availability before player finder/count routes.
- Compound availability, unresolved availability names, fuzzy typo correction,
  frontend rendering, and result contracts were not changed.

### 14.1 Cases Fixed And Seeded

| Case ID | Query | Before | After | Scope proof |
|---|---|---|---|---|
| `pqa_availability_short_lakers_w_luka` | `Lakers record w/ Luka` | `player_game_summary` / `ok`; Luka player subject | `team_record` / `ok`; `with_player=Luka Dončić` | Lakers team summary, 64 games, 43-21, game log |
| `pqa_availability_synonym_reaves_available` | `How many games did the Lakers win with Reaves available?` | `player_game_finder` / `ok`; Reaves player rows | `team_record` / `ok`; `with_player=Austin Reaves`, `wins_only=true` | Lakers team summary, 36 games, 36-0, game log |

Wave 2B added both cases to `qa/raw_query_answer_corpus.yaml` with
`acceptance.family`, `acceptance.variant`, and
`acceptance.no_broad_fallback=true`, then added the case IDs to
`qa/harness_slices/public_query_acceptance.yaml`.

Current public acceptance slice totals after Wave 2B:

| Metric | Count |
|---|---:|
| Total `public_query_acceptance` slice cases | 62 |
| Cases added in Wave 2B | 2 |
| Wave 1 deferred behavior failures fixed in Wave 2B | 2 |
| Remaining Wave 1 behavior failures intentionally left for later waves | 3 |
| Product-decision cases still open | 2 |

### 14.2 Behavior Preserved

Existing availability behavior stayed covered and green:

| Query | Preserved route/status |
|---|---|
| `Lakers record with Luka` | `team_record` / `ok`; `with_player=Luka Dončić` |
| `Lakers record with Reaves` | `team_record` / `ok`; `with_player=Austin Reaves` |
| `Lakers record without Luka` | `team_record` / `ok`; `without_player=Luka Dončić` |
| `Lakers record with Reaves without Luka` | `team_record` / `no_result` / `filter_not_supported`; `multi_player_availability` |
| `Lakers record without Luk` | `team_record` / `no_result` / `filter_not_supported`; `unresolved_player_availability` |

Wave 2A no-broad-fallback guards also stayed green through the
`public_query_acceptance`, `natural_query_route_priority`, and
`product_boundaries` raw QA slices.

### 14.3 Validation

Passed:

```bash
.venv/bin/pytest tests/test_ui_failure_coverage.py::TestWithoutPlayer -n0
```

Result: 51 passed.

Passed:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice public_query_acceptance --fail-on-expectation-failure
```

Result: `outputs/raw_query_answer_qa/20260528T111333Z`; 62 cases,
expectation cases `pass: 62`, failed case IDs none.

Passed:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice basic_public_availability --fail-on-expectation-failure
```

Result: `outputs/raw_query_answer_qa/20260528T111713Z`; 7 cases,
expectation cases `pass: 7`, failed case IDs none.

Passed:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice natural_query_route_priority --slice product_boundaries --fail-on-expectation-failure
```

Result: `outputs/raw_query_answer_qa/20260528T111713Z`; 49 cases,
expectation cases `pass: 49`, failed case IDs none.

Passed:

```bash
make PYTEST=.venv/bin/pytest test-parser
```

Result: 782 passed in 205.01s.

Passed:

```bash
make PYTEST=.venv/bin/pytest test-query
```

Result: 798 passed in 342.73s.

Passed:

```bash
git diff --check
```

Result: no whitespace diagnostics.

### 14.4 Remaining Later Waves

Wave 2B intentionally left these Wave 1 failures for later work:

- player-specific count shorthand: `pqa_count_short_lebron_triple_doubles`
- bench split boundary: `pqa_split_unsupported_celtics_bench_home_away`
- streak sentence route priority: `pqa_streak_sentence_curry_3_threes`

The product-decision items for typo-tolerant player resolution also remain
open:

- `pqa_comparison_typo_kevn_durant`
- `pqa_typo_synonym_stephn_averages`
