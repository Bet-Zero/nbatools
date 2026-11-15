# Independent coverage research (2026-11-14 Detroit)

Checker: separate Codex session `/root/coverage_checker`. Read-only source analysis;
no canonical data, runtime code, gates or production pointer changed. NBA originals
were read as JSON dictionaries directly, without application normalizers. New
bounded captures: 14 bodies for seven game IDs, with hashes, URLs and UTC retrieval
times in `transaction-probes/captures.json`. These are archival research observations,
not new source freshness, accepted publication data or a backfill.

## What exact-game sources can recover

Traditional V3 names played players and explicit DNP/DND rows. Summary V2's
`InactivePlayers` adds identities not present in Traditional. Each positive row
is dated team association and participation evidence for that game. Neither an
omission nor a row count proves nonmembership, and no season tenure is inferred.

Independently checked controls outside LeBron/Davis/Reaves/Tatum cohorts:

| Category | Native source observation | Independent check |
| --- | --- | --- |
| Actual opening absence | LAL-DEN, Oct 24 2023, game `0022300061`: Jarred Vanderbilt `1629020` explicitly inactive for LAL. | [Official final gamebook](https://statsdmz.nba.com/pdfs/20231024/20231024_LALDEN.pdf) names Vanderbilt inactive. |
| Actual ending absence | LAL-NOP, Apr 14 2024, game `0022301195`: Vanderbilt explicitly inactive for LAL. | [Official final gamebook](https://statsdmz.nba.com/pdfs/20240414/20240414_LALNOP.pdf) names him inactive; final record 47-35 confirms 82-game endpoint. |
| Two-way | Same Oct 24 opener explicitly lists Colin Castleton `1630658`, Alex Fudge `1641788`, D'Moi Hodge `1641793` inactive. | Same independent gamebook labels all three G League–Two-Way. G League assignment does not mean NBA contract termination. |
| Trade, no appearances | MEM Jan29 `0022300663`: Steven Adams `203500` inactive for MEM. HOU Jan31 `0022300679`: Oladipo inactive; Adams omitted. HOU Feb2 `0022300692`: Adams inactive for HOU; MEM Feb2 `0022300693`: Oladipo inactive for MEM. | [Rockets Feb1 trade announcement](https://www.nba.com/rockets/news/rockets-complete-trade-with-memphis), [Grizzlies confirmation](https://www.nba.com/grizzlies/news/memphis-grizzlies-complete-trade-with-houston-rockets), and [Feb2 final gamebook](https://statsdmz.nba.com/pdfs/20240202/20240202_TORHOU.pdf) explicitly name Adams for HOU (Trade Pending). No stale traded-player listing found in these checked dates. Jan31 omission remains unknown on its own. |
| Late signing | Retained `k08-direct-dependencies/lal-2023-24` Summary files list Dylan Windler `1629685` inactive Jan13 `0022300549` and Jan23 `0022300618`; Skylar Mays `1630219` inactive Jan23. | Official [Windler signing release](https://gleague.nba.com/news/los-angeles-lakers-sign-dylan-windler-to-two-way-contract), [Mays signing release](https://gleague.nba.com/news/lakers-sign-skylar-mays-to-two-way-contract). Exact transaction-vs-publication date needs reconciliation before intervals. |
| Waiver | Retained Dec21 `0022300380` Summary lists Fudge/Hodge inactive. Later omissions cannot mean misses. | Official [Lakers waiver release](https://www.nba.com/lakers/news/lakers-waive-alex-fudge-and-dmoi-hodge-010624), corroborated by Jan6 entries in the official G League season transaction page below. Windler's Mar2 waiver independently stated in [official Giles signing release](https://gleague.nba.com/news/lakers-sign-harry-giles-iii-to-two-way-contract). No post-waiver absence total accepted. |

Game IDs are not chronological: `0022300001` is Nov3 CLE-IND, not the LAL opener.
That unrelated pair was retained as a diagnostic rather than silently relabeled.

## Counterexample to historical full-roster completeness

Already-retained HOU-DET Nov2 2004 `0020400001` has 12 HOU Traditional players and
zero Summary inactive rows. Bob Sura, Reece Gaines and Andre Barrett are absent
from both lists. The [official NBA-hosted Rockets media guide](https://ak-static-int.nba.com/wp-content/uploads/sites/3/2016/10/2016-17-Media-Guide-Rockets.pdf),
printed page 157, records their placement on the injured list Nov1 2004; it also
records Sura's Aug9 signing. This is independent primary evidence of rostered
nonparticipants omitted by the proposed union. Existing 1997 opener Summary
also has an empty inactive table, without a completeness promise.

Therefore downloading every Traditional/Summary pair is a reusable recovery
route, but is not a demonstrated exact league-wide 1996+ solution. Missing older
injured-list coverage remains unknown.

## Bulk membership source families and their limits

- Official [G League 2023-24 season transaction page](https://gleague.nba.com/2023-24-nba-g-league-transactions)
  provides daily assignments, recalls, two-way additions/terminations and callups
  in one season document. Distinguish NBA contracts from G League returning-player
  rights. It confirms Fudge/Hodge termination Jan6, and has Mays acquisition Jan9
  versus Lakers release URL Jan8. A concrete typo labels Windler's Mar2 termination
  as Knicks; the same-day official Giles release says Lakers. Treat as a supporting
  source with conflicts, not an unquestioned complete ledger. Native HTML retrieval
  from this cloud failed at the proxy (403); diagnostic retained in
  `official-pages/capture.json`. Browser text could be read, but no canonical source
  qualification or retried endpoint is claimed.
- NBA's historical `NBA_Player_Movement.json` is documented by old open-source
  clients as transactions since 2012. No historical native body/completeness was
  established here; do not claim 1996+ or closed-world membership coverage.
- Team media-guide transaction/IL chronologies can cover older injured-list eras
  in bulk per team/season. The Rockets guide provides a real primary counterexample,
  but league-wide completeness and exact inclusive/exclusive date rules still need
  qualification before producing membership intervals.
- The current NBA transactions webpage exposes a loading table in browser text,
  not an inspectable complete historical transaction body.
- An external [open-source availability contract](https://evanz.github.io/nba-lineup-model/data/player-availability/)
  calls Traditional+Summary complete for its 2015+ model. That is a third party's
  assertion and has different availability semantics. Its [opening-roster docs](https://evanz.github.io/nba-lineup-model/data/opening-rosters/)
  explicitly qualify incomplete reconstruction. Do not import either as acceptance.

## Recommendation

Proceed with an offline, game/season source inventory and recovery planner using
all retained Traditional/Summary pairs and existing qualifiers. Report listed
played, explicit nonparticipants, unresolved membership and source conflicts
separately. Keep stronger gamebook evidence and existing accepted cells. This
can recover arbitrary already-listed players without a new NBA download and
without changing query semantics. Plan any later missing-body acquisition by
season/game, with old-era IL and transaction coverage explicitly unresolved.
