# Combined qualified availability publication package

This is preparation evidence for the existing protected publication process,
not authorization to publish. Production publication still requires the owner's
future explicit approval. No publishing credential or workflow is added here.
The sole active queue remains [README.md](README.md).

## Source and scope

The deterministic producer combines the reviewed opening GSW/LAL report with
the four qualified BOS/LAL reports. It retains all five official PDFs, receipt
bytes, opening identity/profile evidence, and per-game import digests. It does
not add season-wide availability, injury, or medical-clearance claims.

- Opening: reviewed631b259a10be675be9a97da93ebc38053a274e79,
  request3ae073562a19b339ea387037deca30fe90a2677f,
  run39002683645/artifact12090016663. Exact file/archive checksums remain in
  [opening inventory](opening-availability-inventory.json).
- BOS/LAL: reviewed9895ee04ec9b0144e314dac3e9981e3737b6aacc,
  request9c844e3d7a96c0be9fd040764264102b2fc97c0f,
  run39007679992/artifact12091388833. Exact file/archive checksums are in
  [S4 source inventory](s4-availability-source-inventory.json), including the
  canonical evidence retained by that successful source run.
- Both use `queue-d-production-0574735-20260716`.
- 2023-24: 68 listed rows, 41 played and 27 explicit DNP, two games.
- 2025-26: 102 listed rows, 70 played and 32 explicit DNP, three games.

`tools/combine_availability_package.py` verifies every input file before writing
local output. It rejects changed/missing/extra files, unsafe paths/symlinks,
changed bases, overlapping games, duplicate player-game keys, lost/extra import
lineage and conflicting retained source bytes. CSV fields are preserved as text;
only deterministic row ordering and CSV encoding change. No base dataset is
opened for mutation. Canonical selected evidence is validated as input but is
not copied into the publishable raw overlay.

The bounded producer selector is
`tests/test_combined_availability_package_real_data.py::test_combined_reviewed_availability_source_package`.
It uses the existing publication gate's successful-run, request-parent, archive
hash, exact file inventory and executed-positive-count checks to retrieve both
sources. It verifies exact combined game keys, all canonical played-player keys,
all ten 240-minute team totals, explicit Tatum/LeBron/Moody participation and
existing `validate_publication` source/import/identity validation before emitting
an artifact. The runner is read-only. Artifacts remain temporary evidence.

## Verified preparation and publication boundary

Actual combined source run [39086974163](https://github.com/Bet-Zero/nbatools/actions/runs/39086974163)
passed one selected/executed test with zero skips/failures/errors. Reviewed
producer48a63f4d692bb49fa2aee681f2dd4dc34d5db4b4,
request3edf7ec96ab31620f2d01cd49da77555e11da603; artifact12120538437, ZIP
SHA25671ced9c4765da2205416733d2f2121963b0d8622124c5d447da293ab5a3c0e8c.
Independent checker /root/availability_checker accepted fresh receipts, all170
unchanged source rows, five recomputed import digests and retained source bytes.
The [combined inventory](combined-availability-inventory.json) pins19artifact
files, including18rawfiles/518,002bytes and candidate-bound validation metadata.
It also pins both wrapper/shared publisher and all existing validator dependencies.

Local integrity fixtures: 13 passed. The fixed publisher entry-point fixtures
add seven checks; with the 19 existing publication-gate tests, 39 passed. Cached source replay preserved every source
cell, all source file checksums and all five import digests. These checks do not
substitute for the actual pinned runner or complete snapshot preparation.

The registry binds `opening-s4-availability-v1` to immutable publisher
`b7eead87c20dc5abc036ce6fecc6413423b38d1e`. The fixed combined entry point
reuses the existing publisher; the opening package and its original pinned
revision remain unchanged. Both wrapper and shared publisher implementation are
checksum-bound in the combined inventory. No workflow, bucket, credentials or
publication infrastructure were added.

Actual complete-snapshot run
[39091103560](https://github.com/Bet-Zero/nbatools/actions/runs/39091103560)
passed **one selected/executed test, zero skips/failures/errors**. Reviewed
candidate `072bd3b78389d9cf27058d6bf0eb137495563bd1`, request
`e23a27b00ee9e9910e4d441c43c9c586f27fca89`. Artifact `12122218736`, ZIP SHA256
`290778578b035bdb4df8c1594f238697fa7d40c2dea32d72586df93a67b2f801`.
Independent checker /root/availability_checker accepted the fresh receipts,
recomputed the manifest hash and exact base/overlay/derived inventory, checked
the budget and matched all six consumers to independently frozen source truth.
Implementation merge still requires applicable CI. Production publication
remains unauthorized.

The executed selector was
`tests/test_combined_availability_publication_real_data.py::test_combined_availability_complete_snapshot_prepare`.
It verified every size/hash in the proposed **703-object, 402,749,125-byte**
snapshot: all 684 base objects unchanged, 18 exact reviewed raw overlay objects,
and only the expected derived player-name index added (500,982 bytes, SHA256
`f7097aaefe54b986ea5036e3c9ca5ca4c05a58266aa6cd0e2b4710e4cfe5f1b2`). The active base pointer
and authenticated manifest stayed unchanged around preparation. Whole-bucket
conservative projected storage was **1,167,483,320 bytes**, below the unchanged
10,000,000,000-byte limit. The receipt explicitly says `prepared_no_writes`.

| Retained receipt | SHA256 |
| --- | --- |
| Base manifest | `4bfa194ad102f0ab7b257fafdc66e2d9d5af1bfe95318196f5e20a46fdc5b28e` |
| Proposed manifest | `5497832bca4567734386e26367798c60fd6e3685a0c93cd561227a5e5d833f52` |
| Preparation receipt | `38a4d91e93e532c5bed090a476956d4827a73a9ed19611e43b3e0346b1bc37cb` |
| Consumer checks | `d42941826283e9973bbcd0123ce67d3bf001889f434d514a18c7fea7ab2f1979` |

Six application checks passed against this complete locally staged generation:

| Qualified sample | Games / W–L | PTS average |
| --- | --- | --- |
| LAL without LeBron, 2025-10-21 | 1 / 0–1 | 109 |
| GSW without Moody, 2025-10-21 | 1 / 1–0 | 119 |
| BOS vs LAL with Tatum, 2023-24 | 2 / 1–1 | 115.5 |
| BOS vs LAL without Tatum, 2025-26 | 2 / 2–0 | 118.5 |
| Brown vs LAL with Tatum, 2023-24 | 2 / 1–1 | 13.5 |
| Brown vs LAL without Tatum, 2025-26 | 2 / 2–0 | 31 |

S4 REB/AST means also passed. Brown's returned game IDs were exactly
`22300403/22300684` and `22500338/22500823`. These are local staged-generation
consumer checks; they are not deployed verification or permanent storage.
The same six queries are registered for eventual post-publication verification.

The fresh environment audit found no `r2-publication` environment (404), so
publication readiness remains false. Reuse the existing accepted workflow and
bucket. The only owner account setup is the protected publishing environment and
separately controlled bucket-scoped writer secrets described in the runbook.
No owner terminal work, credentials in chat, or duplicate infrastructure is needed.
Actual publication additionally requires future explicit owner approval; it has
not occurred.

If the opening package or another generation is published first, the existing
same-base guard must stop this package. Agents must then requalify against that
new base and review the merged availability files; do not bypass the guard or
silently overwrite published rows. Future production execution uses the same
protected environment, immutable generation, conditional pointer update,
rollback protections, object/consumer verification and durable receipt process
in [the publication runbook](../../docs/operations/data_publication.md).
