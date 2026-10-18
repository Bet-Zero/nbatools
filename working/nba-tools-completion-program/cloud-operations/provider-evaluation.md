# Core NBA provider evaluation

Owner authorization: sample and pricing evaluation only, October 18, 2026.
No purchase, subscription, payment method, paid trial, new paid service,
production data update or architecture replacement is authorized.

## Result and recommendation

**No commercial provider has passed actual-data acceptance.** No evaluator key
or authenticated real-data package is available in this session. Published
examples are schema evidence, not collected live data. No account, key, card,
trial, purchase or vendor agreement has been created or accepted by this evaluation.

Test **API-Sports API-NBA Free at exactly $0/month first**. Its published separate
schedule/game, player-game and team-game endpoints are the best low-cost match
for the current core contracts. Free access is not proof of current-season
coverage, accuracy, correction handling, permissions or service reliability.
If it qualifies and its quota suffices, keep $0. If quota is the only verified
problem, direct-dashboard Pro is published at **US$15/month**, subject to checkout
confirmation/tax and separate owner purchase approval. Do not upgrade during
evaluation. Do not use third-party older $19 pricing or confuse NBA with the
separate Basketball product.

Required access: an owner-controlled no-card API-NBA Free evaluation key made
available through the existing GitHub `r2-validation` environment as
`NBA_PROVIDER_EVALUATION_KEY`. This is an access request, not permission to alter
production credentials. It has been requested; no key value is in this report.
Actual tests remain pending until it is securely available. The other providers'
real sample access also requires account/evaluator access or a vendor-supplied
package; no bypass of those controls is attempted.

## Comparison

| Provider | Verified published ongoing price | Core suitability from documentation | Actual-data and rights limitations |
| --- | --- | --- | --- |
| API-Sports API-NBA | Free $0, 100 requests/day, 10/min; Pro US$15/month, 7,500/day, 300/min | Separate games, games/statistics (team) and players/statistics endpoints; standard box counts, plus/minus and minutes documented | No authenticated sample tested. Vendor IDs need NBA crosswalk; string/null minutes and counts need verification. Terms do not grant publication/commercial competition rights; resolve NBA Tools display, durable storage/backups and retention before adoption. Update frequency is not guaranteed. |
| BALLDONTLIE NBA | All-Star US$9.99/month, 60/min; GOAT US$39.99/month, 600/min; free excludes player-game statistics | Player-game stats on All-Star; box scores/advanced/standings documented on GOAT | Neither tier is shown to provide the full independent team aggregate required by our contract. Do not sum player rows to invent team-credited totals. Documented vendor IDs and whole-minute-looking examples require crosswalk and precision qualification. Terms allow storage/archiving/derived display with restrictions on competing products/raw resale and third-party rights. No actual sample tested. Card-backed 48-hour auto-converting trial is excluded. |
| SportsDataIO commercial NBA | **Quote required; exact monthly cost unavailable** | Explicit Game + TeamGames + PlayerGames box score structure, Minutes/Seconds and NbaDotComPlayerID are the strongest documented fit | Ordinary trial/dev data can scramble scores/statistics and cannot prove NBA accuracy. Real historical Replay is advertised but login-gated, not a current-feed demonstration. Commercial agreement must cover app use, attribution, R2 storage/backups and post-termination retention. Personal Discovery Lab pricing is not a commercial NBA Tools license. No actual sample tested. |

No listed provider is claimed to be an official NBA-authorized feed merely because
it returns NBA statistics. No price buys away an unresolved identity, field or
rights gap. Provider marketing promises are not executed availability evidence.

## Acceptance against existing contracts

Retain all existing historical snapshots and the protected R2 publication path.
A new provider may supply qualified new core rows; it does not replace historical
data or redefine existing columns. Specialized period/on-off datasets are separate
coverage limits, not prerequisites for a valid core source.

