# DQ-005: evidence-only closeout, blocked evidence

Agent2 session `/root`, branch `codex/agent2-dq005-20261106`, starts from live
main after PR587: `4bd2f799ddeb06544ef2223e56449ec609318dec`.
Investigation version: **dq005-investigation-v1-20261106**. This is an evidence
version, not a qualified corrected dataset. [PR588](https://github.com/Bet-Zero/nbatools/pull/588)
retains the investigation and administrative closeout. Agent1's application
checkpoint is untouched.

The investigation is administratively closed out with **blocked_evidence** retained.
It is **nonblocking for application development**: current canonical team margins
already match final-score arithmetic, no application defect was established, and
no qualified data correction was established. No source statistic, canonical
dataset or production value changes in this PR.

## Complete affected values

| Game | Team | Raw GameFinder PLUS_MINUS | Raw player sum / 5 | Traditional V3 team +/- | Summary V2 scores | Existing canonical margin |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| 0022200138 | SAS | -20 | -100 / 5 | -25 | 101-126 | -25 |
| 0022200138 | DEN | 22.4 | 112 / 5 | 25 | 126-101 | 25 |
| 0022200749 | BOS | 3 | 15 / 5 | 4 | 125-121 | 4 |
| 0022200749 | LAL | -3 | -15 / 5 | -4 | 121-125 | -4 |

The intake's two observations affect **four** team fields. Every played player
in both games was checked:12SAS+12DEN+9BOS+9LAL=42values. Traditional V3 player
values agree with the retained GameLog vector, while its own team values disagree
with player-sum/5. Summary V2 complete period scores agree with final totals and
the separate Traditional V3 team values. The DEN GameFinder minutes241 versus
Traditional V3 team240:00 is also retained; no minutes or player values are changed.

These contradictions exist in the original JSON before local processing. The
exact player-sum/5 agreement supports a shared upstream processing hypothesis;
it does **not** prove the upstream algorithm, missing event, intended alternate
field definition, or technical-foul explanation. The archive paths do not establish
independent upstream generation. NBA's general
[plus/minus glossary](https://www.nba.com/stats/help/glossary?hidenav=true)
describes on-floor point differential, but this alone does not settle an anomalous
endpoint's implementation. No root cause is invented.

## Existing output and dependencies

The unchanged `pull_team_game_stats.run` already calls
`canonicalize_team_game_pairs` and derives plus/minus from paired final scores.
The separate checker actually replayed all four original rows through that
producer: canonical outputs are already-25/+25/+4/-4. It also executed the
existing score-margin helper and schedule-context builder: absolute margins are
25/25/4/4 and all four `one_possession` flags are0. Normalization is not a newly
qualified source correction or proof that every game statistic is clean.

Team margin filters, sums/means, comparisons, stretches/streaks and inferred
opponent scoring depend on canonical team margins. Player-query team context
uses canonical team values; individual player plus/minus remains distinct and
unchanged. Existing team rolling features use points/shooting/rebounds/turnovers,
not this source-reported field. No dataset changed, so no dependent dataset or
cache was replaced and no recalculation is represented as an adopted correction.
No application feature, loader, schema or validator was edited.

## Provenance and independent evidence gap

The original PR587 ZIP remains byte-identical, SHA256
`6e4b06650519da0b9bfc46269fff5e4f0c231949d8922585e7f4590fbac9d6a1`.
Its complete team and player bodies remain in their existing location. Four new
original JSON bodies are retained under `originals/`, without reserialization.
`analysis.json` supplies exact source URLs, immutable archive revision, byte counts,
Git blob IDs and SHA256 hashes. Git blob IDs were checked against connector
metadata. Source: NBA Stats, archived by SportsDataverse/hoopR NBA Stats raw;
archive [license/attribution](https://github.com/sportsdataverse/hoopR-nba-stats-raw/blob/2e44b7c039f104bc6b41a1de494411e83a03714e/LICENSE.md).
Retrieval date is2026-11-06; exact connector retrieval timestamps and original
capture times are not asserted. Body metadata remains verbatim, not freshness proof.

Read-only web discovery found the official
[LAL-BOS scorer gamebook](https://statsdmz.nba.com/pdfs/20230128/20230128_LALBOS_book.pdf),
page0: complete team totals show-4/+4; player entries differ from Stats for ten
players in the expected1point direction. This is a promising **lead**, not retained
native PDF-body evidence. The web tool returned extracted text and no reusable
PDF/screenshot bytes. SAS-DEN PDF candidates returned inaccessible/internal errors.
NBA game summaries, ESPN/Basketball-Reference score pages and the glossary were
discovered only; their upstream independence and native bodies are unqualified.
`sources-investigated.json` records exact routes and limitations.

The historical two-final-box capture runner was reviewed at
`e548f629d038055f84c3b448ed4ec184f2d62ecf`; controlled success and failure checks
made zero network calls. It is **removed from active test execution**: the file
`tests/cloud_dq005_source_capture_real_data.py` is deleted in this closeout. Its
exact original implementation and review remain available in that immutable Git
revision; they are historical evidence, not a runnable test or queued acquisition.
Automatic approval review previously rejected the request-manifest write before
it happened, citing possible new compute costs or credential-bearing execution.
No targeted workflow ran, no PDFs were acquired, and no rejection was bypassed.
The empty `r2-validation/dq005-source-e548f629` branch has no request commit.
There is no pending capture, approval request, acquisition packet or owner action.

## Reopening trigger

Keep DQ-005 parked. Reopen investigation only for one of these concrete changes:

- Newly available attributable original scorer evidence for both complete team
  vectors, or endpoint-specific documentation, establishes whether the raw field
  is erroneous/stale or intentionally uses an alternate basis. Existing extracted
  web text and agreement among shared NBA Stats endpoints remain insufficient.
- A named future consumer actually requires source-reported GameFinder PLUS_MINUS
  or individual player/lineup plus/minus instead of canonical score margins, or
  changes the current paired-score canonical contract. Record the consumer,
  exact affected keys and required field meaning before taking further action.

A restored capture route, elapsed time or unrelated app development alone does
not justify reopening. Independent scorer totals plus intended field meaning may
establish a correction even if the precise upstream algorithm remains unknown.
Any future correction still needs original preservation, complete affected-vector
checks, independent review and a new qualified version. This closeout authorizes
no acquisition and requests no new approval.

## Verification and stop

Run from the repository root:

```bash
.venv/bin/python working/nba-tools-completion-program/source-evidence/dq005-20261106/replay.py
```

Actual NBA retained-byte replay authenticates4newbodies and checks4team/42player
values, complete periods, source relationships and existing canonical output.
Independent `/root/dq005_checker` separately replayed the producer and dependent
schedule calculations. Its actual model identifier is not exposed; no Claude or
cross-model identity is claimed. Review covers the investigation, **not** correction
acceptance. `independent-review.json` and `independent_replay.py` preserve its work.
The original review hashes bind the investigation at
`cd488fc44d0c00a91bd139c192d04e8217cd9b74`; they are not relabeled as a review of
subsequent administrative wording. The closeout review and exact-head checks are
recorded in PR588. Numerical originals, analysis and review artifacts stay unchanged.

Status: **blocked_evidence**. Zero source values corrected; no qualified output
version, production publication or acceptance. No application/core data changes,
Agent1 coordination, new credentials, permissions, services or schedules.
The worker stops after this bounded investigation; no worker/service continues
in the background. DQ001-DQ004 and their evidence are unchanged. The administrative
next step is reviewed evidence-only landing and verification,
then stop. No further source investigation is active; use the reopening triggers
above if a future consumer or new original evidence makes it necessary.
