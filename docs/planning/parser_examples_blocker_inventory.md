# Parser Examples Blocker Inventory

> **Role:** Evidence inventory for Phase K / Phase L of
> [`parser_examples_completion_plan.md`](./parser_examples_completion_plan.md).
>
> This file reflects the latest full parser-examples sweep plus targeted
> Phase L validation and lists only unresolved blocker groups.

---

## Evidence Base

Source artifacts from the fresh full sweep:

- [`outputs/parser_examples_full_sweep/report.md`](../../outputs/parser_examples_full_sweep/report.md)
- [`outputs/parser_examples_full_sweep/results.csv`](../../outputs/parser_examples_full_sweep/results.csv)
- [`outputs/parser_examples_full_sweep/manifest.json`](../../outputs/parser_examples_full_sweep/manifest.json)
- [`docs/operations/parser_examples_full_sweep_protocol.md`](../operations/parser_examples_full_sweep_protocol.md)

Latest run:

| Metric | Count |
| --- | ---: |
| Run timestamp | 2026-04-25T15:42:59Z |
| Git commit SHA | `8cd6441fadcba3e14ac0d095dc43e5cd9a16cb44` |
| Total cases | 402 |
| Passing cases | 384 |
| Failing cases | 18 |
| Phrasing-pair mismatches | 4 |
| Equivalence-group mismatches | 1 |

Delta against the prior Phase K baseline:

| Metric | Prior | Latest | Delta |
| --- | ---: | ---: | ---: |
| Passing cases | 324 | 384 | +60 |
| Failing cases | 78 | 18 | -60 |
| Phrasing-pair mismatches | 12 | 4 | -8 |
| Equivalence-group mismatches | 7 | 1 | -6 |

