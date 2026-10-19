"""Qualified played checks on one original team game, never an appearance cohort."""

from __future__ import annotations

import json
import re

from nbatools.commands.structured_results import FinderResult, NoResult

_PREFIX = "yes_no_last_game: "


def read_request(text: str) -> dict | None:
    """Consume the entire bounded question, including both complete identities."""
    from nbatools.commands._matchup_utils import _is_exact_player_reference_phrase, detect_player
    from nbatools.commands._teammate_resolution import _only_the_name

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

    scope = _read_scope(match["scope"])
    return {**scope, "event": "played_pair", "players": players} if scope else None


def _read_scope(scope: str, *, require_matchup=True, require_season=True) -> dict | None:
    """Static original-game scope shared by one- and two-player checks."""
    from nbatools.commands.entity_resolution import TEAM_ALIASES

    scope = scope.strip(" ,")
    seasons = list(
        re.finditer(
            r"\b(?:in|during|of)\s+(?:the\s+)?(?P<season>(?:19|20)\d{2}-\d{2})(?:\s+season)?\b",
            scope,
        )
    )
    if len(seasons) > 1 or (require_season and not seasons):
        return None
    season_match = seasons[0] if seasons else None
    season = season_match["season"] if season_match else None
    # Reject malformed years instead of letting a resolver silently repair them.
    if season and int(season[-2:]) != (int(season[:4]) + 1) % 100:
        return None
    if season_match:
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
    last_game = (
        r"(?:last|latest|most\s+recent)\s+(?:original\s+)?(?:(?:1|one)\s+)?"
        r"(?:(?P<venue>home|road|away)\s+)?(?:game|meeting|matchup)"
    )
    matchup = rf"\s+(?:against|versus|vs\.?)\s+(?:the\s+)?(?P<opponent>{aliases})"
    if not require_matchup:
        matchup = rf"(?:{matchup})?"
    pattern = (
        rf"(?:(?:of|in|during|from|for)\s+)?(?:the\s+)?(?P<team>{aliases})(?:'s|')?\s+"
        + last_game
        + matchup
    )
    clean = re.sub(r"\s+", " ", scope).strip()
    scope_match = re.fullmatch(pattern, clean)
    if scope_match:
        team = TEAM_ALIASES[scope_match["team"]]
        opponent = TEAM_ALIASES[scope_match["opponent"]] if scope_match["opponent"] else None
    elif not require_matchup:
        scope_match = re.fullmatch(
            r"(?:(?:in|of)\s+)?(?:(?:(?:his|her|their)(?:\s+team's)?|the|team's)\s+)?" + last_game,
            clean,
        )
        if not scope_match:
            return None
        team = opponent = None
    else:
        return None
    if team and team == opponent:
        return None
    return {
        "team": team,
        "opponent": opponent,
        "season": season,
        "start_date": start_date,
        "end_date": end_date,
        "home_only": scope_match["venue"] == "home",
        "away_only": scope_match["venue"] in ("road", "away"),
    }


def _read_scalar_request(text: str, out: dict) -> dict | None:
    from nbatools.commands._matchup_utils import _is_exact_player_reference_phrase, detect_player
    from nbatools.commands._teammate_resolution import _only_the_name

    # Preserve the existing scalar yes/no auxiliaries, not just Did. Every
    # reading still consumes the complete single identity and original scope.
    verb = r"(?:did|does|do|was|were|is|has|have|had)"
    played = r"play(?:ed|s)?"
    match = re.fullmatch(rf"(?P<scope>.+?)\s*,?\s*{verb}\s+(?P<name>.+?)\s+{played}", text)
    if match is None:
        match = re.fullmatch(rf"{verb}\s+(?P<name>.+?)\s+{played}\s+(?P<scope>.+)", text)
        # Playing FOR a team has separate ownership meaning, not merely the
        # game selected by the leading scope "For the Lakers' last game ...".
        if match and match["scope"].startswith("for "):
            return None
    if match is None:
        return None
    fragment = match["name"].strip()
    player = detect_player(fragment)
    if not player or not (
        _is_exact_player_reference_phrase(fragment, player) or _only_the_name(fragment, player)
    ):
        return None
    scope = _read_scope(match["scope"], require_matchup=False, require_season=False)
    if scope is None or (out.get("season_type") or "Regular Season") != "Regular Season":
        return None
    # Keep the existing implicit-season choice, not a new calendar/freshness rule.
    scope["season"] = scope["season"] or out.get("season")
    if not scope["season"]:
        return None
    return {**scope, "event": "played_scalar", "players": [player]}


