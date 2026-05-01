# Product Polish Master Plan

> **Role: single top-level completion authority for taking nbatools from
> engineering-complete to friends-tier-production-grade.**
>
> This is the one document that answers:
>
> - Is the polish plan done?
> - What is the active continuation?
> - What stage of the product transition are we in?

---

## Goal

Take nbatools from "works locally for the developer" to "looks, acts, and
functions like a professional product, deployed at a real URL, used by a
small private user base (developer plus invited friends)."

Out of scope: anything that only matters for a multi-tenant paid product
(auth, billing, marketing, legal). Reachable via a follow-on plan.

---

## Current Whole-Plan Status

**Whole plan status: in progress.**

Engine and parser are complete (see
[`master_completion_plan.md`](../archive/completed-plans/master_completion_plan.md)). This plan begins
the product polish work. Track A Parts 1 and 2 are complete; Track A Part 3 is
in progress and the active continuation is Phase P5.

---

## Whole-Project Completion Rule

Not done unless all of the following are true:

1. The product is deployed to a real URL with a custom domain
2. Data refreshes via documented sync mechanism with monitoring
3. A real design system is in place across all surfaces
4. Every shipped query class has an opinionated, designed layout
5. First-run experience explains the product in under 30 seconds
6. Mobile experience is functional and visually clean
7. The product can be sent to a friend without caveats about rough edges

---

## Plan Structure

Four subplans, organized as two parallel tracks plus two sequential closing
phases.

The product polish work is split into deployment work (which lives in the
backend and infrastructure) and visual work (which lives in the frontend).
Because these touch different parts of the codebase, they can run in
parallel without conflict. The agent picks up whichever has executable work
at any given time.

### Track A — Visual Build (priority, agent-runnable continuously)

The visual track does the actual product polish — the work that makes the
product look and feel like a real product. It splits into three sequential
parts.

#### Part 1 — Visual Foundation

**Plan doc:** [`visual_foundation_plan.md`](./visual_foundation_plan.md)
**First queue:** [`phase_v1_work_queue.md`](../archive/product-polish/completed-work-queues/phase_v1_work_queue.md)

Build the design system into a usable primitives library. Tokens become live
across the app, fonts are wired in, player headshots and team logos render
consistently, the app shell has a real layout. The frame Part 2 builds inside.

Roughly 2-3 weeks part-time.

#### Part 2 — Component Experience

**Plan doc:** [`component_experience_plan.md`](./component_experience_plan.md)
**First queue:** [`phase_c1_work_queue.md`](./phase_c1_work_queue.md)

Every query class — summary, leaderboard, comparison, finder, streak,
record, split, playoff, occurrence, count — gets a real designed layout.
Hero stat treatments, charts and sparklines where they aid comprehension,
card-based results, mobile responsive throughout.

Roughly 4-6 weeks part-time.

#### Part 3 — First-Run and Polish

**Plan doc:** [`first_run_and_polish_plan.md`](./first_run_and_polish_plan.md)
**First queue:** [`phase_p1_work_queue.md`](./phase_p1_work_queue.md)

Landing experience, starter queries, freshness banner, mobile verification
pass, keyboard shortcuts, copy buttons, share links, transitions, error
states, loading skeletons. The 50 small things that separate "looks
finished" from "feels finished."

Roughly 2 weeks part-time.

### Track B — Production Deployment (parallel, developer-gated)

**Plan doc:** [`production_deployment_plan.md`](./production_deployment_plan.md)
**First queue:** [`phase_n1_work_queue.md`](./phase_n1_work_queue.md)

Vercel + Cloudflare R2 + custom domain. Refactors the FastAPI app into
Vercel Functions. Sets up the laptop-to-R2 data sync mechanism.

This track has items that require the developer (R2 signup, Vercel env
configuration, domain purchase). Those items block the track until the
developer completes them. The agent can pick up Track B's other items once
the human-required ones are done.

Roughly 1-2 weeks part-time, mostly waiting on developer steps.

---

## Active Continuation

**Active continuation: Track A, Part 3, Phase P5.** Specifically,
[`phase_p5_work_queue.md`](./phase_p5_work_queue.md).

Track A is the priority track because it is fully agent-runnable without
infrastructure dependencies. Track B can run in parallel whenever the
developer is available to complete its human-required steps.

The agent should always work the next unchecked item in Track A first. If
Track A has a blocker (rare — usually a user-facing decision the developer
needs to make), the agent should switch to Track B's queue if Track B has
unblocked work available. If both tracks are blocked on the developer, the
agent stops and waits.