The latest sweep resolved 61 previously failing case IDs and introduced one
new failing classification: `S2_2_6_06` ("How does Jamal Murray score when
Nikola Jokić is out?"), which is now treated as `supported_exact` but remains
unrouted.

Failure reasons from the latest `results.csv`:

| Failure reason | Count | Primary resolution type |
| --- | ---: | --- |
| Supported behavior was unrouted | 6 | Code fix or honest reclassification |
| Coverage-gated/fallback behavior was unrouted | 4 | Code fix |
| Unsupported/future boundary returned a supported result | 3 | Documentation-truth decision or stricter unsupported handling |
| Supported behavior routed to runtime error | 2 | Code fix |
| Supported behavior routed to no-data | 2 | Data/support-boundary decision |
| Supported behavior routed to unsupported/no-result | 1 | Code fix or honest reclassification |

Targeted validation after Phase L item 1 resolved 8 failing case IDs and 2
pair mismatches without a full-sweep rerun. Active unresolved status is now:

| Metric | Active unresolved count |
| --- | ---: |
| Failing cases | 10 |
| Phrasing-pair mismatches | 2 |
| Equivalence-group mismatches | 1 |

## Resolution Labels

- **Implementation blocker:** behavior should be fixed in parser, routing,
  command execution, or ambiguity handling.
- **Documentation-truth blocker:** the examples/docs/catalog overstate or
  contradict shipped behavior and may need honest reclassification.
- **Data/support-boundary blocker:** the parser route exists, but the current
  data layer cannot return the documented result.

---

## 1. Remaining Failing Cases

After Phase L item 1 targeted validation, 10 failing cases remain across
Section 2, Section 3, Section 4, and Section 8.

| Case ID | Query | Actual behavior | Likely resolution |
| --- | --- | --- | --- |
| `S2_2_6_06` | "How does Jamal Murray score when Nikola Jokić is out?" | `error/unrouted` | Implementation blocker for player summary with teammate absence. |
| `S3_3_3_12_S` | "best net rating last 15 games" | `no_result/unsupported` on `season_team_leaders` | Boundary decision: team net-rating leaderboard support vs honest reclassification. |
| `S4_4_2_10` | "how many players scored 40 points this season" | `error/error` on `player_occurrence_leaders` | Implementation blocker in occurrence count execution. |
| `S4_4_2_11` | "number of players with 10 assists this season" | `error/error` on `player_occurrence_leaders` | Implementation blocker in occurrence count execution. |
| `S4_4_4_06` | "Warriors conference finals appearances" | `no_result/no_data` on `playoff_appearances` | Data/support-boundary blocker for playoff appearances. |
| `S4_4_4_09` | "best second round record" | `no_result/no_data` on `playoff_round_record` | Data/support-boundary blocker for playoff round records. |
| `S4_4_4_12` | "winningest team of the 2010s" | `error/unrouted` | Implementation or scope blocker for historical decade records. |
| `S8_8_1_04` | "best record vs teams above .600" | `ok` on `team_record_leaderboard` | Documentation-truth blocker for above-.600 opponent-quality boundary. |
| `S8_8_5_02` | "Who has the most ___ since becoming a starter?" | `ok` on `season_leaders` | Documentation-truth blocker for placeholder/fill-in templates. |
| `S8_8_5_04` | "What is ___ record in overtime games this season?" | `ok` on `team_record_leaderboard` | Documentation-truth blocker for placeholder/fill-in templates. |

---

## 2. Remaining Pair Mismatches

After Phase L item 1 targeted validation, 2 Section 3 pair-level mismatches
remain.

| Pair | Mismatch | Question form | Search form | Likely resolution |
| --- | --- | --- | --- | --- |
| `S3_3_3_12` | pass/fail divergence | "Which team has the best net rating in its last 15 games?" | "best net rating last 15 games" | Decide and align team net-rating rolling-window support. |
| `S3_3_9_45` | result status | "What is the Lakers' record when LeBron James and Anthony Davis both play?" | "Lakers record when LeBron and AD both play" | Tighten multi-player availability boundary or document support. |

Resolved pair mismatches from the prior baseline include period leaderboard,
recent scorer, shooting percentage with minimum attempts, absence summaries,
frequency phrasing, player-threshold team-record pairs, hottest-from-three
shorthand, and double-double rolling-average reclassification.

---

## 3. Remaining Equivalence-Group Mismatch

The latest report identifies 1 Section 7 equivalence mismatch.

| Group | Members / representative queries | Evidence pattern | Likely resolution |
| --- | --- | --- | --- |
| `S7_7_15` | `Jokic on/off`; `Jokic on off`; `Nikola Jokic on-off` | Routes diverge between `player_on_off` unsupported and `player_game_summary` ok. | Implementation blocker for on/off token normalization, or documented non-equivalence if plain "on off" means generic player summary. |

Resolved equivalence mismatches from the prior baseline include lineup-with-player
phrasing, stretch leaderboards, count-frequency groups, Bucks-without-Giannis
record variants, Curry threes frequency, and fourth-quarter leaderboard groups.

---

## 4. Remaining Documentation / Support-Boundary Mismatches

These cases are marked unsupported or future by the sweep classification, but
the product returned a supported result.

| Case | Query | Actual route | Likely resolution |
| --- | --- | --- | --- |
| `S8_8_1_04` | "best record vs teams above .600" | `team_record_leaderboard` | Documentation-truth blocker for above-.600 opponent-quality bucket. |
| `S8_8_5_02` | "Who has the most ___ since becoming a starter?" | `season_leaders` | Documentation-truth blocker for placeholder/fill-in query templates. |
| `S8_8_5_04` | "What is ___ record in overtime games this season?" | `team_record_leaderboard` | Documentation-truth blocker for placeholder/fill-in query templates. |

Prior documentation-boundary mismatches in Section 2 and `S3_3_9_45_S` are no
longer failing in the latest sweep.

---

## 5. Ambiguity Handling

No ambiguity-handling failures remain in the latest sweep. The Section 5.8
ambiguous-fragment cases now pass by surfacing ambiguity or clean non-guessing
behavior instead of returning a confident supported result.

---

## 6. Follow-Up Order

Use this inventory as the source of truth for the remaining Phase L closure
decision:

1. Fix or honestly reclassify the 10 remaining failing cases in Section 1.
2. Align the 2 remaining Section 3 pair mismatches.
3. Resolve or explicitly document the `S7_7_15` on/off equivalence mismatch.
4. Decide whether the 3 remaining documentation-boundary mismatches represent
   real support or should fail more honestly.

Do not remove a blocker from this file unless the corresponding behavior is
fixed, honestly reclassified, or superseded by a fresh full-sweep inventory.
