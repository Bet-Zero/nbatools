# Frozen K03 binding — implementation pending

This is a finite binding for the existing completion-program K03 row, not another queue. The independent checker froze these expectations before interpreter execution. A later single cached baseline is preserved in [k03-baseline.json](k03-baseline.json); no capability acceptance is claimed. The controlling checkpoint requires I/N/L/D, controlled discrimination, actual raw arithmetic, a second entity/value, and rendered/deployed evidence. Source: pinned queue-d-production-0574735-20260716, regular season 2023-24.

## Existing anchors to reuse

| Obligation | Existing test/corpus anchors | Remaining binding |
|---|---|---|
| Two AND bounds, exact zero | `tests/test_compound_event_routing_integrity.py::test_two_threshold_parse_reads_both_conditions`; `tests/test_ranked_zero_conditions.py`; corpus `b1_games_with_10_assists_0_turnovers_list`, `b1_how_often_player_10_assists_0_turnovers` | Exact-zero finder/count combination must execute, not only parse/rank. A1/A2 below. |
| Strict/inclusive | `tests/test_query_service.py::TestCountFinalizerParity::test_strict_threshold_copy_is_deduplicated_and_human_readable`, `test_strict_under_threshold_copy_hides_storage_epsilon`; `tests/test_c1_negated_bounds.py::test_not_under_is_a_floor` | Bind equality-containing actual populations B1–B4; display exclusive vs inclusive correctly. |
| Grouped OR | `tests/test_query_service.py::TestCountFinalizerParity::test_grouped_or_evaluates_against_an_unfiltered_base`, `test_top_level_and_grouped_or_are_result_equivalent`; corpus `a06_boolean_count_grouped_or`, `a06_boolean_count_top_level_or` | C1/C2 direct union, no duplicated overlap or prefiltered branch. |
| Games vs distinct players | `tests/test_occurrence_queries.py::TestServiceCompatibility::test_distinct_player_count_natural`; `tests/test_c1_occurrence_vs_groups.py::test_distinct_counts_require_every_condition_in_one_game`; corpus `players_40_point_count` | D1/D2 same predicate, different declared grain; no leaderboard truncation. |
| Qualified zero | `tests/test_query_service.py::TestCountNegativeFinalization::test_explicit_no_match_becomes_trusted_zero`, `test_negative_reasons_never_become_zero`, `test_exact_coverage_failure_survives_shared_cli_envelope` | E1/E2 full covered subject season with max below threshold; separate unavailable-source negative control. |

Existing dynamic “this season” corpus cases are reusable semantic anchors, not numeric proof for this pinned 2023-24 binding. New frozen IDs below need committed selectors and corpus entries before delivery.

## Frozen proposed raw-row expectations

Each tuple below is `(game_id, team_id, player_id)`. Lists must match the entire key set; counts must declare their grain. Sums/means are supporting arithmetic, not required extra display fields for a count response. Player W/L is joined from canonical team rows by `(game_id,team_id)`.

### K03-A1

List Nikola Jokic games with at least 10 assists and exactly zero turnovers in 2023-24.

- Grain: player-game list. Player-game rows=3; unique NBA game IDs=3; distinct players=1; W/L=2/1.
- PTS/REB/AST sums: [100, 35, 40]; means: [33.333333333333336, 11.666666666666666, 13.333333333333334].
- Exact keys: `[[22300263,1610612743,203999],[22300290,1610612743,203999],[22300906,1610612743,203999]]`.

### K03-A2

In 2023-24, how many Jalen Brunson games had 8 or more assists and no turnovers?

- Grain: player-game count. Player-game rows=4; unique NBA game IDs=4; distinct players=1; W/L=3/1.
- PTS/REB/AST sums: [117, 11, 37]; means: [29.25, 2.75, 9.25].
- Exact keys: `[[22300643,1610612752,1628973],[22300671,1610612752,1628973],[22301009,1610612752,1628973],[22301175,1610612752,1628973]]`.

### K03-B1

How many Nikola Jokic games exceeded 30 points in 2023-24?

