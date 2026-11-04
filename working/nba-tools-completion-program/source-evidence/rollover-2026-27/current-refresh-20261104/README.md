# Current-season staging and reusable acquisition — 2026-11-04

This is an **unpublished, incompletely qualified** 2026–27 Regular Season stage.
It advances merged PR574 (`0d6758b1c432a3ac8bb210338464ddf158a227f4`), without
changing production, its active pointer, the 24-hour requirement, or K08/K12.
The completion-program Resume checkpoint remains the sole active queue. Follow
the task PR's final receipt for candidate, independent review, CI and merge SHAs.

## Verified progress

- The exact 24-hour population at **2026-11-04 05:51:04 UTC** is **107 due games**.
  Whole-game rows are staged for all107: 2,413 player rows and214 team rows.
  This closes the prior15-game whole-row gap (0158–0172), not full qualification.
  Fourteen new whole Traditional bodies corroborate the new primary counts;
  whole0172 has an invalid literal clock and stays quarantined. Its new primary
  context remains unaccepted pending the first direct whole0172 request.
- Existing accepted88 game cells and their literal player CSV prefix remain
  unchanged. All prior originals remain unchanged. Four later partial contexts
  were never fully accepted: in **0154 only**, 14 explicit player `plus_minus`
  changes now reconcile to both the retained, validated whole source and all four
  already admitted quarter sources. All other prior92 core cells are unchanged;
  the exact before/after/source ledger is in the assessment. Earlier549 period
  windows retain their literal CSV byte prefixes.
- **0097 Q4/H2** now pass the unchanged importer. Independently replayed complete
  event chronology establishes the entire subsecond clock vector, including
  8:16.5 rather than rounded8:17 for Anthony Davis. Both endpoints' copied input
  clocks are refined; every count/rate/identity cell is unchanged. No selective
  residual shaving or wider tolerance. The original two failures remain retained.
- **0111 has four periods**: both Summary arrays, all527 retained PBP events and
  final131–122 agree. Its raw Summary header5 remains preserved. The adjacent final
  redundant period-end event differs only in IDs/video metadata; both events stay
  present. This is qualified period metadata, not general canonical PBP acceptance.
- All **11 raw /5 processed** datasets were materialized and assessed. All five
  existing processed builders execute. **14 dataset records pass** structural,
  trust and coverage checks; both period datasets fail. The earlier pre-build
  raw-validation failure also remains in the report. Actual finder consumers
  return the repaired Davis quarter and a new0158 whole-game result.

## Unfinished source obligations

There are **647 known required period windows**, **551 admitted**, and **96 known
missing**. These include four score-quarantined windows (0142 Q3/H2 and0144 Q2/H1),
0128 OT, 90 regulation windows for0158–0172 and0165 OT. Game0161's Summary is absent
from the archive; its first direct Summary can increase that denominator. Missing
player OT participation is unknown, never filled with zero rows.

All retained disjoint original quarters/available OT were compared against the
staged whole counts, including original quarantines: **86 integer disagreements
across19 games** remain. Those originals are not silently promoted. PBP confirms
accepted Boozer16PTS/Coward15PTS in0118, Caleb Martin's missing Q3 basket in0142,
and Jalen Johnson's missing Q2 free throw in0144. It does not supply a safe full
Advanced replacement. Contradictory0142 substitutions also prevent unique clock
reconstruction. `period-basis-deltas.json` records every conflicting cell and
source hash; the alternate RangeType2 requests isolate the filtered-source basis.

At the same107-game scope, reported NBA Advanced has **12 TS disagreements**,
**11 MIN comparisons outside the existing serialized comparison**, and **six
unresolved rounding boundaries**. A boundary comparison is not proof of the
underlying real clock. Player population/GP and all448 W/L records reconcile.
The staged version explicitly derives TS from preserved game PTS/FGA/FTA and
minutes-per-game from preserved game-minute tokens. Original reported values,
explicit basis columns and exact-rational derivation ledgers remain beside them.
This delivers a coherent computed basis, not a claim that reported NBA sources
were corrected. Other NBA Advanced fields, including usage, remain unchanged.

