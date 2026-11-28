# November 27 snapshot stabilization evidence

## Frozen application and data

- Source `605d71af787ff2ff02811bba45635560d7f4f657`, tree
  `2da3ed3293695c9ce72ad47552550e0a55c591b5`, production
  deployment `dpl_5bTrBeMV4aMD2NMmYzRCXmUvizC8` in `iad1`.
  [Application delta](https://github.com/Bet-Zero/nbatools/pull/665) ·
  [Frozen CI](https://github.com/Bet-Zero/nbatools/actions/runs/46077109413)
- Hosted iad1 build used Vercel CLI 66.6.0, Python 3.12 and uv 0.13.5
  installing from uv.lock. The tracked command uses npm ci and built with
  Vite 8.1.6. The provider project config reports Node 24.x.
  Served application SHA-256
  `2283d4d9a67e5d5387bf93687ebaaee426e28574bd1dc7898b1c9430140830af`.
  Before and after browser checks matched deployed input-tree SHA-256
  `73f45eb0c4ee761fda928916bff2126f071e696d3ffc9f5563ba4a7974d4f107`.
  [Source and dependency inputs](https://github.com/Bet-Zero/nbatools/tree/605d71af787ff2ff02811bba45635560d7f4f657) ·
  [Provider build](https://vercel.com/zeros-projects-686e97fc/nbatools/dpl_5bTrBeMV4aMD2NMmYzRCXmUvizC8)
- Cleveland `availability-cleveland-2024-v3-20261124`, manifest SHA-256
  `d574144512821d202249e1d87926cbbfd053126b7f1e6960582f4a9b52149034`.
  [Authenticated pin and release jobs](https://github.com/Bet-Zero/nbatools/actions/runs/46077661280)

## Measured operating range

| Scope | Observation |
| --- | --- |
| Native deadline | Both local adapters returned complete correct Cleveland answers near 16.16 s. The controlled body setup took about 0.27 s and serialization and write took at most 6 ms. The handler budgets 17 s end to end, including 0.5 s for the response. |
| Vercel termination | Both authorized preview holds produced correlated native 20 s timeouts. The receipt binds the artifact, ref, access revocation and four requests. [Diagnostic receipt](w3a-host-cutoff-packet.md#november-27-execution-receipt) |
| Hosted positive paths | 200 for Ewing 5,027 points across 348 covered games in 11.677 s externally and the five-row 30-season ranking in 10.939 s. Observed process RSS was 354.039 and 678.234 MiB. Both oversized requests returned typed 413s. [Application delta](https://github.com/Bet-Zero/nbatools/pull/665) |
| Local common queries | Retained locked-runtime evidence covers 8 process-cold requests in 1.339–2.066 s and 40 warm repeats with p95 0.260 s for Curry, the team record, the ranking and the comparison. The single-season readers exercised there are unaffected by the cold multi-season prefetch delta. |
| Local costly history | The frozen source returned twelve independently checked Ewing answers over native loopback with verified original input bytes. Two process-cold replies measured 3.424 and 4.146 s with empty caches. Ten warm replies measured 0.949–1.083 s. One cold run read 136 objects including the pointer and about 170 MB. |
| Local concurrency | One process admitted three overlapping requests in 2.602, 3.689 and 8.454 s. They covered a player summary, Cleveland appearance and broad ranking. Peak process RSS was 730.434 MiB and sampled disk was 259,632,840 bytes. Separate controls verified excess 429, deadline 504 with occupied slots until completion, and a subsequent 200. |
| Local rollover and faults | Two generations remained pinned while their readers overlapped. Results preserved the old unknown and new qualified rostered samples. Retirement waited for reader exit. The old generation was evicted and redownloaded on revisit. Peak process RSS was 976.184 MiB and sampled disk was 510,609,453 bytes. Missing/corrupt required data failed closed and a subsequent correct answer passed. |
| Hosted resource limits | The temporary filesystem reported 550,461,440 bytes total, with 284,545,024 available after the ranking observation. The existing read-only endpoint required an elevated service plan for effective memory configuration, and worker memory limits were absent from the recorded environment. Same-worker concurrency, effective hosted headroom and useful hosted near-deadline margin remain unqualified. |

Local transport read independently restored immutable files and provided the production
admission and native HTTP paths. The figures are finite observations. A hosted first
observation lacks an unprimed-worker marker.

## Broad release evidence

- Raw QA exercised all 621 scenarios. 481 passed and 140 failed. The 140 include
  132 literal 2026–27 season/date coverage failures, seven incomplete participation
  or status predicates and one canonical spelling mismatch in a correct 43–21
  Lakers answer. The eighteen `unrouted` negative cases met their expectations.
  [Raw QA receipt](https://github.com/Bet-Zero/nbatools/actions/runs/46077661280/artifacts/15235337877)
- Filter sweep exercised all 521 comparisons. 477 had a comparable signal
  (148 applied, 290 refused, 39 dropped, zero incorrect claims or execution
  errors). The remaining 44 had no comparison signal.
  [Filter evidence](https://github.com/Bet-Zero/nbatools/actions/runs/46077661280/artifacts/15234918561)
- Required numerical suite passed 1,675 and failed 232. All 142 earlier failure
  node IDs recurred. Independent triage found 144 earlier binding or source
  qualification failures, 73 literal-current expectations, 10 strict readiness
  checks, two incomplete full-season participation positives, two assertions
  superseded by accepted evidence or meaning and one older opponent expectation
  conflicting with TEAM scope. Preserve the original positives and oracle identities.
  [Frozen numerical evidence](https://github.com/Bet-Zero/nbatools/actions/runs/46077661280/job/140769245200) ·
  [Prior full run](https://github.com/Bet-Zero/nbatools/actions/runs/43658019032)

- The two-viewport replacement passed with independent review. All 44 original
  captures and 40 timed repeats were fresh, with 84 unique request IDs and
  verified screenshots. Pooled p95 was 562 ms and the slowest timed repeat
  was 585 ms. The proof binds the before and after deployment, verified
  pointer, exact asset and original oracles to the frozen source.
  Archive SHA-256
  `ee848896a76cda2018e6462a1a786c937d56cc253f87c6f9bd2af7f96ecb74ec`.
  [Browser run](https://github.com/Bet-Zero/nbatools/actions/runs/46078137747) ·
  [Browser evidence](https://github.com/Bet-Zero/nbatools/actions/runs/46078137747/artifacts/15236515268)
- Separate desktop and mobile Chromium checks on the same asset exercised
  the snapshot disclosure, actual typed HTTP 413 and request ID, then used
  the keyboard to run the Cleveland example. Both rendered 31–13 in 44
  and cleared the previous error.
- The spelling repair passed all three targeted Raw QA variants and the
  independently derived Cleveland appearance checks on the authenticated
  generation. The 22 original restored-data payloads matched the frozen
  source exactly. The full-run totals stay with the earlier frozen source.
  The corrected application merged at
  `aa5e51c999b3a61208a7329134753193244968b9` and its production deployment is
  `dpl_EoKjoaxSjNbDAB1ordqetqtFtfoo`.
  [Repair](https://github.com/Bet-Zero/nbatools/pull/666) ·
  [Targeted validation](https://github.com/Bet-Zero/nbatools/actions/runs/46079589717)

The prepared verifier change has focused independent review and remains isolated
until the corrected frozen release is accepted. The original archive and its
source and receipt identities remain available.
[Prepared transition](https://github.com/Bet-Zero/nbatools/commit/5446f6c3490d2e54c896a2c1d606ccaf908571e9)

## Release check reconciliation

The [exact case inventory](stabilization-release-scope-20261127.json) records
all 232 failed numerical IDs, including the 90 additional IDs. The 142 earlier
IDs all recurred. The snapshot corrections address 21 IDs. Ten deployed
historical questions had been stopped by a strict readiness binding. Eight
relative-date tests use numerical expectations for a fixed April 2026 clock.
Three participation expectations needed the accepted team-versus-opponent
meaning or the subsequently qualified inactive rows. The remaining 65
literal-current and two incomplete full-season participation positives keep
their original assertions. The remaining 144 fail in original source, stage,
profile, or delivery contexts against the Cleveland run's single active pin.
Historical source and delivery receipts retain their original identities.

Ten deployed historical tests passed through the public alias using the
checksum-verified Cleveland data for the independent expected rows. The
readiness bracket accepts the fully typed single known blocker on that exact
snapshot. The endpoint continues to report HTTP 503 for strict Live readiness.

The 39 sweep differences were 18 minimum-games floors and 21 starter/bench
conditions. The team-points leaderboard already used the floor, and the
team-occurrence route now forwards it to its existing consumer. Both routes have
an independent discriminating control above the 82-game sample. The 37
unfinished combinations returned explicit filter limitations with no false
answer on the restored data. They remain recorded as desired combinations.

The full R2 jobs continue to execute their complete populations and retain
their original exit status. `python -m tools.verify_snapshot_release` uses
the same run's authenticated artifact digests, the complete numerical case
population, the original Raw QA corpus, and all configured filter comparisons.
New or altered failures and newly lost comparison signal require review.

## Additional hosted operating evidence

The spelling-corrected deployment `dpl_EoKjoaxSjNbDAB1ordqetqtFtfoo` returned
all three simultaneous historical requests in 6.206–11.627 s across workers.
A warm cohort of the broad ranking, Curry summary and Ty Jerome rostered
record returned all three in 1.187–5.030 s. Overlapping native intervals and
shared evolving cache counters indicate a common worker in that cohort.
Peak observed process RSS was 807.742 MiB and the minimum observed completion
volume headroom was 278,290,432 bytes. Effective worker memory allocation was
unavailable. These measurements describe the observed workload. The separately
parked unprimed K12 claim retains its original gates.

Under one controlled native worker with 100 ms per object, the duplicate-read
repair reduced 217 to 166 GETs for the same 163 distinct keys and saved
85,767,228 transferred bytes. It preserved all three complete answers and the
follow-up rostered result. Peak observed RSS fell from 900.824 to 784.719 MiB
with 271,658,867 sampled disk bytes in both runs. A two-slot comparison rejected
an otherwise valid third answer and had higher measured RSS. The existing
three-slot policy is retained.

## Corrected release acceptance

[PR #668](https://github.com/Bet-Zero/nbatools/pull/668) merged at
`adcbe8e1b14b967a19878dfbd89ce37497980d5a`. Its tree
`781f71cac8f36c6148482a926bfff514dc4bcb02` exactly matches reviewed candidate
`cee3df5ff1d3c8b85c7feb0b13e1446425dea423`.
The [full authenticated run](https://github.com/Bet-Zero/nbatools/actions/runs/46087190603)
executed every configured check: 1,907 numerical tests, 621 Raw QA cases, and
521 filter comparisons. There were zero snapshot-scope failures. The full
numerical verdict records 1,696 passes, 144 original historical-context
failures, 65 literal-current failures, and two incomplete participation
positives. Raw QA records 482 passes and 139 unfinished positive cases.
The sweep preserves all 148 applied comparisons. Its 37 changed verdicts
are explicit limitations for the previously dropped combinations.
The [authenticated exact-manifest consumer](https://github.com/Bet-Zero/nbatools/actions/runs/46087458901)
passed with zero skips.

The stable alias before and after qualification resolved to
[deployment `dpl_BbLgFqmkwD5f9ZMXbjHfhiTDH9ba`](https://vercel.com/zeros-projects-686e97fc/nbatools/dpl_BbLgFqmkwD5f9ZMXbjHfhiTDH9ba)
in `iad1`, with the original browser asset SHA-256
`2283d4d9a67e5d5387bf93687ebaaee426e28574bd1dc7898b1c9430140830af`.
The provider built with Python 3.12 and uv 0.13.5 from the exact lock.
The corrected application returned all seven independently checked hosted
answers. The initial concurrent Ewing, ranking and LeVert responses
completed in 11.742, 11.182 and 6.245 seconds. The warm ranking, Curry and Ty
Jerome responses completed in 5.657, 1.164 and 1.515 seconds across two
workers, with ranking and Ty Jerome sharing a worker during overlap.
Observed process peak was 821.855 MiB, with at least 266,285,056 bytes free
on the temporary filesystem at completion.

The exact reviewed runtime admitted three together on one controlled native
worker. Correct Ewing, ranking and LeVert replies completed in 9.357, 8.787
and 4.467 seconds, followed by a correct rostered response in 0.442 seconds.
The worker issued 166 GETs and transferred 271,659,455 bytes. Observed
peak RSS was 732.820 MiB and disk usage was 271,658,867 bytes. Focused
controls verified generation retirement, checksum failure, timeout handoff
and recovery. Hosted results qualify the measured workload. The provider
does not expose an effective memory ceiling within the available access,
and the final hosted cohort did not place all three requests on one worker.
Earlier hosted three-way overlap and the exact controlled three-way result
give the applicable single-worker measurements. The separate unprimed K12
claim stays parked.

[Final request and provider receipt](source-evidence/stabilization-20261127/hosted-final.json)