- Grain: player-game count. Player-game rows=26; unique NBA game IDs=26; distinct players=1; W/L=20/6.
- PTS/REB/AST sums: [901, 346, 226]; means: [34.65384615384615, 13.307692307692308, 8.692307692307692].
- Exact keys: `[[22300006,1610612743,203999],[22300024,1610612743,203999],[22300048,1610612743,203999],[22300156,1610612743,203999],[22300169,1610612743,203999],[22300182,1610612743,203999],[22300252,1610612743,203999],[22300263,1610612743,203999],[22300290,1610612743,203999],[22300369,1610612743,203999],[22300383,1610612743,203999],[22300478,1610612743,203999],[22300586,1610612743,203999],[22300602,1610612743,203999],[22300614,1610612743,203999],[22300631,1610612743,203999],[22300824,1610612743,203999],[22300869,1610612743,203999],[22300906,1610612743,203999],[22300937,1610612743,203999],[22300965,1610612743,203999],[22300995,1610612743,203999],[22301071,1610612743,203999],[22301099,1610612743,203999],[22301114,1610612743,203999],[22301164,1610612743,203999]]`.

### K03-B2

How many Nikola Jokic games reached at least 30 points in 2023-24?

- Grain: player-game count. Player-game rows=28; unique NBA game IDs=28; distinct players=1; W/L=21/7.
- PTS/REB/AST sums: [961, 373, 249]; means: [34.32142857142857, 13.321428571428571, 8.892857142857142].
- Exact keys: `[[22300006,1610612743,203999],[22300024,1610612743,203999],[22300048,1610612743,203999],[22300156,1610612743,203999],[22300169,1610612743,203999],[22300182,1610612743,203999],[22300226,1610612743,203999],[22300252,1610612743,203999],[22300263,1610612743,203999],[22300290,1610612743,203999],[22300369,1610612743,203999],[22300383,1610612743,203999],[22300478,1610612743,203999],[22300586,1610612743,203999],[22300602,1610612743,203999],[22300614,1610612743,203999],[22300631,1610612743,203999],[22300824,1610612743,203999],[22300869,1610612743,203999],[22300906,1610612743,203999],[22300937,1610612743,203999],[22300965,1610612743,203999],[22300995,1610612743,203999],[22301009,1610612743,203999],[22301071,1610612743,203999],[22301099,1610612743,203999],[22301114,1610612743,203999],[22301164,1610612743,203999]]`.

### K03-B3

Anthony Edwards games above 35 points in 2023-24.

- Grain: player-game list. Player-game rows=10; unique NBA game IDs=10; distinct players=1; W/L=8/2.
- PTS/REB/AST sums: [404, 63, 44]; means: [40.4, 6.3, 4.4].
- Exact keys: `[[22300154,1610612750,1630162],[22300338,1610612750,1630162],[22300423,1610612750,1630162],[22300501,1610612750,1630162],[22300620,1610612750,1630162],[22300723,1610612750,1630162],[22300775,1610612750,1630162],[22300903,1610612750,1630162],[22300944,1610612750,1630162],[22301152,1610612750,1630162]]`.

### K03-B4

Anthony Edwards games with 35 or more points in 2023-24.

- Grain: player-game list. Player-game rows=13; unique NBA game IDs=13; distinct players=1; W/L=8/5.
- PTS/REB/AST sums: [509, 78, 56]; means: [39.15384615384615, 6.0, 4.3076923076923075].
- Exact keys: `[[22300050,1610612750,1630162],[22300154,1610612750,1630162],[22300338,1610612750,1630162],[22300423,1610612750,1630162],[22300451,1610612750,1630162],[22300471,1610612750,1630162],[22300501,1610612750,1630162],[22300620,1610612750,1630162],[22300723,1610612750,1630162],[22300775,1610612750,1630162],[22300903,1610612750,1630162],[22300944,1610612750,1630162],[22301152,1610612750,1630162]]`.

### K03-C1

How many Jalen Brunson games had (over 40 points or over 12 assists) in 2023-24?

- Grain: union of player-game keys. Player-game rows=11; unique NBA game IDs=11; distinct players=1; W/L=9/2.
- PTS/REB/AST sums: [461, 50, 84]; means: [41.90909090909091, 4.545454545454546, 7.636363636363637].
- Exact keys: `[[22300002,1610612752,1628973],[22300268,1610612752,1628973],[22300333,1610612752,1628973],[22300451,1610612752,1628973],[22300468,1610612752,1628973],[22300579,1610612752,1628973],[22300960,1610612752,1628973],[22300975,1610612752,1628973],[22301070,1610612752,1628973],[22301139,1610612752,1628973],[22301149,1610612752,1628973]]`.

### K03-C2

In 2023-24, list Anthony Edwards games with (over 40 points or over 12 rebounds).

- Grain: union of player-game keys. Player-game rows=6; unique NBA game IDs=6; distinct players=1; W/L=5/1.
- PTS/REB/AST sums: [222, 46, 22]; means: [37.0, 7.666666666666667, 3.6666666666666665].
- Exact keys: `[[22300069,1610612750,1630162],[22300423,1610612750,1630162],[22300775,1610612750,1630162],[22300903,1610612750,1630162],[22301014,1610612750,1630162],[22301152,1610612750,1630162]]`.

