# Bare Player Vs Player Query Policy Preflight Return Package

Date: 2026-05-31

## Objective

Decide the product policy for bare player-vs-player natural queries such as:

```text
LeBron vs KD
```

This was a product-policy preflight only. No production code, parser/routing
behavior, frontend rendering, corpus expectations, release status, or QA cases
were changed.

## Files Changed

- `docs/planning/raw-product/BARE_PLAYER_VS_PLAYER_QUERY_POLICY_PREFLIGHT.md`
- `return_packages/raw-product/BARE_PLAYER_VS_PLAYER_QUERY_POLICY_PREFLIGHT_RETURN_PACKAGE.md`
- `docs/index.md`

## Policy Decision

V1 policy recommendation: bare `PLAYER vs PLAYER` should not be public-accepted
or advertised as `player_compare`.

Preferred V1 implementation behavior is a clean ambiguous/unsupported result
until a typed clarification response and UI exist.

Future ideal behavior is a typed clarification flow with options for:

- simple player stat comparison
- player head-to-head games
- one player's stats/games against the other player
- playoff matchup/history when applicable and supported

## Current Behavior Evidence

Probe path:

```text
nbatools.query_service.execute_natural_query(query)
nbatools.api_handlers.query_result_to_payload(result)
```

Requested probes:

| Query | Current route | Current status | Current interpretation |
| --- | --- | --- | --- |
| `LeBron vs KD` | `player_compare` | `ok` | Silent simple current-season player stat comparison. |
| `LeBron James vs Kevin Durant` | `player_compare` | `ok` | Silent simple current-season player stat comparison. |
| `Jokic vs Embiid` | `player_compare` | `ok` | Silent simple current-season player stat comparison. |
| `Celtics vs Bucks` | `team_compare` | `ok` | Silent simple current-season team stat comparison. |
| `Lakers vs Celtics` | `team_compare` | `ok` | Silent simple current-season team stat comparison. |
| `LeBron stats vs KD` | `player_game_finder` | `ok` | Player-opponent game finder semantics. |
| `Lakers record vs Celtics` | `team_record` | `ok` | Team record with opponent filter. |

Contrast probes:

| Query | Current route | Current status | Current interpretation |
| --- | --- | --- | --- |
| `Jokic head-to-head vs Embiid since 2021` | `player_compare` | `ok` | Explicit player head-to-head sample. |
| `Jokic game log vs Embiid` | `player_game_finder` | `no_result` | Game-log wording is not treated as stat comparison. |
| `Lakers vs Celtics head to head record` | `team_matchup_record` | `ok` | Explicit team matchup record. |
| `Lakers Celtics playoff matchup history` | `playoff_matchup_history` | `ok` | Explicit playoff matchup history. |

## Corpus Guidance

Do not add an expected-ok public acceptance case for bare `LeBron vs KD`,
`LeBron James vs Kevin Durant`, or `Jokic vs Embiid` as `player_compare`.

Continue to rely on disambiguated comparison cases:

- `LeBron James vs Kevin Durant comparison`
- `Compare LeBron James and Kevin Durant`
- `How do LeBron James and Kevin Durant compare this season?`
- `Jokic vs Embiid recent form`

If option C is implemented before clarification UI exists, add a boundary case
that expects clean ambiguous/unsupported behavior. If option B is implemented,
assert the typed ambiguity payload and available intent options.

## Documentation Guidance

Do not advertise bare `LeBron vs KD` as supported.

Advertise disambiguated wording instead:

- `Compare LeBron and KD this season`
- `LeBron James vs Kevin Durant comparison`
- `How do LeBron James and Kevin Durant compare this season?`
- `Jokic vs Embiid recent form`

Reference docs were intentionally not changed in this preflight because no
behavior or public acceptance policy was implemented.

## Stop Conditions For Later Implementation

Stop before implementation if any of these are unresolved:

- typed ambiguity/clarification response shape
- CLI ambiguity rendering
- React UI ambiguity rendering
- route/reason contract for clean ambiguous unsupported behavior
- corpus expectation would encode the current silent default
- docs would advertise bare `PLAYER vs PLAYER` before the policy is implemented
- explicit comparison, player-opponent, team matchup, or playoff-history routes
  regress

## Validation

Docs-only validation:

- `git diff --check`: passed for tracked diff
- `git diff --check --no-index /dev/null docs/planning/raw-product/BARE_PLAYER_VS_PLAYER_QUERY_POLICY_PREFLIGHT.md`:
  no whitespace warnings; exit code `1` is expected for `/dev/null` comparisons
  with file content
- `git diff --check --no-index /dev/null return_packages/raw-product/BARE_PLAYER_VS_PLAYER_QUERY_POLICY_PREFLIGHT_RETURN_PACKAGE.md`:
  no whitespace warnings; exit code `1` is expected for `/dev/null` comparisons
  with file content
- Markdown lint: not run; no `markdownlint`, `markdownlint-cli2`, `mdl`, or
  `mdformat` command was found on PATH, and no repo-local markdown lint target
  was found in `Makefile`, `pyproject.toml`, or `frontend/package.json`
