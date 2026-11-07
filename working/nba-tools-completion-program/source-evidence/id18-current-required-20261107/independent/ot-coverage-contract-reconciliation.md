# Independent OT coverage contract reconciliation

Reviewer `/root/id18_checker`, separate Codex session; backend model unavailable.
This reconciles the existing contract before a validation change. It does not
waive a gate, change a dataset, authorize publication or infer missing zeros.

The earlier 2,249 new-player-key number was a conservative planning lattice:
2,208 standard-window keys (368 whole-game appearances × six windows) plus all
41 whole-game appearances in OT games 179/186. It was explicitly a whole-player
planning calculation, not evidence that all41 played OT or require literal OT
statistic rows. The existing production contract is more precise.

`docs/reference/data_contracts.md` explicitly limits automatic zero completion
to six standard quarter/half windows and forbids invented OT rows for games or
players without OT activity. `pull_game_period_stats.py` and
`tools/stage_rollover_periods.py` implement this: normalize the actual source
rows, join them to whole-game identities, and zero-complete only standard
windows. OT has a separate aggregate5–14 source request. It is therefore wrong
to require a whole-player OT cross-product or fill omitted OT rows with zeros.

Independent retained-original checking in `ot-source-key-reconciliation.json`
authenticates the exact existing request parameters, acquisition response size/
hash and original Traditional/Advanced pairs. Both endpoints' exact listed
identity sets agree with the accepted canonical OT CSV for every old OT game:

| Game | Whole-game player keys | Qualified source OT keys |
| --- | ---: | ---: |
| 110 | 21 | 12 |
| 120 | 19 | 13 |
| 128 | 22 | 16 |
| 141 | 19 | 12 |
| 165 | 21 | 16 |
| Total | 102 | 69 |

The missing33 are whole-game participants not listed in those OT source
windows, not thirty-three demonstrated missing source values. Game165 includes
one actual source-listed `0:00` row for player1642852, which the importer
preserves. The expected OT key set must therefore come from qualified source
rows, including explicit literal zero-clock rows, rather than merely counting
positive-minute target CSV rows. This review does not invent any row from the
absence of an identity. Original source clocks retain their recorded precision;
the existing independently reviewed clock qualification is reused, not changed.

The required window denominator stays **745**, including all seven known OT
games. The new sixteen-game population still needs every one of its98 windows,
196 team rows and 2,208 standard player-window keys. The new179/186 OT player
row denominator remains unknown until their actual period originals qualify.
Replacing a conservative planning cross-product with a demonstrated exact
source key set is contract reconciliation, not reducing required game/window
coverage. Every actual source-listed key remains required, no unknown becomes
zero and a missing or incomplete OT response cannot become an empty source set.

An independently valid OT player coverage proof requires the actual bound
Traditional/Advanced OT requests and bodies, exact game/team identity, the
Summary-derived period/score envelope, correct team elapsed minutes, complete
player clock/count consistency, exact participant identities and ordinary
normalization/source checks. The expected key set must be frozen from those
original bodies and compared with the materialized CSV; deriving it solely from
the CSV being checked would be circular. The existing source qualification and
required numerical/structural validation workflows can record this proof. A
nonempty file, matching endpoint title, lower row count or sum of target rows
alone is not independent coverage acceptance. Rate facts keep their own checks.

The generic `validation_control.py` currently requires only the six standard
windows. Adding known OT **team** keys is a genuine strengthening: both teams
in every independently known OT game need the OT row. Existing catalog and
whole-team clocks must agree; missing or contradictory metadata stays unknown/
failed. A team-only generic gate must not claim to prove complete player OT
source coverage. Keep exact source/consumer proof separately required through
the existing workflows rather than silently treating a structural pass as
whole-snapshot qualification.

There is a distinct conservative consumer limitation. The existing
`period_coverage_failure` restricts team OT expectations using whole-team
minutes, but player mode compares the requested whole-player base directly with
OT rows. Executed against accepted old source data, complete team OT coverage
passes, while the five-game whole-player OT base reports33missing keys; the
exact source-listed player subset passes. Thus a correctly complete sparse OT
dataset does not automatically make all broad player OT queries work. The
existing player finder and its summary consumers can refuse when a requested
population includes games/players without recorded OT rows. Do not call that
refusal a successful positive, change its meaning silently, infer player OT
zeros, or present the source-row denominator as a delivered consumer repair.
Source-qualified restricted OT populations and team OT answers can qualify
independently. Any original accepted Core-1 obligation that actually depends on
broader player OT semantics remains open until a separately verified repair;
this reconciliation creates no new adjacent feature prerequisite.

The previous source-only freeze is retained unchanged as historical evidence.
Its2,249 planning number must be described with this qualification in current
handoffs; neither the immutable earlier receipt nor the745window denominator is
rewritten. ID18's separate reviewed source/consumer approval remains unaffected.
