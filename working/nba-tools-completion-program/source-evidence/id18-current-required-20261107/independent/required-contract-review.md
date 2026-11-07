# Independent required-data contract and bounded milestone review

Checker `/root/id18_checker`, separate Codex session, backend model unavailable.
Reviewed live-main baseline `fc53dda20fc8965cda87f8d33997f81d4f73f270` and
the existing PR596 release handoff. This review makes no production decision.

The actual required regular-season dataset contract in
`src/nbatools/commands/validation_control.py::DATASET_SPECS` contains eleven raw
families: games, schedule, team game statistics, player game statistics, starter
roles, player period statistics, team period statistics, team season Advanced,
player season Advanced, rosters and standings. Its five processed families are
team game features, game features, schedule context, player game features and
league season statistics. Optional play-by-play, clutch, on/off and lineup
families are not silently added to this required slice by this review.

Independent source-only arithmetic against the retained original 16 Summary
bodies and complete fresh PlayerGameLogs reconfirms 98 additional windows,
196 team period keys, 2,249 player period keys and 368 whole-game appearance/role
keys. Games 179 and 186 each require their OT window. The old accepted 647
windows plus 98 gives the existing required denominator of 745. Summary proves
identity, score and the window denominator; it cannot supply missing period
statistics, starter positions or zero participation. The immutable initial
regulation-limited 192/2,208 failure receipt must remain historical evidence.

These missing source families have different effects. Missing roles prevent
starter/bench-dependent consumers from accepting the new games. Missing periods
prevent quarter, half and OT questions from accepting the complete 123-game
population. Missing season Advanced keys or stale season values prevent the
corresponding season usage/efficiency and dependent ranking consumers from
qualifying; merely adding the four missing identities does not establish the
fresh values of every existing identity. Catalog OT metadata controls which
windows are expected and therefore must agree with the independent denominator.

DQ-006 is a separate participation requirement: exact applicable game-day Davis
membership/nonmembership is missing for the named current Lakers, LeBron-owned
and paired/cross-club conditions. Neither an observed WAS appearance nor a
season roster snapshot establishes the missing Lakers fact. This does not
invalidate Luka's independently qualified same-game Lakers association in game
143, the eight other positive appearances or independently qualified LeBron and
Reaves source populations.

The older 484 unknown period-rate values remain another separate requirement:
242 TOV% and 242 USG% values in twenty recorded team/window groups. Their missing
award-credit methodology, 0118 adjudication and 0009 Eason association facts
remain exactly those recorded in the existing dependency ledger. This review
does not reopen their exhausted investigations. They prevent qualification of
consumers of those exact rate inputs, including filters, ranking and aggregated
rate answers. They do not turn independently qualified integer PTS or record
facts into unknowns. The old 484 count cannot certify that the new sixteen-game
scope has no additional unknown values.

A smaller independently valid milestone already exists under the unchanged
acceptance rules: source-qualified ID18 can progress from a `no_data` refusal
to a correctly labeled, complete nine-game Rest-empty development answer while
the whole snapshot remains explicitly provisional. Reused PR595 historical
numerical evidence and PR596's precisely bound historical desktop/mobile
delivery remain valid within their original scopes when unaffected. This is
useful verified capability, not a complete Core-1 or publication candidate.

The complete publication candidate still requires all required families and
actual source/numerical/structural/current-freshness validation, the full
original Core-1/K08 acceptance scopes, and subsequently separately approved
protected publication and served-generation/deployed acceptance. Existing
criteria do not authorize calling a partial snapshot complete. No automatic
refresh, production change or owner approval request follows from this review.
