# Authenticated recovery and full dataset assessment

This is an unpublished source-qualification checkpoint. It does **not** accept a
coherent full snapshot or authorize production publication. PR574 carries the
candidate, independent review, focused execution and CI receipts.

The owner original `collection.zip` is byte-exact: 1,445,891 bytes, SHA256
`7eb2f30f0afa7806fd2e7a7bca98c1a42c1b3d480134c226f577f99f1415bf17`.
It was first pushed to **unmerged** staging branch
`data/readiness-recovery-capture-20261104`, immutable commit
`828c741f6500a96b956d5a1d2481d241d275f275`; independent remote readback passed.
This candidate selectively preserves those same bytes, without merging staging.
All 517 attempts/responses match the fixed request, manifest and original hashes.
All 602 earlier successes are reused by exact request/hash; none was recollected.
The two batches stay separate. The independent transport report and staging
custody receipt are adjacent; artifact hashes are in `preservation.json`.

The only new archive bodies are 29 first-time Summary originals needed for the
recovered tail and one changed official schedule, at immutable public mirror
revision `a0d9c9539f0ffbb6a912fb9c25ac04ba7ce1d5bb`. They are retained in
`supplementary-sources.zip`, with URLs, blob hashes, sizes and capture metadata.
No completed collector request was repeated. Archive commit/retrieval time does
not establish the original NBA source capture time.

## Period and clock results

All 555 **captured** paired direct windows execute through the existing importer and raw
validators, against separately hash-bound Summary originals. **536 direct
windows pass**; 19 originals remain quarantined (15 clock and four score failures).

Thirteen malformed-clock windows additionally qualify using explicit derived
clock observations from two independently admitted complementary period requests.
For example, a player's H1 minus Q2 supplies Q1 timing. Each endpoint derives its
own seconds; exact team/player/game identities and all 16 Traditional count fields
must reconcile, both endpoint clocks must agree, and the unchanged importer must
pass. Only the explicit copied minute fields change. Every original source,
original failure, source hash, term, coefficient, derived body and hash is retained.
References cannot depend on another derived window or form cycles. This is not
carrying an invalid `:60` literal, increasing tolerance or silently editing a
source. Valid clocks with residual disagreement are not adjusted to force a pass.

The resulting **549 qualified windows / 12,369 player rows / 1,098 team rows**
remain partial. Six windows fail and contribute no staged period rows:

| Game | Windows | Unresolved evidence |
| --- | --- | --- |
| 0022600097 | Q4, H2 | Displayed player clocks exceed the team duration by four seconds; unchanged guard allows two. Complementary references are not independently admitted. Whole-game diagnostics do not establish a unique erroneous direct cell. |
| 0022600142 | Q3, H2 | Dallas direct scores 27/53 disagree with Summary 29/55. Caleb Martin's quarter count basis is 8 points/5 attempts, while accepted and latest whole-game counts are 10/6. |
| 0022600144 | Q2, H1 | Atlanta direct scores 29/45 disagree with Summary 30/46. Jalen Johnson's quarter basis is 16 points/0 free-throw attempts, while accepted and latest whole-game counts are 17/1. |

The capture plan is also incomplete relative to source period evidence.
The 92 Summary period arrays imply **556 known windows**, including overtime
for 0110, 0120, **0128**, and 0141; only the other three OT pairs were requested.
Game0128 therefore needs two **first-time** OT requests, not a retry. Its retained
whole-team MIN264 hid overtime from the old threshold-based request selection.
The original TeamAdvanced elapsed-minute totals corroborate all 30 teams on the
four observed OT arrays. Summary0111 also has a root period5 header but only four
period arrays on both sides; that metadata disagreement remains explicit, not
silently normalized. The whole period universe remains unaccepted.

`source-period-denominator.json` preserves the independent all92 audit and exact
source hashes. The full assessment separately checks known OT team keys against
the stage: 0128 contributes two additional missing team-window keys. The ordinary
manifest's 142 player/12 team missing-key counts cover the six standard-window
quarantines only; they do **not** establish complete overtime coverage. Missing
0128 OT player participation remains unknown, not fabricated zero rows.
The assessment also retains aggregate whole-team minute differences in OT games
0120, 0128 and 0141 against Summary-derived elapsed duration; those existing core
cells are not silently corrected or promoted as authoritative timing.

