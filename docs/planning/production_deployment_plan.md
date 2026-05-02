# Production Deployment Plan

> **Role: Track B plan for the product polish master plan.** Takes nbatools
> from localhost to a deployed product with synced data.
>
> Whole-plan completion authority is
> [`product_polish_master_plan.md`](./product_polish_master_plan.md). This
> doc covers Track B only.

---

## Position in the master plan

Track B runs in parallel with Track A. Track A is the priority track
because it's fully agent-runnable and produces visible-to-user
improvements; Track B is plumbing that becomes valuable when both tracks
finish.

Track B's work happens whenever the developer is available to complete its
human-required steps. The agent picks up Track B items between Track A
items only if Track A is currently blocked.

---

## Goal

Get the product deployed to Vercel, accessible at a custom domain, with a
hybrid data sync mechanism that keeps the deployed instance fresh without
requiring cloud-side scraping. No design or UX changes in this track —
just plumbing.

---

## Phase structure

Four phases, each with a companion work queue.

### Phase N1 — Backend refactor for Vercel + R2 data sync

Refactor FastAPI to Vercel Functions. Add the `sync-r2` pipeline command.
Wire the deployed app to read from R2.

**Companion queue:** [`phase_n1_work_queue.md`](./phase_n1_work_queue.md)

### Phase N2 — Frontend deployment + custom domain

Deploy the React frontend to Vercel. Configure custom domain. HTTPS.
Deploy-on-push from main. Verify end-to-end.

**Companion queue:** [`phase_n2_work_queue.md`](./phase_n2_work_queue.md)

### Phase N3 — Monitoring, freshness, and stability

Domain-agnostic monitoring and freshness verification against the active
deployed URL (currently the Vercel `*.vercel.app` deployment until the
custom domain exists). Track A already built the UI freshness banner; this
phase makes the deployed monitoring path, freshness evidence, and stability
workflow repeatable. Custom-domain-only checks stay deferred to wrap-up
time.

**Companion queue:** [`phase_n3_work_queue.md`](./phase_n3_work_queue.md)

### Phase N4 — Track B closure

Capture learnings. Finish any custom-domain-specific wrap-up that Phase N3
could not execute before the domain existed. Verify Track B's done
definition is met. Update the master plan with Track B closure status.

**Companion queue:** [`phase_n4_work_queue.md`](./phase_n4_work_queue.md)

---

## Current continuation note

As of 2026-05-02, Phase N3 is closed: the reusable deployment smoke harness,
preview monitoring baseline, and deployed freshness-banner evidence are in
place, and the synthetic seven-day soak was intentionally skipped for
friends-tier scope. Track B's active continuation is now Phase N4. N2 items
4-6 are re-opened there for re-completion once the developer purchases or
chooses the production domain and can complete Vercel DNS/HTTPS setup. The
queue is allowed to continue past those domain-gated items to later
domain-independent prep work.

---

## Done definition for Track B

Track B is done when:

1. The product is reachable at a custom-domain URL
2. HTTPS works without warnings
3. Pushing to main triggers an automatic Vercel deploy
4. `nbatools-cli pipeline sync-r2` syncs local data to Cloudflare R2 in
   one command
5. The deployed app reads data from R2, not from the local filesystem
6. Errors in production are surfaced to the developer when they happen
7. The deployment has a recorded smoke baseline and a reusable smoke path for
   targeted follow-up checks
8. The deployed instance is what friends are using
