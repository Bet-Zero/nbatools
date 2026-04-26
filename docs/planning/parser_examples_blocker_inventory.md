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

The latest full sweep resolved 61 previously failing case IDs and introduced
one new failing classification: `S2_2_6_06` ("How does Jamal Murray score when
Nikola Jokić is out?"). Phase L targeted validation has since resolved that
case without a full-sweep rerun.

Failure reasons from the latest `results.csv`:

| Failure reason | Count | Primary resolution type |
| --- | ---: | --- |
| Supported behavior was unrouted | 6 | Code fix or honest reclassification |
| Coverage-gated/fallback behavior was unrouted | 4 | Code fix |
| Unsupported/future boundary returned a supported result | 3 | Documentation-truth decision or stricter unsupported handling |
| Supported behavior routed to runtime error | 2 | Code fix |
| Supported behavior routed to no-data | 2 | Data/support-boundary decision |
| Supported behavior routed to unsupported/no-result | 1 | Code fix or honest reclassification |

Targeted validation after Phase L items 1 through 4 resolved all known active
failing case IDs, pair mismatches, and equivalence mismatches without a
full-sweep rerun. Active unresolved status is now:

| Metric | Active unresolved count |
| --- | ---: |
| Failing cases | 0 |
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

No active failing cases remain after Phase L item 4 targeted validation.

---

## 2. Remaining Pair Mismatches

No active pair mismatches remain after Phase L item 4 targeted validation.

Resolved pair mismatches from the prior baseline include period leaderboard,
recent scorer, shooting percentage with minimum attempts, absence summaries,
frequency phrasing, player-threshold team-record pairs, hottest-from-three
shorthand, double-double rolling-average reclassification, and multi-player
availability record fallbacks.

---

## 3. Remaining Equivalence-Group Mismatches

No equivalence-group mismatches remain after Phase L item 2 targeted
validation. `S7_7_15` now routes `Jokic on/off`, `Jokic on off`, and
`Nikola Jokic on-off` consistently to the coverage-gated `player_on_off`
route.

Resolved equivalence mismatches from the prior baseline include lineup-with-player
phrasing, stretch leaderboards, count-frequency groups, Bucks-without-Giannis
record variants, Curry threes frequency, and fourth-quarter leaderboard groups.

---

## 4. Remaining Documentation / Support-Boundary Mismatches

No active documentation/support-boundary mismatches remain after Phase L item 4
targeted validation.

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

1. Rerun the full parser-examples sweep.
2. Refresh this inventory from the full-sweep artifacts.
3. Decide whole-plan completion or draft the next continuation from that fresh
   evidence.

Do not remove a blocker from this file unless the corresponding behavior is
fixed, honestly reclassified, or superseded by a fresh full-sweep inventory.