The existing statistical consumer returns Cameron Boozer's recovered October 25
Q1 as 3 points, 1/6 FG, 8:09, TS .25, with original rate values preserved.
No whole-game answer is silently changed to match a period source.

## Core, Advanced basis and required validation

All accepted 88-game core cells remain unchanged. Four games append via retained
primary context and existing explicit whole-source reconciliation; game0154's
completed whole-game counts/clocks supply an explicit ledger, while game0157's
malformed whole clock remains quarantined. Its literal POS projection is a
separate field scope, not numeric clock qualification.

The new Advanced snapshot now reflects completed game0154. It agrees with all
442 player TS calculations on the diagnostic primary-plus-completed0154 basis,
but disagrees with 12 players in the preserved accepted core. The seven new whole
game probes demonstrate a mixed basis: 39 integer cells now agree with primary
and disagree with accepted values; eight others retain accepted values against
primary. In particular, the latest whole142/144 bodies and their Summary scores
still contradict the direct periods and Advanced basis. Neither whole source nor
Advanced gets blanket precedence. No accepted cell, TS or usage value is replaced
merely to remove a conflict. Independent exact source/cell mappings are retained.

All **11 required raw / five processed datasets are physically present and
assessed**, using existing normalizers, all five existing processed builders,
`validate_raw`, `build_slice_manifest` and manifest validation. Thirteen dataset
records pass schema/trust/coverage checks; **schedule, player periods and team
periods fail**. These are not 13 fully source-qualified datasets. The raw validator
also fails the exact final catalog gate. Separate numerical/source checks retain
12 TS disagreements, nine clear per-game minute-basis contradictions, five
unresolved precision boundaries and the unestablished independent usage basis. All 442 player GP/WL records and 30 team
GP/WL/standings/net-rating checks pass; those do not resolve the count/time basis. There is no
trusted passed acceptance receipt, complete backfill manifest or protected R2
validation claim. Building processed files for diagnosis does not accept their
source data.

Independent review caught two false minute contradictions at the exact rounding
boundary. The diagnostic now preserves literal CSV tokens and uses exact
decimal/binary64 representation intervals against the unchanged inclusive 0.05
minute half-step. A boundary-straddling interval stays unresolved and blocks
acceptance; no tolerance, data cell or clock guard changes. Applying the method
consistently also leaves three formerly inside comparisons unresolved.

The existing exact 24-hour due-ID calculation, refreshed against the latest
retained official schedule, finds **107 due games** and **15 absent games
0022600158–0022600172**. It records its precise execution time and the schedule's
separate immutable identity. Ninety-two was the earlier capture population, not
current completeness. Refresh this calculation again before eventual acceptance.

## Reproduction and continuation

From the repository root with its existing Python environment:

```bash
python -m tools.qualify_readiness_recovery --output work/recovery-replay
python -m tools.assess_readiness_recovery work/recovery-replay/stage \
  --output work/recovery-assessment
```

Both destinations must be new. No network or production credentials are used by
these commands. `qualification-evidence.zip` preserves the executed qualification,
all 16 assessment records, staged diagnostic files, derived clock inputs and
independent source/clock reports. Synthetic tests remain tests, not NBA evidence.
The PR receipt identifies focused checks and the frozen review candidate.

Next reconcile the six precise clock/score dependencies and Summary0111 metadata
using independently qualified alternate evidence; obtain the missing0128 OT pair
without repeating any captured request. Preserve conflicting originals, then extend
coverage with first-time sources for the 15 newly due games. Do not recapture a
completed request automatically. Repeat affected source/numerical checks, all
required dataset gates and exact fresh due IDs before proposing publication.
The production generation, pointer, LeBron answers/backup and K08/K12 remain
untouched. Separate concrete approval is required before any production publish.
