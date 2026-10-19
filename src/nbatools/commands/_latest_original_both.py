"""Two qualified played checks on one original matchup, never an appearance cohort."""

from __future__ import annotations

import json
import re

from nbatools.commands.structured_results import FinderResult, NoResult

_PREFIX = "yes_no_last_game: "


def read_request(text: str) -> dict | None:
    """Consume the entire bounded question, including both complete identities."""
    from nbatools.commands._matchup_utils import _is_exact_player_reference_phrase, detect_player
    from nbatools.commands._teammate_resolution import _only_the_name
    from nbatools.commands.entity_resolution import TEAM_ALIASES

    text = text.lower().replace("’", "'").strip(" ?.!")
    if not re.search(r"\bboth\b", text):
        return None
    # The scope may lead the question or follow the complete Boolean check.
    pair = r"(?:(?:both\s+)?(?P<a>.+?)\s+and\s+(?P<b>.+?)\s+(?P<both>both\s+)?play)"
    match = re.fullmatch(rf"(?P<scope>.+?)\s*,?\s*did\s+{pair}", text)
    if match is None:
        match = re.fullmatch(rf"did\s+{pair}\s+(?P<scope>.+)", text)
    if match is None or not re.search(r"\bboth\b", match.group(0)):
        return None
    players = []
    for key in ("a", "b"):
        fragment = match[key].strip()
        name = detect_player(fragment)
        if not name or not (
            _is_exact_player_reference_phrase(fragment, name) or _only_the_name(fragment, name)
        ):
            return None
        players.append(name)
    if players[0] == players[1]:
        return None

    scope = match["scope"].strip(" ,")
    seasons = list(
        re.finditer(
            r"\b(?:in|during|of)\s+(?:the\s+)?(?P<season>(?:19|20)\d{2}-\d{2})(?:\s+season)?\b",
            scope,
        )
    )
    if len(seasons) != 1:
        return None
    season_match = seasons[0]
    season = season_match["season"]
    # Reject malformed years instead of letting a resolver silently repair them.
    if int(season[-2:]) != (int(season[:4]) + 1) % 100:
        return None
    scope = (scope[: season_match.start()] + " " + scope[season_match.end() :]).strip()
    dates = list(re.finditer(r"\b(?:before|after|since|through|on)\s+\d{4}-\d{2}-\d{2}\b", scope))
    if len(dates) > 1:
        return None
    start_date = end_date = None
    if dates:
        from datetime import date

        from nbatools.commands._date_utils import extract_date_range

        date_match = dates[0]
        try:
            date.fromisoformat(date_match.group().split()[-1])
        except ValueError:
            return None
        start_date, end_date = extract_date_range(date_match.group(), season)
        if start_date is None and end_date is None:
            return None
        scope = scope[: date_match.start()] + " " + scope[date_match.end() :]
    aliases = "|".join(re.escape(a) for a in sorted(TEAM_ALIASES, key=len, reverse=True))
    scope_pattern = (
        rf"(?:(?:of|in|during|from|for)\s+)?(?:the\s+)?(?P<team>{aliases})(?:'s|')?\s+"
        r"(?:last|latest|most\s+recent)\s+(?:original\s+)?(?:(?:1|one)\s+)?"
        r"(?:(?P<venue>home|road|away)\s+)?(?:game|meeting|matchup)\s+"
        rf"(?:against|versus|vs\.?)\s+(?:the\s+)?(?P<opponent>{aliases})"
    )
    scope_match = re.fullmatch(scope_pattern, re.sub(r"\s+", " ", scope).strip())
    if not scope_match:
        return None
    team, opponent = (TEAM_ALIASES[scope_match[k]] for k in ("team", "opponent"))
    if team == opponent:
        return None
    return {
        "event": "played_pair",
        "players": players,
        "team": team,
        "opponent": opponent,
        "season": season,
        "start_date": start_date,
        "end_date": end_date,
        "home_only": scope_match["venue"] == "home",
        "away_only": scope_match["venue"] in ("road", "away"),
    }


