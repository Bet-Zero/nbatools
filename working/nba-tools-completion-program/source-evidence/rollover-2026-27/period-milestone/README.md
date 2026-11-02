# Period-input milestone: qualified Q1, fixed remaining capture

This replaces the obsolete missing-Q1-ZIP dependency. Original handoff commit
`8ffc9eadc4666d4d0fca502db19ca04855f405ec` was read and selectively preserved;
its branch was not merged. No production data or pointer was changed.

`python -m tools.qualify_rollover_q1 --output work/new-q1-stage` replays the
hash-bound original ZIP and PR571's accepted expanded core through existing
whole-game producers, the SDK period parser, existing normalizers and validators,
then actual player finder and team-record consumers. The output is an isolated
partial stage: 22 player keys (19 positive and three authoritative Q1-only zeros),
two team keys, Q1 only. Cade has 6 points/3-of-5/9:15, Tatum 7 points/4 assists,
Huerter TS/eFG1.5, Garza zero Q1 minutes, and Boston wins Q1 28–27. Q2 stays
unavailable. CSVs and actual consumer responses are retained here. Full-season
backfill still uses its six standard windows; partial admission explicitly passes
only the observed window. V3 turnoverRatio has fixed percent-point units, so
22.2 becomes .222 and .5 becomes .005 regardless of other rows.

The independent original review is [original-q1-review.json](original-q1-review.json).
Body `meta.request` values remain literal NBA origin metadata; HTTPS transport
comes from the original acquisition receipt, not that body string. This does not
turn local self-checks or HTTP200 into full dataset acceptance.

## Fixed population and retained sources

[scope.json](scope.json) records the cutoff, exact IDs and package bindings.
At 2026-11-02 04:37:23 UTC, with the unchanged 24-hour lag, the independently
normalized 1,206-row schedule has **88 due/final games**. The latest Finder,
team log and player log contain exactly those IDs, through October31. Seven new
games0147–0153 add161 player rows. The due set was checked again before packaging;
its next scheduled change is November2 20:30UTC. Refresh it again at eventual
snapshot acceptance; 88 is a frozen acquisition basis, not permanent freshness.

[archive-refresh.zip](archive-refresh.zip) preserves seven changed season originals
and14 new-game Traditional/Summary originals at mirror revision
`75049d7c3ed9db26aa6f3b6f2956afc0c403acb2`, plus metadata and SHA256 bindings.
The first scratch capture had filename collisions; three originals were overwritten
locally and recovered once from the same immutable URLs with identical hashes.
That diagnosed retry and the initial metadata are retained, not called a zero-retry
capture. Mirror commit/retrieval times are not NBA source capture times.

[fresh88-review.json](fresh88-review.json) independently checks exact IDs, the six
valid new Traditional bodies, all30 team Advanced GP/WL/net arithmetic, and the
same12 unresolved player TS conflicts. The old525-player/30-team roster projection
covers all441 currently observed player-team keys; it does not establish tenure.
New0151 Traditional has Nate Ament `18:60`; quarantine its clock/core admission,
preserve valid primary18.9916667 and source originals, and keep literal position
projection separate. Old0096 quarantine and PR571's accepted115player/22team
changes remain intact. No fresh conflicting source cell silently replaces them.

## One owner package

[NBA-Tools-Readiness-Capture.zip](NBA-Tools-Readiness-Capture.zip) contains one
self-contained collector and Mac/Windows launchers. Unzip into a new folder and
open **Run Capture.command** or **Run Capture.bat** using the laptop's existing
Python/nba_api installation. No checkout, install, source choice or command writing
is required. Return `readiness-capture/collection.zip` through the existing handoff,
including on failure, and retain the output folder until receipt is confirmed.

The embedded [fixed request](../../../collection-requests/rollover-period-readiness-2026-27.json)
contains **1,061 calls**:530 missing windows × Traditional+Advanced =1,060;
one Player Advanced/PerGame response with `DateTo=10/31/2026`. The already-qualified
game0001/Q1 pair is excluded. Six direct standard windows are requested per game,
plus direct overtime for0110/0120/0141. Halves and Advanced rates are never summed
from quarters. Fresh team Advanced/rosters are reused; no redundant laptop capture.

Requests are serial, one attempt each, at least1second apart,30second timeout,
2MB/body,12hour invocation ceiling,20MB compressed/100MB expanded/2000file bounds.
HTTP/transport/JSON failure stops the batch. Original successes, failed partial
bytes, exact parameters, timestamps, SDK version and all unattempted jobs survive
in the data-only ZIP. Rerunning cannot automatically retry a recorded failed
request. There is no fallback host, new credential, unattended refresh or write.
Typical successful duration depends on source latency (at least18minutes from
spacing alone); there is no promise that the whole finite batch will succeed.

25 collector tests include the real Q1 bytes, failure/interruption preservation,
size/integrity bounds, generated launchers and all1,061 dry SDK mappings. Exact
SDK1.12 execution was not claimed: automatic approval rejected a cloud-only install;
read-only v1.12 declarations were compared instead. They expose one default-None
ISTRound addition; the collector narrowly accepts absent/None equivalence, rejects
non-None and otherwise fails closed on any SDK parameter difference. The successful
original laptop1.12Q1 evidence is reused; no setup repeat is requested.

## Stop and next acceptance

Stop at this reviewed/preserved milestone awaiting the one package's output.
The next agent verifies its exact request/hash/bytes, qualifies each direct window
through `tools.stage_rollover_periods.import_window`, and reconciles the12 Advanced
conflicts against the same88-game cutoff. Returned transport success alone is not
acceptance. Then assemble/validate all11raw+5processed datasets with trusted
receipts, refresh exact due IDs, and present a concrete publication package for
separate approval. Unattended freshness and any later due games remain explicit.
Existing LeBron publication,16live answers and backup are preserved; K08/K12 stay
paused. The [final independent review](final-review.json) APPROVES semantic candidate
`279e66a408116367f6be9e390d0ecb2e150044b0`; the checker independently reproduced
a contradictory-margin admission, then confirmed its repair against both Summary
scores. Unfamiliar PaulReed/IsaiahJoe/PaulGeorge consumers, direct-H1-only completion
and all-sub1 turnover rates passed.60focused controls passed. Exact final-head
CI and landing details belong in [PR572](https://github.com/Bet-Zero/nbatools/pull/572)
and its final receipt; receipt-only descendants retain the reviewed hashes.
