# ReviewPage Exhaustive Deps Warning Cleanup Return Package

## Root Cause

`ReviewPage` aborts in-flight review query requests during its mount effect
cleanup. The cleanup read `abortControllersRef.current` directly, which triggers
`react-hooks/exhaustive-deps` because a mutable ref value could be different by
the time an effect cleanup runs.

This is a ref cleanup pattern, not dependency drift. `abortControllersRef`
stores one `Set<AbortController>` for the component lifetime and `ReviewPage`
does not reassign `.current`.

## Fix Applied

The mount effect now snapshots the active abort-controller set into a local
`abortControllers` variable and uses that local set in the unmount cleanup.
The query-run and stop paths still add, delete, abort, and clear controllers
through the existing ref.

No lint rule was disabled.

## Production Behavior

Production behavior did not change. Unmount cleanup still invalidates the
current run, marks the page unmounted, aborts in-flight review requests, and
clears the controller set.

No `/review` UX, query behavior, parser/routing behavior, result contract, or
Visual QA behavior changed.

## Files Changed

| File | Change |
| --- | --- |
| `frontend/src/ReviewPage.tsx` | Snapshot the abort-controller set inside the mount effect for cleanup. |
| `return_packages/raw-product/REVIEWPAGE_EXHAUSTIVE_DEPS_WARNING_CLEANUP_RETURN_PACKAGE.md` | Record the warning cause, fix, validation, and release impact. |

## Validation Results

| Command | Result |
| --- | --- |
| `npm --prefix frontend run lint` | Passed with no lint warnings after the fix. |
| `npm --prefix frontend test -- src/test/ReviewPage.test.tsx` | Passed: 1 test file, 10 tests. |
| `npm --prefix frontend run build` | Passed. Vite emitted its existing non-failing chunk-size notice. |
| `git diff --check` | Passed. |

Existing `ReviewPage` coverage already exercises review runs and cancellation
through the Stop control. This ref-lifetime lint cleanup does not require a new
behavior test.

## Release Impact

Lint-only frontend maintenance cleanup for the internal review page. No release
behavior or data-contract impact.
