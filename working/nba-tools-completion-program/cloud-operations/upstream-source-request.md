# Prepared upstream request — not sent

Suggested destination: `sportsdataverse/hoopR-nba-stats-raw` GitHub issues.
Owner authorization is required before contacting an outside maintainer. This
file is a reviewable proposal, not a claim that the maintainer accepted work or
that a new source is operational.

Title: Qualify current-season Finder, missing NYK roster and exact period/on-off captures

Thank you for preserving original NBA endpoint responses. We are qualifying
cloud-only development inputs against fixed source revisions and found these
specific gaps at revision `9e81bacbd75f882c5194eb70b6900bbdf30bd0fc`:

- `nba_stats/json/leaguegamefinder/2027/regular-season.json` has
  `parameters.Season: null` and 30,000 rows spanning season IDs22013–22025.
  It is not a2026-27 response. Could the collector bind the requested season and
  reject response-parameter mismatches before replacing a season file? An empty
  correctly scoped2026-27 table before opening day would be appropriate.
- `commonteamroster/2026/1610612752.json` returns404, while the other29team
  captures are available. Could the missing NYK response and current-season
  roster captures be included with their original response parameters?
- The examined2026quarter captures for games0022500003 and0022500002, and2025
  game0022400001, contain zero team points in every quarter. Could period pulls
  retain and verify exact StartPeriod/EndPeriod and RangeType/range parameters,
  and include the matching official traditional and advanced period responses?
  Full-game totals and quarter score summaries are not equivalent.
- Is it feasible to retain exact `TeamPlayerOnOffSummary` responses, including
  both on/off tables and parameters, GP, MIN, PLUS_MINUS, OFF_RATING, DEF_RATING
  and NET_RATING? A transformed dashboard or `Details` subset omitting off-court
  exposure does not establish the same dataset.

Please preserve original responses and capture timestamps (separate from Git
commit/download time), season/type/filter parameters and existing attribution.
We are not asking for credentials, paid access, private network workarounds or
changes to the original NBA data. If these endpoints are not accessible to your
collector, knowing that limitation would help us avoid unnecessary retries.
