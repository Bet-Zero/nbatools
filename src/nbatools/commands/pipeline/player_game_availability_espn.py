"""Game-day ESPN boxscore adapter when NBA Stats is unreachable.

An ESPN athlete id is NOT an NBA player id. Verify a game by day, both teams
and BOTH final scores; map only uniquely identified NBA players in that team's
season data. Omitted athletes are unknown, never assumed absent or injured.
"""

from __future__ import annotations

import json
import re
import unicodedata
import urllib.request
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/"
ESPN_ABBRS = {"GS": "GSW", "NY": "NYK", "SA": "SAS", "NO": "NOP", "WSH": "WAS"}


def _get_json(endpoint: str) -> dict:
    request = urllib.request.Request(
        BASE_URL + endpoint,
        headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; NBATools game status importer)",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


@lru_cache(maxsize=128)
def _scoreboard(day: str) -> dict:
    return _get_json(f"scoreboard?dates={day.replace('-', '')}")


def _abbr(value: object) -> str:
    short = str(value or "").strip().upper()
    return ESPN_ABBRS.get(short, short)


def _name(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode().lower()
    parts = re.sub(r"[^a-z0-9 ]", " ", text).split()
    while parts and parts[-1] in {"jr", "sr", "ii", "iii", "iv"}:
        parts.pop()
    return " ".join(parts)


def _nba_players(root: Path, season: str, safe: str) -> pd.DataFrame:
    frames = []
    start = int(season[:4])
    previous = f"{start - 1}-{str(start)[-2:]}"
    # Prior-season rows resolve identity only. The game-specific source must
    # independently list the athlete under this team; no membership is inferred.
    paths = [
        path
        for year in (season, previous)
        for path in (
            root / "raw/player_game_stats" / f"{year}_{safe}.csv",
            root / "raw/rosters" / f"{year}.csv",
        )
    ]
    for path in paths:
        if path.is_file():
            df = pd.read_csv(path)
            keys = {"team_id", "player_id", "player_name"}
            if keys.issubset(df.columns):
                frames.append(df[list(keys)])
    if not frames:
        raise ValueError("ESPN player IDs require canonical NBA player/roster data")
    out = pd.concat(frames, ignore_index=True).dropna().copy()
    out["team_id"] = pd.to_numeric(out.team_id, errors="raise").astype(int)
    out["player_id"] = pd.to_numeric(out.player_id, errors="raise").astype(int)
    out["normalized"] = out.player_name.map(_name)
    return out.drop_duplicates()


def _nba_teams(root: Path, season: str, safe: str, game_id: int) -> dict[str, tuple[int, int]]:
    path = root / "raw/team_game_stats" / f"{season}_{safe}.csv"
    df = pd.read_csv(path, dtype={"game_id": str})
    keys = {"game_id", "team_id", "team_abbr", "pts"}
    if not keys.issubset(df.columns):
        raise ValueError("NBA team score/identity data unavailable for ESPN match")
    rows = df[df.game_id.map(int).eq(game_id)]
    if len(rows) != 2 or rows.team_id.nunique() != 2:
        raise ValueError("NBA team-game source must have exactly two distinct teams")
    output = {}
    for row in rows.itertuples(index=False):
        score = float(row.pts)
        if not score.is_integer() or score < 0:
            raise ValueError("Invalid NBA final score")
        output[_abbr(row.team_abbr)] = (int(row.team_id), int(score))
    if len(output) != 2:
        raise ValueError("Ambiguous NBA team abbreviations")
    return output


def espn_boxscore_as_v3(
    *,
    game_id: int,
    game_date: str,
    season: str,
    season_type: str,
    home_team_id: int,
    away_team_id: int,
    data_root: Path,
) -> tuple[pd.DataFrame, str]:
    """Return only explicitly reported player records with verified NBA identities."""
    safe = season_type.lower().replace(" ", "_")
    teams = _nba_teams(data_root, season, safe, game_id)
    if {ident for ident, _ in teams.values()} != {home_team_id, away_team_id}:
        raise ValueError("NBA game catalog conflicts with team-game source")
    matched = []

    def verified_competition(event: dict) -> bool:
        """Bind a completed source event to NBA date, sides and final scores."""
        try:
            competitions = event["competitions"]
            if len(competitions) != 1:
                return False
            competition = competitions[0]
            stamp = datetime.fromisoformat(competition["date"].replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                return False
            if stamp.astimezone(ZoneInfo("America/New_York")).date().isoformat() != game_date:
                return False
            if competition["status"]["type"]["completed"] is not True:
                return False
            competitors = competition["competitors"]
            if len(competitors) != 2:
                return False
            expected = {
                team: ("home" if ident == home_team_id else "away", score)
                for team, (ident, score) in teams.items()
            }
            actual = {
                _abbr(c["team"]["abbreviation"]): (c["homeAway"], int(c["score"]))
                for c in competitors
            }
            return actual == expected
        except (KeyError, TypeError, ValueError, AttributeError):
            return False

    for event in _scoreboard(game_date).get("events", []):
        if verified_competition(event) and str(event.get("id", "")).isdigit():
            matched.append(str(event["id"]))
    if len(matched) != 1:
        raise ValueError(f"No unique score/team/date match for NBA game {game_id}")
    event_id = matched[0]
    summary = _get_json(f"summary?event={event_id}")
    header = summary.get("header") or {}
    if str(header.get("id")) != event_id or not verified_competition(header):
        raise ValueError("ESPN summary identity/date/status differs from verified NBA game")
    raw_teams = (summary.get("boxscore") or {}).get("players") or []
    if len(raw_teams) != 2:
        raise ValueError("ESPN box score missing the two teams")
    persons = _nba_players(data_root, season, safe)
    output = []
    seen = set()
    for entry in raw_teams:
        team = _abbr((entry.get("team") or {}).get("abbreviation"))
        if team not in teams or team in seen:
            raise ValueError("ESPN team does not match verified NBA game")
        seen.add(team)
        nba_team_id = teams[team][0]
        for stat in entry.get("statistics", []):
            keys = stat.get("names") or []
            if "MIN" not in keys:
                raise ValueError("ESPN box-score player table lacks MIN")
            minute_index = keys.index("MIN")
            for athlete in stat.get("athletes", []):
                espn_name = str((athlete.get("athlete") or {}).get("displayName") or "")
                ids = persons[
                    persons.team_id.eq(nba_team_id) & persons.normalized.eq(_name(espn_name))
                ].player_id.unique()
                if len(ids) != 1:
                    raise ValueError(
                        f"Unresolved ESPN-to-NBA player ID: {espn_name!r} "
                        f"on {team} ({season}), candidates={len(ids)}"
                    )
                played = athlete.get("didNotPlay")
                if type(played) is not bool:
                    raise ValueError("ESPN player lacks didNotPlay observation")
                stats = athlete.get("stats") or []
                minutes = stats[minute_index] if len(stats) > minute_index else None
                if minutes in {"--", "-", "DNP", ""}:
                    minutes = None
                # ESPN reason can be a default even for players who played;
                # retain only the explicit didNotPlay flag, not an injury cause.
                comment = "DNP - ESPN confirmed didNotPlay" if played else ""
                nba_name = persons.loc[persons.player_id.eq(int(ids[0]))].iloc[0].player_name
                words = str(nba_name).split(" ", 1)
                output.append(
                    {
                        "gameId": game_id,
                        "teamId": nba_team_id,
                        "teamTricode": team,
                        "personId": int(ids[0]),
                        "firstName": words[0],
                        "familyName": words[1] if len(words) > 1 else words[0],
                        "minutes": minutes,
                        "comment": comment,
                    }
                )
    if len(seen) != 2 or not output:
        raise ValueError("ESPN summary has missing team/athlete data")
    return pd.DataFrame(output), event_id
