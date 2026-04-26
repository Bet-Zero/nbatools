# Product Polish Master Plan

> **Role: single top-level completion authority for taking nbatools from
> engineering-complete to friends-tier-production-grade.**
>
> This is the one document that answers:
>
> - Is the polish plan done?
> - What is the active continuation?
> - What stage of the product transition are we in?
>
> Subplans, phase queues, and retrospectives roll up here. They do not
> independently answer overall plan completion.

---

## Goal

Take nbatools from "works locally for the developer" to "looks, acts, and
functions like a professional product, deployed at a real URL, used by a small
private user base (developer + invited friends)."

This plan deliberately scopes out anything that only matters for a true
multi-tenant paid product (auth, billing, marketing, legal). Those are
reachable from this plan's endpoint by adding a follow-on plan; they are not
in this plan's scope.

---

## Current Whole-Plan Status

**Whole plan status: not started.**

The parser/query engine and underlying data pipeline are complete (see
[`master_completion_plan.md`](./master_completion_plan.md)). This plan
begins where that one ended.

---

## Whole-Project Completion Rule

The polish plan is **not done** unless all of the following are true:

1. The product is deployed to a real URL with a custom domain
2. Data refreshes via a documented sync mechanism with monitoring
3. Every shipped query class has an opinionated, designed layout (not a
   generic table dump)
4. The visual design system is consistent across all surfaces
5. First-run experience explains the product in under 30 seconds
6. Mobile experience is functional and not visibly broken
7. The product can be sent to a friend without caveats about rough edges

Closed subplans, deployed code, partial component redesigns, or "looks better
than before" do **not** by themselves equal whole-plan completion.

---

## Active Continuation Rule

This document must always name exactly one of:

- the current active continuation plan or queue, if the polish plan is not
  done
- the exact next required action, if no active queue exists yet
- an explicit statement that the polish plan is done

### Current Active Continuation

The polish plan has not started. The active continuation is
[`production_deployment_plan.md`](./production_deployment_plan.md), starting
with [`phase_n1_work_queue.md`](./phase_n1_work_queue.md).

---

## Plan Structure

Three sequential subplans plus a closing phase.

### Part 1 — Production Deployment

**Plan doc:** [`production_deployment_plan.md`](./production_deployment_plan.md)

**Goal:** The current product (UI as-is) is deployed to a real URL with custom
domain, HTTPS, automated data sync from local pipeline to cloud storage, and
basic error monitoring.

**Done definition:** Friends can reach the deployed product. Data updates
within hours of the developer running the local refresh. Developer no longer
runs production manually.

**Estimate:** 1-2 weeks part-time.

### Part 2 — Visual Foundation

**Plan doc:** `visual_foundation_plan.md` (drafted at end of Part 1)

**Goal:** Design system in place across the entire product. Typography,
spacing, color palette, dark theme, accent color, NBA player headshots and
team logos threaded through, layout primitives. Components are not yet
redesigned per query class — that's Part 3 — but the foundation any redesign
would build on is locked in.

**Done definition:** Every existing UI surface uses the new design system.
Visual quality is felt across the board.

**Estimate:** 2-3 weeks part-time.

### Part 3 — Component Experience

**Plan doc:** `component_experience_plan.md` (drafted at end of Part 2)

**Goal:** Each query class — summary, comparison, leaderboard, finder, streak,
record, split, playoff, occurrence, count — gets an opinionated, purpose-built
layout. Charts and sparklines where they add understanding. Hero-stat
treatments for high-signal numbers. Card-based layouts, not table dumps.
Mobile responsive throughout.

**Done definition:** Every query class renders in a layout designed for that
class specifically. Charts appear where they aid comprehension. Mobile works
on every layout.

**Estimate:** 4-6 weeks part-time.

### Closing Phase — First-Run + Polish

**Plan doc:** `first_run_and_polish_plan.md` (drafted at end of Part 3)

**Goal:** Landing/empty state, starter queries, freshness banner, mobile
verification pass, keyboard shortcuts, copy-to-clipboard, share links,
transitions, tooltips, error states, loading skeletons.

