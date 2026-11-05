# Typed foul-anchor qualification

Continuation from merged PR580/main `ee949ed5`. The exact starting 27-group,
664-key dependency ledger is preserved in `dependency-ledger.json`, with each
original group mapped to its current result, source hashes and shared dependency.
The only active queue remains the completion-program Resume checkpoint.

This package qualifies **110 additional rates in five complete groups** from
retained originals: **68 TOV and 42 USG**. Total qualification is now **811 of
1,365**, with **554 unknowns in 22 groups**. All 701 earlier qualifications are
exactly preserved. No source body was acquired or repeated.

| Statistic | Previously qualified | Gained | Qualified now | Unknown now |
| --- | ---: | ---: | ---: | ---: |
| AST | 226 | 0 | 226 | 38 |
| REB | 277 | 0 | 277 | 52 |
| TOV | 112 | 68 | 180 | 206 |
| USG | 86 | 42 | 128 | 258 |
| Total | 701 | 110 | 811 | 554 |

## Common rule and complete-group application

Foul eligibility precedes uniqueness. An explicitly typed technical FT belongs
to its technical/defensive-three-second award. Ordinary numbered attempts exclude
Technical fouls; a nonpenalty Personal foul cannot explain an ordinary multiple
attempt award. Unsupported retained-possession types remain candidates/blockers;
they are never filtered away to manufacture uniqueness. The existing ownership,
exact same-clock/order, full ordinal sequence, and-one and dead-ball rebound
checks remain mandatory. Multiple eligible anchors still reject the group.

In 0118 Q1, Personal9 lacks penalty evidence, while Shooting10 uniquely explains
ordinary attempts11/12. This establishes Q1 and H1 TOV/USG: 84 observations.
In 0138 Q3, Technical365 explains technical attempt366, while Shooting364
explains ordinary attempts367/369. The separate technical award adds no ordinary
trip. Together with the qualified Q4 count basis, this restores 26 H2 TOV values.
H2 USG still fails the independent Q4 on-court requirement.

TOV retains the independently established numerator and FGA + ordinary non-and-one
trips + personal turnovers + assists denominator. USG retains its independently
replayed positive-duration/scoring-credit offensive-play denominator. Complete
whole-game and canonical count vectors, complete affected window inputs, positive
player membership and clock vectors must pass where the statistic depends on
on-court exposure. TOV does not depend on an on-court denominator; no Q4 lineup
is silently accepted by its restoration. No reported rate or POSS is an oracle.

## Evidence limit and precise remaining dependencies

| Shared source/interpretation | Groups | Unknown values | Exact missing evidence |
| --- | ---: | ---: | --- |
| 0009 Q1/H1 scoring chronology | 2 | 38 AST | Independent corrected scoring sequence/clocks. Action91 literal27–30 differs from event prefix22–25; Q1 end121 literal26–30 differs from27–32; Q2 start122 changes to27–30. These are scoring/cross-clock contradictions, outside the accepted same-clock nonactor replay rule. |
| 0091 Q4/H2 take/flagrant awards | 4 | 48 TOV / 48 USG | Statistical trip/use/exposure treatment for retained-ball take294 plus corrected attempt types/ordinals for three blank-subtype Q4 FTs401/403/404 after foul399. H2 needs both dependencies. |
| 0118 Q4/H2 canceled trip | 4 | 42 TOV / 42 USG | Complete violation/award record for MISS1of2 action524 followed by LaneViolation turnover526 without2of2, and authoritative joint trip/turnover credit treatment. |
| 0121 Q2/H1 take award | 4 | 58 TOV / 58 USG | Statistical trip/use/exposure treatment for PersonalTake151 and1of1 FT152 with retained ball. |
| 0121 Q4/H2 flagrant award | 4 | 58 TOV / 58 USG | Statistical trip/use/exposure treatment for Flagrant566 and explicitly typed attempts568/569 with retained ball. |
| 0138 Q4/H2 on-court identity | 4 | 52 REB / 52 USG | Tshiebwe exits432 at6:55, rebounds481 at3:04 before recorded entry482 forSheppard. Independent identity/order evidence plus complete clocks and exposure; no same-clock event reorder is presumed. |
| Total | 22 | 554 | Every individual key and exact shared dependency survives in the ledger. |

Ball retention is observable. It does not independently define whether awarded
FT sequences are included in statistical trip/use credit, or which lineup gets
credit. Aggregate counts cannot distinguish those alternatives. Required next
sources are attributable NBA/scorer/provider statistical-method clarification,
and corrected detailed same-game gamebook/PBP or synchronized video for incomplete
or contradictory event sequences. Use the existing approved acquisition-only
handoff; qualify any returned originals before implementation. No confirmed
retained/public statistical-definition source resolves these answers. Do not fit
coefficients to reported rates/POSS or replay unchanged sources.

0142 remains a **separate** known evidence gap. Existing independent witnesses
still allow either Sasser or Risacher to leave when Martin enters at Q3 2:02
(action368), after Washington already exited at3:44 (343). Its three shooting
counts remain proven but unadmitted; Q3/H2 still need complete positive-player
clocks/rates. Reused archive discovery at `2b57bdea` found no2027gamerotation and
only season aggregate lineupviz, so no directory/PBP capture was repeated.
A specific independent acquisition target is official OKC-at-DAL October28 video
covering Q3 3:44–1:00 and showing Dallas's five players before/after the2:02 entry;
a genuinely independent same-game rotation/gamebook naming the outgoing player
would also qualify. No available body or confirmed obtainable public URL has been
established. This is a conditional source target, not a solved acquisition.

## Reproduction and readiness

Frozen semantic candidate: `c55a4a590fc1caee52be11b96595461cee59a9d8`.
The 15 focused author tests pass without skips, including preservation and hostile
competing shooting/penalty/unsupported anchors. Independent review/oracles are
bound by `receipt.json` and `independent-review.zip`.

The fixed validation population reuses PR580's exact 107 due IDs and historical
cutoff **2026-11-05T06:59:31.715470Z**, with unchanged24-hour lag and zero whole-row
gaps. This is not a claim of current production freshness. Refresh authenticated
schedule metadata/body as needed and exact24-hour due IDs before full readiness
acceptance. Reproduce the same population without network or production writes:

```python
from datetime import datetime
from pathlib import Path
from tools.qualify_period_rates import qualify
qualify(Path("work/foul-anchor-replay"),
        now=datetime.fromisoformat("2026-11-05T06:59:31.715470+00:00"))
```

`qualification-evidence.zip` retains all16 staged datasets, event exposure and
exact811/554 accounting. All11 required raw and5 processed requirements were
reassessed after the substantive change: **14 structural passes, two period
coverage failures (48 player /4 team keys),645/647 windows**. Every undeclared
CSV token and all15 other dataset files are byte-identical, including allfive
processed files and their unchanged inputs; accepted builder evidence is reused.
Structural passes do not establish full numerical readiness.

Stop at this independently verified checkpoint/external dependency. Next acquire
the missing shared credit specification and narrowly distinguishing event/identity
records; do not start another unchanged-source investigation loop. Full numerical,
R2, readiness and production acceptance remain false. No production publication,
pointer, deployment, safeguards, spending, credentials, permissions, K08 orK12
change is authorized or performed by this package.
