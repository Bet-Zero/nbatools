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
scorers 2025-26`. Its text is part of repository configuration, not retained
user input. The generated monitor report omits request bodies and query text;
it contains only the policy, stable case names, timings, response status,
allowlisted response summaries, and bounded request IDs. Every response read is
capped at 1 MiB; exceeding the cap fails immediately without retaining the body.

The workflow fixes its target to the accepted production deployment in tracked
configuration. It has no dispatch URL input, secret, or mutable repository
variable that can silently redirect scheduled requests. A production target
change therefore requires a normal reviewed repository change plus a passing
manual probe. The eight-case deployment smoke remains the release/promotion
gate; the three-case monitor is deliberately cheaper and is not a replacement.

The 30-day objective has 360 intended two-hour slots. Calculate service success
only across completed normal scheduled runs; at a complete 360-run window,
99.0% requires at least 357 successful runs. Report scheduling coverage
separately against all 360 intended slots. A delayed or dropped workflow is a
monitoring-coverage gap with unknown service state, not evidence that the app
was unavailable. Manual and synthetic notification-test runs are excluded.
Before 30 days of history exists, report the available observation window
rather than claiming the rolling objective is proven.

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
best-effort monitor rather than a commercial continuous-uptime service. A
successful synthetic delivery receipt and owner confirmation remain required
before alert delivery is accepted. `/health` remains liveness, `/readiness`
remains the release gate, and the full deployment smoke remains explicit
promotion evidence.
