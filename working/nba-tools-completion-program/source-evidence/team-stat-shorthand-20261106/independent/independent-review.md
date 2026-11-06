# Independent application review

**Approved runtime:** `3105fee4dabfe8826d10151cbe932699800b2af9`, against merged
PR587/main `4bd2f799ddeb06544ef2223e56449ec609318dec`.
Reviewer: `/root/team_threshold_checker`, a separate Codex agent session.
The exact model identifier was not exposed; this is neither a cross-model nor
human-review claim. The checker did not author application code or interact with
Agent 2. Reviewed source hashes are recorded in `reviewed-runtime.json`.

## Verdict and scope

Approve the generalized whole-game team-owned noun-threshold implementation and
its repaired ownership handling. No unresolved blocking semantic finding remains.
This approval permits the existing required read-only validation request; ordinary
merge still requires its actual numerical/Raw QA results, applicable broad checks
and exact-head blocking CI. It does not approve production publication or full-season
Poeltl acceptance.

The implementation extends shared span/owner/bound interpretation and its existing
consumers. It adds no phrase/player/game exception or second statistical engine.
The availability reader recognizes complete statistic clauses without erasing
unread tails. Upper-bound containment only masks predicates received by the final
consumer with the same owner and bounds. Bare zero remains exact zero; explicit
zero-plus remains a floor. Strict and inclusive conjunctions remain distinct.
Existing injury/status, unsupported-metric, source-qualification, publication,
security and positive acceptance obligations remain in force.

## Independent executed evidence

On a detached checkout of the approved revision, with an absolute `PYTHONPATH`
pointing to that checkout's `src`, the three checker-authored test files passed:

**19 selected / 19 executed / 19 passed / 0 skipped / 0 failed / 0 errors /
0 xfails**, in 75.43 seconds. One existing Starlette/httpx deprecation warning is
informational. `review-3105-pytest.txt` retains the actual summary.

- Fourteen controlled positive cases cover different players, points/assists/
  rebounds/turnovers/threes, strict and inclusive ceilings, floors, player/team/
  opponent ownership, summary arithmetic, team records, splits, qualifying last-N,
  and explicit DNP counts through the natural service and HTTP API. Fixture data
  establishes software behavior, never real NBA tenure or injury.
- Three native held-outs reuse PR587's retained immutable originals and unchanged
  staged qualification. Direct original JSON arithmetic independently freezes
  exact selected IDs for Stephen Curry team assists, Kevon Looney team turnovers,
  and a date-bounded Poeltl DNP team-point ceiling. Selected AST/TOV team values
  reconcile to sums of original player rows. The NBA endpoints share upstream
  origin; no independent upstream source is claimed. No original was reacquired.
- Two additional discovery controls verify that abbreviated and spelled-out
  opponent owners select the same exact four game IDs: 368, 377, 407, 458. A
  condition naming Boston cannot admit Denver games through the opponent union.

Before candidate review, the original controlled hold-outs were frozen as
`holdouts-frozen.json` (SHA256
`57831d2057b081aab29f9e9c716ea75c55f115511a9dca486b3d0d1e3d8143ff`),
`absence-holdouts-frozen.json` (SHA256
`31b0236ab4052532c568ab62646b50ebe6901a9803dd0bb7a06719f071f84d5f`), and
`native-holdouts-frozen.json` (SHA256
`eee41d8156a64f2b0ab70c18ab78c18447d27360585b1e02d7251074aee225f6`).
The author did not receive these initial wordings before the first frozen review.

Two checker assumptions were corrected explicitly in `oracle-amendments.json`:
bare last-N with conditions is the documented qualifying sample, and the existing
explicit-team missed path need not expose the multi-club `membership_coverage`
metadata key. Original oracles and failed execution receipts are retained;
expected row/count values were not copied from engine answers. The amended last-N
IDs come from an independent raw CSV selection using the unchanged documented
sample contract. Corrected explicit-team tests retain exact missed IDs/counts,
the absence actor and answer wording, plus HTTP checks.

## Findings resolved

The first review found that mixed noun opponent/team assists were interpreted as
the player's own assists plus team assists, producing false no-match instead of
18 expected games. Reusing the existing opponent span reader repaired it.
The first repair then exposed a genuine canonical-owner loss: abbreviated BOS
conditions admitted Denver rows (9 games instead of 4). Preserving the existing
`opponent_team` key through the context boundary repaired that defect. Both are
covered by the final independent run; initial failure logs remain in this package.
The author's additional exact-zero and strict/inclusive boundary repairs were
reviewed in source and have dedicated author tests.

## Raw QA expectations independently checked

Direct arithmetic from retained original JSON confirms the three new corpus cases:

| Scope | Games | Wins/losses | Looney rebounds | Average rebounds |
| --- | --- | --- | --- | --- |
| Warriors points <110 | 14 | 3/11 | 113 | 8.071 |
| Warriors points <=110 | 17 | 4/13 | 143 | 8.412 |

`independent-rawqa-oracle.json` preserves exact original game IDs. Actual hosted Raw
QA execution remains an integration gate; this arithmetic receipt does not invent
an execution on R2 or a deployed browser.

## Broad-check applicability and limits

The broad preflight on `3e38cbe209c2d0d4fa0e972a31b12596d960aeda` is its actual
original execution, not an exact-head run on the approved revision. The reviewed
runtime delta from that revision only preserves an already canonical named
opponent key when it belongs to the explicit opponent set. Items without that
key retain the legacy `team` path. It changes no data bytes, source classifier,
metric, date/window selection, route/result schema, dependency, workflow or gate.
Focused ownership-family tests and the final nineteen independent cases cover
that affected binding. Unaffected broad results may be reused once the broad
run's terminal outcome and any unrelated findings are reconciled.

The generated inventory's raw QA count changes only 600 to 603, reflecting the
three added corpus cases. Its earlier stale-count failure must remain recorded;
the affected generated-inventory/docs-governance test must actually pass after
regeneration. Test-only finder/game-log assertion corrections do not change
runtime source or these source/data judgments. Final exact-head CI remains
mandatory; this review does not call an incomplete or failing broad run passed.

DQ-004 original-tenure evidence, the proposed full-season Poeltl total, DQ-005
unqualified margins, remaining rate unknowns, freshness, full Core-1 and production
acceptance remain unresolved in their existing records. No Agent 2 coordination,
blocked-route retry, K12 work, publication, new access, spending or schedule was
performed by this reviewer.

### Subsequent broad-result reconciliation

The broad run later completed at its original `3e38cbe2` revision with
10201 passes, 1863 unavailable-data skips and two failures. The generated Raw QA
inventory discrepancy was repaired separately. The other failure was an obsolete
ranked-opponent refusal, independently verified and approved for positive
promotion in [the supplemental review](ranked-opponent-promotion-review.md).
That receipt preserves both failures and gives two additional independent
controlled executions; it does not rewrite the historical broad outcome.