**Done definition:** A friend lands on the URL cold, understands what the
product is in 30 seconds, runs a useful query without help, and has it work
on mobile.

**Estimate:** 2 weeks part-time.

---

## Locked Decisions

These were decided during plan-drafting and are not up for re-litigation
without a documented reason in a phase retrospective.

### Hosting

- **Frontend:** Vercel (free tier, custom domain on free, automatic HTTPS)
- **Backend:** Vercel Functions (refactored from FastAPI long-running server
  to function-per-route during Phase N1)
- **Data storage:** Cloudflare R2 (free tier covers the entire dataset and
  expected read volume)

### Data refresh strategy

Hybrid: developer's laptop runs `nbatools-cli pipeline auto-refresh` as
today, with a new `nbatools-cli pipeline sync-r2` command that pushes the
resulting data files to Cloudflare R2 on success. Deployed app reads from R2
instead of the local `data/` directory. The deployed instance never talks to
`stats.nba.com` — eliminates IP-blocking risk and cloud-cron complexity.

### Visual direction

"Analytical, calm, considered." Dark theme with deep navy-tinted background
(not pure black). One warm-orange accent color used sparingly. Inter for UI
typography, JetBrains Mono for numerals. Card-based result layouts. NBA
player headshots and team logos as first-class visual elements. Charts via
Recharts. Subtle, considered animations only.

A formal design system in `tokens.css` lands during Part 2. All components
in Part 2 and Part 3 reference those tokens.

---

## Capability Status

| Capability area | Current state              | Done state                                                   | Active continuation |
| --------------- | -------------------------- | ------------------------------------------------------------ | ------------------- |
| Deployment      | Localhost only             | Real URL, custom domain, HTTPS, deploys on push              | Part 1              |
| Data sync       | Manual local refresh       | `sync-r2` command + automated read from R2 in production     | Part 1              |
| Design system   | Default styles, ad-hoc CSS | Real typography, spacing, color palette, tokens.css          | Part 2              |
| Player imagery  | Names as text              | Headshots and team logos throughout                          | Part 2              |
| Query class UIs | Generic data tables        | Opinionated card-based layouts with charts where appropriate | Part 3              |
| Mobile          | Not verified               | Functional and visually clean                                | Part 3 + closing    |
| First-run       | Empty query bar            | Landing experience explains product in 30 seconds            | Closing             |
| Error/loading   | Functional but ugly        | Designed states with helpful copy                            | Closing             |

---

## Guardrails

These apply across every part.

### Design consistency

Once `tokens.css` lands in Part 2, do not introduce ad-hoc styles in Part 3
or the closing phase. New components extend the design system; they do not
fork it.

### Mobile is not optional

Every component built in Part 3 has explicit mobile acceptance criteria.
Layouts that only work on desktop are not done.

### Test the deployed instance

After Part 1, every UI change is verified on the deployed URL, not just
localhost. Catches deployment-only issues early.

### No multi-user features

Auth, accounts, billing, rate limiting, multi-user observability — all
explicitly out of scope. Do not add.

### Honest data freshness

The UI must always honestly reflect data freshness. When data is stale, say
so; do not silently return stale results without a note.

### Visual quality bar

Each phase queue's items must include a "looks done" acceptance criterion
beyond functional correctness. A component that works but looks
half-finished is not done.

---

## Out of Scope

Explicitly excluded from this plan:

- Auth, accounts, signup/login
- Billing, payments, Stripe
- Rate limiting and per-user quotas
- Marketing site beyond in-app landing/empty state
- SEO, analytics, content marketing
- Email infrastructure
- Privacy policy, terms of service, legal copy
- Customer support tooling
- Multi-user observability
- Cloud-side data scraping (eliminated by hybrid sync strategy)

If a follow-on "real product" plan opens later, those items live there.

---

## Agent Rule

When an agent is asked "is the polish plan done?", "what is the next step?",
or any similar status question without a narrower qualifier, it must
interpret the question as asking about the whole polish plan and answer from
this document, not from the nearest closed phase.
