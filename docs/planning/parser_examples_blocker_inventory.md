# Parser Examples Blocker Inventory

> **Role:** Evidence inventory for Phase K of
> [`parser_examples_completion_plan.md`](./parser_examples_completion_plan.md).
>
> This file turns the latest full parser-examples sweep into explicit blockers
> that later queue items can cite directly.

---

## Evidence Base

Source artifacts:

- [`outputs/parser_examples_full_sweep/report.md`](../../outputs/parser_examples_full_sweep/report.md)
- [`outputs/parser_examples_full_sweep/results.csv`](../../outputs/parser_examples_full_sweep/results.csv)
- [`outputs/parser_examples_full_sweep/manifest.json`](../../outputs/parser_examples_full_sweep/manifest.json)
- [`docs/operations/parser_examples_full_sweep_protocol.md`](../operations/parser_examples_full_sweep_protocol.md)

Run summary from the latest sweep:

| Metric | Count |
| --- | ---: |
| Total cases | 402 |
| Passing cases | 324 |
| Failing cases | 78 |
| Phrasing-pair mismatches | 12 |
| Equivalence-group mismatches | 7 |

Failure reasons from `results.csv`:

| Failure reason | Count | Primary resolution type |
| --- | ---: | --- |
| Supported behavior was unrouted | 35 | Code fix or honest reclassification |
| Supported behavior routed to unsupported/no-result | 18 | Code fix or honest reclassification |
| Unsupported/future boundary returned a supported result | 9 | Documentation-truth decision or stricter unsupported handling |
| Coverage-gated/fallback behavior was unrouted | 7 | Code fix |
| Ambiguous input produced a confident route/result | 5 | Code fix or ambiguity-spec decision |
| Supported behavior routed to runtime error | 2 | Code fix |
| Supported behavior routed to no-data | 2 | Data/support-boundary decision |

## Resolution Labels

- **Implementation blocker:** behavior should be fixed in parser, routing, command
  execution, or ambiguity handling.
- **Documentation-truth blocker:** the examples/docs/catalog overstate or
  contradict shipped behavior and may need honest reclassification.
- **Boundary decision:** either implementation or reclassification is plausible;
  the follow-up item must decide explicitly from current docs and product scope.

---

## 1. Canonical Section 2 Failures

Section 2 is the canonical 100-example set. The sweep found 31 failing Section 2
cases: 25 `supported_exact`, 1 `supported_with_fallback`, and 5
`unsupported_expected` cases that returned supported results.

| Case IDs | Representative queries | Evidence pattern | Likely resolution |
| --- | --- | --- | --- |
| `S2_2_2_02`, `S2_2_2_06`, `S2_2_2_09` | "Which players have been the hottest from three lately?"; "Which players have been the most efficient recently?"; "Which scorers have cooled off over their last 10 games?" | Recent/lately supported examples are unrouted. | Implementation blocker unless examples are reclassified. |
| `S2_2_2_04` | "What team has played the best defense recently?" | Routes to `season_team_leaders` but returns unsupported. | Boundary decision: team recent-rating leaderboard support vs honest reclassification. |
| `S2_2_3_02`, `S2_2_3_04`, `S2_2_3_05`, `S2_2_3_08` | "Which team has the best net rating in its last 10 games?"; "What players have averaged a double-double over their last 15 games?"; "Who has been the best rebounder since January 1?"; "Who is shooting the best from three since February 1 with at least 4 attempts per game?" | Last-N/since-date examples are either unrouted or route to unsupported. | Implementation blocker or explicit support-boundary correction. |
| `S2_2_3_09` | "What team has allowed the fewest paint points in its last 12 games?" | Marked unsupported/future, but returns `ok` on `season_team_leaders`. | Documentation-truth blocker or stricter unsupported handling for paint points. |
| `S2_2_4_01`, `S2_2_4_07`, `S2_2_4_09` | "What were the biggest scoring games this season?"; "What are the biggest triple-double games this season?"; "What are the most dominant games by plus-minus this season?" | Best/biggest-game examples are unrouted. | Implementation blocker unless examples are reclassified. |
| `S2_2_5_09` | "Which scorers have the biggest drop-off against top-10 defenses?" | Marked unsupported/future, but returns `ok` on `season_leaders`. | Documentation-truth blocker or stricter unsupported handling for drop-off comparisons. |
| `S2_2_6_03`, `S2_2_6_05`, `S2_2_6_08`, `S2_2_6_09`, `S2_2_6_10` | "Who averages the most points when their co-star didn't play this season?"; "What is the Mavericks' offensive rating when Luka Dončić didn't play?"; "Which players see the biggest usage increase when their star teammate is out?"; "How has Tyrese Maxey played when Joel Embiid didn't play this season?"; "What team has stayed afloat best when its leading scorer was out?" | Teammate-out examples mix unsupported/no-result, unrouted, and unsupported-boundary examples returning `ok`. | Boundary decision; likely split supported absence filters from overbroad co-star/star abstractions. |
| `S2_2_7_01`, `S2_2_7_02`, `S2_2_7_03`, `S2_2_7_04`, `S2_2_7_10` | "Who's been the best scorer over the last 10 games?"; "Who's been the best rebounder since January 1?"; "Who's been the best rim protector over the past month?"; "Who's been the best playmaker in the last 15 games?"; "Who's been the best offensive rebounder lately?" | "Best at _ over _" examples are unrouted. | Implementation blocker or reclassification of unsupported derived skill labels. |
| `S2_2_8_02`, `S2_2_8_04`, `S2_2_8_05`, `S2_2_8_08`, `S2_2_8_10` | "How often has Stephen Curry made 5 or more threes this year?"; "How often has Luka Dončić scored 40 or more this year?"; "How often has a player had 10+ assists and 0 turnovers this season?"; "How often has a team scored 140 or more points this year?"; "How often has a road team won by 20+ this season?" | Frequency/count examples are unsupported or unrouted. | Implementation blocker for count/finder phrasing; road-team comeback/blowout examples may require boundary decision. |
| `S2_2_9_01`, `S2_2_9_07` | "What's the Mavericks' record when Luka Dončić scores 35 or more?"; "What is Milwaukee's record when it wins the rebounding battle?" | One supported record-when case returns unsupported; one unsupported/future case returns `ok`. | Boundary decision around player-threshold team records and team-condition records. |
| `S2_2_10_05` | "Which players score the most in the 4th quarter?" | Expected coverage-gated/fallback behavior is unrouted. | Implementation blocker for period-context leaderboard phrasing. |

