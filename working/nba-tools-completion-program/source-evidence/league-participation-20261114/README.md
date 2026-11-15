# League participation source coverage, November 14, 2026 (Detroit)

This is evidence for the focused recovery after merged PR618, not a second queue.
Source base: main `da6ae71657d7c21594bdd429529ffc8184bd6d95`.
The active queue remains the program README. The preceding checkpoint is preserved
byte-for-byte in `../../checkpoint-history-20261114.md`.

## What was retained, and what was excluded

- `pull_player_game_stats` fetches **LeagueGameFinder player season logs**, not
  Traditional box scores. It normalizes played-game statistics and preserves a
  COMMENT field if provided (otherwise blank). Those logs do not supply a
  league-wide inactive/DNP population. The legacy fetch does not retain original
  HTTP bodies. A missing source row cannot be recovered from its normalized CSV.
- `pull_player_game_starter_roles` separately fetches Traditional V3. Its
  normalizer keeps identity/position fields, and `restrict_to_player_game_keys`
  restricts the result to canonical appearance keys. Nonplayers, minutes and
  comments are not retained in the role output; the legacy fetch does not save
  the original body. This is distinct from the core stats producer.
- The newer availability importer already uses **all listed players per game**.
  Traditional includes played and explicit DNP rows; Summary V2/V3 contributes
  inactive identities. The final envelope checks date, finality, sides and scores,
  plus canonical played identities/points. No engine rewrite is needed.
- The last published generation's 449 availability source objects comprise 139
  Traditional originals, 139 structured provenance packets, 119 Summary V3 and
  20 Summary V2 originals, 14 PDFs, 17 report/identity receipts and one HTML body.
  Its 5,155 observations cover 153 games in seven season slices, not the league.
  Counts include all listed players, not only the named acceptance cohorts.
- A scoped scan of named repository JSON originals found 392 distinct bodies,
  234 game IDs and 157 games with Traditional plus Summary. Some are period
  responses, already superseded by stronger PDF authority, quarantined, or
  outside the published catalog. They are **not** 157 automatically usable new
  games. Zipped and hash-named source stores are additional retained material.
- The roster producer uses CommonTeamRoster season snapshots. Its source/output
  have no qualified joining/leaving dates. Season membership, first/last
  appearances and another game on the same date cannot fill that gap.

For local qualification, 712 relevant files were restored from the existing
backup and retained overlays only when their bytes matched the current publication
receipt's `verified_objects`. The reconstructed manifest has exact SHA256
`cde98408f3390e6191da564197fb77ffbc598a3059963cfc21d9f2d7e1a6b366`.
This is a partial local restore of a published snapshot, not a fresh R2 pointer
check or a new complete inventory. The publication's readiness failure is preserved.

## Bulk routes investigated

| Source | Reusable scope | Qualification limit |
| --- | --- | --- |
| Official Traditional V3 + Summary V2/V3 | One pair per game, all listed players on both teams | Explicit rows only. Older injured-list omissions disprove universal completeness. Existing cloud Stats timeouts were not retried. |
| Official Final Box gamebooks | One final report per game, DNP/inactive/two-way labels | Existing importer and stronger clock authority retained. Missing/malformed reports and identity ambiguity remain explicit. |
| NBA CDN live box scores | Native game-level status/played fields; a source family for modern games | Existing cloud block not retried. No new historical coverage or source adapter accepted here. |
| SportsDataverse raw NBA Stats archive | Existing approved pinned game reads; metadata indexes include supported years | Four retained season-index comparisons prove file presence, not body validity or complete inactives. Whole-season JSON bundles also exist (roughly 40–112MB for inspected season assets); none downloaded here. |
| SportsDataverse `nba_stats_game_rosters` release | Small season files of Summary V2 inactive rows, NBA IDs | **Inactive rows only**, despite the name. Checked 2024 CSV: 11,239 rows/1,313 games; all 1,230 stored regular-season game IDs represented. Not a complete roster certificate or qualified importer input. SHA/capture metadata in `bulk-inactive-observation.json`; original season CSV retained in `bulk-inactive-original.zip`. |
| CommonTeamRoster and season roster archives | Bulk season identities | No effective dates; no nonmembership from omission. |
| NBA Player Movement JSON / transactions page | Potential league transaction feed, documented in historical clients since 2012 | No qualified native historical denominator or full supported-season coverage established. Current transaction page loads its table dynamically. |
| Official G League season transactions | Season document with two-way signings/terminations, assignments and recalls | NBA membership differs from G League rights/assignments. Found date ambiguity and a team-name conflict; not blindly ingestible. |
| Official team media-guide transaction/IL chronology | Team/season history, including older injured lists | Useful primary bulk evidence, but completeness and boundary-day semantics need qualification before membership intervals. |

