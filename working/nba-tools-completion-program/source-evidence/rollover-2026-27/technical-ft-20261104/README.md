# Retained 0144 technical free throw qualification

Unpublished continuation from merged PR577/main d0b970db. The sole active queue
remains the completion-program Resume checkpoint. This package reuses all1,537
successful direct request identities and the retained immutable originals; no NBA
or archive body was acquired, no successful request was repeated, and no laptop
capture, new permission, credential, spending or production write was needed.

## Implemented and exercised

`tools.qualify_technical_ft` separates exact elapsed lineups, foul-time scoring
credit, offensive plays and possessions. It qualifies only retained game0144
Q1/Q2/H1. The technical FT168 links uniquely to foul162 at06:54 and contributes
Johnson's point/FTM/FTA without consuming a new play. FT186 and its made FG182
are one and-one play; FT points use foul183's lineup. Q1 FT55 similarly credits
the lineup before substitution54. No event, clock, player identity or event order
is changed. Literal same-clock elapsed lineups remain distinct from this credit.

Own offensive rebounds start another play in the same possession. Nonfinal FT
misses' dead-ball rebounds do not. The terminal Heave236 closes a play without a
player FGA, and team rebound237 starts the unfinished final play. Exposure needs
positive elapsed time or relevant scoring credit: zero-time outgoing Landale at
174–175, and Q1 Mobley/Harden at82–89, do not gain an extra offensive exposure;
the pre-technical outgoing Atlanta lineup does retain its scoring credit.

All55 positive-player Q1/Q2/H1 observations independently qualify USG, AST%,
REB%, turnover ratio, offensive/defensive ratings and plus/minus. The implementation
requires all four imported rates, personal nonshooting counts and plus/minus to
match the independent event model; it separately checks offensive rating.
The independent checker also replays defensive ratings. Reported possessions
are corroboration only. Tests changing all reported possessions to999 leave
independent ratios unchanged. This bounded evidence is not general NBA credit
acceptance and does not rewrite any reported Advanced rate or TS observation.

The existing entire-vector clock copy and unchanged importer append0144Q2/H1.
Only eight shooting/percentage fields per window change in explicit copies:
Johnson and Atlanta PTS/FTM/FTA/FT%. Team and player plus/minus remain unchanged.
Atlanta scores30–16 inQ2 and46–47 inH1. The real finder returns Johnson3PTS and
TS75/122 inQ2,5PTS andTS125/272 inH1. All prior raw files remain byte-identical;
both period CSVs preserve their entire literal prior prefixes. Coverage is now
645/647known windows. Existing TS, usage and six-of-seven precision evidence is
reused from PR577, not recomputed as another acceptance exercise.

## Remaining source and numerical obligations

| Source family | Exact current result | Remaining requirement |
| --- | --- | --- |
|0144Q2/H1 | Both windows imported,55 positive-player rate/credit controls qualified acrossQ1/Q2/H1 | Closed for this retained stage; reuse these originals and ledgers. |
|0142Q3/H2 | Martin375 uniquely supplies+2PTS/+1FGM/+1FGA. Washington is recorded exiting343 and again368. Independent counterfactual witnesses show either Sasser or Risacher could exit368 while all later substitutions/on-floor actors remain consistent | A qualified same-game record distinguishing the outgoing player/complete on-court intervals, plus complete positive-player Advanced rows or independently qualified rates. Existing Q3 omits Martin; source time224Sasser/544Risacher/0Martin cannot resolve the ambiguity. Do not choose a witness or fabricate his rate row. |
|0142timing witnesses | Hypothetical Sasser exit gives102Sasser/544Risacher/122Martin seconds; hypothetical Risacher exit gives224/422/122 | Hypotheses only, not admitted corrections. All originals preserved. The ambiguity affects bothQ3 andH2 rate/clock requirements. |
|Broader period/count basis | Original86conflicts/19games ledger remains intact.0144's three discrepancies close. Current106complete-game sums have80conflicts/17games, and0142's three original shooting obligations remain outside that complete-game comparison | 83known original obligations remain, not80and not six resolved. Counts/rates require source-family qualification before numerical acceptance. No accepted canonical or period cell is overwritten to force agreement. |
|Advanced and precision | PR577's448player/30team original-basisTS,10bounded0116usage cases and6exact minute boundaries reused | General possession/usage and full numerical coherence remain open.1642854still needs missing0160exact PBP or another qualified exact timing source. |
|Schedule and all11raw/5processed | Fresh directory metadata still identifies retained schedule bloba79d57a… at97d4ff2…; source body reused. Fresh exact due IDs:107with0whole-row gaps under unchanged24-hour lag. All5builders execute;14required structural records pass and2periodcoverage records fail | Missing0142windows mean48player keys/4team keys. Full numerical/R2/readiness acceptance stays false; repeat due-ID freshness at eventual acceptance. |

## Reproduction and evidence

Seed `SourceCache` once from the retained Q1, partial, recovery and incremental
collection ZIPs (or reuse the authenticated returned-run cache). Run:

```
python -m tools.qualify_technical_ft --cache <cache> --output <fresh-stage>
```

This runs the real importer, all five processed builders, structural assessment
of all16required datasets and actual finder consumers; it performs no acquisition
or publication. The original uncorrected windows must still fail the unchanged
Summary score check. Normalized derived TS comes from qualified counts, not a
modified source TS. Failed full validation remains explicitly recorded.

`qualification-evidence.zip` retains all16staged datasets, source hash/field/clock
ledgers, play/possession intervals, actual consumers and all required assessments.
`independent-review.zip` retains separate checker oracles, the two0142 ambiguity
witnesses, review and focused verification. `count-coherence.json` and its archived
reproduction script bind the complete-game diagnostic; the original86ledger is
unchanged. `schedule-recheck.json` retains exact due IDs and metadata reuse.
`receipt.json` binds reviewed code, source/evidence hashes and test results.

Production remains availability-lebron-season-v1-20261031; no R2 object, active
pointer, publication, recovery, readiness waiver or deployment changed. The
separate publication approval remains required. No K08/K12 work occurred.
