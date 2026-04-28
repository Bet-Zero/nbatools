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

**Companion queue:** drafted at end of N1.

### Phase N3 — Monitoring, freshness, and stability

Error monitoring. UI freshness banner integrated into the deployed app
(Track A may have already built the UI side; this phase wires it to real
data freshness signals from the deployed system). 7-day stability soak.

**Companion queue:** drafted at end of N2.

### Phase N4 — Track B closure

Capture learnings. Verify Track B's done definition is met. Update the
master plan with Track B closure status.

**Companion queue:** drafted at end of N3.

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
7. The deployment has run for at least 7 consecutive days without manual
   intervention
8. The deployed instance is what friends are using
