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

## Verification and remaining release binding

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

Before registry enablement, bind the independently accepted producer inventory
to an immutable reviewed publisher revision. Reuse the existing
publisher and secure workflow, preserving exact reviewed-code hashes, same-base
checks and refusal to overwrite existing raw files. The combined artifact must
be prepared against the complete current base with no writes; verify every base
object is unchanged, only the reviewed overlay and expected derived data differ,
all manifest hashes/budget checks pass, and opening plus S4 consumers still work.
The fixed `publish-combined-availability.py` entry point delegates to the
existing publisher using keyword-only inventory/default-generation arguments;
the opening entry point retains its original defaults. A missing or changed
inventory fails closed. The combined inventory pins both wrapper/shared publisher
code as well as the existing validator/import dependencies. Register the new package
only after those reviewed pins exist. No placeholder package is currently registered.

If the opening package or another generation is published first, the existing
same-base guard must stop this package. Agents must then requalify against that
new base and review the merged availability files; do not bypass the guard or
silently overwrite published rows. Future production execution uses the same
protected environment, immutable generation, conditional pointer update,
rollback protections, object/consumer verification and durable receipt process
in [the publication runbook](../../docs/operations/data_publication.md).
