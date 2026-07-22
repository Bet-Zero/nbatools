# Owner's Guide

This doc is for the human owner of the project, not for agents. It explains
how the whole thing works in plain language. If you are an agent updating
this file: keep it plain. No jargon, no evidence-layer language, no
abbreviations that only make sense to you. Every term used here is defined
here.

If the project ever feels like a black box again, start here. The owner's
current plan lives in [`ROADMAP.md`](../../ROADMAP.md) at the repo root.

---

## The whole product in one paragraph

Someone types an NBA question. The engine reads the sentence and fills out a
form (which player, which team, which season, what kind of question). It
then picks one of the registered "recipes" that can answer that kind of form.
The [generated repository inventory](../../contracts/repository_inventory.json)
records the current recipe count. The recipe loads game data and computes the
answer. The answer gets wrapped with a headline sentence and labels, and the
web page displays it. That's it. Everything else in this repo exists either to
feed data into that pipeline or to check the answers coming out of it.

---

## How one query actually gets answered

Follow `"Jokic recent form"` through the system. There are five stations.

**1. The front door.**
The web page sends the text to `POST /query` in
[`src/nbatools/api.py`](../../src/nbatools/api.py). The CLI command
`nbatools-cli ask` goes to the same place underneath. The front door does
nothing smart — it hands the raw text to the engine.

**2. The parser — English in, filled-out form out.**
`_build_parse_state()` in
[`src/nbatools/commands/natural_query.py`](../../src/nbatools/commands/natural_query.py)
reads the sentence and fills out a big form (a Python dict): player =
"Nikola Jokić", how many games = recent, what kind of ask = summary, season =
current, and so on. It answers nothing. It only translates English into
form fields. Helper functions live in `_parse_helpers.py` next door.

**3. The router — form in, recipe name out.**
`_finalize_route()` (same file) looks at the filled-out form and picks which
recipe answers it. A "route" is just the name of a recipe —
`"Jokic recent form"` becomes the route `player_game_summary`. If no recipe
fits, the route stays empty and the user sees the "Unsupported Query" card.
That refusal card is a feature, not a failure: this product refuses rather
than guesses.

**4. The recipe — recipe name in, numbers out.**
Each route name maps to a command module, e.g.
[`src/nbatools/commands/player_game_summary.py`](../../src/nbatools/commands/player_game_summary.py).
The recipe reads request-pinned CSV datasets through the project's configured
data source, filters them with pandas (this player, last 10 games), and
computes the numbers. Local mode reads files under `data/`; deployed R2 mode
downloads files from one immutable generation into a local cache. No NBA API
call is made while answering a question.

**5. The envelope — numbers in, answer out.**
`execute_natural_query()` in
[`src/nbatools/query_service.py`](../../src/nbatools/query_service.py) runs
stations 2–4 and wraps the result with everything the page needs: the
headline sentence ("Nikola Jokić has averaged 25.3 points…"), the little
filter labels (called chips), notes, and caveats. The React frontend
(`frontend/src/`) looks at the result type and picks a matching display
(table, stat cards, comparison, streak, and so on).

**Why this matters when something is wrong:**

- A *wrong* answer is almost always station 2 or 3 — the sentence was
  misread or sent to the wrong recipe.
- A *missing* answer ("no data") is almost always station 4 — required data
  coverage or trust is unavailable for what was asked.
- An answer that is right but *displayed* badly is station 5 or the
  frontend.

---

## The query test systems — what they are

You built this in stages, and from the inside it can look like three
abandoned attempts. It isn't. It is one funnel, and the stages connect.

**Stage 1: Exploratory review — "just look at it."**
`qa/exploratory_query_samples.yaml` and `qa/exploratory/slices/` hold
queries with **no** expected answers attached — on purpose. You run a batch
of ten, the tool asks the real engine, and writes out what came back so a
human can read it and judge. This is the *input* system: the place where
new phrasings get tried before anyone commits to what the right answer is.

```bash
make exploratory-query-review-slice SLICE=001_player_last_n
```

**Stage 2: The Raw QA corpus — "lock it in."**
`qa/raw_query_answer_corpus.yaml` holds the current versioned query contracts;
the exact count is generated from source and checked in the
[repository inventory](../../contracts/repository_inventory.json).
Each case records what the engine must do: which recipe, what status, and what
shape of result. A tool re-asks all of them and fails loudly if any contract
changed. Human acceptance remains a separate review state; putting a case in
the corpus does not manufacture that acceptance. The files in
`qa/harness_slices/` are named subsets of the corpus so you can re-check one
theme at a time. The file
`qa/raw_query_answer_acceptance_families.yaml` records family/variant
expectations and the current review-closure state; it does not by itself prove
human acceptance.

```bash
make raw-query-answer-qa
```

**Around the funnel, three ordinary safety nets:**

- **pytest** (`tests/`, with `make test-query` and related commands) — normal
  code tests protecting the parser and engine internals.
- **Smoke tests** (`make test-smoke-all`) — a small set of end-to-end
  natural queries through the real CLI and API paths.
- **Visual QA** (`make visual-qa-screenshots`, plus the `/visual-qa` page)
  — screenshots of rendered answers, for checking the page looks right.

**And one intake valve for later:** the manual query-feedback endpoint
(`POST /query-feedback` and `make query-feedback-export`) can capture bad
answers explicitly reported by real users, so they can enter the funnel at
Stage 1 after a future feature-promotion decision. It is not part of the
current public release: no submission control is shown, automatic public query
diagnostics do not persist, and deployed manual feedback storage remains
disabled. The future activation gates are in
[`query_feedback_privacy.md`](../operations/query_feedback_privacy.md).

The funnel, end to end:

```text
new phrasing idea
    → exploratory slice (no expectations — human looks at output)
    → promoted into the corpus (expectations locked — machine checks forever)
    → protected by pytest/smoke when the code underneath changes
```

---

## Which lever do I pull

| You want to… | Do this |
| --- | --- |
| See what the engine says to one query | `nbatools-cli ask "your question"` |
| Try a batch of new phrasings and judge them | add them to an exploratory slice, run `make exploratory-query-review-slice SLICE=<id>`, read the generated review |
| Freeze a query's behavior so it can never silently change | add a case with expectations to `qa/raw_query_answer_corpus.yaml`, run `make raw-query-answer-qa` |
| Change parser/routing code safely | edit, then `make test-parser` and `make test-query` |
| Change a recipe or the envelope | edit, then `make test-engine` (and `make test-api` if the response shape changed) |
| Change the frontend | edit, then `npm --prefix frontend test` and `npm --prefix frontend run build` |
| Refresh the game data | `nbatools-cli pipeline refresh` |
| Run everything before calling work done | `make test-preflight` |

---

## Map of the repo, shortest useful version

- `src/nbatools/commands/natural_query.py` — the parser and the router
  (stations 2 and 3). The most important file in the repo.
- `src/nbatools/commands/*.py` — the recipes (station 4), one per answer
  type.
- `src/nbatools/query_service.py` — the envelope (station 5): headline
  sentences, chips, metadata.
- `src/nbatools/api.py` — the front door (station 1).
- `frontend/src/` — the React page that displays answers.
- `data/` — local datasets, validation manifests, and immutable-generation
  pointers. Production can read the equivalent generation from R2.
- `qa/` — the query funnel described above.
- `tests/` — ordinary code tests.
- `docs/` — deep documentation, mostly written by and for agents. You do
  not need to read it to own the project; this guide and
  [`query_catalog.md`](query_catalog.md) (the list of what's supported) are
  the two human-facing entry points.