---

## 2. `supported_exact` Failures

The sweep found 57 `supported_exact` failures. These are direct blockers unless
the examples are proven to overstate shipped support and are reclassified.

| Source area | Count | Representative case IDs and queries | Evidence pattern | Likely resolution |
| --- | ---: | --- | --- | --- |
| Section 2 canonical examples | 25 | `S2_2_2_02` "Which players have been the hottest from three lately?"; `S2_2_4_01` "What were the biggest scoring games this season?"; `S2_2_8_02` "How often has Stephen Curry made 5 or more threes this year?" | Canonical supported examples are unrouted or unsupported. | Implementation blocker or explicit canonical-example reclassification. |
| Section 3 paired examples | 25 | `S3_3_2_07_Q/S` "Which players have been the hottest from three lately?" / "hottest from 3 lately"; `S3_3_3_14_Q/S` double-double last-10 phrasing; `S3_3_8_37_Q` Curry 5+ threes question form. | Supported pair members fail even when their sibling sometimes passes. | Implementation blocker; handled with pair repair. |
| Section 4 capability clusters | 6 | `S4_4_2_10` "how many players scored 40 points this season"; `S4_4_2_12` "how many teams scored 120+ this season"; `S4_4_4_06` "Warriors conference finals appearances"; `S4_4_4_12` "winningest team of the 2010s". | Occurrence queries hit runtime/unrouted paths; playoff/historical examples return no-data or unrouted. | Code fix for occurrence errors; data/support-boundary decision for playoff/historical examples. |
| Section 7 equivalence members | 1 | `S7_7_5_01` "How often has Stephen Curry made 5 or more threes this year?" | Question-form frequency example returns unsupported while shorthand siblings pass. | Implementation blocker tied to equivalence group `S7_7_5`. |

Recurring supported-exact implementation themes:

- recent/lately/past-month leaderboards: `S2_2_2_02`, `S3_3_2_08_Q`
- team recent defensive/net rating leaderboards: `S2_2_2_04`, `S3_3_3_12_Q`
- last-N/since-date derived leaderboards: `S2_2_3_04`, `S3_3_3_15_Q`
- best/biggest game finders: `S2_2_4_01`, `S3_3_4_16_S`
- teammate-out/off-court phrasing: `S2_2_6_05`, `S3_3_6_30_S`
- frequency/count phrasing: `S2_2_8_05`, `S3_3_8_40_Q`, `S7_7_5_01`
- occurrence and historical cluster coverage: `S4_4_2_10`, `S4_4_4_09`

---

## 3. Pair Mismatches From Section 3

The report identified 12 pair-level mismatches. These are consistency blockers
even when both individual cases pass.