def prepare(out: dict) -> dict:
    """Use the existing yes/no note boundary without introducing a request field."""
    text = out.get("normalized_query") or ""
    request = read_request(text)
    if request is None:
        # A failed full pair reading must not fall back to the one recognized
        # player (notably an unknown first name followed by a known second).
        attempt = re.search(
            r"\bdid\s+(?:both\s+.+?\s+and\s+.+?|.+?\s+and\s+.+?\s+both)"
            r"\s+(?:not\s+)?play\b",
            text,
        )
        if not attempt:
            return out
        result = dict(out)
        kwargs = dict(out.get("route_kwargs") or {})
        kwargs["unsupported_filters"] = list(
            dict.fromkeys([*(kwargs.get("unsupported_filters") or []), "multi_player_availability"])
        )
        # None of the recognized names is the primary answer subject, and
        # an unadmitted check did not apply a with/without matching cohort.
        for key in (
            "player",
            "player_a",
            "player_b",
            "opponent_player",
            "with_player",
            "without_player",
        ):
            result[key] = None
            kwargs[key] = None
        result["route_kwargs"] = kwargs
        return result
    kwargs = {
        k: request[k]
        for k in ("team", "opponent", "season", "start_date", "end_date", "home_only", "away_only")
    }
    kwargs.update(
        season_type="Regular Season",
        last_n=1,
        last_n_scope="window",
        sort_by="game_date",
        limit=1,
        unsupported_filters=[],
    )
    result = dict(out)
    result.update(
        route="game_finder",
        route_kwargs=kwargs,
        player=None,
        with_player=None,
        without_player=None,
        season=request["season"],
        start_season=None,
        end_season=None,
        start_date=request["start_date"],
        end_date=request["end_date"],
        team=request["team"],
        opponent=request["opponent"],
        last_n=1,
        last_n_scope="window",
        stat=None,
        min_value=None,
        max_value=None,
        threshold_conditions=None,
        conditions=None,
        extra_conditions=None,
        count_intent=False,
        home_only=request["home_only"],
        away_only=request["away_only"],
    )
    result["notes"] = list(out.get("notes") or []) + [_PREFIX + json.dumps(request)]
    return result


def request_from_notes(notes: list | None) -> dict | None:
    for note in notes or []:
        if isinstance(note, str) and note.startswith(_PREFIX):
            request = json.loads(note[len(_PREFIX) :])
            if request.get("event") == "played_pair":
                return request
    return None


def build_result(kwargs: dict, request: dict) -> FinderResult | NoResult:
    """Run inside the service's execution boundary: unknown is never a Boolean No."""
    import pandas as pd

    from nbatools.commands._participation_observations import filter_played
    from nbatools.commands.freshness import compute_current_through_for_seasons
    from nbatools.commands.game_summary import select_team_summary_sample

    season, season_type = kwargs["season"], kwargs["season_type"]
    original = select_team_summary_sample(
        season=season,
        season_type=season_type,
        team=kwargs["team"],
        opponent=kwargs["opponent"],
        home_only=kwargs["home_only"],
        away_only=kwargs["away_only"],
        last_n=1,
        last_n_scope="window",
        start_date=kwargs["start_date"],
        end_date=kwargs["end_date"],
    )
    if isinstance(original, NoResult):
        return original
    if original.empty:
        return NoResult(
            query_class="finder",
            notes=["No original matchup game is available to check both players"],
        )
    if len(original) != 1:
        raise ValueError("The original participation check requires exactly one matchup game")
    players = request["players"]
    qualified = filter_played(
        original, " and ".join(players), [season], season_type, opponent_context=True
    )
    passed = not qualified.empty
    row = original.iloc[0]
    day = str(pd.Timestamp(row["game_date"]).date())
    verb = "both played" if passed else "did not both play"
    phrase = (
        f"{'Yes' if passed else 'No'}: {' and '.join(players)} {verb} in the "
        f"{row['team_name']}' latest original game against the {row['opponent_team_name']} ({day})."
    )
    games = original.reset_index(drop=True).copy()
    games.insert(0, "rank", [1])
    return FinderResult(
        games=games,
        current_through=compute_current_through_for_seasons([season], season_type),
        metadata={"answer_phrase": phrase},
        caveats=[
            "Both played predicates were checked on the selected original game. "
            "A No answer means at least one player did not play; "
            "it does not imply that neither played."
        ],
    )
