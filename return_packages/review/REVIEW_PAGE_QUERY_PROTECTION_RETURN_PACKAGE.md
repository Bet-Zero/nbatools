# Review Page Query Protection Return Package

## Summary of changes

- Changed `/review` so it only fetches fixture metadata on page load.
- Added manual controls for full sweep, first 10 fixtures, stop, cached-result
  usage, and cache clearing.
- Added a concurrency-limited runner with a limit of 3 active query requests.
- Added versioned localStorage caching for successful responses and failure
  messages.
- Added a visible cost warning for review sweeps.

## Files changed

- `frontend/src/ReviewPage.tsx`
- `frontend/src/ReviewPage.module.css`
- `frontend/src/api/client.ts`
- `frontend/src/test/ReviewPage.test.tsx`
- `docs/operations/ui_guide.md`
- `return_packages/review/REVIEW_PAGE_QUERY_PROTECTION_RETURN_PACKAGE.md`

## Behavior before vs after

Before:

- Opening `/review` fetched fixtures and immediately called `/query` for every
  fixture.
- All review queries were fired without a local concurrency brake.
- Refreshing the page recomputed the whole review set.

After:

- Opening `/review` fetches fixture metadata only and waits for user action.
- `Run review sweep` executes all fixtures manually.
- `Run first 10` executes only the first 10 fixtures.
- `Stop` halts queued work and aborts in-flight browser requests where the
  browser supports `AbortController`.
- The runner starts at most 3 query requests at a time.
- Cached successes and failures are reused when `Use cached results` is
  enabled.
- `Clear cached results` removes review cache entries and clears visible
  results.

## Testing performed with command output

```text
npm --prefix frontend test -- ReviewPage

> frontend@0.0.0 test
> vitest run --no-file-parallelism ReviewPage

 RUN  v4.1.4 /Users/brenthibbitts/nba_tools/frontend

 Test Files  1 passed (1)
      Tests  10 passed (10)
   Start at  04:44:00
   Duration  6.87s (transform 1.39s, setup 191ms, import 1.75s, tests 1.82s, environment 2.24s)
```

```text
npm --prefix frontend test

> frontend@0.0.0 test
> vitest run --no-file-parallelism

 RUN  v4.1.4 /Users/brenthibbitts/nba_tools/frontend

 Test Files  18 passed (18)
      Tests  249 passed (249)
   Start at  04:44:13
   Duration  57.44s (transform 2.02s, setup 2.27s, import 5.60s, tests 16.93s, environment 26.39s)
```

```text
npm --prefix frontend run build

> frontend@0.0.0 build
> tsc -b && vite build

vite v8.0.8 building client environment for production...
transforming...✓ 130 modules transformed.
rendering chunks...
computing gzip size...
../src/nbatools/ui/dist/index.html                   0.77 kB │ gzip:   0.41 kB
../src/nbatools/ui/dist/assets/index-DPo76hQn.css   66.16 kB │ gzip:  11.22 kB
../src/nbatools/ui/dist/assets/index-boQvxk8a.js   476.63 kB │ gzip: 141.53 kB

✓ built in 1.23s
```

## Known limitations or follow-up recommendations

- Stop cancels the local queue and aborts browser fetches, but any request that
  already reached the server may still consume server work.
- Cache entries are scoped to `v1`, fixture `case_id`, and fixture query text.
  Bump the version if response contracts change in a way that makes old review
  results misleading.

## Confirmation

`/review` no longer auto-invokes `/api/query` on mount. The page fetches
fixtures on mount, shows the available fixture count, and waits for an explicit
manual run control before calling `postQuery`.