Independent NBA usage checking now includes a real no-FTA/no-OREB quarter with
event-derived numerators, lineups and end-action opportunities: **four ratios
match, six remain unresolved because possession-credit semantics differ**.
Zero-numerator and restricted-denominator checks are separately retained.
Neither using Advanced.POSS as its own oracle nor substituting the familiar
0.44-FTA/minute estimate establishes NBA USG. Full independent usage acceptance,
full snapshot acceptance and production readiness remain **false**.

## One reusable acquisition package

Download **[incremental-acquisition.zip](incremental-acquisition.zip)**, unzip,
and open **Run Capture.command** on the existing acquisition Mac (Windows launcher
also included). Return **readiness-refresh/current-run.zip**, including if the run
stops. **Keep the extracted folder**: open the same launcher for later updates.
No repository checkout, commands, installation, credentials or setup is required.
The launcher discovers the existing working Python/nba_api environment.

The reviewed initial plan has **416 first-time requests** across35 game IDs:
185 missing standard inputs (180 regulation, four known OT responses, one Summary),
228 alternate-range diagnostics (19 games ×6 windows ×2 endpoints), two snapshots
at the current observed cutoff, and the quarantined0172 whole source. All1,121
earlier successful identities (2Q1 +602partial +517recovery) are excluded.
RangeType2 has a narrow fixed19-game diagnostic allowlist and exact time bounds;
successful RangeType1 requests are not repeated. No successful capture was made
again to assemble this package.

The existing approved cloud archive supplies whole-game/aggregate sources but
lacks these filtered period Advanced bodies. The previously diagnosed cloud
Stats route remains blocked, with no changed route or credential evidence.
The already working laptop source is therefore necessary for this bounded gap;
development, qualification and review remain in the cloud.

Each invocation checks the current approved archive schedule and Summary metadata,
retains immutable source bodies, calculates due games with the unchanged24-hour
lag, and collects only missing direct identities. It enforces40 games/500 direct
requests,30-second source timeout,2MB response,32MB archive and12-hour ceilings.
New OT discovered by a first direct Summary can add its pair within that ceiling.
Successful sources survive interrupted runs. Failed/interrupted identities require
cloud diagnosis before retry. This is an on-demand reusable path, not an unattended
schedule or a claim that production now refreshes itself.

Cloud `tools/readiness_refresh.py` seeds authenticated old originals, stages only
changed immutable mirror blobs, plans missing identities and imports the single
returned run archive. Import verifies outer ZIP, reviewed seed binding, nested
collection protocol and original hashes in isolated scratch state before updating
the cache. Duplicate/path-traversal/symlink/size-limit failures leave accepted
cache state unchanged; original outer/nested archives remain retained.
An imported capture still needs source/numerical qualification and a newly checked
due population before acceptance. No collection result auto-publishes anything.

## Evidence and verification

- `current-sources.zip`:42 authenticated originals,41 newly acquired immutable
  bodies and one retained unchanged PBP144; original schedule bytes reused.
  SHA256 `0dfd1bb7dcd9cff467fb110cf888c006266f00c7f02073fa6956e4a0c965ae13`.
- `summary-catalog.json`:106 qualified period metadata entries, one unresolved;
  SHA256 `e03bc219cf7545e6926d004e0d6806726da0066a6e41f08a97dfbc182c462812`.
- `qualification-evidence.zip` and `receipt.json`: all16 staged CSVs, executed
  assessment, copied clock inputs, exact hash inventory and separate checker
  source oracles. These are staging evidence, not publishable production data.
- `incremental-preflight.json` and `incremental-initial-request.json`: initial
  exact jobs, SDK mapping proof, cache seed binding and final package/runtime hashes.
- Root's13 focused real-source/guard tests passed; the refresh author's focused
  collection/cache/import checks and independent frozen review are recorded in the
  final PR receipt. Reused PR574 evidence applies to its unchanged549 admitted
  windows and safeguards; PR574's prior execution is not presented as a new run.

Reproduction uses `python -m tools.stage_current_season --output <fresh-directory>`
in the configured cloud repository. It never writes production storage. The next
step is to authenticate/import the returned run, qualify its sources against these
preserved counts/clocks, resolve the remaining explicit disagreements, refresh the
actual due population, and execute required full validation when supported.
