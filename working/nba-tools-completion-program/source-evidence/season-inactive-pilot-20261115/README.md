# Retained 2023-24 participation pilot

This is data-production work using retained sources, not a reopened membership
investigation. No game-source acquisition or automatic refresh is involved.

PR619's complete-game recovery alone changes 18 complete player/team/season cases
in the published generation to 19 in its existing staging (Tatum). The other
retained native pairs add individual observations but no further complete case.
The already retained season CSV supplies 11,010 explicit inactive records across
all 1,230 regular-season games. Combining it with PR619 yields **93 complete cases
across 27 clubs**: 75 above published, 74 beyond prior staging. Each case has all
82 games classified. No club is complete for every candidate player.

The bounded denominator is 713 observed candidate player/team identities from
manifest-bound appearance, availability and roster files plus retained dated
movement identities. Those inputs enumerate candidates, never infer tenure.
After the batch, 620 cases remain incomplete: 134 include an omission even in an
already processed whole-game source; 486 have unresolved keys only outside those
processed whole-game reports. All 20,846 unresolved cells lack both a qualified
game association and play state; none is a certified-member/unknown-play-only
case. These categories cannot be relabeled as proven DNP versus nonmembership.
Trades, late joins and omitted two-way players can still require dated membership
or further explicit game observations. No source hunt is reopened to fill them.

The new producer/reader stages a separate immutable inactive dataset, replays its
original CSV and canonical bindings, checks conflicts, and supplements only
missing observation keys. Existing 597 published availability rows, all PR619
staging and stronger game/PDF clock authority are preserved. It creates no dated
membership intervals and fills no source omission. Publication remains gated.

Original CSV and capture metadata are already retained in
`../league-participation-20261114/bulk-inactive-original.zip`, SHA256 of CSV
`adf13e62baeb356fab9f8507a37379f35a4631cae3846700cb49fab4cd01969b`.
`source.json` binds the matching publisher release asset digest, exact canonical
files and capture uncertainty. This is archive-derived NBA SummaryV2
`InactivePlayers`, not original NBA wire bodies or complete rosters.
The inspected [publisher registry](https://github.com/sportsdataverse/hoopR-nba-stats-data/blob/26a6296dbbd743da71ee30d3e05086726c932d76/python/nba_data_build/reshape/datasets.py)
explicitly selects that table; the reference revision is not a claimed build-run
identity. All 30 retained native SummaryV2 key sets agree; no source duplicate,
wrong game side or canonical appearance contradiction was found.

Focused product verification runs both natural-language with/without queries for
all 93 complete cases (186 checks), comparing exact game IDs and W/L to direct
retained source keys and canonical team rows. Genuine empty samples stay distinct
from unsupported unknowns. Coverage includes opening/finale absences and three
players with no appearances (Čančar, Clark, Lee). Whole-season Adams/Houston and
Dinwiddie/Lakers remain unsupported rather than counting pre-join games as DNPs.

Local editing verification passed the season test and 43 focused source/boundary
controls; 18 historical-applicability checks passed after the finite companion
update. Exact-head review, targeted R2 result and CI are recorded in PR623.
The data overlay is staging only until separately approved publication. Core-1's
limited acceptance, Davis default-season/cross-team gaps, freshness/readiness and
parked K12 work remain separate; no full-Core or new deployed acceptance claim.
