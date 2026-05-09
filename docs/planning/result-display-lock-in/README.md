# Result Display Lock-In Planning

This folder is the organized workspace for the result-display lock-in and implementation effort.

## Purpose

Keep the result display work visually and organizationally separated from the broader `docs/planning/` folder.

This initiative turns the screenshot review decisions into an implementation-ready spec, then into preflight and execution prompts.

## Source decision logs

The original review decision logs currently live one level up:

- `../result_display_family_review_lock_in.md` — Families 1–15 and global rules G1–G20
- `../result_display_family_review_lock_in_batch_6_addendum.md` — Families 16–19 and global rules G21–G24

These should be treated as source evidence until they are merged into the final synthesis spec.

## Planned docs in this folder

Recommended next files:

- `result_display_lock_in_implementation_spec.md`
  - Final merged source-of-truth spec for all 19 families.
  - Should read both source decision logs above.

- `result_display_preflight_prompt.md`
  - Repo-agent prompt for discovery-only mapping of current implementation files/functions to the lock-in spec.

- `result_display_wave_plan.md`
  - Implementation wave breakdown after preflight evidence is available.

- `prompts/`
  - Execution prompts for each implementation wave.

- `return_packages/`
  - Optional local index/links to return packages if we want them visually grouped near this effort.

## Intended workflow

1. Merge the two source decision logs into `result_display_lock_in_implementation_spec.md`.
2. Run a preflight-only repo-agent task to map current code to the spec.
3. Use preflight evidence to write scoped implementation prompts.
4. Implement in waves:
   - shared display rules
   - leaderboard patterns
   - game logs/entity summaries
   - records/comparisons/playoff history
   - no-result behavior
5. Validate each wave with targeted fixtures/screenshots before moving on.

## Organization note

Do not add more loose result-display planning docs directly under `docs/planning/` unless they are legacy/source references. New result-display lock-in work should go in this folder.
