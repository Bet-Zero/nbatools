# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog:
https://keepachangelog.com/en/1.0.0/

---

## [Unreleased]

### Added
- Natural player season leaderboard coverage:
  - top scorers
  - highest TS%
  - most 30-point games
  - most threes made
- Natural team season leaderboard coverage:
  - best offense
  - best eFG%
  - best TS%
  - most threes
- Matchup and head-to-head coverage:
  - player vs team matchup filters
  - team vs team matchup filters
  - head-to-head phrasing
- Date-aware natural query support:
  - `in <month>`
  - `since <month>`
  - `last <N> days`
  - `since All-Star break`
- Player streak queries:
  - threshold streaks
  - longest streak queries
  - made-three streaks
  - triple-double streaks
- Team streak queries:
  - winning / losing streaks
  - team threshold streaks
  - scoring streak phrasing
- First-class split routing fixes for natural split queries
- Expanded natural-query tests and streak-specific coverage

### Changed
- Natural query routing now covers:
  - player and team leaderboards
  - player and team streaks
  - matchup / head-to-head phrasing
  - month-based and All-Star-break date windows
- Split routing was hardened so split queries resolve to split-summary commands instead of generic finders
- Docs updated to reflect the current shipped query surface
- Full suite expanded to **206 passing tests**

### Fixed
- Team scoring streak phrasing like:
  - `Celtics 5 straight games scoring 120+`
- Split queries incorrectly falling through to game finder routes
- Split override kwargs passing unsupported date arguments
- Team scoring streak regex edge case on `120+`
- Several route-selection and dispatch issues uncovered during streak and split rollout

---

## [0.7.0] - 2026-04-09

### Added
- Grouped boolean query support using:
  - `and`
  - `or`
  - parentheses `(...)`
- Support for grouped boolean logic across:
  - Player game finder
  - Team game finder
  - Player game summary
  - Team game summary
  - Player split summary (home/away, wins/losses)
  - Team split summary (home/away, wins/losses)
- Full boolean expression parsing with:
  - Nested conditions
  - Operator precedence
  - Tree-based evaluation (`AndNode`, `OrNode`, `ConditionNode`)
- New module:
  - `query_boolean_parser.py`
- Sample-aware advanced metrics (v2):
  - USG%
  - AST%
  - REB%
  - Correctly recomputed from filtered game samples
- Safe dataframe injection pattern:
  - Commands accept `df` overrides for filtered subsets
- JSON export support for all commands

### Changed
- Advanced metrics upgraded from season averages → sample-aware recomputation
- Natural query engine now routes grouped boolean queries through:
  - Base dataset loaders
  - Boolean evaluation tree
  - Filtered dataframe execution
- Split summary commands updated to support injected filtered datasets
- Output consistency improved across:
  - summaries
  - splits
  - comparisons

### Fixed
- Incorrect advanced metric values when filtering subsets (USG%, AST%, REB%)
- Boolean queries returning empty results due to missing base dataset loading
- Split summaries incorrectly applying filters twice
- Edge cases in OR query merging and deduplication

### Tests
- Added grouped boolean smoke tests for:
  - Player summary
  - Player split summary
  - Team summary
  - Team split summary
- Added formula tests for advanced metrics v2
- Added boolean parser unit tests
- Test suite expanded to 125 passing tests

---

## [0.6.0] - 2026-04-08

### Added
- Boolean query parsing (`and`, `or`)
- OR query merging for finder queries
- Initial grouped boolean support (finder only)
- Natural language parsing improvements

---

## [0.5.0]

### Added
- Natural query CLI (`nbatools-cli ask`)
- Player comparisons
- Team comparisons
- Split summaries (home/away, wins/losses)

---

## [0.4.0]

### Added
- Advanced metrics v1 (USG%, TS%, eFG%)

---

## [0.3.0]

### Added
- Player and team summaries
- Finder commands
- CLI test harness

---

## [0.2.0]

### Added
- Core CLI structure
- Data loading pipelines

---

## [0.1.0]

### Initial release
