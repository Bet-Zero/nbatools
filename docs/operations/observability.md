# Operational Observability

This runbook defines the privacy-safe repository contract for public request
telemetry. It does not define or claim owner-approved service objectives,
external alert delivery, provider retention, or incident-response acceptance.

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

## Current limitations and open gates

Process memory and cache counters describe only the current serverless/local
process. They are evidence inputs, not global aggregates. The repository does
not currently claim:

- an availability or latency SLO;
- an alert threshold or burn-rate policy;
- a monitored alert destination or successful alert-delivery test;
- provider log retention or access configuration; or
- that process-local events alone prove service health.

Those values require the Queue E operating-policy decision and external
configuration proof. Until then, `/health` remains liveness, `/readiness`
remains the release gate, and deployment smoke remains explicit evidence rather
than an always-on SLO monitor.
