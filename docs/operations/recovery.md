# Recovery and Rollback

This runbook defines the repository recovery contract for application code and
immutable runtime data. It separates safe local proof from any production
mutation. External backup controls and live recovery evidence remain explicit
operational gates.

## Approved recovery objectives

John Matthew approved these Queue E objectives on 2026-07-22:

- **Recovery point objective (RPO): 24 hours.** At incident time, the newest
  independently recoverable trusted generation may be no more than 24 hours
  older than the affected state.
- **Recovery time objective (RTO): 8 hours.** Measure from the first confirmed
  failed production-monitor probe until the service again passes readiness and
  the required post-recovery deployment smoke.

The two-hour monitor interval creates a separate detection gap of up to roughly
two hours; every live receipt must record the last known-good probe, first
failed probe, and best-known failure start rather than hiding that gap. The
objectives are owner policy, not evidence that the current system has met them.
The isolated 79.662 ms drill is only an implementation lower bound.

The 24-hour RPO requires an independent backup/export at least daily while data
can change. Retaining the previous generation in the active pointer is useful
rollback protection but is not an independent backup and cannot close E-03B by
itself.

## Safe drill

Run the deterministic production-isolated drill before proposing a live drill:

```bash
nbatools-cli pipeline recovery-drill --output <evidence-path>.json
```

The command creates all data under an automatically deleted temporary
directory. It exercises a local filesystem and an in-memory R2-compatible
object API. It does not read environment credentials, open a network
connection, inspect the repository's real data directory, or mutate any real
bucket or active pointer.

The drill publishes two valid immutable generations in each simulator, saves
an exact backup of the rollback target, damages that target, proves rollback is
refused without moving the pointer, restores the exact bytes and checksum
metadata, then rolls back. It verifies manifest/checksum validation,
conditional or atomic pointer switching, and retention of the formerly active
generation. Its JSON receipt records each passed invariant and measured local
restore/rollback durations.

These timings are a lower-bound implementation measurement. They do not include
real dataset size, network transfer, provider recovery, diagnosis, deployment,
DNS/cache propagation, or human response, so they are not an RTO or RPO.

## Code rollback

1. Identify the last known-good commit, the failing commit, and the exact CI and
   deployment evidence for both.
2. Stop further promotion. Preserve logs and the failing request IDs without
   copying raw query text or credentials.
3. Prepare a normal revert PR for the smallest failing change. Do not rewrite
   history, force-push, reset, or bypass CI.
4. Require the standard lint, docs, frontend, and Python CI gates.
5. Deploy or promote only with separate authorization, then run deployment
   smoke and record the deployment identifier, source commit, request IDs,
   readiness generation, results, operator, and timestamps.

A passing revert PR proves repository recovery only. It does not prove the
deployed application changed until the authorized deployment and smoke evidence
exist.

## Immutable data rollback and restore

Normal data rollback uses the retained `previous_generation_id`:

```bash
# Temporary/local operation
nbatools-cli pipeline rollback-generation --target local

# Production R2 mutation: explicit authorization required for this exact run
nbatools-cli pipeline rollback-generation --target r2
```

Before moving a pointer, the implementation validates the target generation's
manifest, inventory, sizes, and SHA-256 metadata. Local pointer replacement is
atomic; R2 pointer replacement is conditional on the previously read ETag.
Missing, corrupt, legacy-unmanifested, or concurrently changed targets fail
closed and leave the active pointer unchanged.

If a retained generation is incomplete, restore its exact immutable bytes and
checksum metadata from an independently retained backup or provider recovery
source before retrying rollback. Never manufacture a manifest, overwrite a
different object under an existing generation ID, or point at a partially
restored generation. Validate the restored generation and preserve both the
pre-incident active generation and the recovered target until the incident is
closed.

## Backup and retention boundary

The publication layer creates content-addressed manifests under immutable
generation prefixes and retains one previous generation in the active pointer.
It has no pruning command, so application tooling must not delete either the
active or previous generation.

That is rollback retention, not an independent backup. Dependable-production
acceptance additionally requires externally verified backup/export coverage,
restore access independent of the failed path, retention satisfying the
24-hour RPO, and a live or provider-representative restore receipt.

## Credential loss and incident escalation

On suspected credential loss or compromise:

1. Stop publication, rollback, deployment, and feedback persistence; do not
   place credentials in tickets, chat, logs, or evidence files.
2. Notify John Matthew, project and incident owner. A monitored incident
   channel is still required before dependable-production acceptance.
3. Determine which read-only runtime, publication, deployment, or future
   feedback credential boundary is affected. Preserve safe request IDs and
   provider event metadata.
4. Credential revocation, rotation, replacement, scope changes, and deployment
   configuration are external mutations and require explicit authorization.
5. Revalidate least privilege, run the applicable read-only smoke first, and
   record the authorized recovery action before restoring traffic or writes.

## Required recovery receipt

Every live recovery exercise or incident must record:

- start/end time, operator, incident owner, and authorization reference;
- affected source commit, deployment ID, data generation, and provider target;
- symptom and safe correlation/request IDs, with no raw query or secret data;
- last known-good commit/generation and verified backup source;
- validation/checksum results before the pointer or deployment changes;
- each mutation, its result, measured detection/recovery time, and data-loss
  window;
- post-recovery health, readiness, and deployment-smoke evidence; and
- remaining exceptions, follow-up owner, and expiry.

The owner approved preparation of a live drill but explicitly did not authorize
production or R2 mutation. Repository tests and the safe drill do not
substitute for external backup proof, a separately authorized exact live
operation, successful alert delivery, or measured RTO/RPO evidence.
