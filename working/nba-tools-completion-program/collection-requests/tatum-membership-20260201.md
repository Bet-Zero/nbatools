# Bounded participation collection proposal

This is a proposed collection requirement, not collected coverage, an accepted
feature, or publication approval. No source fetch or production write occurred.

## Smallest useful new acquisition

Collect one complete original NBA Official Final Box PDF:

- Game `0022500702`, Milwaukee at Boston, February 1, 2026.
- Exact GET: `https://statsdmz.nba.com/pdfs/20260201/20260201_MILBOS.pdf`.
- Canonical final score: Boston 107, Milwaukee 79.
- Target: an explicit report listing for Jayson Tatum (`1628369`) on Boston
  (`1610612738`), together with all other source-listed players on both teams.
  If Tatum is unlisted or ambiguous, preserve the report and mark the target
  unmet. Do not manufacture an observation.
- Optional identity-only GET if needed to resolve report-listed names:
  `https://cdn.nba.com/static/json/liveData/boxscore/boxscore_0022500702.json`.
  A failed optional source remains failed; no provider investigation is needed.

`collection-request.json` was generated with the existing
`tools.data_availability.collection_request`, then supplemented with exact
source parameters and acceptance limits. Its required game is absent from
production availability and present in the pinned production final-game catalog.

## Why this one report

The latest production inventory is `availability-opening-s4-v1-20261017`, manifest
`5497832bca4567734386e26367798c60fd6e3685a0c93cd561227a5e5d833f52`.
Its complete inventory bytes match SHA256
`d5f72265f5b7baf113ed25d29c65494cb9f3eb40896073b7a657c687ede16f04`.
Four restored production CSV hashes were independently matched to that inventory;
`production-evidence.json` records those hashes and exact rows.

Production already has the four qualified Boston–Lakers report games:
`0022300403`, `0022300684`, `0022500338`, `0022500823`, plus Warriors–Lakers
opener `0022500002`. These five games total 170 listed availability observations.
They establish neither complete seasons nor every player's membership.

The 2025-26 Lakers-versus-Boston-or-New-York sample comprises the two already
qualified Boston games and New York games `0022500708` (February 1) and
`0022500922` (March 8). The #462 opposing-player positive obligation explicitly
excludes Knicks games from Tatum's missed Boston games. The existing
`listed_player_rows_only` contract cannot establish that exclusion from missing
Tatum rows. Fetching the two Knicks PDFs alone would not solve it.

Boston also plays on both Knicks game dates. On March 8, canonical production
player data already explicitly records Tatum with Boston in game `0022500921`
(27 minutes, 20 points). On February 1, canonical player data contains no Tatum
appearance; that absence is unknown. The requested same-date Boston report may
supply the missing explicit positive game-date Boston association.

This is the smallest acquisition to advance the two-date membership distinction.
It does not itself prove that a different game's observation can be used to
exclude a same-date Knicks game. That requires a reviewed, explicit applicability
contract, conflict checks and consideration of any same-day transfer/time ambiguity.
Do not infer a tenure interval between games or return an accepted answer until
that meaning and its source sufficiency are independently checked. The February
source may also advance bounded one/two-participant K08 samples after its actual
contents are qualified; no outcome is presumed in this request.

All 46 #462 positive absence obligations remain open. The original #462 fixture
obligation `tests/test_c1_availability_words.py::test_team_record_with_an_opposing_player_out`
is not repaired by acquiring a real report or by deleting fixture player rows.
The fixture still needs explicitly stipulated, meaningful membership evidence;
real-data acceptance then uses the qualified immutable production/candidate slice.

## Backup laptop steps

Use the existing acquisition collector to save the exact original bytes under:

```
collected/
  acquisition.json
  sources/20260201_MILBOS.pdf
  sources/boxscore_0022500702.json  # only if collected
```

Record exact URL/parameters, timezone-qualified capture time, status/error and
coverage limits for each attempted source in `acquisition.json`. Preserve
`source`, `captured_at` and `parameters` at its top level for the bundle helper.
The helper generates file SHA256/size bindings. Retain original bytes; no PDF
reconstruction, derived CSV substitution, artificial IDs or medical inference.
No NBA Tools install, R2 credential, source research or application build is needed.

```
python collection_bundle.py create collected --request collection-request.json --output collection.zip
```

This copy of `collection_bundle.py` is byte-identical to the reviewed repository
helper. It uses Python's standard library. Stage the ZIP on a data-staging branch
or the established cloud handoff. Do not upload executables inside the collection,
credentials or `.env`. Original profile HTML cannot pass this helper's current
CSV/JSON/PDF allowlist; keep unresolved profile-only identity as a cloud blocker.

## Cloud handling and current collector compatibility

```
python -m tools.collection_bundle unpack collection.zip --request collection-request.json --output work/tatum-membership-20260201
```

The existing source-report importer understands this exact game and derives the
same report URL when called in the cloud with the pinned complete catalog:

```
nbatools-cli pipeline backfill-game-availability --season 2025-26 --season-type 'Regular Season' --source report --game-id 22500702 --limit 1
```

That is a parameter reference, not a laptop command or an instruction to refetch
upstream in the cloud: the current report importer always fetches its PDF and has
no `--cached-report` option (`--cached-boxscores` supports Stats JSON only).
Cloud processing therefore needs a bounded, independently checked retained-report
input seam before replaying the laptop bytes offline. Preserve existing report
parsing, game/date/team/score validation, exact played-identity and minute checks,
DNP/inactive parsing, import receipts and source hashes. Do not evade source
qualification by populating a membership row from a roster snapshot.

Merge any proposed result into a full isolated copy of the existing generation;
never replace its season CSV with this one game's rows. Qualify every listed
identity, both final scores, source date, retained provenance and all actual played
minutes independently. A received ZIP stays staging. Normal review, required
checks, registered immutable package validation and separate owner-approved
protected publication remain required.
