# Query Feedback Privacy and Deletion

This runbook is the durable repository contract for the optional manual query
feedback capability. Persistence is deferred and out of scope for the current
public release: the public UI exposes no feedback submission control, deployed
storage is disabled, and no feedback bucket, credential, lifecycle, legal
basis, notice, deletion channel, or SLA is required for current release
acceptance. The implementation remains fail-closed and tested so a later
owner-approved feature-promotion decision can use this runbook.

## Current release classification

“Feedback persistence” means the optional server-side write of one minimized,
redacted, explicitly submitted manual-feedback record to R2. It does not refer
to query execution, local saved queries, ordinary application logs, or the
machine/human QA evidence used to accept supported answers.

No current owner-approved release requirement says this storage must be
activated. The D-02 decision approved the safeguards required *if* manual
records are retained and expressly kept deployed persistence disabled. The
deployment variables have always been optional, and the owner guide describes
the capability as an intake valve for later. Historical release-candidate
planning included a feedback experiment but classified its missing dedicated
bucket as a non-blocking follow-up; it is not a locked current-release
contract. D-08's least-privilege proof and D-09's external privacy operations
therefore become future activation prerequisites rather than Queue D release
gates.

## Approved collection boundary

- Public query execution never persists automatic diagnostics. Backend
  diagnostics require explicit local `QUERY_AUTOMATIC_DIAGNOSTICS_ENABLED=true`
  and are forced off in every deployed environment. The public feedback endpoint
  rejects `feedback_source=automatic`.
- If the capability is promoted later, manual feedback begins only when the
  user opens the feedback dialog and submits it. The dialog must disclose the
  retained categories, server redaction, 90-day maximum, and receipt-based
  deletion support before submission.
- A manual record retains the redacted query, selected report category, optional
  redacted note, route/status/reason, compact allowlisted result metadata,
  result shape, and limited redacted answer/error context. Full result rows,
  arbitrary fields, account data, IP addresses, device fingerprints, and
  session replay are not retained.
- Common email, phone, IP, long-number, bearer credential, secret assignment,
  and sensitive URL-parameter patterns are redacted server-side before any
  free-text field is stored. Pattern redaction is defense in depth; users are
  still told not to submit personal information.

For any future activation, privacy/deletion ownership and incident ownership
are assigned to **John Matthew, project owner**. Legal basis remains an
owner/legal decision; this repository does not invent or approve one.

## Fail-closed deployed activation

`QUERY_FEEDBACK_STORE=r2` is not enough to enable a deployed store. Every one of
these gates is also required:

- `QUERY_FEEDBACK_PUBLIC_PERSISTENCE_ENABLED=true`
- `QUERY_FEEDBACK_LEGAL_BASIS_APPROVED=true`
- `QUERY_FEEDBACK_PUBLIC_NOTICE_APPROVED=true`
- `QUERY_FEEDBACK_DELETION_CONTACT=<dedicated monitored public channel>`
- `QUERY_FEEDBACK_LIFECYCLE_VERIFIED=true`

The current release intentionally does not activate this optional capability.
These variables remain unset and deployed feedback persistence remains
disabled. This is the accepted current product boundary, not an open release
gate. Before a future feature-promotion decision can activate persistence, the
owner must approve the legal basis and notice, create and disclose a monitored
contact, configure the bucket lifecycle, run the read-only verification below,
and retain browser proof of the final notice/contact. Actual environment
changes require separate authorization.

## Fixed 90-day lifecycle

Every schema-v2 raw record includes immutable `created_at`, `expires_at`, and
`retention_days=90`; `expires_at` is exactly 90 days after creation. The R2
feedback prefix must also have an enabled relative-expiration lifecycle rule of
90 days or less. Converting a report into a QA case, issue, or planning artifact
does not extend the raw record: copy only the minimized facts needed by that
durable artifact and let the raw record expire.

Read and verify the provider rule without changing it:

```bash
.venv/bin/python tools/query_feedback_privacy.py \
  --bucket nbatools-feedback \
  --prefix query_feedback \
  verify-lifecycle
```

Set `QUERY_FEEDBACK_LIFECYCLE_VERIFIED=true` only after that command identifies
an enabled covering rule with `expiration_days <= 90`. The repository has not
run this command against a real bucket and does not claim that the external rule
exists.

## Deletion request procedure

The current release stores no public feedback, so it needs no deletion intake
channel or deletion SLA. If persistence is promoted and enabled later, the
owner must first create and publish the monitored channel and SLA. The process
is then:

1. The requester supplies the `qfb_...` receipt shown after submission.
2. John Matthew records the request without copying query text into the request
   log and confirms the receipt format.
3. With separately authorized delete-capable feedback credentials, run the
   receipt-addressed command below. Repeat the receipt after
   `--confirm-feedback-id`; this prevents a bucket-wide or ambiguous deletion.
4. Retain the command's minimal `qfd_...` deletion receipt in the protected
   request log and confirm its result is `deleted` or `already_absent`.
5. Notify the requester through the monitored channel. The owner must publish
   an approved response/completion SLA before persistence is enabled; no SLA is
   claimed while the channel and notice remain absent.

```bash
.venv/bin/python tools/query_feedback_privacy.py \
  --bucket nbatools-feedback \
  --prefix query_feedback \
  delete-receipt qfb_<receipt> \
  --confirm-feedback-id qfb_<receipt>
```

The delete command is a real remote mutation. Do not run it without explicit
authorization for the named request and bucket. Schema-v2 UUID and server
receipts map to one key. Older schema-v1 date-partitioned records require a
read-only lookup; do not replace that lookup with a broad deletion.

## Access and incidents

Use the dedicated feedback credential boundary in
[`deployment.md`](deployment.md). Public runtime access is write-only to the
submission prefix when the store is eventually enabled; review, lifecycle
verification, and deletion use separately controlled permissions. The frontend
never receives R2 credentials.

John Matthew owns suspected disclosure, unauthorized access, lifecycle drift,
or deletion failure. On an incident, disable persistence first, preserve only
minimal non-query evidence, assess affected receipt IDs and dates, rotate or
revoke the feedback credential when appropriate, and do not re-enable until the
owner has verified remediation and the external gates again.
