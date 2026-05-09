# Result Display Family Review Lock-In Notes

> Purpose: running decision log for the 19 result-display family screenshots.
> This file captures user-approved visual/content decisions after each review
> batch so the final implementation prompts are based on written decisions, not
> chat memory.
>
> Workflow:
> 1. Review screenshots in batches.
> 2. Add decisions here after each batch.
> 3. After all 19 families are reviewed, convert this doc into implementation
>    prompts / acceptance criteria.
>
> Important screenshot note: screenshot review captures may suppress player
> headshots/logos for easier image generation. Missing headshots in screenshots
> should not be treated as a real-site bug unless confirmed separately.

---

## Global lock-in rules discovered so far

### G1 — Review by family/pattern, not individual query

The project has hundreds of query fixtures, but they collapse into a smaller
number of visual families. Decisions should be made at the family/pattern level
and then applied across all routes that map into that pattern.

### G2 — Do not write implementation prompts after each batch

Collect all family decisions first. Write implementation prompts only after all
19 families are reviewed, unless a single issue blocks further review or is a
safe global fix.

### G3 — Debug/parser chrome is allowed in parser review, not product UI

Parser review pages may show status chips, route names, query class, fixture
numbers, and freshness/debug metadata. User-facing result UI should not expose
route/query-class/debug labels by default.

### G4 — Normal filters are context, not caveats

Do not label ordinary interpreted filters as `CAVEATS`. Examples like `vs good
teams`, `season 2025-26`, or `last 10 games` are query context. Reserve
`CAVEATS` for actual uncertainty, data limitations, approximation, or degraded
answers.

### G5 — No-result copy must be human-first

Primary no-result copy should not expose developer/backend terms like column
names unless in debug/details mode. Translate technical causes into user-facing
language and, where possible, suggest a nearby supported query.

### G6 — Suggestions should be contextual

Generic suggestions are acceptable as a fallback, but no-result flows should
prefer query-specific suggestions based on the failed filter/reason.

---

# Batch 1

Screenshots reviewed:

1. Entity Summary
2. Message No Result
3. Guided No Result

---

## Family 1 — Entity Summary

### Example reviewed

- Query: `How has Jayson Tatum played against good teams this season?`
- Fixture: 44
- Route/pattern shown: `player_game_summary` / `summary`

### Verdict

Keep the broad sentence-hero direction, but this family is not locked yet. It is
missing important filter wording and should include game logs when the summary
is based on a filtered game subset.

### Decisions

- The one-sentence hero direction is good.
- The sentence must include every meaningful interpreted filter.
  - Bad: `Jayson Tatum has averaged 23 points, 9.5 rebounds and 5.5 assists this season.`
  - Better: `Jayson Tatum has averaged 23.0 points, 9.5 rebounds and 5.5 assists against good teams this season.`
  - Best when sample size is available: `Jayson Tatum has averaged 23.0 points, 9.5 rebounds and 5.5 assists in 12 games against good teams this season.`
- If the query summarizes a filtered set of games, include the matching game-log
  answer table below the hero unless the route explicitly opts out as
  summary-only.
- `vs good teams` should be presented as context/filter interpretation, not as a
  caveat.
- Screenshot headshot/avatar absence should be ignored for this review because
  screenshots may intentionally suppress headshots/logos.

### Lock-in rule

Entity Summary should answer with a clear sentence hero, then include a dense
answer table when the query implies an underlying game set/window/filter. The
hero sentence must not drop filters like `against good teams`.

### Likely implementation areas

- `frontend/src/components/results/patterns/EntitySummaryResult.tsx`
- `frontend/src/components/results/patterns/GameLogResult.tsx`
- `frontend/src/components/results/config/routeToPattern.ts`
- summary sentence builders / context builders

---

## Family 2 — Message No Result

### Example reviewed

- Query: `What team has played the best defense recently?`
- Fixture: 14
- Route/class shown: `season_team_leaders` / `leaderboard`
- Status: unsupported / no result

### Verdict

Keep the family, but narrow its usage and improve copy.

### Decisions

- Use Message No Result only for hard unsupported cases where there is no safe
  obvious recovery path.
- Do not expose developer wording in the primary message.
  - Bad: `Column 'def_rating' not available`
  - Better: `Defensive rating is not available in the current dataset.`
- Technical details may remain in debug/details mode, but not as the main user
  explanation.
- This specific example probably deserves a guided no-result or fallback
  suggestion because `best defense recently` has reasonable nearby alternatives
  like opponent points allowed or opponent FG%.

### Lock-in rule

Message No Result = hard unsupported with no obvious next step. User-facing copy
must explain the limitation plainly, without backend implementation terms.

### Likely implementation areas

- `NoResultDisplay`
- no-result reason/copy mapping
- recovery suggestion generation

---

## Family 3 — Guided No Result

### Example reviewed

- Query: `Who scored the most points last night?`
- Fixture: 11
- Route/class shown: `season_leaders` / `leaderboard`
- Status: no match / no result

### Verdict

Keep the family. It should become the default no-result pattern for valid but
empty queries, but suggestions need to be more query-specific.

### Decisions

- Guided No Result is the right shape for valid queries that produce no rows.
- The primary explanation should name the specific failed filter/date/range when
  possible.
  - Better: `No NBA games matched Apr 11, 2026.`
- Avoid raw ISO date ranges in primary user-facing copy. Prefer readable date
  formatting like `Apr 11, 2026` or `Apr 1–12, 2026`.
- Suggested next steps should be contextual when possible.
  - For date no-results: `Try the previous NBA game day`, `Try the next NBA game day`, `Show scoring leaders this season`.
  - For missing metric no-results: suggest nearby supported metrics.
- Generic suggestions like spelling/range/filter broadening should remain only
  as fallbacks.

### Lock-in rule

Guided No Result = default valid-but-empty pattern. It must explain the specific
reason and provide query-specific recovery suggestions where possible.

### Likely implementation areas

- `NoResultDisplay`
- date/range display formatting
- recovery suggestion generation
- parser/query metadata for failure reason

---

## Open questions for final synthesis

- Should parser review pages keep the current large debug/context card exactly,
  or should they be visually separated from product-output screenshots?
- Should `EntitySummaryResult` always compose with `GameLogResult` when a
  `game_log` section exists, or only for specific routes / metadata flags?
- Should `good teams` expansion list show all teams behind a detail disclosure,
  or only summarized as `19 opponents` in primary context?
