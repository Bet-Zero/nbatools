# Partial capture recovery — unpublished readiness milestone

The owner's original1698901-byte ZIP is preserved exactly, SHA256
`03ee634189d3f245badbd0baadc60ddaeac4b9efd978c5d2bd62d02aa7d4ceb3`, first pushed
on the dedicated unmerged branch `data/readiness-partial-capture-20261103`, commit
`489933dead602ad75c359a7f90bc165fd2742357`. This implementation selectively retains
the same bytes; it does not blindly merge that staging branch. The original
[verified handoff](https://github.com/Bet-Zero/nbatools/pull/572#issuecomment-6599779395)
is metadata, not a replacement for these original bytes.

## What qualified

The existing safe unpacker and independent checker verified every604 bound file,
605 ZIP entries, the original PR572 request hash and all attempt metadata.602
HTTP200 complete JSON responses survive unchanged:301Traditional,300Advanced,
one Player Advanced snapshot through10/31. One zero-byte30second ReadTimeout
stopped Advanced game0116/Q1;458 jobs were never attempted. No successful request
was repeated. The isolated timeout after602 successes is consistent with a
transient transport failure, not proof of invalid NBA statistics or permanent
route failure. One new explicit attempt after the elapsed cooldown is bounded
and diagnosed; failed requests still never retry automatically.

`python -m tools.qualify_readiness_partial --output work/new-partial-stage`
replays all300 captured pairs plus the accepted original Q1 against51 immutable
Summary originals through the existing period SDK/importer/validators. It admits
**290 windows /6588 player rows /580 team rows** and quarantines11. The orphan
Traditional0116/Q1 remains retained awaiting its Advanced partner. Only observed,
qualified windows are materialized. No raw/processed complete flag is created.
`partial-stage.zip` retains actual raw CSVs and consumer results; every prior
accepted81-game core cell survives and seven retained games are appended as
separate context. This partial period stage is not a coherent full snapshot.

Actual consumers return Tatum's0001/Q4=2PTS on1of5, Boston0001/H1=58PTS/+13;
independent held-out consumers match Franz0114/Q4=21PTS and Murray0024/H2=28PTS.
Naji0095/Q1 correctly stays unavailable. The independent actual replay is in
[actual-replay-review.json](actual-replay-review.json).

## Remaining quality and basis dependencies

[clock-dependencies.json](clock-dependencies.json) records exact source hashes,
players and windows. Nine pairs have invalid literal `:60` clocks;0097/Q4 and H2
have four-second player-clock residuals. Both endpoints repeat these defects.
No carrying seconds, tolerance change, invented timing, automatic recapture or
clock waiver is authorized. All22 original bodies are preserved; HTTP success
is distinct from numerical qualification. These11 windows require changed,
qualified timing evidence or an independently reviewed alternative; the new
transport package does not pretend to supply it.

The returned10/31 Player Advanced response is fully retained, hash
`c53e696f1ba87c1d91039aecf605ae828fb08b26c3b530b6ac58efc83a411961`.
Its441-player GP population matches1990 rows and its TS matches primary88-game
logs for all441 players. It disagrees with accepted corrected counts for the
same12 players, concentrated in seven games0091/0109/0118/0121/0138/0142/0144.
Captured disjoint-quarter counts also match primary rather than corrected values
in41 integer cells across13 games; direct halves agree with quarter count sums.
This is a reproducible filtered-source/whole-source basis disagreement, not an
uncollected or simply stale snapshot. [The exact12-player mapping](advanced-basis-review.json)
preserves every source value. Do not revert accepted corrections or patch raw
TS/USG automatically. Count-only projections from malformed-clock windows are
identified separately and do not become accepted period rows.

## Current population and the one recovery package

[Current92 source review](current92-review.json) independently establishes exact
92 due/final IDs at2026-11-03T09:22:50Z, against the complete retained1206-row
schedule and unchanged24-hour rule. Four new games0154–0157 are due; no new OT.
Fresh originals at mirror123d89ef are in `current-sources.zip`; original source
capture time is not inferred from retrieval/commit time. All442 observed
player-team keys occur in the existing525-player roster projection.

This is not blanket92-game acceptance.0154 primary has only206.75 player-minutes
per side and BOS90/ORL83 points versus final whole/schedule BOS108/ORL97. Its76
integer count cells and15 minute cells conflict with the full Traditional body.
Current Player Advanced minutes match incomplete primary; Team Advanced elapsed
minutes are seven short for BOS/ORL, with the other28 teams matching. New0157 has
literal Collin `19:60`; preserve valid primary clocks and quarantine supplementary
whole-clock admission. Earlier0096/0151 quarantines remain intact.

**Run only [NBA-Tools-Readiness-Recovery.zip](NBA-Tools-Readiness-Recovery.zip).**
Unzip into a new folder and open `Run Capture.command` on Mac (or the Windows
launcher). It checks the existing Python/nba_api installation, active environment
and finitely bounded neighboring `.venv`/`venv` folders; no installation, home
crawl, source choice or command writing. Return `readiness-capture/collection.zip`
even if it stops, and retain the output folder until receipt is confirmed.

The [fixed request](../../../collection-requests/readiness-recovery-20261103.json)
and [build receipt](build-report.json) bind **517 calls**, excluding every one of
the602 successful original requests:

- 459 original transport gaps (the zero-byte timeout plus458 never attempted).
- 48 direct Traditional/Advanced windows for new0154–0157.
- One missing0154 Summary;155–157 Summaries were recovered from the archive.
- Seven first direct unfiltered whole Traditional probes for the12-player basis conflict.
- Two distinct Player/Team Advanced snapshots through11/01, justified by the0154
 partial-clock/count contradiction; the successful10/31 snapshot is reused.

The existing serial, one-attempt,30second/2MB request bounds, minimum1second
spacing,12hour invocation ceiling and20MB ZIP/100MB expanded/2000-file limits
remain. HTTP/JSON/transport failure stops and preserves prior/partial bodies and
unattempted jobs. New collector forms are restricted to exact full Traditional
SDK zero defaults and Summary GameID-only. No full Advanced backfill or alternate
host is added. `reuse-ledger.json` binds all602 originals; original failure remains
failed. Scope extension is independently reviewed, not silently expanded on laptop.

## Stop and exact next checkpoint

Stop after normal review/CI/merge and preservation, awaiting this one package's
output. Authenticate it against the fixed517-job request, merge sources only by
exact request/hash, qualify remaining direct windows, and use the seven probes
and new snapshots to reconcile source basis without replacing accepted cells
silently. Keep the11 timing dependencies explicit. Qualify0154 final core fields
through reviewed per-field evidence; do not admit its partial primary as final.
Then all11raw/5processed datasets, trustworthy receipts and newly refreshed exact
24-hour due IDs must pass before any concrete publication package is proposed.
No production write/pointer change, readiness waiver, new credentials/spend or
K08/K12 work occurred. PR571/572 and LeBron publication/16 live answers/backup
remain applicable historical evidence, not repeated execution on this candidate.

The [final independent review](final-candidate-review.json) APPROVES semantic
candidate3270a9e3e7d9b208ace64b98eb75260e9922e4dc;65focused author checks and65
independent checks pass. All602 successful request URLs are excluded from the
517-job package. Receipt-only descendants preserve the listed executable/input
hashes. Exact final-head CI, post-merge CI and stop state are recorded in
[PR573](https://github.com/Bet-Zero/nbatools/pull/573) and its final receipt.
