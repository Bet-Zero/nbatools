# W6A verifier transition

The canonical current selector is
`tests/cloud_core_historical_delivery_real_data.py::test_stabilization_original_historical_api_and_ui`.
It binds the serving artifact and before/after immutable generation, original
case identities and independent arithmetic. It checks all 44 fresh desktop and
mobile captures and 40 timing observations, including distinct request IDs,
capture order, screenshots, source inputs and the served asset. Only the explicit
historical replay reads the applicability companion.

## Accepted equivalent evidence

- The [original replacement run](https://github.com/Bet-Zero/nbatools/actions/runs/46078137747)
  recorded the 84 observations against the frozen November 27 build.
  Its [archive](https://github.com/Bet-Zero/nbatools/actions/runs/46078137747/artifacts/15236515268)
  has SHA-256 `ee848896a76cda2018e6462a1a786c937d56cc253f87c6f9bd2af7f96ecb74ec`.
  The independent review verified all screenshot hashes, distinct native
  request IDs, exact original oracles and the served JavaScript. The pooled
  p95 was 562 ms and the slowest timed repeat was 585 ms.
- An independent replay of all 22 complete payloads on the checksum-restored
  Cleveland generation matched the 22 recorded original payloads on the
  corrected [release candidate](https://github.com/Bet-Zero/nbatools/pull/668).
  Normal JSON serialization and per-request identifiers were accounted for.
  The authenticated [full release](https://github.com/Bet-Zero/nbatools/actions/runs/46087190603)
  and [manifest-specific consumer](https://github.com/Bet-Zero/nbatools/actions/runs/46087458901)
  carry their exact candidate and data identities. The hosted release
  measurements and final serving artifact are in the release evidence.
- The transition changes verifier tests and the checkpoint. The provider
  build and ordinary data and application inputs are verified separately from
  these test changes. Guard cases still reject malformed archives, missing
  or duplicate capture rows, wrong build or data, changed samples, stale
  request IDs and reused evidence.

## Replay the original historical context

Keep `historical-live-original.zip`, `live-code-binding.json`, the latest
reviewed historical applicability companion and their independent receipts.
The original archive has SHA-256
`a5c718c7498f24d787866ff4e3d53220363e00588a045607e92f5947ac2074a5`.
Original screenshot and code bindings are reachable from the
[historical evidence directory](https://github.com/Bet-Zero/nbatools/tree/34d8daf31f90baee77c50e93c3220f526022369a/working/nba-tools-completion-program/source-evidence/core-live-current-20261107).

For a replay of the old source-binding guards and the retained original
answers, use detached source `34d8daf31f90baee77c50e93c3220f526022369a`
with the original `availability-lebron-season-v1-20261031` data.
The [775-file archive](https://github.com/Bet-Zero/nbatools/releases/tag/cloud-backup-41259773052)
was verified and replayed without R2 credentials or public requests by the
independent checker. In that detached context, run
`tests/test_core_historical_applicability.py` for the old source and tamper
guards, and explicitly select
`tests/cloud_core_historical_delivery_real_data.py::test_requalify_retained_actual_historical_api_and_ui`
for the retained replay. The earlier live capture selectors and their
original execution reports remain available at their original revisions.
