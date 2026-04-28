> **Archive status:** Completed / superseded historical planning document.
>
> **Current active plan:** See [../../planning/product_polish_master_plan.md](../../planning/product_polish_master_plan.md).
>
> **Do not use this file as the active continuation source.**

# Parser Examples Blocker Inventory

> **Role:** Evidence inventory for Phase K / Phase L / Phase M of
> [`parser_examples_completion_plan.md`](./parser_examples_completion_plan.md).
>
> This file reflects the latest full parser-examples sweep and records that no
> unresolved blocker groups remain.

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
| Run timestamp | 2026-04-26T10:08:40.940353+00:00 |
| Git commit SHA | `aebd18328f09ca27ee96035ce26a192a22bc5d55` |
| Total cases | 402 |
| Passing cases | 402 |
| Failing cases | 0 |
| Phrasing-pair mismatches | 0 |
| Equivalence-group mismatches | 0 |

Delta against the Phase K 384/18 baseline:

| Metric | Prior | Latest | Delta |
| --- | ---: | ---: | ---: |
| Passing cases | 384 | 402 | +18 |
| Failing cases | 18 | 0 | -18 |
| Phrasing-pair mismatches | 4 | 0 | -4 |
| Equivalence-group mismatches | 1 | 0 | -1 |

The Phase M closure sweep confirmed that all remaining blocker families have
been fixed or honestly reclassified. The two Finals-specific record examples
were moved from the supported playoff cluster to the explicit historical-splits
boundary because no approved Finals-specific team/player record data contract
exists for that entity grain.

Failure reasons from the latest `results.csv`:

| Failure reason | Count | Primary resolution type |
| --- | ---: | --- |
| None | 0 | Closed |

Active unresolved status after the Phase M closure sweep:

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

No remaining failing cases.

Resolved in Phase M closure:

| Prior case | Current case | Query | Resolution |
| --- | --- | --- | --- |
| `S4_4_4_02` | `S8_8_5_05` | "Celtics finals record" | Reclassified from supported playoff history to the explicit historical-splits boundary. Latest sweep returns `no_result` (`unsupported`) / `team_record` and passes as `unsupported_expected`. |
| `S4_4_4_10` | `S8_8_5_06` | "LeBron record in the Finals" | Reclassified from supported playoff history to the explicit historical-splits boundary. Latest sweep returns `no_result` (`unsupported`) / `player_game_summary` and passes as `unsupported_expected`. |

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

No active documentation/support-boundary mismatches remain after Phase M item 2
targeted validation. `S2_2_7_09` now carries the explicit
`unsupported_boundary` note through the CLI JSON metadata even when execution
also appends clutch fallback notes.

Prior documentation-boundary mismatches in Section 2 and `S3_3_9_45_S` are no
longer failing in the latest sweep.

---

## 5. Ambiguity Handling

No ambiguity-handling failures remain in the latest full sweep. The Section 5.8
ambiguous-fragment cases now pass by surfacing ambiguity or clean non-guessing
behavior instead of returning a confident supported result.

---

## 6. Follow-Up Order

No follow-up order remains. The latest full sweep is clean:

- 402 total cases
- 402 passing cases
- 0 failing cases
- 0 phrasing-pair mismatches
- 0 equivalence-group mismatches

This inventory is closed unless a future sweep introduces a new blocker.
