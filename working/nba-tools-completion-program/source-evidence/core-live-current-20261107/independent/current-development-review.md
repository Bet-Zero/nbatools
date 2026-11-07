# Independent development/source review

Reviewer: separate Codex checker (`/root/id44_checker`), backend model not exposed.
Reviewed working delta on `codex/current123-development-20261107`, 2026-11-07.
No shared runtime, parser, test, source, or checkpoint edits by this reviewer.
Exact frozen candidate review remains required after author commit.

No blocking semantic finding in the reviewed development loader and opponent-list
changes. The eight games exclusions exactly match deliberately unsupported blank
catalog metadata in `pull_games.py`; the schedule family and readiness timestamps
remain subject to their existing guards. Required numeric identity, scores/rates,
played clocks and unknown participation clocks remain protected. A null clock is
allowed only for literal `did_not_play`, remains null, and is not a fabricated zero.
The opt-in process-local isolation and production refusal remain unchanged.

The optional `either` addition belongs to the existing enumerated-opponent parser,
retains both named clubs as one opponent sample, and preserves the participation
predicate. It resolves the frozen original current opponent wording dependency;
it does not establish cross-club membership or an absent Tatum appearance.

Independent focused invocation with `PYTHONPATH=src` passed all 45 tests in
`test_development_data.py` and `test_opponent_entity_span.py`, including the ten
new loader cases and six enumerated-opponent variants. The shared venv's editable
install otherwise imports the main checkout, so candidate-scoped PYTHONPATH is
necessary for these worktree checks. Both independent replay scripts pass Ruff.

The durable `current-originals.zip` hash and size match current-artifacts.json
(411435a52ba299441e06cc0af50bfd4e31da7e853d0dc2cd03fe197e13a695dd,
635409 bytes). The source-only oracle now extracts that package into an isolated
temporary directory and reuses original retained body paths. Its output remains
byte-identical: 6d382d91e1ee6e5ee21e63ec22fcd74d6461692d885912d4e6e63b5014bab97d.
This preserves the prior independently frozen full vectors and arithmetic.

The durable provisional snapshot hash and size match current-artifacts.json
(eb60f64204a089d0d5a9083496aa44e172e3fe511b71d7980a0649e0e3778c17,
793724 bytes), with manifest
373e0b5c1e53f7e60dbfdb2c2799bf7b661f439fbd5e6662f9d6dcedadf5fe95.
All 18 manifested bodies match. All prior107 game,214 team,2413 player rows
preserve every cell exactly, with16/32/368 additions respectively. All other old
raw family bodies except the intentionally updated schedule and availability are
byte-identical. All246 canonical team identities/dates/opponents/home flags/WL/PTS
match the independently qualified Finder original. All five actor vectors match
canonical identities and selected record facts, including positive player MIN.
Six packaged retained bodies match their original SHA256, Git blobs, and custody.
Their later e3 revision binding is metadata equivalence, not a fresh body capture;
the six actual authenticated metadata responses should be retained with the claims.

`replay_current_consumers.py` independently passed9 structured and9 loopbackHTTP
cases against the durable snapshot. Frozen current results: LeBron PHI2 absences,
home1; Luka LAL without1–0/103PPG, with6–2/124.125PPG; Reaves absence no_match;
LAL vs BOS/NYK parent no_match with both opponents/Tatum retained. Default omitted
season also resolves2026–27. Rest remains no_data; Davis explicitLAL membership
remains unsupported. Both channels retain provisional labels and false whole
numerical/production acceptance. These are local targeted qualified facts, not
deployed proof or whole-snapshot acceptance. Extra returned metrics outside the
qualified record/PTS scope receive no new NBA numerical acceptance here.

The strict required validator still fails roles368 keys, playerperiod2208,
teamperiod192, playerseasonAdvanced4. Five optional unavailable families are
separate. Old484 rate unknowns remain unchanged; new16 period/advanced numerical
facts and exact period universe remain unqualified. No freshness/publication gate
is weakened by this application repair.

The one-PDF harness is approved for its proposed bounded capture-only role:
fixed official20261028_LALLAC URL, source-pinned game143 final103–87/inactiveLuka,
one reader, no redirects/retries,20-second timeout,1.5MB limit, original body/hash
and failure retention, `rest_qualified:false`. An actual PDF must subsequently
match final game/club/player identity and explicitly state the reason before any
Rest answer is accepted. Failed capture is a precise source dependency, not a
reason to retry an unchanged blocked route. Standard authorized runner request,
source custody and exact-candidate review still apply.
