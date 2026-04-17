# NBA Tools Quick Query Guide

> **Role: quick-start examples.**
> This is the fastest way to see what you can ask. For the full reference
> (including structured CLI commands), see [query_guide.md](query_guide.md).
> For verified shipped behavior details, see
> [current_state_guide.md](current_state_guide.md).

Learn the current NBA Tools query surface fast.

---

## Core idea

You can ask for:

- leaderboards
- summaries
- comparisons
- splits
- filtered game finds
- matchup / head-to-head queries
- date-aware windows
- streaks

---

## 1. Recent form

Examples:
Jokic recent form
Celtics recent form
Jokic vs Embiid recent form

Default recent-form window:
last 10 games

---

## 2. Leaderboards

Player leaderboards:
top scorers this season
highest ts% among players
most 30 point games

Team leaderboards:
best offensive teams
teams with best efg%
teams with most threes

---

## 3. Matchups and head-to-head

Player vs team:
Jokic vs Lakers
Jokic last 10 vs Lakers
Jokic summary vs Lakers

Head-to-head:
Embiid head-to-head vs Jokic
Jokic h2h vs Embiid
Lakers head-to-head vs Celtics
Celtics h2h vs Bucks home

---

## 4. Splits

Home vs away:
Jokic home vs away in 2025-26

Wins vs losses:
Celtics wins vs losses

---

## 5. Dates and windows

Month window:
top scorers in March
best offensive teams in March

Open-ended month window:
best offensive teams since January

Special NBA window:
Jokic since All-Star break
best offensive teams since All-Star break

---

## 6. Streaks

Player streaks:
Jokic 5 straight games with 20+ points
Jokic longest streak of 30 point games
Jokic consecutive games with a made three
Jokic longest triple-double streak

Team streaks:
longest Lakers winning streak
longest Bucks streak with 15+ threes
Thunder consecutive games with 110+ points
Celtics 5 straight games scoring 120+

---

## 7. Thresholds

Over:
Jokic over 25 points

Under:
Jokic under 20 points

Between:
Jokic between 20 and 30 points

---

## 8. Multi-condition queries

Use `and`:
Jokic last 10 games over 25 points and over 10 rebounds
Celtics wins vs Bucks over 120 points and over 15 threes
Jokic last 10 games over 25 points and under 15 rebounds

Use `or`:
Jokic over 25 points or over 10 rebounds
Jokic between 20 and 30 points or under 10 rebounds

Use parentheses:
Jokic (over 25 points and over 10 rebounds) or over 15 assists
Jokic over 25 points and (over 10 rebounds or over 15 assists)
Celtics (over 120 points and over 15 threes) or under 10 turnovers

Grouped boolean logic currently works across:

- finders
- summaries
- split summaries

---

## 9. Advanced metrics you’ll see

Summaries, comparisons, and player splits can show:

- eFG%
- TS%
- USG%
- AST%
- REB%

USG%, AST%, and REB% are recomputed from the filtered player sample.

---

## 10. Export results

Natural query exports:
nbatools-cli ask "Jokic recent form" --txt outputs/jokic_recent.txt
nbatools-cli ask "top scorers in March" --csv outputs/top_scorers_march.csv
nbatools-cli ask "Jokic vs Embiid recent form" --json outputs/jokic_embiid_recent.json

Structured query exports:
nbatools-cli query player-game-summary --player "Nikola Jokić" --season 2025-26 --json outputs/player_summary.json

---

## 11. Good starter queries

    Jokic recent form
    top scorers this season
    best offensive teams
    Jokic vs Lakers
    Jokic since All-Star break
    Jokic 5 straight games with 20+ points
    longest Lakers winning streak
    Jokic home vs away in 2025-26
    Jokic (over 25 points and over 10 rebounds) or over 15 assists
