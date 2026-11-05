# Grouped dependent-rate qualification

This unpublished continuation from merged PR579/main2139b487 closes **701 of
1,365 withheld rate observations** through31 complete calculation/window groups.
The other664 observations in27 groups remain explicit unknowns. These are grouped
statistical dependencies, not664 acquisition requests. The sole active queue is
the completion-program Resume checkpoint.

| Rate | Original withheld | Independently qualified | Still unknown |
| --- | ---: | ---: | ---: |
| AST | 264 | 226 | 38 |
| REB | 329 | 277 | 52 |
| TOV | 386 | 112 | 274 |
| USG | 386 | 86 | 300 |
| Total | 1,365 | 701 | 664 |

## Established calculations

- AST numerator is the verified player assist count; denominator is made field
  goals by teammates while that player was on court.
- REB numerator is the verified player rebound count; denominator is live rebound
  opportunities while on court. Missed nonterminal free throws and qualified
  technical/defensive-three-second dead-ball rebounds are excluded. Separate team
  events never become player rebound credits.
- TOV is personal turnovers divided by FGA, qualified non-and-one FT trips,
  personal TOV and assists combined. The retained NBA `turnoverRatio` is percent
  points; normalized stored values are fractions. No0.44 possession estimate.
- USG is FGA plus qualified non-and-one FT trips plus personal TOV, divided by
  independently replayed offensive-play exposure. Offensive rebounds begin
  another play. Exposure requires positive elapsed on-court time or qualified
  scoring credit; a positive terminal unfinished play counts, a zero-time shell
  does not. Exact pre-substitution lineups own time ending at substitution clocks.

Complete numerator-field vectors are checked against independent whole-game
Traditional and preserved canonical counts, including all identities/zeros.
Every affected window's complete input vector must also agree. AST/REB/USG
require unique on-court identity, complete positive-player membership and complete
clock vectors within the unchanged2-second importer tolerance. Full groups are
qualified before restoring any of their withheld observations. Reported rates
and possessions are never calculation inputs or independent oracles.

The ledger retains every original withheld key, exact numerator/denominator and
fraction, original reported value, restored value or explicit dependency. Of701
restorations,100 differ beyond original0.001 rounding (21AST/61REB/4TOV/14USG).
Every undeclared CSV token survives literally; all15 other dataset files remain
byte-identical. Source originals and accepted count corrections remain intact.
The existing finder consumes the stage, including ReavesQ3 TOV=1/11.

## Remaining groups

0009Q1/H1's38AST values retain the strict scoreboard contradiction; count-only
proof cannot authorize on-court rate denominators. 0138Q4/H2's52REB and26Q4USG
remain blocked by an on-court actor absent from the reconstructed lineup.

0091/0118/0121/0138 retain274TOV and274 additionalUSG unknowns: unsupported
retained-possession foul/FT types, absent attempt subtype, nonunique same-clock
foul anchors, or incomplete/canceled trips. These need distinguishing credit
semantics and complete event support, not player/game patches. The receipt lists
all27 exact groups. No ambiguous trip is assigned a guessed coefficient.

0142 remains separate. Current independent source-directory discovery at archive
2b57bdea finds no2027 rotation directory;2026 contains the prior season, and2027
lineup visualization files are season aggregates without same-game intervals.
No new distinguishing evidence selects Sasser versus Risacher at action368.
Its three Martin shooting counts remain proven but unadmitted; Q3/H2 still need
unique same-game substitution/on-court evidence and complete positive-player
clock/rate support. OriginalPBP was not fetched again.

## Verification and readiness

Reviewed semantic candidate: `aca1d563f5d53891cb8df489f7141d538950ec1e`.
Ten focused author tests passed, including actual finder, complete population,
all-token/all-file preservation, hostile foul semantics, new-clock substitutions
and independently established jump-ball ownership. Separate review evidence is
retained in `independent-review.zip`; its receipt records the actual checker,
revision, independently derived numbers and findings.

All11raw/5processed requirements were reassessed after the rate changes:
14structural passes and two period-coverage failures (48player/4team keys).
Coverage remains645/647. All five processed files and their unchanged inputs
reuse accepted builder evidence; no broad rebuild or repeated full suite was
needed. Structural passing does not certify full numerical readiness.

At2026-11-05T06:59:31.715470Z, the unchanged24-hour lag and authenticated official
schedule give107 exact due games and zero whole-row gaps. A new directory read
at the latest immutable archive revision2b57bdea confirms the retained schedule
blobef4feaa4/4,393,859bytes unchanged; no successful body was repeated. The
original schedule and all sources are hash-bound in the retained prior archives.
No new source body or laptop capture was needed.

`python -m tools.qualify_period_rates --output <new-directory>` reproduces the
explicit copy, event exposure ledger, complete701/664 accounting and16-dataset
assessment without network or production writes. `qualification-evidence.zip`
retains that exact report and all16 staged datasets; `receipt.json` records their
scope and hashes. Full numerical/R2/readiness/production acceptance remains false.
Production publication, active pointers, safeguards, costs, credentials,
permissions, K08 and K12 remain unchanged.
