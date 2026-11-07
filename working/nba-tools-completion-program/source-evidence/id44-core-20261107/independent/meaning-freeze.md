# Independent ID44 meaning and evidence freeze

Checker: separate Codex session `/root/id44_checker`; exact backend model is not
available. This is neither Agent 2 nor a human/Claude/cross-model review. Initial
inspection is on main merge `a0fb2211a6707d647325129f1262308545001241`, before
the author supplies new source qualification or query results.

Original ID44 remains
`tests/test_c2_franchise_identity.py::test_with_and_without_a_player_keep_his_earlier_franchise_games`.
Its existing controlled population spans Seattle 2007–08 and Oklahoma City
2008–09, both franchise/team ID `1610612760`, with declared played and
did-not-play states in both eras. Both positive and negative participation filters
must retain the earlier identity. Preserve that original test and its assertions.

The real-data companion's question is **“Thunder record without Kevin Durant in
2007-08.”** Its population is the complete Seattle SuperSonics regular-season
schedule for that season, not a handful of convenient games, current Thunder
games, a career sample, or another season. Player ID is `201142`. Franchise
identity and actual game-day club must be established separately from wording.
The current team abbreviation names the franchise; historical SEA names its era.
The result must disclose its earlier Seattle identity in the applicable output.

Before numerical acceptance, establish:

- Exact canonical final game IDs/dates, both clubs, venue/reciprocal identity and
  team results; match an independently qualified season population/denominator.
- Durant's same-game played facts with positive valid minutes and matching
  game/team/player identity. A complete qualified appearance log can supply played
  keys; it cannot supply DNP for its absent keys.
- Explicit qualified DNP/inactive facts and relevant Seattle association for each
  remaining game, or separately qualified dated membership plus an adequately
  complete participation source. A roster snapshot, an empty inactive list,
  another game that day or zero/missing minutes alone supplies neither DNP nor
  nonmembership. Preserve unknowns and conflicts.
- A disjoint, exhaustive classification of every required game, including any
  verified nonmembership and unknown. Accept no absence total while unknown or
  contradictory relevant games remain. Do not infer membership over a gap merely
  from appearances before and after it.
- Independently freeze exact selected IDs and W/L (and any additionally asserted
  scoring values) from qualified facts and canonical outcomes, before examining
  the application result. Verify both with and without paths against those IDs.
- Retain original source bodies, URLs/immutable archive revisions, SHA256 and
  archive Git blob hashes where available, capture times and literal limits.
  Archive retrieval time is not NBA capture time or freshness.

Independent unfamiliar language, frozen before execution:

1. `How did the Thunder do in 2007-08 when Kevin Durant did not play?`
2. `Thunder record in 2007-08 with Kevin Durant playing`
3. `Seattle SuperSonics record without Kevin Durant in 2007-08`
4. `Seattle record with Kevin Durant in 2007-08`

These ask the same qualified full-season populations. A parser registration,
natural/structured agreement, correct refusal, fixture result or historical
deployment receipt cannot substitute for their real-NBA source/N acceptance.
If a held-out fails it becomes a regression; do not silently replace it.

Retained inspection: PR593's original-46 mapping identifies this source/N gap;
PR594's affected-ID delta does not close it. A filename inspection of 17 relevant
retained K08/historical source ZIPs found no `00207`, `2007-08` or `2008-09`
member. Production-recovery manifests retain hashes for canonical 2007–08 games,
team/player stats and schedule, but that is no proof of Durant absence coverage.
The structured archive index includes year 2008, which is a source-discovery lead,
not game-content evidence. No new source body has been independently qualified yet.

This freeze neither adds a requirement to collect the whole 2008–09 season nor
reduces the full 2007–08 real companion to examples. Unchanged multi-era controlled
proof remains applicable only to its synthetic scope. Keep all 46 original K08
requirements and all 12 Core-1 bindings; numerical, unfamiliar-language, deployed
and literal current/default-season obligations remain distinct. K12 cold chasing
and DQ-005 stay parked; no production/publication/pointer/access change is reviewed.