Primary archive documentation checked:
[game-rosters schema/coverage](https://github.com/sportsdataverse/hoopR-nba-stats-data/blob/26a6296dbbd743da71ee30d3e05086726c932d76/docs/datasets/game_rosters.md),
[inactive-only loader](https://github.com/sportsdataverse/hoopR/blob/main/R/load_nba_stats.R),
[raw season bundle metadata](https://github.com/sportsdataverse/hoopR-nba-stats-raw/releases/tag/nba-stats-raw-json).
The game-rosters coverage document reports only 34 games with inactive rows in
1996-97 versus 1,261 known games; absence of an inactive row is not itself a
missing game response, and neither establishes completeness.

## Independent edge checks and counterexample

`independent-findings.md` records the separate checker's native-body and official
gamebook/transaction cross-checks: actual opener/finale Vanderbilt absences;
Adams' MEM-to-HOU trade despite no Houston appearances; Windler/Mays late
two-way additions; Fudge/Hodge terminations; arbitrary inactive players.
The 14 new bounded archive bodies (170,709 bytes) and original capture metadata
are in `boundary-source-originals.zip`; these are research, not published data.
The capture record's file paths describe its original scratch location.

Crucial falsification: HOU-DET November 2, 2004 (`0020400001`) lists 12 Houston
Traditional players and **no** Summary inactives. Bob Sura, Reece Gaines and Andre
Barrett are omitted. The official Rockets media guide independently records
their November 1 injured-list placement. Thus acquiring every pair alone cannot
complete arbitrary-player membership for all supported seasons.

The official G League season page calls Windler's March 2 termination a Knicks
transaction, while the same-day official Lakers/Giles release says Lakers.
Preserve that conflict; do not manufacture a membership boundary from it.

## Small reusable improvement

The existing offline stager accepts `requirement_grain: "game"`, with one
game/date/source-pair requirement per game in a season, no player targets.
It uses the same qualifier, source hashes, exact source set, canonical checks,
append-only preservation and publication rebuild. Each game receipt reports
played/explicit DNP/unknown counts with `listed_player_rows_only` scope.
It refuses already represented games, including one-sided PDF groups.

`game-request.json` recovers **278 rows = 173 played + 105 explicit
nonparticipants**, eight games/eight teams, from 16 originals already retained
in `k08-tatum-2023`. No recollection. The independent checker compared all native
keys/states and all 597 prior CSV rows, not just one target player. This adds
arbitrary players such as Markquis Nowell, Taj Gibson and Seth Curry through the
same input. It can also complete the held Boston/Tatum 2023-24 sample in isolated
staging; it does not publish that sample or complete other player-seasons.

Focused verification is `tests/test_game_participation_collection_real_data.py`
plus the staging/structured unit tests and separate checker controls. No broad
replay, full suite, current-season refresh, cost, publication or pointer change
is part of this work. Exact reviewed revision and hosted validation evidence
belong in the PR and active checkpoint.

## Remaining evidence, without guessing

Recover valid retained pairs first by game/season. Then qualify a small,
representative season source matrix using the game catalog as denominator and
independently checked membership boundaries. Modern explicit game lists may
close many selected keys, but unlisted players still need qualified dated
membership/nonmembership. Older injured-list eras need supplemental bulk team
chronologies or equivalent primary evidence. Reasons are secondary.
Before any substantial historical acquisition, present the exact remaining
season/game bodies, source/coverage gaps and storage/request bounds for approval.
Production publication remains a separate protected approval.

Focused R2 run [43674107752](https://github.com/Bet-Zero/nbatools/actions/runs/43674107752) executed the one required test and passed (zero skips/failures/errors) on request `2c56414f`, parent reviewed code `a9895ea`, against the pinned generation. Official job logs were inspected. Artifact `14146130009`, upload-reported SHA256 `6be1a41d76de0f1dc4585f8c8a3cfc4c2f4d446c12058b7306fe59d80dfec0fa`, contains the overlay; local artifact transfer was blocked by the environment proxy, so no local artifact-byte verification is claimed. The code/data/native originals are unchanged from local verification.
