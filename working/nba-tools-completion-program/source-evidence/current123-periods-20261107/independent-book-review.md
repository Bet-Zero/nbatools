# Independent game184 scorer and rebound-rate qualification

Reviewer: `/root/current123_period_source_review`, a separate Codex checker. Backend model identity is unavailable; no other reviewing model is claimed. **APPROVED** the eight explicitly keyed canonical count corrections and the 38 independently derived Q2/H1 REB% values below, with original bytes and prior versions preserved. Final v5 remains subject to independent cell-delta comparison, affected consumer checks, exact-head CI and the existing production isolation. This is not publication approval.

## Original source and identity

The original PDF has 152,520 bytes and SHA256 `5d11d1974ca1426afda19575cc9a8af316d5a9471f26ced48f8470bbaf830b2b`, with 20 pages. Independently verified the exact captured receipt: one HTTP200 attempt, no redirects, matching declared Content-Length, matching raw/body hashes, game0022600184 and request8ae14a5d. The URL is `https://statsdmz.nba.com/pdfs/20261104/20261104_DALSAS_book.pdf`. Every page identifies Wednesday, November4,2026 in SanAntonio; the final scorer report shows Dallas111away/SanAntonio112home, matching the separately retained Summary identity.

The original artifact/capture remains separate and immutable. NBA hosting and a literal scorer/PBP report establish the applicable field-specific authority, not a proven different upstream observer. No new USG/TOV/free-throw award methodology or old DQ001–003 investigation was undertaken. The checker made no NBA requests or production writes.

## Exact missing defensive rebound

Zero-based scorer page02 shows P.J.Washington's Q2 OREB0/DREB1/REB1 and Dallas OREB2/DREB6/REB8. Page03 shows his H1 OREB2/DREB2/REB4 and Dallas OREB9/DREB11/REB20. The returned period sources instead omit exactly that one defensive rebound: playerQ2 0/0, playerH1 1/3, teamQ2 5/7 and teamH1 10/19 for DREB/REB. Page00 whole totals are Washington4/6/10 and Dallas18/32/50, agreeing with the previously retained whole-game original.

The independently parsed Q2 play-by-play on page12 supplies the missing period allocation without a guess:

1. At05:21 Castle misses FreeThrow2of2.
2. At05:21 Washington explicitly enters for Irving.
3. At05:14 `P.Washington REBOUND` is recorded for Dallas.
4. At05:03 Gafford scores, then Washington leaves for Martin.

This is a literal defensive player rebound after an opponent's terminal missed FT, with the player explicitly on court. It does not require an unknown award credit or foul-time/attempt-time inference. The Q2 and H1 scorer tables corroborate the event, and all quarter/half/whole sums reconcile once that event is included.

The independent scorer parser compared 1,904 numeric Traditional count cells across all six game184 quarter/half sources. **Exactly eight cells differ**, all the declared Washington/Dallas DREB/REB Q2/H1 corrections, each +1. Every other tested count cell agrees. All literal table rows and correction keys are retained in the oracle; no unrelated quarter, player, team, whole-core, season or processed value needs changing.

## Complete dependent REB% proof

The existing accepted count-to-rate dependency policy invalidates REB% for the complete affected windows. The checker independently reconstructed both teams' Q1/Q2 five-player lineups directly from the PDF's literal starters and 37 substitutions, preserving exact event order and fractional clocks. Every player minute total agrees with the quarter scorer table within one second, each team has exactly3,600player-seconds per quarter, every rebound actor is on court, and all player rebound numerators agree with the scorer tables.

There are 74 literal Q1/Q2 rebound events. The existing live-rebound opportunity semantics exclude only the two zero-clock team shells following quarter-ending misses. No positive-clock rebound is omitted or invented. Thus Q1 has38live rebound opportunities and Q2 has34. The oracle retains every rebound, its preceding missed attempt, literal source page/line and both contemporaneous five-player lineups. Missed nonterminal FT attempts that have no rebound row in the PDF do not create a live opportunity or an invented source event.

For every affected player, REB% is the independently counted player rebounds divided by the combined live rebound opportunities while that player is on court. Q2 uses period2; H1 combines periods1+2. This yields **38 exact fractions**, including WashingtonQ2 `1/22` and H1 `4/49`. No denominator is fitted to the reported Advanced percentage. Several original percentages differ under the accepted canonical live-opportunity basis; all 38 affected values are therefore explicitly rederived, including values that happen to remain zero. Every zero has a known positive denominator and literal zero rebound count. No missing source fact is replaced by zero, and no extra unknown is necessary.

The frozen independent oracle is `book-rebound-oracle.json`, SHA256 `7d054703091f5f0334d2b01dd7bd978e619d2e36a11eead390fdb23cf0646698`. Its stand-alone, standard-library original-body parser is `book_rebounds.py`, SHA256 `ca76985b27bc43db95f4d4a17726631271a77c56dc180d8bcff269bfdfd90b26`. It imports no author integration, patching or rate/exposure helper. Its first run exposed a local table-layout assumption of18numeric columns; the actual fixed scorer header has16, and the corrected explicit column mapping reproduces every scorer rebound and minute check. This was a checker-harness correction, not a source or canonical-value edit.

## Candidate correction boundaries

Reviewed `apply_book_correction.py`: it starts from pinned v4 a0ab6f64/93b2b8f8, checks the original book hash/receipt, requires the exact independently supplied oracle hash and every positive denominator, and patches only the eight keyed DREB/REB cells plus 38 complete-window REB% cells. It checks old tokens before changing them, preserves untouched CSV lines/tokens and all other prior files, keeps the old484USG/TOV unknowns intact, writes new correction/structural receipts and creates a new provisional v5. If independent rate proof is absent it withholds affected rates explicitly rather than retaining stale values or inventing zeros.

With all38rates proven, v5 may remove the newly resolved game184 count-basis exception from **its own** manifest. V4, original captured API bytes, original PDF, initial failed comparison/exception and custody failures remain retained as history. DQ006, old484rate facts, current freshness, original Core-1/deployed acceptance and production approval remain separate and open. The existing strict player-period file guard still refuses reads because of old484unknowns; that refusal is not a successful positive. No all-snapshot numerical or production acceptance is approved here.
