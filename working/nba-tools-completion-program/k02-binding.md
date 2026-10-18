# K02 summary and record acceptance binding

This binds the existing K02 row in the sole completion-program README, not a
new queue or whole-family acceptance claim. Twelve natural/structured pairs
cover the finite scope. Ten reuse previously independently accepted cases;
two add explicit-season anchors. No acquisition, publication, runtime or parser
change is part of this lane.

The raw-key oracle was frozen before interpreter execution in
[k02-raw-oracle.json](k02-raw-oracle.json), SHA256
`7063b4d91ad641f8d0440f3b44d4db4eec64ede562de7b761099605891162021`.
It records exact source hashes, game/team/player keys, W–L, PTS/REB/AST sums
and means on `queue-d-production-0574735-20260716`. Both sources are the already
qualified 2023-24 regular-season player/team CSVs. Raw derivation does not itself
constitute independent-agent acceptance of the two new season anchors.

| IDs | Required sample | Expected games / W–L / PTS sum |
| --- | --- | --- |
| A1 | BOS explicit 2023-24 | 82 /64–18 /9887 |
| A2 | Curry explicit 2023-24 | 74 /43–31 /1956 |
| B1 | BOS vs NYK, 2023-11-01 through2024-03-01 | 3 /3–0 /363 |
| B2 | Curry vs LAL, 2024-01-01 through2024-03-31 | 3 /2–1 /109 |
| C1 /C2 | BOS last10 window >=110PTS /last10qualifying >=110PTS | 6 /5–1 /762;10 /8–2 /1255 |
| C3 /C4 | Curry last10 window >=30PTS /last10qualifying >=30PTS | 2 /1–1 /66;10 /6–4 /364 |
| D1 /D2 | DEN final8 window >=114PTS /final8qualifying >=114PTS | 5 /4–1 /634;8 /7–1 /991 |
| D3 /D4 | Jokic final9 appearances window >=29PTS /final9qualifying >=29PTS | 4 /2–2 /151;9 /7–2 /311 |

All C/D cases explicitly select 2023-24. A threshold applies to the named
subject's own points. Window selects the lastNappearances first; qualifying
filters first then takes the lastNmatches. Dates and opponents both restrict B.
No inference about season-wide participation, injury, or current freshness is made.

## Existing runner selectors and accepted evidence

The complete numerical selection is twelve executed cases, each checking
natural and structured paths against raw rows:

- `tests/test_k02_explicit_season_real_data.py` — A1/A2, two new cases. Require
  exact full-season keys and row counts, identity/season labels, W–L and means.
- `tests/test_sample_order_contract_real_data.py` — B1/B2/C1–C4, six reused
  cases. Preserve date/opponent labels, sample-order badges and exact keys;
  team records capture the actual computation input because their public summary
  does not expose a game log.
- `tests/test_recent_window_meaning_real_data.py` — D1–D4, four reused cases.
  Preserve exact keys, identity, threshold, count and window/qualifying labels.

S5 run [39011364134](https://github.com/Bet-Zero/nbatools/actions/runs/39011364134)
executed six numerical cases with zero skips and six Raw QA cases/42checks;
PR476 merged the accepted sample-order behavior. Final-window run
[39013419722](https://github.com/Bet-Zero/nbatools/actions/runs/39013419722)
executed four numerical cases with zero skips and two Raw QA cases/26checks;
PR480 merged that repair. These prior receipts remain valid bounded evidence,
not an assertion that the entire integrated K02 row or its deployed rendering
has passed. Reuse the qualified source; do not reacquire NBA data for these cases.

Controlled distinctions already execute in `tests/test_sample_order_contract.py`
(six raw fixture samples plus four label/default tests) and
`tests/test_recent_window_meaning.py` (number/appearance grammar and ambiguity
controls). They remain synthetic evidence distinct from NBA numeric checks.

Before an actual integrated runner request, independently confirm A1/A2 raw
truth and the test binding, inspect cached execution and unchanged predecessor
coverage, and review the fixed candidate. The twelve-case actual gate must
execute without skipped or missing required data. Independent unfamiliar wording,
deployed API/rendering and operational acceptance stay separately assessed;
this binding does not mark I/N/L/D complete.

## Cached verification and independent language gap

After the original freeze, all twelve natural/structured pairs passed against
cached qualified rows, and all33existing fixture/grammar controls passed. The
independent checker confirmed both new anchors' exact hashes, keys, W–L and
arithmetic and approved the original twelve-case numerical binding. This is
cached checking, not a new actual-runner receipt.

Four independently frozen fresh language probes and their original results are
retained verbatim in [k02-language-baseline.json](k02-language-baseline.json).
Milwaukee's explicit-season record, Boston's "finish with" record and Curry's
possessive season averages passed. **"Give Devin Booker's averages for the
2023-24 regular season."** was refused by the unresolved-player guard despite
correct player resolution. Its independent raw truth is68games,43–25,
27.073529411764707PTS,4.529411764705882REB,6.9411764705882355AST per game.
This remains a required positive language obligation, not a negative test.

`tests/test_k02_explicit_season_real_data.py::test_k02_fresh_booker_possessive_summary`
freezes that exact request and verifies source hashes, raw arithmetic, all68
unique game/team/player keys and the actual summary. It reproduces the existing
refusal before any runtime repair. Root alone owns the shared parser repair.
The integrated numerical selection now requires **13cases**: the original12
plus this separately frozen fresh-language positive. Do not request acceptance
while that regression fails, or shrink the original binding.

Raw QA reuses six existing `s5_*` cases and
`recent_window_p2_s5_1`/`recent_window_p2_s5_3`; four new cases
`k02_a1`, `k02_a2`, `k02_d2`, `k02_d4` complete the original12case scope without
duplicating predecessor entries. All12cached QA cases passed170checks, including
83new hard assertions; no suspicious flags. The exact selection is:

```
k02_a1, k02_a2,
s5_team_date_opponent, s5_player_date_opponent,
s5_team_last_n_window, s5_team_last_n_qualifying,
s5_player_last_n_window, s5_player_last_n_qualifying,
recent_window_p2_s5_1, k02_d2, recent_window_p2_s5_3, k02_d4
```

Original human-review fields retain their historical literal meanings. Passing
these QA cases does not close the Booker gap, deployed rendering, or broader K02
language acceptance. Baseline failures and frozen oracle values remain unchanged.

## Current runtime and validation

Local8ca5c6f separates the imperative summary command from the full candidate
player name before typo validation. A polite response request such as show-me
or give-me no longer chooses finder output when an explicit summary is asked;
explicit game-list wording retains its grain. Genuine misspelled given names
remain refused. The original Booker refusal is unchanged in the baseline.

All13 complete cached raw selectors now pass, with natural/structured pairs
retained for the original12. Add RawQA `k02_booker_command` to the12IDs above:
all13cases/183checks passed.53focused grammar/identity/list controls passed.
Final preflight8107passed1530skipped5warnings142.19s; local skips are not real-data
acceptance. Checker /root/availability_checker independently verified the Booker
repair, polite summary versus explicit list wording, genuine-name-typo refusal
and43-game win-only subset. Bounded13numerical+13RawQA request approved conditional
on normalCI. Actual runner and deployed K02 verification remain pending.
