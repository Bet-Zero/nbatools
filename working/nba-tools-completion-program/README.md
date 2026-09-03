# NBA Tools completion program

Coordination file for trust projects that were **out of scope for PR #295** and
must not be started inside it.

PR #295's final bounded scope was *Phase 1A - explicit metric selection and no
cross-metric substitution*: metric selection and aggregation integrity on the
ranking branches that choose their metric from the query. The durable
description of that scope lives in
`docs/architecture/parser/leaderboard_metric_boundary.md`.

Everything below is a real defect class that PR #295 does **not** fix and does
**not** claim to fix.

---

## Program status

| Item | State |
| --- | --- |
| Phase 1A - explicit metric selection | **Merged** at `1914bb10c12bdb98fe4b2371df8ba9fa5fd76521` (PR #295) |
| CI-01 - trustworthy frontend verification and dependency security | **Merged** at `ed15443d5ddc3ef8982d580226eb5dc49c4c7e06` (PR #296) |
| QA-01 - fail-closed Raw QA and filter-sweep signal integrity | **Merged** at `e2e70583f05f568df8945f4cb7039ac18a79c943` (PR #297) |
| OPS-01 - production monitoring and dependency-security recovery | **Active** (operations) |
| OPS-MON-01 - cold-start response failures and false-alert policy | Deferred, unstarted (monitoring policy) |
| CI-GOV-01 - required-check enforcement decision | Deferred, unstarted (governance) |
| Phase 1B - compound event and filter routing integrity | Deferred, unstarted |
| Phase 1C - unexecuted qualifier protection | Deferred, unstarted |
| Phase 1D - filter execution receipts | Deferred, unstarted |
| Immutable data-backed CI | Separate infrastructure decision, not taken |

**CI-01** splits frontend CI into two independent verdicts so a newly published
npm advisory can no longer mark the frontend build, lint, and test steps
*skipped*. `frontend-verify` reports whether the code is healthy;
`frontend-security` reports whether the dependency tree is. The audit stays a
real check at `--audit-level=low` that fails the workflow, and project policy
requires it green before merge — though GitHub does not currently enforce that
mechanically (see CI-GOV-01 below). `tests/test_ci_workflow_policy.py` prevents
the old ordering from returning and keeps verification unconditional.

CI-01 is infrastructure. It changes no parser behavior, query routing, result
contract, or frontend product behavior.

---

## QA-01 - fail-closed Raw QA and filter-sweep signal integrity

**Merged** at `e2e70583f05f568df8945f4cb7039ac18a79c943` (PR #297). It repairs
two gates that reported success without producing the evidence their success
claimed.

1. `make raw-query-answer-qa` omitted `--fail-on-expectation-failure`, so the
   repository's named Raw QA target printed failed cases and still exited zero.
   The target now passes the flag and fails closed. Artifacts are still written
   before exit, and the direct harness keeps its explicit report-only mode.
2. `tools/filter_execution_sweep.py` classified every comparison as an honest
   refusal when there was no data to compare, and exited zero - "no lies found"
   from a run that compared nothing. Rows without a populated control are now
   `NO_SIGNAL`, the run reports `PASS` / `PASS_WITH_GAPS` / `FAIL` /
   `NO_SIGNAL`, and a run with no comparable rows exits 2.

QA-01 is QA tooling. It changes no parser behavior, query routing, result
contract, API behavior, frontend product behavior, NBA data, or Raw QA case
expectation. `tests/test_qa_gate_integrity.py` runs without NBA data and pins
both gates' exit semantics.

**Immutable data-backed CI remains a separate decision.** GitHub CI does not
carry the local NBA dataset, so the full Raw QA corpus and the data-backed
filter sweep were deliberately not added to ordinary CI in QA-01.

Phases 1B, 1C, and 1D stay deferred and unstarted.

---

## OPS-01 - production monitoring and dependency-security recovery

**Active task.** Operations only. It restores two signals that had gone
untrustworthy after QA-01 merged.

1. A sustained sequence of scheduled `Production Monitor` runs failed with
   HTTP `410 Gone`. The workflow targeted
   `nbatools-fvdbt0pfv-brents-projects-686e97fc.vercel.app`, a single
   deployment's URL from the Queue D acceptance receipt; that deployment has
   since been removed, so its host answers `410` regardless of service state.
   The tracked target is now `https://nbatools.vercel.app`, the project's
   stable production alias, which was healthy at every probe taken during the
   repair.

   No evidence of a production outage was found. The failures are explained by
   the dead target, and the stable alias and current production deployment were
   healthy when probed. Continuous endpoint availability at every historical
   failure timestamp was not directly proven and is not claimed: while the
   monitor pointed at a host that could not serve the application, its runs
   were a monitoring-coverage gap with unknown service state rather than an
   outage record.

   The regression test now asserts against the *parsed* workflow — the
   executable target, and that exactly one step invokes the monitor — so a
   correct-looking comment or a second overriding invocation cannot satisfy it.

2. `frontend-security` went red on GHSA-p498-v437-472g
   (`@humanfs/node < 0.16.8`, moderate), a transitive dev dependency of
   `eslint@9.39.5`. Remediated by a lockfile-only update inside ESLint's
   existing `^0.16.6` range.

OPS-01 changes no parser behavior, query routing, result contract, frontend
product behavior, NBA data, CI job architecture, audit severity policy, or
monitoring threshold, case, or retry rule. It selects no query-integrity phase.

---

## OPS-MON-01 - cold-start response failures and false-alert policy

**Deferred. Not the next active project.**

Recorded during OPS-01, not acted on:

- one direct cold `POST /query` probe returned HTTP `504`;
- the monitor's single approved retry covers transport failures and latency
  failures where a response was received; it does not retry a response failure,
  and an HTTP `504` is classified as a response failure;
- so a sufficiently cold serverless start could produce a failing run that the
  current retry rule will not absorb;
- deciding whether response failures should receive a bounded retry - or
  whether this should be handled some other way - is a monitoring-policy change
  that needs a separate owner-approved review.

OPS-01 deliberately makes no threshold, timeout, case, or retry change.

---

## CI-GOV-01 - required-check enforcement decision

**Deferred governance item. Not the active next task.**

Current project policy requires both `frontend-verify` and `frontend-security`
to be green before a merge. That policy is real and binding on anyone working
in this repo.

GitHub does not currently enforce it. As of PR #296 there is no classic branch
protection on `main` (the protection endpoint returns *Branch not protected*)
and no repository ruleset - so no check is registered as *required*, and
nothing mechanically prevents merging while a check is red.

The accurate description of a red `frontend-security` is therefore:
**policy-blocking and workflow-failing, but not currently enforced as a
required GitHub merge check.**

Deciding whether to configure required-check enforcement - and if so, which
checks to require and whether to enforce for the solo maintainer - is separate
repository-governance work. **It was deliberately not performed in PR #296**,
which changed no branch protection and no ruleset.

This item is recorded so the gap is known and deliberate rather than
accidental. It does not block the active queue.

---

## Phase 1B - compound event and filter routing integrity

**Problem.** A clear, reasonably formatted query that combines a threshold, an
event condition and a ranking intent can lose part of itself on the way to a
route. The answer that comes back is confident and is not the question asked.

**Priority queries.**

- `teams with most games scoring 120+ and making 15+ threes since 2020`
- `most efficient 30-point games`
- `players with 25 points and 10 rebounds`
- `most 40-point games while the player was injured`
- `Lakers leading scorer while LeBron was out`

**Requirement.** Preserve every requested threshold, event condition, ranking
intent, and concrete availability filter - or refuse. No silent reduction.

**Observed and recorded during the PR #295 repair.**

- `field goals made and attempted leaders` refuses with
  `leaderboard_request_unclear` and residual `["attempted"]`. The refusal is
  correct and truthful, but the elliptical coordination ("field goals [made]
  and [field goals] attempted") is not read as two metrics, so the sharper
  `leaderboard_multiple_metrics_unsupported` reason is not reached.
- `best offense and defense this season` refuses the same way, with residual
  `["defense"]`.

Both belong to compound parsing, not to metric selection.

---

## Phase 1C - unexecuted qualifier protection across fixed-metric routes

**Problem.** A route whose metric is fixed by the route itself can accept an
extra clause it never executes, and answer anyway.

**Route families.**

- `team_record_leaderboard`
- `player_occurrence_leaders`, `team_occurrence_leaders`
- `playoff_appearances`, `playoff_round_record`
- `record_by_decade_leaderboard`
- `player_stretch_leaderboard`
- `lineup_leaderboard`

**Safety probes** (probes only - Phase 1C is *not* expected to define
"depleted"):

- `best team record while depleted`
- `most playoff appearances while depleted`
- `best finals record while depleted`

**Requirement.** Stop a route from discarding an unsupported extra clause. That
is all. Interpreting the clause is not part of this project.

PR #295 pins these families only as *left alone by the metric boundary*; it
does not audit their residual-clause behavior.

---

## Phase 1D - filter execution receipts

The work separated out of superseded PR #294. Keep it as its own future
project: a receipt that a declared filter actually executed, rather than a
parse-time assertion that it was recognized.

Do not reintroduce `FilterExecutionLedger`, ContextVar receipt plumbing, route
receipt decorators, or receipt validators into a metric-boundary PR.

---

## Recorded coverage gaps (not trust defects)

Found during the PR #295 total-backed alias audit. These refuse or fail to
route; none of them answers wrongly, so none is urgent.

- `games played` has no entry in the shared metric vocabulary, so
  `games played leaders` does not route, even though `games_played` is an
  allowed leaderboard stat. Its backing column is not a `*_total`, so a
  `total games played` request would refuse if the alias were added. Making it
  reachable is new metric coverage, not alias repair.
- `3 pointers made` / `3-pointers made` are documented on the `season_leaders`
  route but absent from the detector vocabulary, so the router cannot reach
  them. Same class as the `three-point attempts` defect PR #295 fixed, but on a
  per-game-backed metric and therefore outside that audit's scope.
- `3 point attempts` / `3-point attempts` (digit-adjectival) do not resolve.
  No sibling metric documents a digit-adjectival form, so adding one would be
  new vocabulary rather than restoring parity.
- *(Resolved in PR #295.)* `three-point attempts per game leaders` was stopped
  by the broader `unsupported_concept` boundary before the metric boundary saw
  it, because the bare phrase "attempts per game" was on the unsupported-phrase
  list. That entry existed to catch a minimum-attempts qualifier; it is now
  bound to a number, so the qualifier still refuses generically and the ranking
  reaches the typed aggregation boundary.
- The generic unsupported-phrase boundary still publishes the parser's `stat`
  on its own refusals - it short-circuits before routing and predates the
  truthful-refusal contract. Every remaining query it catches is genuinely
  unrecognizable rather than a recognized ranking, so nothing is presented as a
  metric that ran a ranking. Extending the truthful-refusal contract to the
  generic boundary is Phase 1C-shaped work, not metric selection.
- **Deferred metadata integrity on fixed count and occurrence routes.** Codex
  observed that some fixed count/occurrence routes publish public metadata
  inconsistently with the truthful-refusal contract the variable-metric
  branches now follow. None of those routes chooses its metric from the query,
  so none is governed by the metric boundary, and none of them is a
  variable-metric aggregation decision. Extending the contract to them belongs
  with **Phase 1C** (unexecuted qualifier protection across fixed-metric
  routes), where those route families are already listed.
- `games played` and the occurrence-count columns (`games_20p`, `wins`,
  `losses`) are classified as `count`: only an unqualified request matches one,
  so `total 30 point games` keeps refusing exactly as it did. Whether a season
  count should accept "total" wording is a coverage question, not a trust one.