When Track A finishes Part 1, the next active queue is Part 2's first
phase queue (drafted by Part 1's final task). Same for Part 2 to Part 3.

Track B follows its own internal sequence (`phase_n1` to `phase_n2` to
`phase_n3` to `phase_n4`).

When both tracks are fully closed, the polish plan is done.

---

## Locked Decisions

### Hosting

- Frontend: Vercel (free tier)
- Backend: Vercel Functions (refactored from FastAPI in Track B)
- Data storage: Cloudflare R2 (free tier)
- Data sync strategy: hybrid — laptop pushes to R2, deployed app reads from
  R2

### Design system

Locked in detail in
[`docs/architecture/design_system.md`](../architecture/design_system.md)
(created by the design-system-foundation task that runs before Track A
starts). Summary:

- Dark gray base (not navy, not pure black). Page `#1A1A1A`, elevated
  `#222222`, cards `#2A2A2A`, inputs `#141414`
- Neutral gray text and borders — no blue tint
- Single chromatic accent: warm orange `#F97316`, used sparingly
- Team colors as personality enhancers on team-context cards (stripe, hero
  wash, badge tints) but never on buttons, body text, or multi-team views
- Inter for UI, JetBrains Mono for stat numerals
- 4px-base spacing scale
- Standard radii (4/8/12/16) and shadows (sm/md/lg)

### Visual reference

StatMuse-influenced — dark, image-rich, query-centric, card-based — but
calmer and more analytical. See
[`docs/architecture/design_system.md`](../architecture/design_system.md) for
the full philosophy.

---

## Capability Status

| Area               | Current state                       | Done state                                                 | Owning track      |
| ------------------ | ----------------------------------- | ---------------------------------------------------------- | ----------------- |
| Deployment         | Localhost only                      | Real URL, custom domain, HTTPS, deploys on push            | Track B           |
| Data sync          | Manual local refresh                | `sync-r2` command + cloud-read in production               | Track B           |
| Design tokens      | Phase V1 tokenized frontend CSS baseline complete | Tokens consumed everywhere, no raw hex/sizes in components | Track A Part 1    |
| Primitives library | Phase V2 primitives built and documented | Button, Card, Stat, DataTable, etc. as reusable primitives | Track A Part 1    |
| App shell          | Phase V3 shell/layout complete      | Header, query bar, results region with real layout         | Track A Part 1    |
| Player imagery     | Phase V4 headshots, team logos, fallback behavior, and scoped team theming complete | Headshots and team logos rendered consistently             | Track A Part 1    |
| Component layouts  | Phase C1-C9 complete; Track A Part 2 closed by completion audit | Opinionated layouts per query class with charts            | Track A Part 2    |
| Mobile             | Phase C8 component pass complete; Track A Part 3 Phase P3 broader mobile verification complete | Functional and visually clean on every component           | Track A Parts 2-3 |
| First-run          | Phase P1 first-run surface, starter queries, freshness banner, and first-run mobile polish complete | Landing, starter queries, freshness banner                 | Track A Part 3    |
| Errors / loading   | Track A Part 3 Phase P2 complete    | Designed states with helpful copy and skeletons            | Track A Part 3    |
| Felt polish        | Track A Part 3 Phase P4 complete; Phase P5 closure active | Keyboard shortcuts, copy/share feedback, stat help, transitions, and useful history UI | Track A Part 3    |

---

## Guardrails

These apply across every track and every part.

### Design system is the source of truth

After Track A Part 1 ships the primitives library, no component imports raw
color hex values, raw font sizes, or raw spacing values. Everything goes
through the tokens.

### Mobile is not optional

Every component built in Track A Part 2 has explicit mobile acceptance
criteria. Layouts that only work on desktop are not done.

### No multi-user features

Auth, accounts, billing, rate limiting — all explicitly out of scope.

### Honest data freshness

The UI must always honestly reflect data freshness. When data is stale, say
so; do not silently return stale results without a note.

### Visual quality bar

Each phase queue's items must include a "looks done" acceptance criterion
beyond functional correctness. A component that works but looks
half-finished is not done.

### Tracks do not block each other

If Track A work stalls, Track B work continues. If Track B work stalls,
Track A work continues. The agent picks up whichever track has executable
unchecked items at any given time.

### Track A always takes priority

When both tracks have executable work, the agent works Track A first. Track
A is the work that makes the product visibly better; Track B is plumbing.

---

## Out of Scope

Auth, billing, rate limiting, marketing, SEO, analytics, email, legal,
multi-user observability, customer support tooling, cloud-side data
scraping. If a follow-on plan opens, those live there.

---

## Agent Rule

When asked "is the polish plan done?" or "what is the next step?",
interpret as asking about the whole polish plan and answer from this
document, not from the nearest closed phase or queue.

---

## Reusable Kickoff Prompt

Paste this prompt to start a continuous work session against the master
plan. It self-locates the active queue, runs items in order, and rolls
forward across phase handoffs without needing to be edited per phase.

```text
Read docs/planning/product_polish_master_plan.md and find the "Active
Continuation" section — it names the current active work queue. Open that
queue, read its "How to work this file" instructions, then start at the
first unchecked item and continue through items in order without stopping.
After each item: check it off, commit, open a PR, wait for CI, merge when
green, then move directly to the next unchecked item. If the queue gets
fully checked off and its final item drafts a new queue, re-read the
master plan, follow it to the new active queue, and keep going. Only stop
if every queue under the master plan is closed, or if you hit a genuine
blocker (failing tests you can't resolve, missing credentials, an
ambiguous decision that needs me) — in which case mark the item `[~]`
with an inline note explaining the blocker and stop. Do not stop merely
because one item or one phase finished.
```
