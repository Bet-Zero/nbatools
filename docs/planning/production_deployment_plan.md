# Production Deployment Plan

> **Role: Part 1 plan for taking nbatools from localhost to a deployed product
> with synced data.**
>
> Whole-plan completion authority is
> [`product_polish_master_plan.md`](./product_polish_master_plan.md). This
> doc covers Part 1 only.

---

## Goal

Get the product deployed to Vercel, accessible at a custom domain, with a
hybrid data sync mechanism that keeps the deployed instance fresh without
requiring cloud-side scraping. No design or UX changes in this part — just
plumbing.

---

## Why this comes first

- Every UI change after Part 1 can be verified on the deployed instance
- Surfaces deployment-environment bugs before they tangle with redesign work
- Friends can start using the current product immediately, providing real
  feedback during redesign work
- Forces resolution of the FastAPI-to-Vercel-Functions refactor before more
  work depends on the production architecture
- Forces resolution of the data sync mechanism before Part 2 builds on it

---

## Phase structure

Four phases, each with a companion work queue.

### Phase N1 — Backend refactor for Vercel + R2 data sync

Refactor the FastAPI app to Vercel Functions. Add the `sync-r2` pipeline
command. Wire the deployed app to read from R2.

**Companion queue:** [`phase_n1_work_queue.md`](./phase_n1_work_queue.md)

### Phase N2 — Frontend deployment + custom domain

Deploy the React frontend to Vercel. Configure custom domain. HTTPS.
Deploy-on-push from main. Verify end-to-end.

**Companion queue:** `phase_n2_work_queue.md` (drafted at end of N1)

### Phase N3 — Monitoring, freshness, and stability

Sentry (or simpler) error monitoring. UI freshness banner that surfaces data
age. Stability soak: 7 consecutive days without manual intervention.

**Companion queue:** `phase_n3_work_queue.md` (drafted at end of N2)

### Phase N4 — Retrospective and Part 2 handoff

Capture learnings. Draft `visual_foundation_plan.md` and
`phase_n5_work_queue.md` (or whatever Part 2's first phase is named).

**Companion queue:** `phase_n4_work_queue.md` (drafted at end of N3)

---

## Done definition for Part 1

Part 1 is done when:

1. The product is reachable at a custom-domain URL
2. HTTPS works without warnings
3. Pushing to main triggers an automatic Vercel deploy
4. `nbatools-cli pipeline sync-r2` syncs local data to Cloudflare R2 in one
   command
5. The deployed app reads data from R2, not from the local filesystem
6. Errors in production are surfaced to the developer when they happen
7. The deployment has run for at least 7 consecutive days without manual
   intervention
8. The deployed instance is what friends are using
