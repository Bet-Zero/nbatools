# NBA Tools completion program

Coordination file for trust projects that are **out of scope for PR #295** and
must not be started inside it.

PR #295's final bounded scope is *Phase 1A - explicit metric selection and no
cross-metric substitution*: metric selection and aggregation integrity on the
ranking branches that choose their metric from the query. The durable
description of that scope lives in
`docs/architecture/parser/leaderboard_metric_boundary.md`.

Everything below is a real defect class that PR #295 does **not** fix and does
**not** claim to fix.

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