def prepare(out: dict) -> dict:
    """Use the existing yes/no note boundary without introducing a request field."""
    text = out.get("normalized_query") or ""
    request = read_request(text) or _read_scalar_request(text, out)
    if request is None:
        # A failed full pair reading must not fall back to the one recognized
        # player (notably an unknown first name followed by a known second).
        attempt = re.search(
            r"\bdid\s+(?:both\s+.+?\s+and\s+.+?|.+?\s+and\s+.+?\s+both)"
            r"\s+(?:not\s+)?play\b",
            text,
        )
        scalar_match = re.search(
            r"\b(?:did|does|do|was|were|is|has|have|had)\s+.+?\s+play(?:ed|s)?\b", text
        )
        scalar_attempt = False
        if scalar_match:
            prefix = text[: scalar_match.start()].strip()
            # "What was the Lakers record ... Reaves plays" is a record,
            # not a failed scalar question. A leading scope must itself be
            # consumed, or delimit the auxiliary with a question comma.
            scalar_attempt = (
                not prefix
                or prefix.endswith(",")
                or _read_scope(prefix, require_matchup=False, require_season=False) is not None
            )
        if not attempt and not scalar_attempt:
            return out
        result = dict(out)
        kwargs = dict(out.get("route_kwargs") or {})
        kwargs["unsupported_filters"] = list(
            dict.fromkeys(
                [
                    *(kwargs.get("unsupported_filters") or []),
                    "multi_player_availability" if attempt else "scalar_participation",
                ]
            )
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
    from nbatools.commands._confidence import compute_parse_confidence, generate_alternates
    from nbatools.commands._constants import route_to_intent

    result = dict(out)
    result.update(
        route="game_finder",
        intent=route_to_intent("game_finder"),
        route_kwargs=kwargs,
        unsupported_filters=[],
        season_type="Regular Season",
        player=request["players"][0] if len(request["players"]) == 1 else None,
        player_a=None,
        player_b=None,
        opponent_player=None,
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
    # The whole request is now admitted by this reader. Retain contextual
    # notes, but replace the old reader's refusal rather than contradict the
    # executed answer with "no result was executed".
    result["notes"] = [
        note
        for note in out.get("notes") or []
        if not (
            isinstance(note, str)
            and note.startswith(("unsupported_boundary:", "sample_advanced_metrics:", _PREFIX))
        )
    ] + [_PREFIX + json.dumps(request)]
    result["confidence"] = compute_parse_confidence(result)
    result["alternates"] = generate_alternates(result)
    return result


def request_from_notes(notes: list | None) -> dict | None:
    for note in notes or []:
        if isinstance(note, str) and note.startswith(_PREFIX):
            request = json.loads(note[len(_PREFIX) :])
            if request.get("event") in ("played_pair", "played_scalar"):
                return request
    return None


def build_result(kwargs: dict, request: dict) -> FinderResult | NoResult:
    """Run inside the service's execution boundary: unknown is never a Boolean No."""
    import pandas as pd

    from nbatools.commands._participation_observations import filter_played
    from nbatools.commands._player_identity import select_player_rows
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.commands.freshness import compute_current_through_for_seasons
    from nbatools.commands.game_summary import select_team_summary_sample

    season, season_type = kwargs["season"], kwargs["season_type"]
    players = request["players"]
    scalar = len(players) == 1
    team = kwargs["team"]
    inferred = team is None
    if inferred:
        # A historical appearance supplies a candidate team, not membership
        # proof. Qualification below must establish the player's subject side.
        appearances = load_player_games_for_seasons([season], season_type)
        own = select_player_rows(appearances, players[0])
        own = own.loc[pd.to_numeric(own.minutes, errors="coerce").gt(0)]
        if own.empty:
            raise ValueError("No qualified candidate team for the participation check")
        team = str(own.sort_values(["game_date", "game_id"]).iloc[-1].team_abbr)
    original = select_team_summary_sample(
        season=season,
        season_type=season_type,
        team=team,
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
            notes=["No original team game is available for the played check"],
        )
    if len(original) != 1:
        raise ValueError("The original participation check requires exactly one matchup game")
    qualified = filter_played(
        original, " and ".join(players), [season], season_type, opponent_context=True
    )
    passed = not qualified.empty
    if inferred:
        from nbatools.commands._participation_observations import filter_absent

        own_check = filter_played if passed else filter_absent
        if own_check(original, players[0], [season], season_type).empty:
            raise ValueError("The inferred candidate lacks qualified subject-side membership")
    row = original.iloc[0]
    day = str(pd.Timestamp(row["game_date"]).date())
    if scalar:
        verb = "played" if passed else "did not play"
        matchup = f" against the {row['opponent_team_name']}" if kwargs["opponent"] else ""
        where = f"({day})" if matchup else f"({day} vs the {row['opponent_team_name']})"
        phrase = (
            f"{'Yes' if passed else 'No'}: {players[0]} {verb} in the "
            f"{row['team_name']}' last game{matchup} {where}"
        )
        if passed:
            # Keep useful basic Yes details only from this game's positive row.
            try:
                appearances = load_player_games_for_seasons([season], season_type)
            except FileNotFoundError:
                appearances = pd.DataFrame()
            if not appearances.empty:
                own = select_player_rows(appearances, players[0])
                own = own.loc[
                    own.game_id.astype(int).eq(int(row.game_id))
                    & pd.to_datetime(own.game_date).dt.date.eq(pd.Timestamp(row.game_date).date())
                    & own.team_id.astype(int).isin([int(row.team_id), int(row.opponent_team_id)])
                    & pd.to_numeric(own.minutes, errors="coerce").gt(0)
                ]
                if len(own) == 1:
                    actual = own.iloc[0]
                    values = [
                        f"{float(actual[c]):g} {word}"
                        for c, word in [("pts", "points"), ("reb", "rebounds"), ("ast", "assists")]
                        if c in actual and pd.notna(actual[c])
                    ]
                    if values:
                        line = ", ".join(values)
                        phrase += ": " + (" and".join(line.rsplit(",", 1)) if "," in line else line)
        phrase += "."
    else:
        verb = "both played" if passed else "did not both play"
        phrase = (
            f"{'Yes' if passed else 'No'}: {' and '.join(players)} {verb} in the "
            f"{row['team_name']}' latest original game against the "
            f"{row['opponent_team_name']} ({day})."
        )
    games = original.reset_index(drop=True).copy()
    games.insert(0, "rank", [1])
    return FinderResult(
        games=games,
        current_through=compute_current_through_for_seasons([season], season_type),
        metadata={"answer_phrase": phrase},
        caveats=[
            "The played check is qualified on the selected original game. "
            "Table values are team-game totals, not the checked player's statistics."
        ]
        if scalar
        else [
            "Both played predicates were checked on the selected original game. "
            "A No answer means at least one player did not play; "
            "it does not imply that neither played."
        ],
    )