### K03-D1

How many player games had at least 50 points in 2023-24?

- Grain: player-game count, not distinct NBA fixtures. Player-game rows=20; unique NBA game IDs=20; distinct players=11; W/L=13/7.
- PTS/REB/AST sums: [1116, 152, 107]; means: [55.8, 7.6, 5.35].
- Exact keys: `[[22300088,1610612741,203897],[22300171,1610612749,203507],[22300180,1610612755,1630178],[22300315,1610612749,203507],[22300333,1610612752,1628973],[22300367,1610612755,203954],[22300405,1610612742,1629029],[22300588,1610612756,1626164],[22300608,1610612755,203954],[22300610,1610612750,1626157],[22300634,1610612742,1629029],[22300636,1610612756,1626164],[22300686,1610612755,1630178],[22300699,1610612744,201939],[22301070,1610612752,1628973],[22301092,1610612756,1626164],[22301104,1610612765,1630201],[22301140,1610612755,1630178],[22301152,1610612750,1630162],[22301208,1610612755,203954]]`.

### K03-D2

How many distinct players scored at least 50 points in a game in 2023-24?

- Grain: distinct player_id count. Player-game rows=20; unique NBA game IDs=20; distinct players=11; W/L=13/7.
- PTS/REB/AST sums: [1116, 152, 107]; means: [55.8, 7.6, 5.35].
- Exact keys: `[[22300088,1610612741,203897],[22300171,1610612749,203507],[22300180,1610612755,1630178],[22300315,1610612749,203507],[22300333,1610612752,1628973],[22300367,1610612755,203954],[22300405,1610612742,1629029],[22300588,1610612756,1626164],[22300608,1610612755,203954],[22300610,1610612750,1626157],[22300634,1610612742,1629029],[22300636,1610612756,1626164],[22300686,1610612755,1630178],[22300699,1610612744,201939],[22301070,1610612752,1628973],[22301092,1610612756,1626164],[22301104,1610612765,1630201],[22301140,1610612755,1630178],[22301152,1610612750,1630162],[22301208,1610612755,203954]]`.

### K03-E1

How many Nikola Jokic games reached at least 80 points in 2023-24?

- Grain: qualified zero; positive coverage required. Player-game rows=0; unique NBA game IDs=0; distinct players=0; W/L=0/0.
- PTS/REB/AST sums: [0, 0, 0]; means: undefined (do not invent zero averages).
- Exact keys: `[]`.

### K03-E2

List Jalen Brunson games with 80 or more points in 2023-24.

- Grain: qualified empty list; positive coverage required. Player-game rows=0; unique NBA game IDs=0; distinct players=0; W/L=0/0.
- PTS/REB/AST sums: [0, 0, 0]; means: undefined (do not invent zero averages).
- Exact keys: `[]`.

## Discrimination and qualification

- Jokic exactly 30-point games: 2; Edwards exactly 35-point games: 3. These distinguish strict/inclusive bounds.
- Brunson OR branch-only populations: points-only=9, assists-only=2, overlap=0.
- Edwards OR branch-only populations: points-only=4, rebounds-only=2, overlap=0.
- Qualified-zero coverage: Jokic 79 canonical played rows, max points 42; Brunson 77 played rows, max points 61. No absence inference; source is a positively populated historical season.
- Source SHA256 player CSV `a455e553ceb0b4e74bd4caf37aca482c0a9aab193631b6f2b383b623f861d760`; team CSV `b1c337e1f0099072538054b580cf280de98a5bc5aa0efd61f325037012963449`.

## Explicit remaining obligations

- No new numerical selector/corpus case is implemented or run here. Reuse fixture controls, then bind these exact raw populations to natural and structured execution; preserve identity, season, two predicates, operator and grain metadata.
- Add controlled OR overlap if actual samples do not include it; both branch-only sides are mandatory. Existing grouped-OR fixture proves independent branch evaluation but its shown rows lack overlap.
- Keep missing/unqualified data separate from E1/E2 qualified zero; a no-data/refusal is not positive completion.
- Require one unfamiliar wording/entity/value per relevant family. The above second entities provide a frozen prospective check; do not rewrite queries after observing output and call them held-out.
- Exact candidate CI, required pinned-data runner, Raw QA meaning review, current integrated state and actual desktop/mobile/deployed I/N/L/D evidence are not supplied by this memo. Vercel rate limit remains a deployment dependency. No human review certification is implied.
