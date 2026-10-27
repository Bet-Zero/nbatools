# Data availability and acquisition-only handoff

Owner direction (October 18, 2026): the backup laptop collects NBA source data
when needed. R2 remains central storage. Codex develops, validates, processes and
analyzes in the cloud. Commercial provider evaluation and cloud NBA access
investigations are stopped. No provider key is needed. The owner resumed normal development on October 18 after accepting minimum setup. Missing specialized data does not prevent
work on supported core datasets.

The owner's 2026-10-27 K08 exception in [AGENTS.md](../../AGENTS.md#narrow-k08-report-acquisition-exception-owner-2026-10-27)
authorizes exactly three named official reports through the existing GitHub
Actions acquisition route. All other acquisition and publication restrictions
below remain in force; that exception is not a general cloud-fetch authorization.

Current K08 direction additionally authorizes the small representative structured
source investigation described in AGENTS. It favors verified Traditional V3 plus
Summary V2/V3 archival evidence, with PDFs as targeted fallback. Metadata inventory
is distinct from body qualification or inactive/membership completeness. No bulk
acquisition, automatic refresh or production publication follows from that sample.

## Before implementing a data-dependent change

1. Read the active generation's generated `inventory.md` and `inventory.json`.
   Initial inventory: [permanent release data-inventory-39158132815](https://github.com/Bet-Zero/nbatools/releases/tag/data-inventory-39158132815)
   from [read-only run39158132815](https://github.com/Bet-Zero/nbatools/actions/runs/39158132815). Subsequent approved publications attach
   inventories to `cloud-backup-<publication-run-id>` releases automatically.
   Releases/artifacts identify the exact generation and authenticated manifest
   SHA256. Never assume the newest report is still active after a rollback.
2. Match its generation to the read-only R2 workflow preflight/active pointer.
   If they differ, run the explicit inventory selector below for the active
   generation. Do not relabel an old inventory as current.
3. Inspect exact file, season/type, columns, game IDs, key/null/numeric/trust checks,
   game/team coverage and the independent recorded pipeline receipt. A file
   existing, a legacy complete flag or a passed receipt does not prove every
   player, period or season is complete. Full-season completeness stays unknown
   without a qualified external denominator. Game coverage uses observed final
   games in the pinned generation; player team-game presence is not every
   played player. Listed-player availability never establishes all absences.
4. Read the separate development-staging section. Git bundles, laptop collections,
   unregistered candidates and retained/inactive generations are not active
   production coverage. The staged list covers hash-verified bundles tracked in
   this repository, not every private machine or historical worktree.

The existing read-only R2 validation workflow can run the reviewed selector:

`tests/cloud_data_inventory_real_data.py::test_generate_production_inventory`

A reviewed request on `r2-validation/data-inventory-<unique-label>` produces a
permanent GitHub release with both reports, after the required test really
executes/passes. It authenticates the pointer/manifest, verifies every listed
object's bytes/hash and checks the pointer again. Drift or corruption fails the
run rather than publishing a mixed-generation inventory. Ordinary CI gets no
R2 credentials. No R2 writes or extra cloud service are introduced.

After each future separately approved production publication, the existing
verified backup/restore path scans the authenticated restored generation and
appends the inventory to the same permanent backup release. This does not fetch
NBA APIs, publish data, start a refresh timer or overwrite any immutable object.
First execution of that future publication hook remains distinct from the
initial live read-only scan. Expiring Actions artifacts are transport only.

## Precise missing-data request (Codex, in the cloud)

Generate a request against the selected inventory, for example:

```bash
python -m tools.data_availability request inventory.json \
  --dataset raw/player_game_period_stats --season 2026-27 \
  --season-type 'Regular Season' --game-ids 0022600001 \
  --fields pts ts_pct > collection-request.json
```

The packet preserves the base generation/hash, requested and missing NBA game
IDs, fields, grain, keys, source requirements and applicable standard period
windows. Games absent from the production game catalog are reported explicitly;
no game or result is invented. Add explicit team/player IDs when requesting a
seasonal on/off or lineup scope. `collection_needed` distinguishes missing rows
or columns, wholly null fields, or unobserved requested identity keys from a
present dataset needing quality/trust review. Identity absence is not evidence of
DNP, injury, or expected participation; request qualified coverage. Partial nulls
are flagged for cloud review, not silently accepted as complete. Processed data
is built in the cloud; request its raw inputs rather than asking the laptop to
build the application. If a field's meaning is not in an existing contract,
Codex must define/qualify it before treating any new source value as that field.

## Backup laptop: acquisition and transfer only

Codex supplies the bounded request and exact collector parameters. The laptop
uses its existing NBA API collector to save **original source responses**, not
fabricated or derived replacements. Put files under this data-only layout:

```
collected/
  acquisition.json
  sources/...
  data/raw/...       # optional existing collector CSV output
```

`acquisition.json` records source, timezone-qualified capture time, exact request
parameters and any errors/coverage limits. Do not include credentials, cookies,
`.env`, executable files or a development environment. Missing endpoints remain
missing. Do not turn full-game totals into period data or participation into
on/off. Source responses must retain official IDs and statistical basis.

The standalone helper uses only Python's standard library and does not require
installing or running NBA Tools development on the laptop:

```bash
python collection_bundle.py create collected \
  --request collection-request.json --output collection.zip
```

Codex can supply this single helper from the reviewed revision. It binds the
request and every file by SHA256; it accepts only raw/source CSV/JSON/PDF and
provenance, refuses existing outputs, and limits a bundle to20MB compressed,
100MB expanded and2000files. Split larger captures into bounded game/windows
requests. The helper checks transport integrity, not basketball correctness.

Upload `collection.zip` through GitHub's web UI on a **data-staging task branch**
(or the existing agreed cloud file handoff), preserving its commit/hash. Do not
upload credentials or push to main. No R2 write credential goes on the laptop.
GitHub staging is not production. Codex handles all subsequent technical work.

## Cloud: validate, prepare and request protected publication

```bash
python -m tools.collection_bundle unpack collection.zip \
  --request collection-request.json --output work/new-collection
```

Unpack rejects mismatched requests, unsafe paths, duplicates, symlinks, wrong
bytes and limits **before writing**, and refuses an existing destination. It
never executes uploaded code. The result remains explicitly unvalidated.

Codex then:

1. Compares source/game/team/player identities, exact statistical meaning,
   source timestamps, full requested row/window coverage and source totals.
2. Uses the existing raw normalizers, validators, processed builders and receipts
   in an isolated cloud stage. Preserve all prior history/last-good generation;
   do not replace a season file with a one-game CSV. A changed active base requires
   rebasing and fresh validation.
3. Preserves the original bundle/source receipt durably and creates the same
   reviewed overlay/source artifact, exact publisher code, inventory and registry
   package used by [protected publication](data_publication.md). The existing
   registry accepts reviewed packages; it does not accept arbitrary laptop ZIPs.
   No general-purpose upload or protection bypass is added here.
4. Obtains independent checks and normal CI; runs protected **validate** read-only
   against that exact registered package. The owner can review the concrete
   generation, base, hashes, tests and storage bounds.
5. Requests separate owner production authorization and the existing environment
   approval. Only the protected publisher writes R2. It verifies the resulting
   generation and preserves the previous generation/receipt/backup. The inventory
   is regenerated from the resulting authenticated snapshot.

No new production data has been published merely to test this handoff. The
packaging/unpacking process is verified independently of a real future laptop
collection; each collection still needs its own data qualification and approval.

## Initial observed coverage (not a new publication)

Read-only scan on October 18, 2026 at 15:19 America/Detroit verified all **703
objects / 402,749,125 bytes** of `availability-opening-s4-v1-20261017` against
manifest `5497832bca4567734386e26367798c60fd6e3685a0c93cd561227a5e5d833f52`.
One required test was selected/executed/passed, with zero skips or errors. Reports
are permanent release assets, not dependent on the seven-day Actions artifact.
The full JSON SHA256 is
`d5f72265f5b7baf113ed25d29c65494cb9f3eb40896073b7a657c687ede16f04`.

Production contains 1996-97 through 2025-26 season files: **37,986 observed final
games**, 786,773 player-game rows and 75,972 team-game rows. Those totals describe
stored rows, not independently complete seasons. The 2025-26 core has 1,230
regular-season and 85 playoff games; player rows 26,651/1,921 and team rows
2,460/170 cover those observed game catalogs. Individual player completeness
remains unknown. Period files exist for 2024-25 and 2025-26; their presence is
not proof of every player/window or independent numerical accuracy.

The inventory exposes **154 files requiring quality review**: 57 legacy game and
57 legacy schedule files lack current site/trust columns; 40 historical team
files have plus/minus consistency findings. Do not silently repair production
or treat those fields as qualified. Validate the exact feature/data slice before
use; issue details and example offending keys are preserved in the report.

There is **no 2026-27 production season** in this snapshot. Production has no
`raw/team_player_on_off_summary`, `raw/league_lineup_viz` or
`raw/play_by_play_events` files. Five checksum-verified repository staging bundles
are listed separately, including source/partial/noncanonical paths. Their
coverage does not fill a production gap until validated and approved for
publication. The sample collection request is illustrative and explicitly says
its game is not in the production catalog; it does not assert an unobserved game
or result exists.

This completes minimum data-availability setup for cloud development under the
owner's acquisition-laptop architecture. No commercial key, new service, or cloud
NBA API route is required. Normal development was explicitly resumed by the owner on October 18. A future missing-data request still requires acquisition; its new
production generation still requires the existing separate approval.