| Pair | Mismatch | Question form | Search form | Likely resolution |
| --- | --- | --- | --- | --- |
| `S3_3_10_49` | route, query class, result status | "Which players score the most in the 4th quarter this season?" | "most 4th quarter points this season" | Implementation blocker for question-form period leaderboard routing. |
| `S3_3_2_08` | route, query class, result status | "Who has been the best scorer over the past month?" | "best scorers past month" | Implementation blocker for question-form recent leaderboard routing. |
| `S3_3_3_15` | route, query class, result status | "Who is shooting the best from three over the last month with at least 5 attempts per game?" | "best 3pt percentage last month min 5 attempts" | Boundary decision: align on leaderboard vs finder semantics, or document non-equivalence. |
| `S3_3_6_26` | route, query class | "How do the Suns perform when Devin Booker didn't play?" | "Suns when Booker out" | Boundary decision: team summary vs finder route equivalence needs clarification. |
| `S3_3_6_28` | route, query class | "How has Anthony Davis rebounded when LeBron James didn't play?" | "Anthony Davis rebounds when LeBron out" | Boundary decision: summary vs finder no-match behavior may need canonical route alignment. |
| `S3_3_6_29` | route | "What is the Mavericks' offensive rating when Luka Dončić didn't play?" | "Mavericks offensive rating without Luka" | Implementation blocker or explicit unsupported route choice for teammate-out offensive rating. |
| `S3_3_6_30` | route, query class, result status | "How has Tyrese Maxey played when Joel Embiid was out this season?" | "Maxey when Embiid out this season" | Implementation blocker for shorthand teammate-out player summary. |
| `S3_3_8_37` | result status | "How often has Stephen Curry made 5 or more threes this year?" | "Curry 5+ threes this year" | Implementation blocker for question-form frequency phrasing. |
| `S3_3_8_38` | result status | "How often has Luka Dončić scored 40 or more this season?" | "Luka 40+ point games this season" | Implementation blocker for question-form frequency phrasing. |
| `S3_3_8_40` | result status | "How often has Victor Wembanyama had 5 or more blocks this season?" | "Wembanyama 5+ blocks this season" | Implementation blocker for question-form frequency phrasing. |
| `S3_3_9_41` | pass/fail divergence | "What's the Mavericks' record when Luka Dončić scores 35 or more?" | "Mavericks record when Luka scores 35+" | Boundary decision: unsupported vs no-match semantics for player-threshold team record. |
| `S3_3_9_45` | result status | "What is the Lakers' record when LeBron James and Anthony Davis both play?" | "Lakers record when LeBron and AD both play" | Documentation-truth blocker or stricter unsupported handling for multi-player availability. |

---

## 4. Equivalence-Group Mismatches From Section 7

The report identified 7 group-level mismatches. Some members individually pass
but still violate intended equivalence because routes, result classes, or
statuses diverge.

| Group | Members / representative queries | Evidence pattern | Likely resolution |
| --- | --- | --- | --- |
| `S7_7_15` | `Jokic on/off`; `Jokic on off`; `Nikola Jokic on-off` | Routes diverge between `player_on_off` unsupported and `player_game_summary` ok. | Implementation blocker for on/off token normalization, or documented non-equivalence if "on off" without slash means generic player summary. |
| `S7_7_17` | `lineups with LeBron and AD`; `lineup with LeBron and AD`; `LeBron and AD together lineups` | Routes diverge between `lineup_leaderboard` and `lineup_summary`, all no-result unsupported. | Boundary decision: lineups-with-player phrasing should pick one canonical route or examples should distinguish summary vs leaderboard intent. |
| `S7_7_18` | Hottest/top 3-game scoring stretch variants | `top 3-game scoring stretches this year` routes to `season_leaders`; other members route to `player_stretch_leaderboard`. | Implementation blocker for stretch leaderboard phrase coverage. |
| `S7_7_2` | Jokic 30+ points and 10+ rebounds count variants | Question form routes to `player_occurrence_leaders`; shorthand variants route to `player_game_finder`, all `count`. | Boundary decision: count route compatibility may be acceptable only if docs declare it; otherwise normalize route. |
| `S7_7_4` | Bucks record / without Giannis variants | Routes diverge across `team_record`, `game_finder`, and `player_game_summary`. | Boundary decision: record phrasing vs generic absence finder should be separated or normalized. |
| `S7_7_5` | Curry 5+ threes variants | Question form returns unsupported; shorthand variants return ok on `player_game_finder`. | Implementation blocker for question-form frequency phrasing. |
| `S7_7_8` | 4th-quarter scoring leader variants | Question form is unrouted; shorthand variants return ok on `season_leaders` with fallback notes. | Implementation blocker for question-form period leaderboard phrasing. |

