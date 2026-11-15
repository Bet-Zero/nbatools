# Bulk team-membership qualification sample

November 14, 2026 (Detroit). This is isolated source assessment, not accepted
tenure, production data, Core-1 expansion or league-wide feature completion.

## Result

The reusable offline tool `python -m tools.assess_team_membership` reconstructs
the conditional history for both **2023-24 Lakers and Rockets**, using whole-team
sources rather than player-specific collections. It automatically reads the
frozen PDF's team columns, including inactive/two-way lists, resolves IDs without
using season rosters as tenure, normalizes the native dated movement feed, and
checks every retained regular-season game. Original bytes and prior work remain.

The two sources do **not yet establish complete accepted membership**. The report
always exports zero accepted intervals and no verified missed-game total. Its
conditional model explicitly assumes complete, accurate inputs; actual exact-game
facts stay separate. Do not interpret its conditional nonmembers as certified
nonmembers or its missing participation cells as DNPs.

| Observed population | Lakers | Rockets |
| --- | ---: | ---: |
| Canonical regular-season games | 82 | 82 |
| Listed opening names / two-way names | 17 / 3 | 18 / 3 |
| Candidate identities: opening + changes + appearances | 21 | 22 |
| People with canonical appearance rows | 21 | 17 |
| Scoped membership changes | 7 | 6 |
| Conditional member / nonmember / unknown game-person cells | 1420 / 300 / 2 | 1394 / 246 / 164 |
| Exact-game positive-minute membership facts / unknown cells | 867 / 855 | 880 / 924 |

Candidate-population totals are **not a complete league player denominator**.
The remaining actual membership cells need dated evidence or qualified exact-game
lists, not inference. Four canonical zero-minute rows remain unknown under the
existing positive-minute rule. Prior qualified availability imports and PR619's
278 staged whole-game rows are unchanged and not included in this report's
appearance-only counter. Reuse PR619 for explicit game-day observations; that
process does not close continuous membership gaps.

Independent whole-team tally found 15 relevant source rows: 13 membership changes,
one conversion and one draft-only entry. Every played identity is explained by
the enumerated source population; no contradictory positive-minute appearance was
found. The five Houston candidates without appearances are Adams, Oladipo,
Hudgins, Days and Robinson-Earl. They deliberately remain distinct: Adams/Oladipo
are a trade without Houston appearances, Hudgins is an opening conflict, and
Days/Robinson-Earl have pre-opening waivers, not inferred season membership.

## Exact remaining gaps and a finite next source step

- **Opening anchor:** NBA's October 23 release claims October 24 opening rosters,
  yet lists Hudgins after the feed's October 23 waiver and omits Hinton after his
  October 23 signing. Both stay unresolved across Houston's 82 games. Days and
  Robinson-Earl were also waived October 23 but omitted from the claimed opener;
  that is consistent, not two extra conflicts. Williams' conversion changes
  contract status, not his team. No silent date relabel or baseline repair.
- **Dated boundaries:** Windler's feed waiver is March 1 while bulk secondary
  records and the Lakers' Giles announcement say March 2. Publication date does
  not settle effective time. The March 1-2 window remains disputed. On March 2,
  Lakers game `0022300869` also coincides with Giles' date-only signing; both
  conditional cells stay unknown. No other sample event falls on its team's
  retained game day.
- **Contract-history closure:** complete transport is not proof of every contract
  event. Whole-team secondary histories corroborate the sample event identities
  but their original bodies/coverage are unqualified. This sample has no ten-day
  signing. The captured NBA feed has five types (Signing, Waive, Trade,
  ContractConverted, AwardOnWaivers) and no explicit expiry type; the tool leaves
  a ten-day contract's end unresolved rather than calculating it.
- **Historical bounds:** retained feed spans **2015-07-01 to 2026-11-13**. It does
  not cover 1996-97 through 2014-15, nor prove uninterrupted later coverage.
  Earlier retained boxes can omit injured-list members entirely. The official
  2009 opening roster and Rockets historical guide are useful bulk leads, but
  their bounded native requests returned 403; no retries were made. The guide's
  indexed team-season chronology explicitly includes ten-day expirations and
  no-appearance transactions, so that source family can supply evidence the
  static feed lacks once a frozen native archive is qualified. A season roster
  or first/final appearance cannot supply it.

**Next practical step:** obtain one bounded, frozen season-final team chronology
or game-notes archive for these two teams, with explicit opening corrections,
contract changes and effective dates; retain its native body and compare its
whole-team event population to this report. Then qualify the uncontested dated
segments through the existing membership contract. Older guide/roster archive
coverage is a separate bounded source gap, not a player-by-player exception list.
No historical backfill, production publication, new service/cost, permission
expansion or automatic refresh has occurred.

## Custody and reproduction

`originals.zip` SHA256
`60a17134030c73ea0cf76233ca790bbd6d2e5c62265fdd4110e9918f0ee66ade`
contains the original PDF (176,609 bytes), complete native JSON (4,286,543 bytes),
and `sources.json` with exact URLs, hashes, HTTP status and capture times. The
official release is retained from the newspaper's frozen mirror; NBA's article
links mutable current team rosters and is not a historical baseline.
Archive retrieval time is not the original NBA capture time or freshness proof.

- First fixed five-source diagnostic: code `6295ad75`, request `670f755c`,
  [run43678627453](https://github.com/Bet-Zero/nbatools/actions/runs/43678627453).
  Three sources returned 403; movement returned 200 but exceeded 4 MB and stayed
  `complete=false`. These were diagnostics, not numerical membership acceptance.
- Measured size justified one 16 MB feed request: code `1babfcb6`, request
  `bc42bfd1`, [run43679122388](https://github.com/Bet-Zero/nbatools/actions/runs/43679122388).
  Full JSON SHA256 `27f33ea01008038b987b31056be05ff087bc4a363957d476fcd5053e83c5aa8b`.
- Original-body transfer read only those pinned GitHub artifacts, without another
  NBA request: reviewed code `2a98f6a4`, request `70a090c0`,
  [run43679808260](https://github.com/Bet-Zero/nbatools/actions/runs/43679808260).
  Both source hashes were rechecked locally after transfer. The first transfer
  request `fd037029` had a malformed SHA and was rejected before credentials or
  tests in run43679696281; it is not a passing acquisition.

Unzip originals into a new scratch directory, then run:

```sh
python -m tools.assess_team_membership \
  --request working/nba-tools-completion-program/source-evidence/team-membership-20261114/sample-request.json \
  --sources work/membership-originals \
  --games <pinned-generation>/raw/games/2023-24_regular_season.csv \
  --appearances <pinned-generation>/raw/player_game_stats/2023-24_regular_season.csv \
  --output work/new-membership-report.json
```

The request binds the published generation/manifest and exact relevant canonical
file hashes. Output creation refuses an existing file. The CLI has no acquisition,
publisher, refresh or runtime-import path. `sample-summary.json` omits detailed
game-person cells; the targeted test retains the full report in its artifact.
`independent-oracle.json` and the three source-stage review receipts preserve
their literal review scope. Final review and focused R2 replay are recorded in PR621.
