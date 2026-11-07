# Independent period inventory

Reviewer: `/root/period_source_checker`; model identity is not exposed by the runtime.
Base main: `226f62b5360b621bc52ce59df3239eda065f87ef` (merged PR599).
No source requests were made. Agent 2 and the parked investigations were not started.

`reconcile_retained.py` is a read-only evidence oracle, not a collector or new pipeline.
Run it from any directory to reproduce `retained-inventory-oracle.json`. It hashes
and checks all 86 retained source-evidence ZIP archives outside this task directory,
examines the six embedded acquisition receipts, lists every new16 filename and
hash, and compares the unique prior qualification cache with retained originals.
Other worktrees repeat repository evidence and are excluded from duplicate scans.
All 50 new16-named files in the unique cache duplicate retained source bytes.
The pinned v3 archive also independently contains 1294 team-period and 14547
player-period rows, each spanning exactly647 windows/107games and zero new16 games;
the report binds both member hashes and the immutable archive hash.

The independent exact inventory is 196 unique Traditional/Advanced requests:
16 games 0022600173–0022600188 × six quarter/half windows × two endpoints, plus
OT5–14 for 0022600179 and 0022600186 × two endpoints. Every request has RangeType1,
StartRange0, EndRange28800. The 647 old windows remain excluded; 647+98=745.
New team keys are 98×2=196. The standard player lattice is 368×6=2208.
The 41 whole-game player appearances from the two OT games are not an OT row oracle;
new OT keys must come from source-listed participation, including literal zero-clock rows.

No successful retained response fulfills an exact new request. All196 remain missing.
The retained failed collector attempted only 173Q1Traditional, returned zero bytes,
and left195 unattempted. Its duplicate custody copy is not another attempt or success.
The known archive_period173 body is independently rechecked: both teams Q1 0:00/0PTS,
Q2 0:38/0–3PTS, Q3 0:23/0PTS, Q4 0:15/0PTS. Those partial clocks cannot supply
complete quarters/halves. The 16 retained whole-game Traditional and 16 Summary
originals have different statistical scope and cannot replace period responses.

This inspection establishes no changed cloud acquisition condition. The diagnosed
Actions timeout is not retried. The existing exact laptop workflow is the useful
next route, subject to independent review of its frozen package and preservation
of every successful response if a later request fails. Transport capture alone
will not establish period-source qualification or release readiness.