| Check | Required evidence | Current result |
| --- | --- | --- |
| Actual unscrambled payload | Provider-authenticated responses or provider-issued real package with URL/endpoint/parameters, retrieval time, source game date, bytes/hash, explicit real-data status | **Blocked on evaluator access**; public examples not accepted |
| Game identity | Provider game ID mapped to canonical NBA game ID through official schedule: date, teams, home/away, season/type, final status and both final scores; reject multiple/no matches | Not executed |
| Player identity | Durable provider-ID to NBA-ID crosswalk, validated independently; exercise rookies, trades, accents/suffixes and collisions; provider IDs are never NBA IDs by assumption | Not executed |
| Grain/completeness | Exactly two distinct paired team rows per final game; all actual played player rows; unique keys; all required points/rebounds/assists/steals/blocks/turnovers/shooting/plus-minus fields present | Not executed |
| Team statistics | Independent provider team totals, not player sums for team-credited rebounds/turnovers; paired scores/plus-minus and shooting identities reconcile | API-NBA and SportsDataIO schema candidates only; BDL unresolved |
| Minute precision | Preserve source precision and units; minutes/seconds and overtime reconcile to official game clock; no rounded minutes presented as exact seconds | Not executed |
| Accuracy | Compare every core count and player key for bounded regulation, overtime and roster-change games against retained official data; account for documented corrections | Not executed |
| Current updates/corrections | Collect current final games and revisit later; prove new-game discovery, completeness, correction handling, missing/delayed/postponed handling and measured latency | Not executed; 2026-27 regular season has not started in the qualified schedule |
| Freshness/rollover | Isolated staging; reject wrong season/type or stale/partial/empty data; preserve last-good snapshot and previous season on failure; no success merely because HTTP200 | Existing architecture preserved; new source operations not accepted |
| Usage rights | Confirm NBA Tools query/display use, raw retention and private cloud backup, any public Git staging/raw-download restriction, attribution, cancellation retention, and third-party rights | Not cleared for adoption; vendor terms reviewed only |
| Ongoing cost | Real request count, quota headers, retry/correction budget, rate-limit handling, exact plan/currency/taxes and no automatic overage/purchase | Public plans known; actual usage not measured |

One regulation sample is not reliability acceptance. Historical Replay, even when
real, cannot establish current delivery latency/corrections. Failures or missing
fields stay failures; unavailable specialized data stays unavailable, never zero.
Do not create a production package until source qualification and existing
publication approvals independently pass.

## Cost-bounded evaluation plan

After secure evaluator access is available, inspect a small number of authentic
responses before implementing an importer. Bind one known completed game to its
retained official raw oracle, then check a recent source game separately. Fetch
only the endpoints needed to assess games, full team totals, player stats and ID
crosswalk. Do not publish vendor payloads or keys in public Git, logs or downloadable
artifacts before storage/redistribution rights are confirmed. Record source hashes
and safe evaluation conclusions separately. Record planned/actual requests and
remaining quota; stop on unexpected
billing, status/rights restrictions, rate limits or statistical mismatch.

A planning estimate for postgame collection is one date-level games request plus
two box-score requests per game (one team and one player endpoint), **if** the
endpoint responses are complete and unpaginated for that scope. Fifteen NBA games
would be31requests; a full second correction pass would be62 before identity
bootstrap, retries and other requests. This is a budget hypothesis, not measured
usage or a guarantee that Free can run the full workflow. Do not promise live
polling or perpetual corrections within100/day.

Stop after bounded real samples if the provider cannot meet the core contracts.
Return the exact failure and the next qualified alternative. No identity/meaning
workaround, card trial or plan upgrade is authorized to obtain a passing result.

## Source references (checked October 18, 2026)

- API-NBA pricing: https://api-sports.io/sports/nba
- API-NBA developer/pricing guide: https://www.api-football.com/news/post/how-to-get-started-with-api-nba-the-complete-beginners-guide
- Current-season endpoint/field guide: https://www.api-football.com/news/post/2026-2027-nba-season-guide-to-using-data-with-api-sports
- API-Sports terms: https://api-sports.io/terms
- BALLDONTLIE NBA plans/schema: https://docs.balldontlie.io/
- BALLDONTLIE terms: https://www.balldontlie.io/terms.html
- SportsDataIO NBA dictionary: https://sportsdata.io/developers/data-dictionary/nba
- SportsDataIO Replay: https://sportsdata.io/developers/replay
- SportsDataIO real vs trial data: https://sportsdata.io/help/scrambled-data
- SportsDataIO commercial rights/pricing: https://sportsdata.io/help/data-rights-and-licensing-questions

SportsDataverse issue15 remains tracked, not a dependency on receiving a reply:
https://github.com/sportsdataverse/hoopR-nba-stats-raw/issues/15
