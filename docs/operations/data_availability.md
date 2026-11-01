# Data availability and acquisition-only handoff

Owner direction updated **2026-11-01**: routine, bounded public NBA collection
and staging is authorized through existing approved sources, tools, credentials
and cost limits. Agents own source collection, validation, implementation and
testing autonomously; do not request approval for every batch. This includes the
reviewed 2026-27 Regular Season request. Use qualified existing inputs first,
then the smallest justified new capture through the existing reviewed GitHub
archive and source tools, targeted read-only Actions route or acquisition laptop.
The laptop remains acquisition/transfer only; development stays in the cloud.

This supersedes older per-batch collection approval, planning-only pauses and
laptop-only restrictions within the standing approved scope. The earlier narrow
K08 captures retain their original evidence and statistical limits; they do not
limit the new standing collection authority. Do not repeatedly probe known
blocked endpoints or treat archive retrieval time as source freshness.

Separate explicit approval remains required for production publication,
substantial bulk backfills, new costs or credentials, expanded permissions,
destructive operations or weakened safeguards. No automatic refresh schedule,
new service, commercial provider investigation or permission expansion is
implied. Keep fixed-plan/$0-overage limits, existing read-only credentials,
source/numerical/readiness safeguards and separate protected publication.
Collection/staging does not change the production pointer.

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

For whole-game participation, inspect the requested team's observed final-game
population before collecting more reports:

```bash
python -m tools.participation_coverage \
  --generation availability-k08-retained-v1-20261031 \
  --manifest-sha256 de83522f37f6bd7f26b51c1bf869deb05bbe242d3249d685997a979c050d16a9 \
  --season 2025-26 --team-id 1610612747 --player-id 2544 \
  --output work/lebron-participation-coverage.json
```

The read-only report checks manifest-bound relevant bytes and applies the same
runtime participation qualification to each catalog game. It separates positive
play, explicit DNP, exact-game opposite-side association and unknown keys. It
withholds a missed total while any key remains unknown; the report's denominator
is the pinned observed catalog, not independent proof of a complete NBA season.
`--game-ids` restricts a deliberately selected population. Missing keys are
unresolved qualification keys: inspect their errors and repair contradictory
existing evidence before requesting new sources. They imply neither DNP nor
permission to acquire/publish data.
The existing LeBron structured request is the retained17-game dependency after
the three formerly staged reports were published. Qualified exact-game states
across this population avoid assuming tenure from roster snapshots.

After a collection within the standing bounded authority, `python -m tools.stage_participation_collection`
accepts `--request-path`, `--source-directory`, new `--work` and `--output`
directories, and `--candidate-sha`. It performs no acquisition or publication.
The source directory contains retained `sources/` originals and `sources.json`;
exact pinned URLs, Git blob/SHA256 hashes, capture times and the requested file
set must match. The existing structured qualifier replays every game against
manifest-bound canonical inputs. Existing availability cells, import lineage
and stronger PDF clock authority survive unchanged. The exported append-only
overlay and `validation.json` remain development staging until independent
checking, required consumer execution and separately protected publication.

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

When the laptop route is appropriate, Codex supplies the bounded request and exact collector parameters. The laptop
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

### Bounded 2026–27 quarter source diagnosis

The standing collection authorization covers this existing laptop route; no new
collection consent, credentials or service is needed. The archived quarter file
contains zero/unparameterized responses, while the correctly parameterized cloud
Traditional V3 request timed out in run41264167626. Do not retry that cloud route
or expand to a season batch without changed evidence.

`tools/collect_rollover_q1_laptop.py` is a standalone acquisition-only helper for
the existing Python/`nba_api` installation. Copy just that reviewed file; an NBA
Tools checkout or development environment is unnecessary. It makes at most two
requests: Traditional V3 and Advanced V3 for game0022600001, Q1, fixed reviewed
parameters. Each endpoint has one attempt,30-second timeout and2MB body cap,
standard SDK headers/session, no redirects or alternate hosts. The retained
Summary oracle is Detroit27/Boston28 with60 team-minutes per side; full-game,
all-zero, conflicting player/clock and invalid-rate responses cannot qualify.

```bash
python collect_rollover_q1_laptop.py --output rollover-q1-capture
```

Transfer `rollover-q1-capture/collection.zip` through the existing data-only handoff,
including when the command fails. The ZIP retains original response bytes (or
failure diagnostics), exact parameters, SDK version, UTC capture times and hashes;
it uses the existing20MB/100MB/2000-file bundle limits and contains no executable,
request/response headers or credentials. It remains unvalidated development data
and never establishes canonical period acceptance or production authority. Codex
qualifies the returned originals in the cloud before any larger bounded request.
No batch-manifest or automatic expansion is included.

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
collection; each collection still needs its own data qualification and independent checking; production publication still requires separate owner approval.

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

### Luka and Reaves participation staging, November 1

The retained development overlay closes both Lakers 2025–26 observed regular-season
populations: Luka Dončić 64 played/18 explicit nonparticipants (9 home), Austin
Reaves 51/31 (13 home), each 82 known games and zero unknowns. It answers Lakers
records with LeBron playing while Luka did not play (7–4, 116.818 PPG), or Reaves
did not play (15–10, 116.720 PPG), through natural, structured and local API routes.
These are staged results; production still uses the existing 775-object generation.

The generic stager authenticates a single Traditional/Summary pair per game and
qualifies every requested player, including shared-game targets. Thirty retained
pairs contribute 1,053 rows. The February 1 official NBA gamebook contributes
17 Lakers rows through the existing cached, team-scoped importer. Two archive
originals for that game remain quarantined because a `28:60` clock fails validation;
the independent gamebook literally reports `29:00`. No clock is silently repaired.
The combined 1,070-row append preserves all 804 prior current-season cells, 146
other-season rows and existing core files. The 94-file overlay exports no test
inventory or claim of full season-pipeline qualification.

[Required staging acceptance](https://github.com/Bet-Zero/nbatools/pull/564)
binds run 41273502501, one selected/executed/passed required test and zero skips.
Its original ZIP, source bytes, failed archive qualification and independent
checks are retained beside the receipt. Production publication needs separate
approval; this overlay does not supply missing 2026–27 season data or restore readiness.