---

## 5. Ambiguity-Handling Failures

The sweep found 5 `ambiguous_expected` failures, all in Section 5.8. These
should surface ambiguity, alternates, or clean non-guessing behavior instead of
confidently selecting a route/result.

| Case | Query | Actual behavior | Likely resolution |
| --- | --- | --- | --- |
| `S5_5_8_01` | "Celtics recently" | Returns `ok` on `game_finder`. | Implementation blocker: require a clearer intent or ambiguous response for underspecified team/recent fragments. |
| `S5_5_8_02` | "Tatum vs Knicks" | Returns `no_result/no_match` on `player_game_finder`, but sweep expected ambiguity/non-guessing. | Boundary decision: define whether opponent matchup fragments should be routed or ambiguous. |
| `S5_5_8_03` | "Jokic triple doubles" | Returns `ok` on `player_game_finder`. | Implementation blocker or doc decision for count/finder default on bare achievement fragments. |
| `S5_5_8_04` | "best games Booker" | Returns `ok` on `player_game_finder`. | Implementation blocker: phrase lacks enough slot clarity for confident route unless examples reclassify it. |
| `S5_5_8_05` | "Thunder clutch" | Returns `ok` on `game_finder`. | Implementation blocker: team + context fragment should be ambiguity/unsupported/fallback-noted rather than confident generic finder. |

---

## 6. Documentation / Support-Boundary Mismatches

These cases are marked unsupported or future in the sweep classification, but
the product returned a supported result. Each one must be resolved by either
documenting that the behavior is actually supported or tightening routing so the
product fails honestly.

| Case | Query | Actual route | Likely resolution |
| --- | --- | --- | --- |
| `S2_2_3_09` | "What team has allowed the fewest paint points in its last 12 games?" | `season_team_leaders` | Documentation-truth blocker for paint-points support. |
| `S2_2_5_09` | "Which scorers have the biggest drop-off against top-10 defenses?" | `season_leaders` | Documentation-truth blocker for drop-off comparison support. |
| `S2_2_6_03` | "Who averages the most points when their co-star didn't play this season?" | `season_leaders` | Documentation-truth blocker for abstract co-star absence. |
| `S2_2_6_10` | "What team has stayed afloat best when its leading scorer was out?" | `game_finder` | Documentation-truth blocker for abstract leading-scorer absence. |
| `S2_2_9_07` | "What is Milwaukee's record when it wins the rebounding battle?" | `team_record` | Documentation-truth blocker for team-condition record support. |
| `S3_3_9_45_S` | "Lakers record when LeBron and AD both play" | `player_game_summary` | Documentation-truth blocker for multi-player availability phrasing. |
| `S8_8_1_04` | "best record vs teams above .600" | `team_record_leaderboard` | Documentation-truth blocker for above-.600 opponent-quality bucket. |
| `S8_8_5_02` | "Who has the most ___ since becoming a starter?" | `season_leaders` | Documentation-truth blocker for placeholder/fill-in query templates. |
| `S8_8_5_04` | "What is ___ record in overtime games this season?" | `team_record_leaderboard` | Documentation-truth blocker for placeholder/fill-in query templates. |

Coverage-gated examples that should route with fallback notes but are unrouted
are implementation blockers rather than documentation-truth blockers:

- `S2_2_10_05` "Which players score the most in the 4th quarter?"
- `S3_3_5_23_Q/S` "Which players shoot the best against top-10 defenses?" /
  "best shooting vs top 10 defenses"
- `S3_3_10_49_Q` "Which players score the most in the 4th quarter this season?"
- `S7_7_8_01` "Which players score the most in the 4th quarter this season?"
- `S8_8_1_03` "against winning teams"
- `S8_8_3_01` "in clutch time"

---

## 7. Follow-Up Order for Phase K

Use this inventory as the source of truth for the remaining Phase K queue items:

1. Canonical Section 2 failures: start with the 31 cases listed in Section 1.
2. Pair mismatches: use the 12 pairs listed in Section 3 after canonical fixes
   land, because some pair failures duplicate canonical families.
3. Equivalence and ambiguity: use Sections 4 and 5, especially the frequency,
   period-context, on/off, lineup, and ambiguous-fragment families.
4. Documentation truth pass: resolve Section 6 cases in the same PR as their
   behavior decision when possible.

Do not remove a blocker from this file unless the corresponding behavior is
fixed, honestly reclassified, or superseded by a fresh full-sweep inventory.
