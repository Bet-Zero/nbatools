# Parser Examples Blocker Inventory

> **Role:** Evidence inventory for Phase K / Phase L / Phase M of
> [`parser_examples_completion_plan.md`](./parser_examples_completion_plan.md).
>
> This file reflects the latest full parser-examples sweep plus targeted
> Phase L / Phase M validation and lists only unresolved blocker groups.

---

## Evidence Base

Source artifacts from the fresh full sweep:

- [`outputs/parser_examples_full_sweep/report.md`](../../outputs/parser_examples_full_sweep/report.md)
- [`outputs/parser_examples_full_sweep/results.csv`](../../outputs/parser_examples_full_sweep/results.csv)
- [`outputs/parser_examples_full_sweep/manifest.json`](../../outputs/parser_examples_full_sweep/manifest.json)
- [`docs/operations/parser_examples_full_sweep_protocol.md`](../operations/parser_examples_full_sweep_protocol.md)

Latest full sweep:

| Metric | Count |
| --- | ---: |
| Run timestamp | 2026-04-26T06:28:49.829488+00:00 |
| Git commit SHA | `4c23bf73d3b91e7de52354b96bd94482435a67d7` |
| Total cases | 402 |
| Passing cases | 399 |
| Failing cases | 3 |
| Phrasing-pair mismatches | 1 |
| Equivalence-group mismatches | 0 |

Delta against the Phase K 384/18 baseline:

| Metric | Prior | Latest | Delta |
| --- | ---: | ---: | ---: |
| Passing cases | 384 | 399 | +15 |
| Failing cases | 18 | 3 | -15 |
| Phrasing-pair mismatches | 4 | 1 | -3 |
| Equivalence-group mismatches | 1 | 0 | -1 |

The Phase L item 5 full sweep confirmed that targeted fixes from items 1
through 4 removed most remaining blocker families. Three failing case IDs and
one phrasing-pair mismatch remained after that full sweep. Phase M item 1
targeted validation has since resolved the active pair mismatch without a
full-sweep rerun.

Failure reasons from the latest `results.csv`:

| Failure reason | Count | Primary resolution type |
| --- | ---: | --- |
| Supported behavior routed to unsupported/no-result | 2 | Code fix, source-backed execution, or honest reclassification |
| Unsupported/future boundary returned a supported result | 1 | Documentation-truth decision or stricter unsupported handling |

Active unresolved status after Phase M item 1 targeted validation:

| Metric | Active unresolved count |
| --- | ---: |
| Failing cases | 3 |
| Phrasing-pair mismatches | 0 |
| Equivalence-group mismatches | 0 |

## Resolution Labels

- **Implementation blocker:** behavior should be fixed in parser, routing,
  command execution, or ambiguity handling.
- **Documentation-truth blocker:** the examples/docs/catalog overstate or
  contradict shipped behavior and may need honest reclassification.
- **Data/support-boundary blocker:** the parser route exists, but the current
  data layer cannot return the documented result.

---

## 1. Remaining Failing Cases

| Case | Query | Expected category | Actual status / route | Blocker label | Notes |
| --- | --- | --- | --- | --- | --- |
| `S2_2_7_09` | "Who's been the best shot creator in clutch time this season?" | `unsupported_expected` | `ok` / `season_leaders` | Documentation-truth blocker | The docs mark this shot-creator/clutch boundary unsupported/future, but the product returned a supported leaderboard with only a clutch fallback note. Resolve by stricter unsupported handling or honest reclassification if this broad fallback is intended. |
| `S4_4_4_02` | "Celtics finals record" | `supported_exact` | `no_result` (`unsupported`) / `team_record` | Data/support-boundary blocker | The examples classify Finals team record as supported, but the current route returns unsupported. Resolve with documented Finals/playoff-round execution support or reclassify the example boundary. |
| `S4_4_4_10` | "LeBron record in the Finals" | `supported_exact` | `no_result` (`unsupported`) / `player_game_summary` | Data/support-boundary blocker | The examples classify player Finals record as supported, but the current route returns unsupported. Resolve with documented Finals/playoff-round execution support or reclassify the example boundary. |

---

## 2. Remaining Pair Mismatches

No active pair mismatches remain after Phase M item 1 targeted validation.
`S3_3_10_50_Q` and `S3_3_10_50_S` now both return `player_on_off` /
`summary` / `no_result` with the explicit on/off unsupported-data note.

Resolved pair mismatches from the prior baseline include period leaderboard,
recent scorer, shooting percentage with minimum attempts, absence summaries,
frequency phrasing, player-threshold team-record pairs, hottest-from-three
shorthand, double-double rolling-average reclassification, multi-player
availability record fallbacks, and the Nuggets/Jokic on/off net-rating pair.

---

## 3. Remaining Equivalence-Group Mismatches

No active equivalence-group mismatches remain after the Phase L item 5 full
sweep. `S7_7_15` routes `Jokic on/off`, `Jokic on off`, and `Nikola Jokic
on-off` consistently to the coverage-gated `player_on_off` route.

Resolved equivalence mismatches from the prior baseline include lineup-with-player
phrasing, stretch leaderboards, count-frequency groups, Bucks-without-Giannis
record variants, Curry threes frequency, and fourth-quarter leaderboard groups.

---

## 4. Remaining Documentation / Support-Boundary Mismatches

`S2_2_7_09` remains an active documentation/support-boundary mismatch: the
example boundary says shot-creator/clutch support is unsupported or future, but
the product returns a supported `season_leaders` result with an unfiltered
clutch note.

Prior documentation-boundary mismatches in Section 2 and `S3_3_9_45_S` are no
longer failing in the latest sweep.

---

## 5. Ambiguity Handling

No ambiguity-handling failures remain in the latest full sweep. The Section 5.8
ambiguous-fragment cases now pass by surfacing ambiguity or clean non-guessing
behavior instead of returning a confident supported result.

---

## 6. Follow-Up Order

Use this inventory as the source of truth for the remaining Phase M closure
decision:

1. Resolve or explicitly reclassify the three remaining failing case IDs:
   `S2_2_7_09`, `S4_4_4_02`, and `S4_4_4_10`.
2. Continue through Phase M until a fresh full sweep confirms whether those
   blockers are fully closed or require another explicit continuation.
3. Keep `master_completion_plan.md` pointed at exactly one active continuation
   until the full examples-library surface is closed.

Do not remove a blocker from this file unless the corresponding behavior is
fixed, honestly reclassified, or superseded by a fresh full-sweep inventory.
