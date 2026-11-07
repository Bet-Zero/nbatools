# Independent bounded period-acquisition review

**Approve** exact source-lane candidate
`578dd16d6ff4137abd13ea69d2276438506ad03b` for the existing targeted read-only
acquisition route. Reviewer `/root/id18_checker`, separate Codex session,
backend model unavailable. This approval covers acquisition and its required
capture harness; source/numerical admission and snapshot completeness remain
separate and unaccepted.

Reviewed the fixed request, `tests/cloud_current123_new16_periods_real_data.py`,
its offline request test, and existing collector SDK construction, transport,
checkpoint, stop and retention behavior. Exact request SHA256 is
`e06682b8da8eb4b4b5c1a627566b617ae9e0e4fffa70d69f675c4b6f71868268`.
The source denominator file is hash-bound, and an independently constructed
expected set agrees with all 196 unique jobs: Traditional plus Advanced for
98 windows, only games 173–188, including aggregate OT5–14 for 179 and 186.
All sixteen games retain their six standard quarter/half windows. None of the
successful old107 source windows is requested again.

Executed 196 offline installed-SDK parameter checks with `get_request=False`.
Every constructed endpoint/parameter dictionary equals its fixed request and
the exact `https://stats.nba.com/stats/<endpoint>` transport host. No source
request occurred during this review. All jobs use RangeType1, StartRange0 and
EndRange28800. No new collector, endpoint, credential or SDK dependency is added.

The existing collector validates a one-attempt, thirty-second response timeout,
two-megabyte body bound, one-second minimum spacing and 1,050-second elapsed
ceiling. It records the attempted job before transport, disables redirects,
retains available original bytes and hashes on failure, stops at the first
transport/JSON failure and preserves the exact unattempted-job ledger. Its
existing resume rejects changed inputs and never retries a recorded failed job.
Elapsed/size exhaustion produces an incomplete receipt instead of success.
The harness requires every one of the 196 attempts to complete and no unattempted
job; a partial capture cannot pass its final assertions. Collection explicitly
retains canonical_period_accepted:false and production_writes:0.

The wrapper first authenticates the retained historical base manifest. It
acquires no production object and changes no production data, active pointer,
protection, credential, permissions or refresh schedule. Actual source schema,
window clocks, identity/count arithmetic, rates and independent validation must
still qualify the captured bodies. Known partial archive windows cannot serve
as substitutes for these actual period source responses. The OT player key
contract reconciliation does not remove either new OT source request or any
other required window; its exact player denominator remains source-dependent.
