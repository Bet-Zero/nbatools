# Operational Observability

This runbook defines the privacy-safe repository contract for public request
telemetry and the owner-approved production monitor. Provider log retention and
broader incident-response acceptance remain separate external gates.

## Public request events

FastAPI and the Vercel adapters emit one `public_request_complete` JSON event
for these public endpoints:

- `GET /health`
- `GET /freshness`
- `GET /readiness`
- `POST /query`
- `POST /structured-query`
- `POST /query-feedback`

Every event is correlated with the response's opaque `X-Request-ID` and uses a
fixed field allowlist:

- event name, request ID, endpoint, method, status, and status class
- elapsed milliseconds and process peak RSS
- process-local DataFrame-cache hit, miss, entry, byte, and eviction counters
- for query endpoints only: stable route, result status, and result reason
- for freshness only: freshness status and current-through date
- for readiness only: readiness status, season state, active immutable
  generation, readiness boolean, and blocker codes

The deployment smoke report also retains `X-Request-ID` when the platform
returns it, alongside its existing per-case duration and selected headers.

## Privacy boundary

Operational events never include raw query text, request or response bodies,
notes, result rows, feedback text, client IP addresses, credentials, provider
error text, object keys, filesystem paths, or exception messages. Unknown
endpoints are not logged by this contract. Outcome values are length- and
character-bounded, and readiness records retain blocker codes rather than
messages.

These events are ordinary application logs, not persisted query-feedback
records. The automatic query-diagnostic and optional feedback-persistence
boundaries in [`query_feedback_privacy.md`](query_feedback_privacy.md) remain
unchanged. Logging failure is best effort and must never alter the public
response path.

## Approved production monitoring policy

John Matthew approved the Queue E operating policy on 2026-07-22:

- run `Production Monitor` from GitHub Actions every two hours, at minute 17
  rather than the high-load start of the hour;
- target at least 99.0% successful scheduled probes over a rolling 30 days;
- call only `GET /health`, `GET /readiness`, and one supported representative
  `POST /query` per normal run (36 requests per day before exceptional retries);
- require health within 2 seconds, readiness within 10 seconds, and the query
  within 15 seconds;
- retry transport or latency failure once immediately, then fail the workflow;
- do not retry a semantic readiness or response-contract failure; and
- deliver failures through Bet-Zero's GitHub Actions email/web notifications,
  monitored by John Matthew as project and incident owner.

The representative query is the completed-season public example `top 10
scorers 2025-26`. The monitor checks the requested regular-season scoring basis
and ten ordered rows with distinct player identities and finite points per
game. The receipt contains the policy, stable case names, timings, response
status, allowlisted summaries, and bounded request IDs. The response read
limit is 1 MiB.

The HTTP socket timeout is deliberately 10 seconds longer than each latency
objective. That grace does not relax the 2/10/15-second pass thresholds; it
allows a slow serverless response to finish so the monitor can classify it as
latency, apply the single approved retry, and retain a measured duration. A
socket failure beyond that grace remains a transport failure.

The owner approved the snapshot alert and recovery policy on November 27,
2026. Each run attempts all three checks. With strict Live readiness
reporting HTTP 503, the overall snapshot verdict passes only when timely
health and scoring pass and the native readiness response identifies the
expected immutable generation and exactly one well-formed
`new_season_not_loaded` blocker. That case records `live_readiness: failed`,
`snapshot_status: passed`, and `notification_required: false`. Other
readiness blockers, malformed responses, wrong generations, and failures
of the health or scoring checks are actionable. A well-formed expected
readiness response that exceeds the time objective gets the usual single
latency retry. Strict Live readiness records its own outcome.

The overall scheduled exit drives the approved GitHub Actions notification
route. Keep the tracked expected generation bound to the exact generation
selected by future protected releases or recovery. Measure the eight-hour
snapshot recovery objective from the first confirmed snapshot failure to
passing snapshot operation and the required post-recovery smoke.
[Recovery runbook](recovery.md#approved-recovery-objectives)

The workflow fixes its target to the accepted production endpoint in tracked
configuration. It has no dispatch URL input, secret, or mutable repository
variable that can silently redirect scheduled requests. A production target
change therefore requires a normal reviewed repository change plus a passing
manual probe.

That target is the stable production alias `https://nbatools.vercel.app`, which
always resolves to the project's current production deployment. It is
deliberately not a deployment-specific host: the previous target
`nbatools-fvdbt0pfv-...` was one build's URL, and when that deployment was
removed the host began answering HTTP `410 Gone`. That produced multiple
scheduled failures caused by the retired target rather than by the service.

Treat a dead target as lost coverage, not as an outage record. While the
monitor points at a host that cannot serve the application, its failures carry
no information about availability, and its window is a monitoring-coverage gap
with unknown service state — the same classification this document already
gives a delayed or dropped scheduled run. Repointing the monitor restores the
signal prospectively; it does not establish what the service was doing during
the affected window, and no run in that window should be cited as evidence
either way.

A dead target also erodes the notification channel this policy depends on:
alerts that are always firing stop being read. The eight-case deployment smoke
remains the release/promotion gate; the three-case monitor is deliberately
cheaper and is not a replacement.

The 30-day objective has 360 intended two-hour slots. Measure snapshot success
prospectively from the approved policy on completed normal scheduled runs. At
a complete 360-run window, 99.0% requires at least 357 successful runs.
Report scheduling coverage against all 360 slots and classify delayed or
dropped runs as unknown service state. Report the available snapshot-policy
window and track strict Live readiness separately. The pre-policy strict,
manual and synthetic runs retain their original verdicts and scopes.

`workflow_dispatch` exposes an approved `synthetic-alert` mode. Its isolated
job checks out no code, installs nothing, makes zero application or R2 requests,
and exits unsuccessfully so the owner can confirm actual GitHub notification
delivery. Repository implementation or a failed synthetic run alone does not
prove that the owner received the notification.

## Current limitations and external gates

Process memory and cache counters describe only the current serverless/local
process. They are evidence inputs, not global aggregates. The repository does
not claim:

- provider log retention or access configuration; or
- that process-local events alone prove service health.

GitHub scheduled workflows can be delayed, dropped under load, or disabled
after prolonged public-repository inactivity. This is a zero-paid-overage,
best-effort monitor rather than a commercial continuous-uptime service. John
Matthew confirmed on 2026-07-23 that the approved network-free synthetic
failure notification reached the GitHub Actions channel he monitors, completing
the Queue E alert-delivery requirement. That confirmation does not turn GitHub
Actions into a continuous-uptime service or provide live recovery or broader
release acceptance. `/health` remains liveness, `/readiness` remains the
release gate, and the full deployment smoke remains explicit promotion
evidence.
