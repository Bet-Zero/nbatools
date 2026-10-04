import re

from nbatools.commands._constants import STAT_ALIASES, STAT_PATTERN
from nbatools.commands._glossary import FUZZY_LAST_N_TERMS, OPPONENT_QUALITY_TERMS
from nbatools.commands._leaderboard_utils import (
    detect_player_leaderboard_stat,
    detect_team_leaderboard_stat,
)
from nbatools.commands._matchup_utils import detect_player
from nbatools.commands.entity_resolution import (
    _normalize_for_matching,
    player_last_name_candidates,
    resolve_player,
    resolve_players_in_query,
)

# "best 3 point percentage" names the three-point stat, not a top-3 list.
_NOT_A_COUNT = r"(?!\s*-?\s*(?:point|pt|pointers?|ptrs?|p%|pa|pm|fg)\b)"


def extract_top_n(text: str) -> int | None:
    # "top N" pattern
    m = re.search(rf"\btop\s+(\d+)\b{_NOT_A_COUNT}", text)
    if m:
        value = int(m.group(1))
        return value if value > 0 else None
    # "bottom N" pattern
    m = re.search(rf"\bbottom\s+(\d+)\b{_NOT_A_COUNT}", text)
    if m:
        value = int(m.group(1))
        return value if value > 0 else None
    # "rank N" / "best N" / "worst N" pattern (e.g. "best 10 scorers")
    m = re.search(rf"\b(?:best|worst)\s+(\d+)\b{_NOT_A_COUNT}", text)
    if m:
        value = int(m.group(1))
        return value if value > 0 else None
    return None


def wants_leaderboard(text: str) -> bool:
    if re.search(
        r"\bseason leaders?\b|\bled the league\b|\bleaders?\s+in\b"
        r"|\bleads?\s+(?:the\s+)?(?:nba|league)\s+in\b"
        r"|\b(?:career|playoff|all[- ]?time)\s+(?:\w+\s+)*leaders?\b"
        r"|\bleaders?\s+(?:since|last|past|this|over)\b"
        r"|\brank\b|\branked\b|\branking\b|\bwho\s+(?:has|had|leads?|led)\s+the\s+most\b"
        r"|\brank\s+(?:players?|teams?)\s+by\b",
        text,
    ):
        return True

    if re.search(
        r"\bin a game\b|\bsingle game\b|\bgame high\b|\bgame-high\b|\bseason[- ]?high\b", text
    ):
        return False

    # "top/highest/best scoring games" -> single-game-best, not a season leaderboard.
    if re.search(
        rf"\b(?:top|highest|best)\s+(?:single[- ]?)?(?:(?:team|player)\s+)?"
        rf"{STAT_PATTERN}\s+(?:(?:team|player)\s+)?games?\b",
        text,
    ):
        return False

    if detect_player_leaderboard_stat(text) is None:
        return False

    # Stat-alias + the noun "leaders" anywhere is a strong leaderboard signal.
    # Covers `scoring leaders`, `points leaders`, `last 10 scoring leaders`,
    # etc., where no operator word like `most`/`best` is present.
    if re.search(r"\bleaders?\b", text):
        return True

    # "who led/leads ... in <stat>" is leaderboard intent even without an
    # explicit "the most" ("who led the playoffs in scoring").
    if re.search(r"\bwho\s+(?:leads?|led)\b", text):
        return True

    return bool(
        re.search(
            r"\btop(?:\s+\d+)?\b|\bhighest\b|\bmost\b|\bbest\b|\bhottest\b|\blowest\b|\bfewest\b|\bleast\b|\bworst\b|\bbottom(?:\s+\d+)?\b",
            text,
        )
    )


# ---------------------------------------------------------------------------
# Position / subset filtering for leaderboard queries
# ---------------------------------------------------------------------------

_POSITION_GROUP_PATTERNS: dict[str, str] = {
    "guards": "guards",
    "guard": "guards",
    "point guards": "guards",
    "point guard": "guards",
    "shooting guards": "guards",
    "shooting guard": "guards",
    "forwards": "forwards",
    "forward": "forwards",
    "small forwards": "forwards",
    "small forward": "forwards",
    "power forwards": "forwards",
    "power forward": "forwards",
    "centers": "centers",
    "center": "centers",
    "bigs": "bigs",
    "big men": "bigs",
    "big man": "bigs",
    "wings": "wings",
    "wing": "wings",
}


def _position_term_pattern() -> str:
    terms = sorted(_POSITION_GROUP_PATTERNS, key=len, reverse=True)
    return "|".join(re.escape(term) for term in terms)


def extract_position_filter(text: str) -> str | None:
    """Extract a position-group filter from the query text.

    Returns the canonical position group name or None.
    """
    position_pattern = _position_term_pattern()

    # "among guards", "among centers", "among big men", etc.
    m = re.search(
        r"\bamong\s+([\w\s]+?)(?=\s+(?:since|this|last|over|in|from|during)\b|[^\w\s]|$)",
        text,
    )
    if m:
        candidate = m.group(1).strip()  # already lowercase from pipeline normalization
        if candidate in _POSITION_GROUP_PATTERNS:
            return _POSITION_GROUP_PATTERNS[candidate]

    # "by guards", "for centers", etc.
    m = re.search(rf"\b(?:by|for)\s+({position_pattern})\b", text)
    if m:
        candidate = m.group(1).strip()  # already lowercase from pipeline normalization
        if candidate in _POSITION_GROUP_PATTERNS:
            return _POSITION_GROUP_PATTERNS[candidate]

    # Noun-prefix leaderboard forms:
    # "centers rebound leaders", "guard scoring leaders",
    # "Which centers have the most rebounds".
    m = re.search(
        rf"^(?:which\s+|what\s+)?({position_pattern})\b"
        r"(?=\s+(?:"
        r"have|has|had|average|averages|averaged|lead|leads|led|leaders?|"
        r"scoring|score|scores|points?|pts|rebound(?:s|ing)?|reb|assists?|ast|"
        r"blocks?|blk|steals?|stl|turnovers?|tov|fg|field|effective|true|"
        r"three|3|ts|efg|ft|free"
        r")\b)",
        text,
    )
    if m:
        candidate = m.group(1).strip()
        if candidate in _POSITION_GROUP_PATTERNS:
            return _POSITION_GROUP_PATTERNS[candidate]

    return None


def detect_rookie_leaderboard_boundary(text: str) -> bool:
    """Detect rookie leaderboard requests ("rookie scoring leaders")."""
    if re.search(r"\b(?:top|best|leading)\s+rookies?\b", text):
        return True
    return bool(re.search(r"\brookies?\b", text) and wants_leaderboard(text))


def detect_sophomore_leaderboard_boundary(text: str) -> bool:
    """Detect sophomore (second-year) leaderboard requests."""
    if re.search(r"\b(?:top|best|leading)\s+sophomores?\b", text):
        return True
    has_sophomore = bool(re.search(r"\bsophomores?\b|\b(?:2nd|second)[\s-]year\b", text))
    return bool(has_sophomore and wants_leaderboard(text))


_TEAM_LEADER_STAT_NOUNS = {
    "scorer": "pts",
    "scorers": "pts",
    "scoring": "pts",
    "rebounder": "reb",
    "rebounders": "reb",
    "rebounding": "reb",
    "passer": "ast",
    "passers": "ast",
}


def detect_team_leader_stat(text: str) -> str | None:
    """Return the stat for a team-scoped player-leader ask, else None.

    Handles "Lakers leading scorer", "who scores the most for the Celtics",
    and "Lakers leader in assists". These are objective (per-game leader),
    distinct from the subjective "best player on the Lakers".
    """
    # Person-nouns only ("top scorer"), never "top scoring games" which is a
    # game-level query.
    m = re.search(
        r"\b(?:leading|top|best)\s+(scorer|scorers|rebounder|rebounders|passer|passers)\b",
        text,
    )
    if m:
        return _TEAM_LEADER_STAT_NOUNS.get(m.group(1))
    if re.search(r"\bwho\s+(?:scores?|score)\s+(?:the\s+)?most\b", text):
        return "pts"
    if re.search(r"\bleads?\s+(?:the\s+team\s+)?in\s+scoring\b", text):
        return "pts"
    m = re.search(r"\bleader\s+in\s+([a-z0-9 %]+)", text)
    if m:
        return detect_stat(m.group(1))
    return None


def detect_subjective_best_player(text: str) -> bool:
    """Detect subjective "best player" asks with no objective metric."""
    return bool(re.search(r"\bbest\s+player\b", text))


def detect_multi_player_aggregate(text: str) -> bool:
    """Detect unsupported two-player combined-total asks.

    "luka and kyrie combined points" silently dropping one player is a
    wrong answer; these must refuse.
    """
    if re.search(r"\b[a-z][a-z'.\-]+\s+and\s+[a-z][a-z'.\-]+\s+combined\b", text):
        return True
    return bool(
        re.search(r"\bcombined\s+(?:points?|stats?|scoring|numbers?)\b", text) and " and " in text
    )


def detect_role_leaderboard_boundary(text: str) -> bool:
    """Detect unsupported league-wide starter/bench leaderboard requests."""
    if not wants_leaderboard(text):
        return False
    return bool(
        re.search(
            r"\b(?:bench|off\s+the\s+bench|reserves?|starters?|starting)\b",
            text,
        )
    )


def detect_team_bench_scoring_boundary(text: str) -> bool:
    """Detect unsupported team bench scoring requests."""
    return bool(
        re.search(r"\b(?:bench|reserves?)\b", text)
        and re.search(r"\b(?:scoring|score|points?|pts)\b", text)
    )


_AWARD_TERMS_PATTERN = (
    r"(?:"
    r"\bmvp\b|"
    r"\bmost\s+valuable\s+player\b|"
    r"\brookie\s+of\s+the\s+year\b|"
    r"\bdefensive\s+player\s+of\s+the\s+year\b|"
    r"\bdpoy\b|"
    r"\bsixth\s+man(?:\s+of\s+the\s+year)?\b|"
    r"\bmost\s+improved(?:\s+player)?\b|"
    r"\bmip\b|"
    r"\bcoach\s+of\s+the\s+year\b|"
    r"\bclutch\s+player\s+of\s+the\s+year\b|"
    r"\bawards?\b"
    r")"
)


def detect_award_query_boundary(text: str) -> bool:
    """Detect unsupported awards-result requests without inferring from stats."""
    if not re.search(_AWARD_TERMS_PATTERN, text):
        return False

    return bool(
        re.search(r"\b(?:who|which|what)\s+(?:player\s+)?won\b", text)
        or re.search(r"\bwon\s+(?:the\s+)?", text)
        or re.search(r"\bwinners?\b", text)
    )


def detect_championship_count_boundary(text: str) -> bool:
    """Detect championship/ring/title questions the game-stats contract cannot answer.

    "how many rings does lebron have" must refuse honestly, never answer
    with a count of games.
    """
    return bool(re.search(r"\b(?:rings?|championships?|champions?|titles?)\b", text))


def detect_schedule_lookup_boundary(text: str) -> bool:
    """Detect future-schedule questions (next game, when do they play).

    The engine answers questions about played games only; schedule
    lookups must refuse honestly, never return past games.
    """
    return bool(
        re.search(
            r"\bplay(?:ing)?\s+next\b|\bnext\s+game\b|\bupcoming\s+games?\b"
            r"|\bwhen\s+(?:do|does|is|are)\b[\w\s'\-]*\bplay(?:ing)?\b"
            r"|\bwhat\s+time\b|\bschedule\b",
            text,
        )
    )


def detect_opponent_conference(text: str) -> str | None:
    """Extract a normalized opponent-conference filter from supported phrasing."""
    patterns = [
        r"\b(?:against|vs\.?|versus)\s+(?:the\s+)?"
        r"(?P<direction>eastern|western)\s+conference\s+(?:teams?|opponents?)\b",
        r"\b(?:against|vs\.?|versus)\s+(?:the\s+)?"
        r"(?P<direction>east|west)\s+(?:teams?|opponents?)\b",
        r"\b(?:against|vs\.?|versus)\s+(?:the\s+)?"
        r"(?P<direction>eastern|western)\s+conference\b(?!\s+finals?\b)",
        r"\b(?:against|vs\.?|versus)\s+(?:the\s+)?"
        r"(?P<direction>east|west)\b(?!\s+(?:coast|conference\s+finals?|finals?)\b)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        direction = match.group("direction")
        if direction in {"east", "eastern"}:
            return "East"
        if direction in {"west", "western"}:
            return "West"
    return None


def detect_opponent_conference_boundary(text: str) -> bool:
    """Detect supported opponent-conference filter phrasing."""
    return detect_opponent_conference(text) is not None


def detect_opponent_conference_geography_boundary(text: str) -> bool:
    """Detect unsupported geography wording that resembles a conference filter."""
    return bool(
        re.search(
            r"\b(?:against|vs\.?|versus)\s+(?:the\s+)?"
            r"(?:(?:east|west|atlantic|pacific)\s+coast|pacific\s+northwest)\b",
            text,
        )
    )


_DIVISION_NAMES_PATTERN = r"atlantic|central|southeast|northwest|pacific|southwest|midwest"
# "vs Pacific Division teams", "vs Pacific teams", "vs the Pacific" and a bare
# "vs Pacific" all name the division (no NBA team shares those names).
_OPPONENT_DIVISION_PATTERN = re.compile(
    rf"\b(?:against|vs\.?|versus)\s+(?P<article>the\s+)?"
    rf"(?P<conference_prefix>(?:east|west|eastern|western)\s+(?:conference\s+)?)?"
    rf"(?P<division>{_DIVISION_NAMES_PATTERN})"
    rf"(?P<suffix>\s+division(?:\s+(?:teams?|opponents?))?|\s+(?:teams?|opponents?))?\b"
)


def _opponent_division_match(text: str):
    for match in _OPPONENT_DIVISION_PATTERN.finditer(text):
        # "vs the Pacific Northwest" / "vs the Atlantic coast" are geography.
        if not match.group("suffix") and re.match(
            r"\s+(?:northwest|coast|coastal|time)\b", text[match.end() :]
        ):
            continue
        return match
    return None


def _normalize_division_name(value: str) -> str:
    return {
        "atlantic": "Atlantic",
        "central": "Central",
        "southeast": "Southeast",
        "northwest": "Northwest",
        "pacific": "Pacific",
        "southwest": "Southwest",
        "midwest": "Midwest",
    }[value.strip().lower()]


def detect_opponent_division(text: str) -> str | None:
    """Extract a normalized opponent-division filter for accepted phrasing."""
    match = _opponent_division_match(text)
    if not match:
        return None
    if match.group("conference_prefix"):
        return None
    return _normalize_division_name(match.group("division"))


def detect_opponent_division_boundary(text: str) -> bool:
    """Detect explicit NBA opponent-division record filters."""
    return _opponent_division_match(text) is not None


def wants_team_leaderboard(text: str) -> bool:
    if detect_team_leaderboard_stat(text) is not None:
        return True

    if re.search(r"\bteam\s+records?\b", text):
        return True

    if re.search(r"\bteams?\b", text):
        if re.search(
            r"\b(best|highest|most|top(?:\s+\d+)?|rank|ranked|ranking|lowest|fewest|least|worst|bottom(?:\s+\d+)?)\b",
            text,
        ):
            return True

    # "rank teams by ..."
    if re.search(r"\brank\s+teams?\s+by\b", text):
        return True

    return False


def extract_season(text: str) -> str | None:
    # The lookahead keeps an ISO date ("2025-11-01") from reading as the
    # nonexistent season "2025-11".
    m = re.search(r"\b(?:19|20)\d{2}-\d{2}\b(?!-\d)", text)
    if m:
        return m.group(0)
    # "the 2024 playoffs" / "2016 finals": playoffs are played in the spring,
    # so the year names the season that ends in it (2023-24). "the 2017 title" /
    # "won the championship in 2016" / "the 2016 champions" name the same season.
    # A year that opens or closes a range ("since the 2016 playoffs", "from 2010
    # to 2020 playoffs") is not one season.
    patterns = (
        r"\b((?:19|20)\d{2})\s+(?:nba\s+)?"
        r"(?:play-?offs?|postseason|finals|conference\s+finals|(?:first|second)\s+round)\b",
        r"\b((?:19|20)\d{2})\s+(?:nba\s+)?(?:titles?|championships?|champions?)\b",
        r"\b(?:titles?|championships?|champions?)\s+in\s+((?:19|20)\d{2})\b",
    )
    for pattern in patterns:
        for m in re.finditer(pattern, text):
            before = text[: m.start(1)]
            if re.search(
                r"\b(?:since|after|before|from|to|until|through|thru)\s+(?:the\s+)?$", before
            ):
                continue
            from nbatools.commands._seasons import int_to_season

            return int_to_season(int(m.group(1)) - 1)
    return None


# "LeBron points per game in 2019", "the 2016 season": a lone year names the
# season that ended in it, as the 2016 playoffs and the 2016 title do.
_YEAR = r"(?:19|20)\d{2}"
# "scored 30 points in 2000 games" is a count, not a year: a stat value
# earlier in the question and "games"/"times" right after the number.
_YEAR_COUNT_NOUN = re.compile(r"\s+(?:games?|times)\b")
_YEAR_COUNT_CONTEXT = re.compile(
    r"\b\d+\+?\s*(?:points?|pts|rebounds?|assists?|steals?|blocks?|threes?)\b|\bscored\b"
)
_BARE_YEAR = re.compile(
    rf"\b(?:in|during|for)\s+(?:the\s+)?({_YEAR})(?:\s+(?:nba\s+)?season)?\b"
    r"(?![-/]\d|\s*(?:-|to\b|through\b|thru\b|until\b|till\b|and\b|or\b))"
    rf"|\b(?:the\s+)?({_YEAR})\s+(?:nba\s+)?(?:season|stats|record|numbers|averages)\b"
)
# "since the 2019 season", "before 2025": a range word owns the year.
_BARE_YEAR_RANGE_WORD = re.compile(
    r"\b(?:since|after|before|until|till|through|thru|starting|from|by|prior\s+to)"
    r"(?:\s+the)?\s*$"
)
# Years in a list: "2024 and 2025", "2024 & 2025", "2024, 2025", "2024 and in 2025".
_YEAR_LIST = re.compile(
    rf"\b{_YEAR}(?:\s*(?:,|&|\band\b|\bor\b|\bvs\.?|\bversus\b)\s*(?:and\s+)?(?:in\s+)?{_YEAR})+\b"
    r"(?![-/]\d)"
)
_YEAR_LIST_JOIN = re.compile(r"\s*(?:,|&|\band\b)\s*(?:and\s+)?(?:in\s+)?")
# Years that name something other than a season.
_BARE_YEAR_NOT_A_SEASON = re.compile(
    r"\b(?:drafted|draft(?:\s+class)?|born|class\s+of|picked|signed|traded|hired|retired)"
    rf"\s+(?:in\s+)?(?:the\s+)?{_YEAR}\b"
)


def extract_bare_year_season(text: str) -> tuple[int, str] | None:
    """``(year, season)`` for a lone year such as "in 2019" (2018-19), else None.

    None when the year is one of several ("2024 and 2025", "2019 or 2020"), or
    a range word owns it ("since the 2019 season").
    """
    if _BARE_YEAR_NOT_A_SEASON.search(text) or _YEAR_LIST.search(text):
        return None
    match = _BARE_YEAR.search(text)
    if not match or _BARE_YEAR_RANGE_WORD.search(text[: match.start()]):
        return None
    if _YEAR_COUNT_NOUN.match(text, match.end()) and _YEAR_COUNT_CONTEXT.search(
        text[: match.start()]
    ):
        return None
    from nbatools.commands._seasons import int_to_season

    year = int(match.group(1) or match.group(2))
    return year, int_to_season(year - 1)


def extract_bare_year_pair(text: str) -> tuple[str, str] | None:
    """First and last season of "in 2024 and 2025" (2023-24 to 2024-25), else None.

    Only two consecutive years joined by "and", "&" or a comma make a span.
    """
    if _BARE_YEAR_NOT_A_SEASON.search(text):
        return None
    match = _YEAR_LIST.search(text)
    if not match or _BARE_YEAR_RANGE_WORD.search(text[: match.start()]):
        return None
    years = [int(y) for y in re.findall(_YEAR, match.group(0))]
    joins = re.split(_YEAR, match.group(0))[1:-1]
    if len(years) != 2 or not all(_YEAR_LIST_JOIN.fullmatch(j) for j in joins):
        return None
    from nbatools.commands._seasons import int_to_season

    first, last = sorted(years)
    if last - first != 1:
        return None
    return int_to_season(first - 1), int_to_season(last - 1)


def extract_relative_season(text: str, season_type: str) -> str | None:
    """Extract singular relative season phrases such as ``last season``."""
    if re.search(r"\b(?:last|previous)\s+season\b", text):
        from nbatools.commands._seasons import previous_season

        return previous_season(season_type)
    return None


_RANGE_POINT = r"((?:19|20)\d{2}(?:-\d{2})?)(?![-\d])"
_RANGE_JOIN = r"(?:\s+season)?\s*(?:-|\bto\b|\bthrough\b|\bthru\b|\buntil\b|\btill\b|\band\b)\s*"
# "since 2020 and 2021" is not a span; "since" only closes with to/through/until.
_SINCE_JOIN = r"(?:\s+season)?\s+(?:to|through|thru|until|till)\s+"
# "between 2000 and 2050 points" is a stat bound, not seasons.
_RANGE_NOT_A_STAT = (
    r"(?!\s*(?:points?|pts|rebounds?|assists?|minutes?|mins?|yards?|steals?|blocks?|"
    r"turnovers?|threes?|3s|fg|games?)\b)"
)
_SEASON_RANGES = (
    # "from 2010 to 2015", "between 2000-01 and 2009-10", "from 1999 through 2003"
    re.compile(
        r"\b(?:from|between)\s+(?:the\s+)?"
        + _RANGE_POINT
        + _RANGE_JOIN
        + r"(?:the\s+)?"
        + _RANGE_POINT
        + _RANGE_NOT_A_STAT
    ),
    re.compile(
        r"\bsince\s+(?:the\s+)?"
        + _RANGE_POINT
        + _SINCE_JOIN
        + r"(?:the\s+)?"
        + _RANGE_POINT
        + _RANGE_NOT_A_STAT
    ),
    # "2015-2017", "2003 - 2010", "2010-11 to 2014-15", "2010 through 2015"
    re.compile(r"(?<![\w-])((?:19|20)\d{2})\s*-\s*((?:19|20)\d{2})(?![-\d])" + _RANGE_NOT_A_STAT),
    re.compile(
        r"(?<![\w-])"
        + _RANGE_POINT
        + r"\s+(?:to|through|thru|until|till)\s+(?:the\s+)?"
        + _RANGE_POINT
        + _RANGE_NOT_A_STAT
    ),
)
# Playoffs and titles are named by the year they end in, as extract_season
# reads "the 2016 playoffs" and "the 2017 title": "titles from 1991 to 1998"
# runs from 1990-91 to 1997-98. "against playoff teams" is a regular-season
# filter, so only the season type or a title word switches this on.
_TITLE_YEAR_CONTEXT = re.compile(r"\b(?:finals|titles?|championships?|champions?|rings?)\b")


def _range_point_season(point: str, ending_year: bool) -> str:
    from nbatools.commands._seasons import int_to_season

    if "-" in point:
        return point
    return int_to_season(int(point) - 1 if ending_year else int(point))


def extract_season_range(
    text: str, season_type: str | None = None
) -> tuple[str | None, str | None]:
    """Two seasons or years that bound a span, inclusive.

    "from 2010-11 to 2014-15" -> 2010-11..2014-15. A bare year names the season
    starting in it, as "since 2010" and "the 2010s" do ("from 2010 to 2015" ->
    2010-11..2015-16). For playoffs and titles a year names the season ending
    in it ("titles from 1991 to 1998" -> 1990-91..1997-98). Two consecutive
    years joined by a hyphen are one season ("2019-2020" -> 2019-20), except
    for titles, where they are two ("Warriors titles 2017-2018"). A span
    written backwards ("from 2010 to 2005") covers the same seasons.
    """
    from nbatools.commands._seasons import int_to_season, season_to_int

    for pattern in _SEASON_RANGES:
        m = pattern.search(text)
        if not m:
            continue
        first, last = m.group(1), m.group(2)
        joined = text[m.start(1) + len(first) : m.start(2)]
        title_years = bool(_TITLE_YEAR_CONTEXT.search(text))
        if (
            not title_years
            and "-" not in first
            and "-" not in last
            and int(last) == int(first) + 1
            and joined.strip() == "-"
        ):
            # "2019-2020" is the 2019-20 season written out.
            season = int_to_season(int(first))
            return season, season
        ending_year = title_years or season_type == "Playoffs"
        start = _range_point_season(first, ending_year)
        end = _range_point_season(last, ending_year)
        if season_to_int(start) > season_to_int(end):
            start, end = end, start
        return start, end
    return None, None


# ---------------------------------------------------------------------------
# Historical span detection
# ---------------------------------------------------------------------------


def detect_career_intent(text: str) -> bool:
    """Detect career / all-time intent in a query."""
    return bool(re.search(r"\b(career|all[- ]?time|lifetime)\b", text))


def extract_since_season(text: str) -> str | None:
    """Extract a 'since SEASON' or 'since YEAR' pattern.

    Returns the season string (e.g. '2020-21') or None.
    'since 2020-21' -> '2020-21'
    'since 2020'    -> '2020-21'  (the season starting in that year)
    """
    # Explicit season format first
    m = re.search(r"\bsince\s+((?:19|20)\d{2}-\d{2})\b(?!-\d)", text)
    if m:
        return m.group(1)
    # "since the 2016 playoffs": the playoffs that end the 2015-16 season
    m = re.search(
        r"\bsince\s+(?:the\s+)?((?:19|20)\d{2})\s+(?:nba\s+)?"
        r"(?:play-?offs?|postseason|finals|conference\s+finals|title|championship)\b",
        text,
    )
    if m:
        from nbatools.commands._seasons import int_to_season

        return int_to_season(int(m.group(1)) - 1)
    # Bare year
    m = re.search(r"\bsince\s+((?:19|20)\d{2})\b(?!-\d)", text)
    if m:
        from nbatools.commands._seasons import int_to_season

        return int_to_season(int(m.group(1)))
    return None


def extract_last_n_seasons(text: str) -> int | None:
    """Extract 'last N seasons' / 'over the last N seasons' / 'past N seasons'.

    Returns N or None.
    """
    m = re.search(
        r"\b(?:(?:over|in)\s+the\s+)?(?:last|past)\s+(\d+)\s+"
        r"(?:seasons?|years?|playoffs|postseasons?)\b",
        text,
    )
    if m:
        value = int(m.group(1))
        return value if value > 0 else None
    return None


_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "twenty five": 25,
    "twenty-five": 25,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
}
_NUMBER_WORD_PATTERN = "|".join(
    re.escape(word) for word in sorted(_NUMBER_WORDS, key=len, reverse=True)
)
_RECENT_WORD = r"(?:last|past|previous|prior|latest|most\s+recent)"
_SAMPLE_UNIT = r"(?:games?|contests?|outings?|matchups?|meetings?|seasons?|starts?|wins?|losses)"


def canonicalize_sample_phrases(text: str) -> str:
    """Rewrite recent-sample wording into the one form the detectors read.

    Every detector downstream reads "last N games" (or "last N seasons"), so
    "last ten games", "previous 5 games", "his 5 most recent games" and
    "past five seasons" used to drop their window silently and answer for
    the whole season. Meetings read as matchups against the named opponent:
    "last 3 meetings with the Warriors" is the last 3 games vs the Warriors.
    Only phrases with an explicit sample unit are rewritten, so "the last
    five minutes" and "previous season" are left alone.
    """
    # Number words to digits, only inside a recent-sample phrase.
    text = re.sub(
        rf"\b({_RECENT_WORD})\s+({_NUMBER_WORD_PATTERN})\s+(?={_SAMPLE_UNIT}\b)",
        lambda m: f"{m.group(1)} {_NUMBER_WORDS[m.group(2)]} ",
        text,
    )
    # "his 5 most recent games" / "LeBron's five latest games" -> "his last 5 games".
    # A determiner is required so "30 points most recent game" keeps its threshold.
    text = re.sub(
        rf"((?:\b(?:his|her|their|its|the|my|your)|'s)\s+)(\d+|{_NUMBER_WORD_PATTERN})\s+"
        rf"(?:most\s+recent|latest)\s+(?={_SAMPLE_UNIT}\b)",
        lambda m: f"{m.group(1)}last {_NUMBER_WORDS.get(m.group(2), m.group(2))} ",
        text,
    )
    # "previous/prior/latest/most recent N games" -> "last N games"
    text = re.sub(
        rf"\b(?:previous|prior|latest|most\s+recent)\s+(\d+)\s+(?={_SAMPLE_UNIT}\b)",
        r"last \1 ",
        text,
    )
    # "past N games" too; "past N seasons" already has its own season reading.
    text = re.sub(
        r"\bpast\s+(\d+)\s+(?=(?:games?|contests?|outings?|matchups?|meetings?|starts?)\b)",
        r"last \1 ",
        text,
    )
    # A single latest meeting is a one-game window against that opponent.
    text = re.sub(
        r"\b(?:last|latest|most\s+recent|previous)\s+(?:meeting|matchup)\s+"
        r"(?:with|against|vs\.?|versus)\b",
        "last game vs",
        text,
    )
    # "meetings/matchups with X" -> "matchups vs X": "with" names the opponent.
    text = re.sub(
        r"\b(?:meetings?|matchups?)\s+(?:with|against|vs\.?|versus)\b",
        "matchups vs",
        text,
    )
    text = re.sub(r"\bmeetings?\b", "matchups", text)
    return " ".join(text.split())


# A last-N phrase introduced by one of these words names the time window the
# rest of the question is measured over ("30 point games in his last 10").
_WINDOW_PREPOSITION = (
    r"(?:in|over|during|across|within|through|throughout|of|from|for)\s+"
    r"(?:(?:his|her|their|its|the|my|your|them|those)\s+)?"
)
# Words that attach a condition to the games themselves ("last 10 games where
# he scored 30"), so the condition picks which games count toward N.
_QUALIFYING_CLAUSE = (
    r"\s+(?:where|when|whenever|with|in\s+which|that|which|scoring|shooting|"
    r"grabbing|dishing|recording|having|posting|putting\s+up|making|he|she|they|"
    r"the\s+\w+\s+(?:scored|had|made|won|lost))\b"
)
_LAST_N_GAMES = (
    r"\blast\s+\d+(?!\s+(?:seasons?|weeks?|days?|months?|minutes?))"
    r"(?:\s+(?:games?|contests?|outings?))?\b"
)
_POSSESSIVE_WINDOW = r"\bof\s+(?:the\s+)?(?:[\w.-]+\s+){0,2}[\w.-]+(?:'s|s'|')\s*$"
_STAT_PERFORMANCE_WORDS = (
    r"\b(?:triple[- ]doubles?|double[- ]doubles?)\b"
    r"|\b\d+\+?\s*[- ]?\s*(?:points?|pts?|rebounds?|rebs?|assists?|asts?|"
    r"steals?|blocks?|threes?|3s|3pm)\b"
)
_PERFORMANCE_WORDS = rf"\b(?:wins?|won|losses|lost)\b|{_STAT_PERFORMANCE_WORDS}"


def detect_last_n_scope(text: str, threshold_conditions: list[dict] | None = None) -> str:
    """Say whether a last-N phrase is a time window or a qualifying count.

    ``window``: "how many 30 point games in his last 10 games" takes the 10
    most recent games, then counts the ones that meet the condition.
    ``qualifying``: "his last 10 games where he scored 30" (and "last 10
    wins", "last 5 home games") keeps the games that meet the condition,
    then the 10 most recent of them. Context such as opponent, home/away,
    season and teammate availability always picks the sample first; only
    game results and stat conditions differ between the two.
    """
    match = re.search(_LAST_N_GAMES, text)
    if not match:
        return "qualifying"
    # Without a game result or stat condition both readings select the same
    # games, so equivalent phrasings keep one parse state.
    if not threshold_conditions and not re.search(_PERFORMANCE_WORDS, text):
        return "qualifying"
    after = text[match.end() :]
    outcome_unit = re.match(r"\s+(?:wins?|losses|loss)\b", after)
    if outcome_unit:
        # "his last 10 wins" is the sample. With another condition ("how many
        # of his last 10 wins did he score 30") it is counted inside those
        # wins; alone, the 10 most recent wins are the answer.
        rest = text[: match.start()] + " " + after[outcome_unit.end() :]
        other_condition = threshold_conditions or re.search(_STAT_PERFORMANCE_WORDS, rest)
        return "outcome_window" if other_condition else "qualifying"
    if re.match(_QUALIFYING_CLAUSE, after):
        return "qualifying"
    before = text[: match.start()]
    if re.search(rf"\b{_WINDOW_PREPOSITION}$", before):
        return "window"
    # "how many of LeBron's last 10 games ...", "of the Lakers' last 10 ...":
    # the possessive names whose window it is.
    if re.search(_POSSESSIVE_WINDOW, before):
        return "window"
    # "LeBron's last 10 games, how many 30 point games": the question about
    # the games comes after the window.
    if re.search(r"\bhow\s+many\b", after):
        return "window"
    # A condition stated before a bare last-N phrase ("LeBron 30 point games
    # last 10") is measured over that window.
    condition_starts = [
        text.find(condition["text"])
        for condition in threshold_conditions or []
        if condition.get("text") and condition["text"] in text
    ]
    condition_starts.extend(m.start() for m in re.finditer(_PERFORMANCE_WORDS, before))
    if condition_starts and min(condition_starts) < match.start():
        return "window"
    return "qualifying"


def last_n_reach_back_seasons(season: str, *, seasons_back: int = 1) -> dict:
    """Season kwargs letting a last-N window reach into the prior season.

    With no season named, "Warriors last 10 games" is the ten most recent
    games, even when the current season has only played a few. The window
    is still the N most recent games; the earlier season only fills it.
    """
    from nbatools.commands._seasons import EARLIEST_SEASON, int_to_season, season_to_int

    if season_to_int(season) <= season_to_int(EARLIEST_SEASON):
        return {}
    start = max(season_to_int(season) - seasons_back, season_to_int(EARLIEST_SEASON))
    return {
        "season": None,
        "start_season": int_to_season(start),
        "end_season": season,
    }


_CURRENT_SEASON_WORDS = re.compile(r"\b(?:this|current)\s+(?:season|year)\b")


def names_current_season(text: str) -> bool:
    """True when the query pins the sample to the current season in words."""
    return bool(_CURRENT_SEASON_WORDS.search(text))


def extract_last_n(text: str) -> int | None:
    # Fuzzy time words → fixed last-N values (glossary / spec §18.1)
    for term, last_n in FUZZY_LAST_N_TERMS.items():
        if re.search(rf"\b{re.escape(term)}\b", text):
            return last_n

    patterns = [
        r"\blast\s+(\d+)\s+games?\b",
        r"\bpast\s+(\d+)\s+games?\b",
        r"\brecent\s+(\d+)\s+games?\b",
        r"\blast\s+(\d+)(?!\s+(?:seasons?|years?|playoffs|postseasons?|weeks?|days?|months?))\b",
        r"\bpast\s+(\d+)(?!\s+(?:seasons?|years?|playoffs|postseasons?|weeks?|days?|months?))\b",
        r"\brecent\s+(\d+)(?!\s+(?:seasons?|years?|playoffs|postseasons?|weeks?|days?|months?))\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            value = int(m.group(1))
            return value if value > 0 else None
    return None


STREAK_SPECIAL_PATTERNS = {
    "made_three": [
        r"\bconsecutive\s+games?\s+with\s+(?:a|an|at\s+least\s+one)?\s*(?:made\s+three|made\s+3|3pm|three-pointer|three pointer)\b",  # noqa: E501
        r"\blongest\s+streak\s+of\s+(?:a|an|at\s+least\s+one)?\s*(?:made\s+three|made\s+3|3pm|three-pointer|three pointer)\b",  # noqa: E501
    ],
    "triple_double": [
        r"\blongest\s+triple[- ]double\s+streak\b",
    ],
}


_STREAK_WORD = re.compile(r"\b(streak|straight|consecutive|in\s+a\s+row)\b")
# "current"/"active" asks for the streak alive at the latest game, not a
# season-scope word ("current season").
_CURRENT_STREAK = re.compile(r"\b(?:current|active|ongoing)\b(?!\s+season)")
# The streak length, never a game condition: "5 straight games with 30",
# "3 straight 30 point games", "5 games in a row", "a 3 game winning streak".
# Each match spans only the length words, so removing it keeps the condition.
_STREAK_LENGTH = re.compile(
    r"\b(\d+)\s+(?:straight|consecutive)\b(?=\s+(?:[\w+-]+\s+){0,3}?games?\b)"
    r"|\b(\d+)\s+games?\s+in\s+a\s+row\b"
    r"|\b(\d+)[- ]games?\b(?=\s+(?:[\w+-]+\s+){0,3}?streak)"
)


def _streak_length(normalized: str) -> tuple[int | None, str]:
    """The stated streak length and the text with the length words removed."""
    match = _STREAK_LENGTH.search(normalized)
    if match is None:
        return None, normalized
    length = int(next(group for group in match.groups() if group))
    return length, normalized[: match.start()] + " " + normalized[match.end() :]


def _with_streak_mode(request: dict | None, normalized: str) -> dict | None:
    if request is not None and _CURRENT_STREAK.search(normalized):
        request = {**request, "current": True, "longest": False}
    return request


def extract_streak_request(text: str) -> dict | None:
    # Receives pre-normalized text from _build_parse_state; no per-detector
    # normalization needed.
    normalized = re.sub(r"[?.!,]+$", "", text)
    if not _STREAK_WORD.search(normalized):
        return None
    # Several game conditions ("30 point 10 rebound games") go to the generic
    # reader first: the fixed patterns would keep only one of them.
    request = _generic_streak_request(normalized, compound_only=True)
    if request is None:
        request = _extract_streak_request_patterns(normalized)
        length, without_length = _streak_length(normalized)
        if request is not None and length and request.get("min_streak_length") is None:
            # A fixed pattern read the condition but not a length stated before
            # it ("3 consecutive 30 point games", "a 3 game 20 point streak").
            request = _extract_streak_request_patterns(without_length) or _generic_streak_request(
                normalized
            )
            if request is not None:
                request = {**request, "min_streak_length": length, "longest": False}
    if request is None:
        request = _generic_streak_request(normalized)
    return _with_streak_mode(request, normalized)


def _generic_streak_request(normalized: str, compound_only: bool = False) -> dict | None:
    """Read the streak's game condition with the occurrence-event parser.

    Covers wording the fixed patterns miss: "longest streak of games with 5+
    threes", "consecutive games with 10+ rebounds", "streak of 30 point 10
    rebound games", "consecutive double doubles".
    """
    from nbatools.commands._occurrence_route_utils import (
        _parse_single_threshold,
        extract_compound_occurrence_event,
        extract_occurrence_event,
    )

    request: dict = {
        "special_condition": None,
        "stat": None,
        "min_value": None,
        "max_value": None,
        "min_streak_length": None,
        "longest": bool(re.search(r"\b(?:longest|most\s+consecutive)\b", normalized)),
    }
    request["min_streak_length"], condition_text = _streak_length(normalized)
    if "in a row" in normalized and condition_text != normalized:
        condition_text += " games"

    compound = extract_compound_occurrence_event(condition_text)
    if compound and len(compound) >= 2:
        return {**request, "conditions": [dict(c) for c in compound]}
    if compound_only:
        return None
    # An upper bound alone ("games with under 20 points", "at most 2
    # turnovers") is read by the threshold parser; the event parser only
    # knows lower bounds.
    event = extract_occurrence_event(condition_text) or _parse_single_threshold(condition_text)
    if not event:
        return None
    if event.get("special_event") in ("triple_double", "double_double"):
        return {**request, "special_condition": event["special_event"]}
    if event.get("stat") and event["stat"] in STAT_ALIASES.values():
        return {
            **request,
            "stat": event["stat"],
            "min_value": event.get("min_value"),
            "max_value": event.get("max_value"),
        }
    return None


def _extract_streak_request_patterns(normalized: str) -> dict | None:

    for pattern in STREAK_SPECIAL_PATTERNS["triple_double"]:
        if re.search(pattern, normalized):
            return {
                "special_condition": "triple_double",
                "stat": None,
                "min_value": None,
                "max_value": None,
                "min_streak_length": None,
                "longest": True,
            }

    m = re.search(
        r"\b(\d+)\s+straight\s+games?\s+with\s+(?:a|an|at\s+least\s+one)?\s*(?:made\s+three|made\s+3|3pm|three-pointer|three pointer)\b",  # noqa: E501
        normalized,
    )
    if m:
        return {
            "special_condition": "made_three",
            "stat": None,
            "min_value": None,
            "max_value": None,
            "min_streak_length": int(m.group(1)),
            "longest": False,
        }

    for pattern in STREAK_SPECIAL_PATTERNS["made_three"]:
        if re.search(pattern, normalized):
            return {
                "special_condition": "made_three",
                "stat": None,
                "min_value": None,
                "max_value": None,
                "min_streak_length": None,
                "longest": True,
            }

    m = re.search(
        r"\b(\d+)\s+straight\s+games?\s+with\s+(\d+)\+\s+([a-z0-9 .%-]+?)(?=\s+(?:from|to|in|on|at|with|home|away|road|wins?|loss(?:es)?|summary|average|averages|record|for|during|playoff|playoffs|postseason|last|past|recent|form|split|over|under|between|and|or)\b|$)",  # noqa: E501
        normalized,
    )
    if m:
        stat = detect_stat(m.group(3))
        if stat:
            return {
                "special_condition": None,
                "stat": stat,
                "min_value": float(m.group(2)),
                "max_value": None,
                "min_streak_length": int(m.group(1)),
                "longest": False,
            }

    m = re.search(
        r"\blongest\s+streak\s+of\s+(\d+)(?:\+)?\s+([a-z0-9 .%-]+?)\s+games?\b",
        normalized,
    )
    if m:
        stat = detect_stat(m.group(2))
        if stat:
            return {
                "special_condition": None,
                "stat": stat,
                "min_value": float(m.group(1)),
                "max_value": None,
                "min_streak_length": None,
                "longest": True,
            }

    # `longest streak with (at least) N STAT` — e.g.
    # "Curry longest streak with at least 3 threes"
    # "longest Curry streak with at least 3 threes" (word-order variant)
    m = re.search(
        (
            r"\blongest\s+(?:[a-z .'\-]+\s+)?streak\s+with\s+"
            r"(?:at\s+least\s+)?(\d+)(?:\+)?\s+([a-z0-9 .%-]+?)(?=\s|$)"
        ),
        normalized,
    )
    if m:
        stat = detect_stat(m.group(2))
        if stat:
            return {
                "special_condition": None,
                "stat": stat,
                "min_value": float(m.group(1)),
                "max_value": None,
                "min_streak_length": None,
                "longest": True,
            }

    # `N+ STAT streak` or `current N+ STAT streak` — e.g.
    # "LeBron current 20+ point streak", "Jokic longest 30-point streak"
    m = re.search(
        r"\b(?:longest|current)?\s*(\d+)(?:\+)?[- ]([a-z0-9 .%-]+?)\s+streak\b",
        normalized,
    )
    if m:
        stat = detect_stat(m.group(2))
        if stat:
            longest = "longest" in normalized or "current" not in normalized
            return {
                "special_condition": None,
                "stat": stat,
                "min_value": float(m.group(1)),
                "max_value": None,
                "min_streak_length": None,
                "longest": longest,
            }

    # `consecutive N STAT games (longest)` — e.g.
    # "Jokic consecutive 30 point games longest"
    m = re.search(
        r"\bconsecutive\s+(\d+)(?:\+)?[- ]?([a-z0-9 .%-]+?)\s+games?\b",
        normalized,
    )
    if m:
        stat = detect_stat(m.group(2))
        if stat:
            longest = "longest" in normalized
            return {
                "special_condition": None,
                "stat": stat,
                "min_value": float(m.group(1)),
                "max_value": None,
                "min_streak_length": None,
                "longest": longest,
            }

    return None


TEAM_STREAK_SPECIAL_PATTERNS = {
    "wins": [
        r"\blongest\s+[a-z0-9 .&'\-]+\s+winning\s+streak\b",
        r"\blongest\s+winning\s+streak\b",
    ],
    "losses": [
        r"\blongest\s+[a-z0-9 .&'\-]+\s+losing\s+streak\b",
        r"\blongest\s+losing\s+streak\b",
    ],
}


_OUTCOME_STREAK = re.compile(r"\b(win(?:ning)?|los(?:ing|s))\s+streaks?\b")


def extract_team_streak_request(text: str) -> dict | None:
    # Receives pre-normalized text from _build_parse_state; no per-detector
    # normalization needed.
    normalized = re.sub(r"[?.!,]+$", "", text)
    if not _STREAK_WORD.search(normalized):
        return None
    request = _extract_team_streak_request_patterns(normalized)
    if request is None and not _OUTCOME_STREAK.search(normalized):
        # One team stat condition ("120 point games", "games with 15+
        # threes"); the team finder takes a single stat bound.
        generic = _generic_streak_request(normalized)
        if generic and generic.get("stat") and not generic.get("conditions"):
            request = {**generic, "team_condition_only": True}
    if request is None and (outcome := _OUTCOME_STREAK.search(normalized)):
        # "Lakers current winning streak", "Celtics winning streak at home"
        request = {
            "special_condition": "wins" if outcome.group(1).startswith("win") else "losses",
            "stat": None,
            "min_value": None,
            "max_value": None,
            "min_streak_length": _streak_length(normalized)[0],
            "longest": True,
        }
    return _with_streak_mode(request, normalized)


def _extract_team_streak_request_patterns(normalized: str) -> dict | None:

    m = re.search(
        r"\b(?:[a-z0-9 .&'\-]+?)\s+(\d+)\s+straight\s+games?\s+scoring\s+(\d+)\+(?:\s+(?:points?|pts))?(?=\s|$)",  # noqa: E501
        normalized,
    )
    if m:
        return {
            "special_condition": None,
            "stat": "pts",
            "min_value": float(m.group(2)),
            "max_value": None,
            "min_streak_length": int(m.group(1)),
            "longest": False,
        }

    for pattern in TEAM_STREAK_SPECIAL_PATTERNS["wins"]:
        if re.search(pattern, normalized):
            return {
                "special_condition": "wins",
                "stat": None,
                "min_value": None,
                "max_value": None,
                "min_streak_length": None,
                "longest": True,
            }

    for pattern in TEAM_STREAK_SPECIAL_PATTERNS["losses"]:
        if re.search(pattern, normalized):
            return {
                "special_condition": "losses",
                "stat": None,
                "min_value": None,
                "max_value": None,
                "min_streak_length": None,
                "longest": True,
            }

    m = re.search(
        r"\b(\d+)\s+straight\s+games?\s+scoring\s+(\d+)\+(?:\s+(?:points?|pts))?(?=\s|$)",
        normalized,
    )
    if m:
        return {
            "special_condition": None,
            "stat": "pts",
            "min_value": float(m.group(2)),
            "max_value": None,
            "min_streak_length": int(m.group(1)),
            "longest": False,
        }

    m = re.search(
        r"\b(\d+)\s+straight\s+games?\s+with\s+(\d+)\+\s+(?:points?|pts)\b",
        normalized,
    )
    if m:
        return {
            "special_condition": None,
            "stat": "pts",
            "min_value": float(m.group(2)),
            "max_value": None,
            "min_streak_length": int(m.group(1)),
            "longest": False,
        }

    m = re.search(
        r"\b([a-z0-9 .&'\-]+?)\s+consecutive\s+games?\s+with\s+(\d+)\+\s+(points?|pts|threes|3pm|rebounds?|reb|assists?|ast)\b",  # noqa: E501
        normalized,
    )
    if m:
        stat_text = m.group(3)
        stat = detect_stat(stat_text)
        if stat:
            return {
                "special_condition": None,
                "stat": stat,
                "min_value": float(m.group(2)),
                "max_value": None,
                "min_streak_length": None,
                "longest": True,
            }

    m = re.search(
        r"\blongest\s+[a-z0-9 .&'\-]+\s+streak\s+with\s+(\d+)\+\s+(points?|pts|threes|3pm|rebounds?|reb|assists?|ast)\b",  # noqa: E501
        normalized,
    )
    if m:
        stat_text = m.group(2)
        stat = detect_stat(stat_text)
        if stat:
            return {
                "special_condition": None,
                "stat": stat,
                "min_value": float(m.group(1)),
                "max_value": None,
                "min_streak_length": None,
                "longest": True,
            }

    return None


def detect_stat(text: str) -> str | None:
    # Word-boundary match so short codes like "ast" do not falsely match
    # substrings in words like "last" — the pre-fix behavior of `key in text`
    # caused `top scorers last 10 games` to resolve stat to 'ast'.
    for key in sorted(STAT_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", text):
            return STAT_ALIASES[key]
    return None


def detect_player_summary_stat_context(text: str) -> str | None:
    """Detect narrow stat-context phrases that should not imply thresholds."""
    if re.search(r"\bfrom\s+(?:three|3)\b", text):
        return "fg3m"
    return None


_OPPONENT_QUALITY_PREFIX_PATTERN = (
    r"(?:against|vs\.?|versus)\s+(?:the\s+)?"
    r"(?:(?:east|west|eastern|western)(?:\s+conference)?\s+)?"
)

_PLAYOFF_TEAM_OPPONENT_QUALITY_PATTERNS = [
    rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}(?:playoff|postseason)\s+teams\b",
    r"\b(?:against|vs\.?|versus)\s+teams?\s+that\s+(?:made|make|qualified\s+for|qualify\s+for)\s+(?:the\s+)?(?:playoffs|postseason)\b",
    rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}playoff\s+qualifiers\b",
]

_NON_PLAYOFF_TEAM_OPPONENT_QUALITY_PATTERNS = [
    rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}(?:non[- ]playoff|non[- ]postseason)\s+teams\b",
    r"\b(?:against|vs\.?|versus)\s+teams?\s+that\s+(?:missed|miss)\s+(?:the\s+)?(?:playoffs|postseason)\b",
]


def detects_playoff_team_opponent_quality(text: str) -> bool:
    return any(
        re.search(pattern, text)
        for pattern in (
            *_PLAYOFF_TEAM_OPPONENT_QUALITY_PATTERNS,
            *_NON_PLAYOFF_TEAM_OPPONENT_QUALITY_PATTERNS,
        )
    )


def _has_explicit_playoff_competition_context(text: str) -> bool:
    patterns = [
        r"\b(?:in|during)\s+(?:the\s+)?(?:playoffs|postseason)\b",
        r"\b(?:playoff|postseason)\s+(?:record|history|games?|series|summary|leaders?|leaderboard|appearances?)\b",
        r"\b(?:record|games?|summary|leaders?|leaderboard)\s+(?:in|during|for)\s+(?:the\s+)?(?:playoffs|postseason)\b",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def detect_season_type(text: str) -> str:
    if re.search(r"\b(playoff|playoffs|postseason)\b", text):
        if detects_playoff_team_opponent_quality(
            text
        ) and not _has_explicit_playoff_competition_context(text):
            return "Regular Season"
        return "Playoffs"
    return "Regular Season"


def default_season_for_context(season_type: str) -> str:
    from nbatools.commands._seasons import default_end_season

    return default_end_season(season_type)


def detect_split_type(text: str) -> str | None:
    if re.search(r"\bhome\s+(?:vs\.?|versus)\s+away\b|\bhome\s+away\b|\baway\s+home\b", text):
        return "home_away"
    if re.search(
        r"\bwins?\s+(?:vs\.?|versus)\s+loss(?:es)?\b|\bwins?\s+loss(?:es)?\b|\bwins_losses\b|\bin\s+wins\s+(?:and|&)\s+loss(?:es)?\b",
        text,
    ):
        return "wins_losses"
    return None


_PERCENTAGE_THRESHOLD_STATS = {"fg_pct", "fg3_pct", "ft_pct", "efg_pct", "ts_pct"}


def _normalize_threshold_value(value_text: str, stat: str) -> float:
    value = float(value_text)
    if stat in _PERCENTAGE_THRESHOLD_STATS and value > 1:
        return value / 100
    return value


def _threshold_bounds(
    value_text: str,
    stat: str,
    mode: str,
    epsilon: float,
) -> tuple[float | None, float | None]:
    value = _normalize_threshold_value(value_text, stat)
    if mode == "min":
        return value + epsilon, None
    return None, value - epsilon


def _parse_threshold_match(
    value_text: str, stat_text: str, mode: str, epsilon: float
) -> tuple[str, float | None, float | None]:
    stat = detect_stat(stat_text)
    if stat is None:
        raise ValueError(f"Unsupported stat phrase: {stat_text}")
    min_value, max_value = _threshold_bounds(value_text, stat, mode, epsilon)
    return stat, min_value, max_value


def _shooting_percentage_stat_for_context(match_text: str) -> str:
    if re.search(r"\b(?:from\s+)?(?:three|3)\b", match_text):
        return "fg3_pct"
    if re.search(r"\b(?:free\s+throws?|from\s+the\s+line)\b", match_text):
        return "ft_pct"
    return "fg_pct"


def _extract_shooting_percentage_conditions(text: str) -> list[dict]:
    """Infer shooting percentage thresholds from clear shooting contexts only."""
    _NUM = r"(\d+(?:\.\d+)?|\.\d+)(?:\s*(?:%|percent))?"
    operator = r"(over|above|at\s+least|under|below|less\s+than)"
    patterns = [
        rf"\b(?:shoots?|shooting|shot)\s+{operator}\s+{_NUM}(?:\s+from\s+(?:the\s+)?(?:field|three|3))?\b",
        rf"\b(?:from\s+(?:the\s+)?(?:field|three|3))\s+{operator}\s+{_NUM}\b",
        rf"\b(?:free\s+throws?|from\s+the\s+line)\s+{operator}\s+{_NUM}\b",
    ]

    matches = []
    for pattern in patterns:
        for m in re.finditer(pattern, text):
            op = m.group(1)
            value_text = m.group(2)
            mode = "min" if op in {"over", "above", "at least"} else "max"
            epsilon = 0.0 if op == "at least" else 0.0001
            stat = _shooting_percentage_stat_for_context(m.group(0))
            min_value, max_value = _threshold_bounds(value_text, stat, mode, epsilon)
            matches.append(
                {
                    "start": m.start(),
                    "end": m.end(),
                    "stat": stat,
                    "min_value": min_value,
                    "max_value": max_value,
                    "text": m.group(0),
                }
            )
    return matches


_JOINED_STAT_THRESHOLD_RE = re.compile(
    rf"\s*(?:,\s*)?(?:and\s+)?(\d{{1,3}})(?!\d)(?:\s*\+)?\s+{STAT_PATTERN}\b"
)


def _joined_stat_thresholds(text: str, end: int) -> list[dict]:
    """Thresholds joined onto a scoring verb: "scoring 30 points and 5 assists".

    The verb carries over to each joined "N <stat>", so the bare "5 assists"
    is a 5+ assists condition rather than leftover text.
    """
    joined = []
    while True:
        m = _JOINED_STAT_THRESHOLD_RE.match(text, end)
        if not m or m.start(1) == m.start():
            break
        stat = detect_stat(m.group(2)) or "pts"
        joined.append(
            {
                "start": m.start(1),
                "end": m.end(),
                "stat": stat,
                "min_value": _normalize_threshold_value(m.group(1), stat),
                "max_value": None,
                "text": text[m.start(1) : m.end()],
            }
        )
        end = m.end()
    return joined


def extract_threshold_conditions(text: str) -> list[dict]:
    _NUM = r"(\d+(?:\.\d+)?|\.\d+)(?:\s*(?:%|percent))?"

    # Standard patterns: operator NUMBER STAT
    patterns = [
        (
            rf"\bbetween\s+{_NUM}\s+and\s+{_NUM}\s+{STAT_PATTERN}\b",
            "between",
            0.0,
        ),
        (
            rf"\bover\s+{_NUM}\s+{STAT_PATTERN}\b",
            "min",
            0.0001,
        ),
        (
            rf"\bat least\s+{_NUM}\s+{STAT_PATTERN}\b",
            "min",
            0.0,
        ),
        (
            rf"\b{_NUM}\s+or\s+more\s+{STAT_PATTERN}\b",
            "min",
            0.0,
        ),
        (
            rf"\bunder\s+{_NUM}\s+{STAT_PATTERN}\b",
            "max",
            0.0001,
        ),
        (
            rf"\bless than\s+{_NUM}\s+{STAT_PATTERN}\b",
            "max",
            0.0001,
        ),
        (
            rf"\bfewer than\s+{_NUM}\s+{STAT_PATTERN}\b",
            "max",
            0.0001,
        ),
        # Shorthand: N+ STAT — "30+ points", "5+ threes" (implicit >=)
        (
            rf"\b{_NUM}\+\s*{STAT_PATTERN}\b",
            "min",
            0.0,
        ),
    ]

    # Reverse patterns: STAT operator NUMBER (for advanced stats like "TS% over .700")
    reverse_patterns = [
        (
            rf"{STAT_PATTERN}\s+over\s+{_NUM}",
            "min",
            0.0001,
        ),
        (
            rf"{STAT_PATTERN}\s+above\s+{_NUM}",
            "min",
            0.0001,
        ),
        (
            rf"{STAT_PATTERN}\s+at least\s+{_NUM}",
            "min",
            0.0,
        ),
        (
            rf"{STAT_PATTERN}\s+under\s+{_NUM}",
            "max",
            0.0001,
        ),
        (
            rf"{STAT_PATTERN}\s+below\s+{_NUM}",
            "max",
            0.0001,
        ),
        (
            rf"{STAT_PATTERN}\s+between\s+{_NUM}\s+and\s+{_NUM}",
            "between",
            0.0,
        ),
    ]

    matches = []
    for pattern, mode, epsilon in patterns:
        for m in re.finditer(pattern, text):
            if mode == "between":
                stat = detect_stat(m.group(3))
                if stat is None:
                    continue
                low = _normalize_threshold_value(m.group(1), stat)
                high = _normalize_threshold_value(m.group(2), stat)
                if low > high:
                    low, high = high, low
                matches.append(
                    {
                        "start": m.start(),
                        "end": m.end(),
                        "stat": stat,
                        "min_value": low,
                        "max_value": high,
                        "text": m.group(0),
                    }
                )
            else:
                if detect_stat(m.group(2)) is None:
                    continue
                stat, min_value, max_value = _parse_threshold_match(
                    m.group(1), m.group(2), mode, epsilon
                )
                matches.append(
                    {
                        "start": m.start(),
                        "end": m.end(),
                        "stat": stat,
                        "min_value": min_value,
                        "max_value": max_value,
                        "text": m.group(0),
                    }
                )

    # Reverse patterns: STAT comes first, then operator, then number
    for pattern, mode, epsilon in reverse_patterns:
        for m in re.finditer(pattern, text):
            stat_text = m.group(1)
            stat = detect_stat(stat_text)
            if stat is None:
                continue
            if mode == "between":
                low = _normalize_threshold_value(m.group(2), stat)
                high = _normalize_threshold_value(m.group(3), stat)
                if low > high:
                    low, high = high, low
                matches.append(
                    {
                        "start": m.start(),
                        "end": m.end(),
                        "stat": stat,
                        "min_value": low,
                        "max_value": high,
                        "text": m.group(0),
                    }
                )
            else:
                min_value, max_value = _threshold_bounds(m.group(2), stat, mode, epsilon)
                matches.append(
                    {
                        "start": m.start(),
                        "end": m.end(),
                        "stat": stat,
                        "min_value": min_value,
                        "max_value": max_value,
                        "text": m.group(0),
                    }
                )

    # Fan-verb scoring thresholds with implied points: "when brunson
    # scores 30", "dropped 40", "puts up 25+". An explicit stat word after
    # the number ("drops 12 assists") keeps that stat instead of points.
    verb_pattern = (
        rf"\b(?:scores?|scored|drops?|dropped|puts?\s+up|put\s+up)\s+"
        rf"(\d{{1,3}})(?:\s*\+)?(?:\s+{STAT_PATTERN})?"
    )
    # "Lakers record when scoring 120", "LeBron splits scoring 30+": the
    # participle reads the same way, except as a ranking adjective ("top
    # scoring 5 games", "highest scoring 10 game stretch").
    scoring_pattern = (
        rf"\bscoring\s+(\d{{1,3}})(?!\d)(?:\s*\+)?(?:\s+{STAT_PATTERN})?"
        r"(?!\s*(?:-|\s)?(?:games?|players?|teams?|stretch(?:es)?|seasons?|nights?)\b)"
    )
    for m in re.finditer(scoring_pattern, text):
        if re.search(
            r"\b(?:top|highest|best|most|lowest|leading|worst|biggest)\s+$",
            text[: m.start()],
        ):
            continue
        stat_text = m.group(2) if (m.lastindex or 0) >= 2 else None
        stat = (detect_stat(stat_text) if stat_text else None) or "pts"
        matches.append(
            {
                "start": m.start(),
                "end": m.end(),
                "stat": stat,
                "min_value": _normalize_threshold_value(m.group(1), stat),
                "max_value": None,
                "text": m.group(0).rstrip(" +"),
            }
        )
        matches.extend(_joined_stat_thresholds(text, m.end()))
    for m in re.finditer(verb_pattern, text):
        stat_text = m.group(2) if (m.lastindex or 0) >= 2 else None
        stat = (detect_stat(stat_text) if stat_text else None) or "pts"
        min_value = _normalize_threshold_value(m.group(1), stat)
        matches.append(
            {
                "start": m.start(),
                "end": m.end(),
                "stat": stat,
                "min_value": min_value,
                "max_value": None,
                # Normalize trailing "+" / whitespace so equivalent
                # phrasings ("scores 35 or more" / "scores 35+") record
                # identical condition text.
                "text": m.group(0).rstrip(" +"),
            }
        )
        matches.extend(_joined_stat_thresholds(text, m.end()))

    # Fan combo shorthand: "20 10 games" / "20 and 10 games" / "20/10
    # games" = 20+ points and 10+ rebounds.
    for m in re.finditer(
        r"(?<!\bbetween )\b(\d{1,2})\s*(?:and\s+|/\s*)?(\d{1,2})\s+games?\b", text
    ):
        pts_value = int(m.group(1))
        reb_value = int(m.group(2))
        if not (10 <= pts_value <= 60 and 5 <= reb_value <= 30 and pts_value >= reb_value):
            continue
        for combo_stat, combo_value in (("pts", pts_value), ("reb", reb_value)):
            matches.append(
                {
                    "start": m.start(),
                    "end": m.end(),
                    "stat": combo_stat,
                    "min_value": float(combo_value),
                    "max_value": None,
                    "text": m.group(0),
                }
            )

    matches.extend(_extract_shooting_percentage_conditions(text))

    matches.sort(key=lambda x: x["start"])

    deduped = []
    for item in matches:
        # "scores 25+ points" also matches "25+ points" on its own; keep one
        # copy of a condition when two readings of the same words agree.
        if any(
            kept["stat"] == item["stat"]
            and kept["min_value"] == item["min_value"]
            and kept["max_value"] == item["max_value"]
            and item["start"] < kept["end"]
            and kept["start"] < item["end"]
            for kept in deduped
        ):
            continue
        deduped.append(item)

    return deduped


def extract_opponent_points_allowed_conditions(text: str) -> list[dict]:
    """Extract defensive points-allowed thresholds.

    Phrases like "held opponents under 100 points" describe the opponent's
    score, not the subject team's points. Keep them out of the generic
    ``pts`` threshold path so team finders filter on ``opponent_pts``.
    """
    _NUM = r"(\d+(?:\.\d+)?|\.\d+)"
    _POINT_SUFFIX = (
        r"(?:\s+(?:points?|pts))?"
        # Followed by the end of the clause: punctuation, a joining word, a
        # filter phrase ("at home", "vs Boston", "since March") or a season.
        r"(?=\s*(?:[?.!,]|$|\d{4}(?:-\d{2})?\b|\b(?:this|that|in|during|last|"
        r"season|year|record|when|and|or|at|on|vs|versus|against|since|over|from|"
        r"for|with|without|while|but|after|before|home|away|road|games?)\b))"
    )
    patterns = [
        rf"\bheld\s+(?:opponents?|teams?|them)\s+(?:to\s+)?(?:under|below)\s+{_NUM}{_POINT_SUFFIX}",
        rf"\blimited\s+opponents\s+to\s+(?:under|below)\s+{_NUM}{_POINT_SUFFIX}",
        rf"\bkept\s+the\s+other\s+team\s+below\s+{_NUM}{_POINT_SUFFIX}",
        rf"\ballow(?:s|ing|ed)?\s+(?:under|below|fewer\s+than|less\s+than)\s+{_NUM}{_POINT_SUFFIX}",
        rf"\b(?:points?|pts)\s+allowed\s+(?:under|below|fewer\s+than|less\s+than)\s+{_NUM}\b",
        rf"\b(?:opponent|opp)\s+(?:points?|pts)\s+(?:under|below|fewer\s+than|less\s+than)\s+{_NUM}\b",
        rf"\b(?:gave|given|giving)\s+up\s+(?:under|below|fewer\s+than|less\s+than)\s+{_NUM}{_POINT_SUFFIX}",
        rf"\bopponents?\s+under\s+{_NUM}(?:\s+(?:points?|pts))?\b",
    ]

    matches = []
    for pattern in patterns:
        for m in re.finditer(pattern, text):
            value = float(m.group(1))
            matches.append(
                {
                    "start": m.start(),
                    "end": m.end(),
                    "stat": "opponent_pts",
                    "min_value": None,
                    "max_value": value - 0.0001,
                    "text": m.group(0),
                }
            )

    matches.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))
    deduped = []
    accepted_spans: list[tuple[int, int]] = []
    for item in matches:
        span = (item["start"], item["end"])
        if any(not (span[1] <= start or span[0] >= end) for start, end in accepted_spans):
            continue
        accepted_spans.append(span)
        deduped.append(item)
    return deduped


def merge_opponent_points_allowed_conditions(
    threshold_conditions: list[dict],
    opponent_conditions: list[dict],
) -> list[dict]:
    """Prefer opponent-points conditions over overlapping generic pts ones."""
    if not opponent_conditions:
        return threshold_conditions

    def overlaps_opponent_condition(condition: dict) -> bool:
        start = condition.get("start")
        end = condition.get("end")
        if start is None or end is None:
            return False
        return any(
            not (end <= opponent["start"] or start >= opponent["end"])
            for opponent in opponent_conditions
        )

    merged = [
        condition
        for condition in threshold_conditions
        if not overlaps_opponent_condition(condition)
    ]
    merged.extend(opponent_conditions)
    merged.sort(key=lambda item: item.get("start", 0))
    return merged


def extract_min_games(text: str) -> int | None:
    """Extract a games-played minimum such as ``at least 50 games``.

    This is a sample-size qualifier on leaderboards, distinct from a per-game
    stat threshold. It is matched only when the number is directly followed by
    "games", so "at least 30 point games" stays a stat threshold.
    """
    patterns = (
        r"\bat least\s+(\d+)\s+games?\b",
        r"\bmin(?:imum)?\s+(\d+)\s+games?\b",
        r"\b(\d+)\s+or\s+more\s+games?\b",
        r"\b(\d+)\+\s*games?\b",
    )
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            value = int(m.group(1))
            if value > 0:
                return value
    return None


# Shot-attempt nouns a rate qualifier is stated in, mapped to the attempt
# column they count. A bare "attempts"/"shots" leaves the column to the rate
# being ranked (three-point percentage counts three-point attempts).
_ATTEMPT_NOUNS = (
    (
        r"(?:three[- ]?point(?:er)?|3[- ]?(?:pt|point)|three|3)s?\s+(?:attempts?|tries)|3pa|fg3a",
        "fg3a",
    ),
    (r"free[- ]?throws?\s+(?:attempts?|tries)|ft\s+attempts?|fta", "fta"),
    (r"(?:field[- ]?goal|fg|shot)s?\s+(?:attempts?|tries)|fga", "fga"),
    (r"attempts?|shots", None),
)
_ATTEMPT_NOUN = "|".join(f"(?:{pattern})" for pattern, _ in _ATTEMPT_NOUNS)
_PER_GAME_TAIL = r"(?P<per_game>\s+(?:per|a|each)\s+game)?"
_MIN_ATTEMPT_PATTERNS = (
    rf"\b(?:min(?:imum)?\.?(?:\s+of)?|at\s+least|with(?:\s+at\s+least)?)\s+"
    rf"(?P<value>\d+(?:\.\d+)?)\+?\s+(?:or\s+more\s+)?(?P<noun>{_ATTEMPT_NOUN})\b{_PER_GAME_TAIL}",
    rf"\b(?P<value>\d+(?:\.\d+)?)\+?\s+(?:or\s+more\s+)?(?P<noun>{_ATTEMPT_NOUN})\b{_PER_GAME_TAIL}"
    r"\s+(?:min(?:imum)?|minimum\s+required|to\s+qualify)\b",
    rf"\b(?P<value>\d+(?:\.\d+)?)\+\s+(?P<noun>{_ATTEMPT_NOUN})\b{_PER_GAME_TAIL}",
)


def extract_min_attempts(text: str) -> dict | None:
    """Extract a shot-attempt qualifier such as ``minimum 100 attempts``.

    A sample-size qualifier on a shooting-rate leaderboard, distinct from a
    stat threshold: "best three point percentage minimum 100 attempts" ranks
    three-point percentage among players with at least 100 three-point
    attempts. Returns ``{"value", "per_game", "attempt_stat", "span"}``;
    ``attempt_stat`` is ``None`` when the noun does not name a shot type.
    """
    for pattern in _MIN_ATTEMPT_PATTERNS:
        m = re.search(pattern, text)
        if not m:
            continue
        value = float(m.group("value"))
        if value <= 0:
            continue
        noun = m.group("noun")
        attempt_stat = next(
            (stat for noun_pattern, stat in _ATTEMPT_NOUNS if re.fullmatch(noun_pattern, noun)),
            None,
        )
        return {
            "value": value,
            "per_game": bool(m.group("per_game")),
            "attempt_stat": attempt_stat,
            "span": m.span(),
        }
    return None


def text_without_min_attempts(text: str) -> str:
    """*text* with any shot-attempt qualifier blanked out, offsets preserved.

    The qualifier names an attempt stat ("minimum 150 three point attempts")
    that is not the metric being ranked, so metric and threshold detection
    read the question without it.
    """
    qualifier = extract_min_attempts(text)
    if qualifier is None:
        return text
    start, end = qualifier["span"]
    return text[:start] + " " * (end - start) + text[end:]


def extract_min_value(text: str, stat: str | None) -> float | None:
    """Fallback threshold extraction for when extract_threshold_conditions
    finds no stat-aware match.

    Handles stat-less generic patterns (``30+``, ``at least 30``) and bare
    ``N STAT`` phrases using the unified alias table from ``STAT_PATTERN``.
    """
    # Generic stat-less patterns (no stat word adjacent to number).
    # The (?!\s+games?\b) guard keeps a games-played minimum ("at least 50
    # games") out of the stat threshold: that is a sample-size qualifier, not a
    # per-game stat cutoff, and extract_min_games picks it up instead. A stat
    # word between the number and "games" ("at least 30 point games") still
    # reads as a threshold because the lookahead only rejects a bare "games".
    _NOT_GAMES = r"(?!\s+games?\b)"
    patterns = [
        rf"\b(\d+){_NOT_GAMES}\+",
        rf"\bat least (\d+){_NOT_GAMES}\b",
        rf"\bminimum (\d+){_NOT_GAMES}\b",
        rf"\bmin(?:imum)? (\d+){_NOT_GAMES}\b",
        rf"\b(\d+){_NOT_GAMES}\s+or\s+more\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return float(m.group(1))

    if stat is None:
        return None

    # Bare N STAT — uses the unified alias table instead of per-stat
    # hardcoded patterns.  Order matters: "N STAT games" is more specific
    # than bare "N STAT", so try it first.
    # Guard against matching count/limit numbers that happen to precede
    # a stat word (e.g. "last 10 scoring" where 10 is last_n, not a threshold).
    _CG = r"(?<!last )(?<!past )(?<!top )(?<!first )(?<!bottom )"
    bare_patterns = [
        rf"{_CG}\b(\d+)\s+{STAT_PATTERN}\s+games?\b",  # "30 point games"
        rf"{_CG}\b(\d+)-{STAT_PATTERN}\s+games?\b",  # "30-point games"
        rf"{_CG}\b(\d+)\s+{STAT_PATTERN}\b",  # "30 points"
        rf"{_CG}\b(\d+)-{STAT_PATTERN}\b",  # "30-points"
    ]
    for pattern in bare_patterns:
        m = re.search(pattern, text)
        if m and detect_stat(m.group(2)) == stat:
            return float(m.group(1))

    return None


def detect_home_away(text: str) -> tuple[bool, bool]:
    home_only = bool(re.search(r"\bhome\b", text))
    away_only = bool(re.search(r"\baway\b|\broad\b", text))
    return home_only, away_only


def detect_opponent_quality(text: str) -> dict | None:
    patterns = [
        (rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}contenders\b", "contenders"),
        (rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}good\s+teams\b", "good teams"),
        (rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}bad\s+teams\b", "bad teams"),
        (rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}top\s+teams\b", "top teams"),
        (rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}top[- ]10\s+teams\b", "top 10 teams"),
        (rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}top[- ]5\s+teams\b", "top 5 teams"),
        (
            rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}top[- ]seeded\s+teams\b",
            "top seeded teams",
        ),
        *[(pattern, "playoff teams") for pattern in _PLAYOFF_TEAM_OPPONENT_QUALITY_PATTERNS],
        *[
            (pattern, "non-playoff teams")
            for pattern in _NON_PLAYOFF_TEAM_OPPONENT_QUALITY_PATTERNS
        ],
        (rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}winning\s+teams\b", "winning teams"),
        (rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}losing\s+teams\b", "losing teams"),
        (
            rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}teams?\s+(?:over|above)\s+\.500\b",
            "teams over .500",
        ),
        (
            rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}teams?\s+(?:under|below)\s+\.500\b",
            "teams under .500",
        ),
        (rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}top[- ]10\s+defenses\b", "top-10 defenses"),
        (rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}top\s+defenses\b", "top-10 defenses"),
    ]
    for pattern, term in patterns:
        if re.search(pattern, text):
            policy = OPPONENT_QUALITY_TERMS[term]
            return {
                "type": "opponent_quality",
                "surface_term": term,
                "definition": dict(policy.resolved_definition),
            }
    return None


def build_opponent_quality_note(opponent_quality: dict | None = None) -> str | None:
    del opponent_quality
    # Opponent-quality filters are represented as applied-filter chips in
    # result metadata, so repeating them as notes only leaks implementation
    # detail into the user-facing UI.
    return None


def detect_wins_losses(text: str) -> tuple[bool, bool]:
    wins_only = bool(re.search(r"\bwins?\b|\bwon\b", text))
    losses_only = bool(re.search(r"\bloss(?:es)?\b|\blost\b", text))
    return wins_only, losses_only


def detect_clutch(text: str) -> bool:
    """Detect clutch context filter.

    Surface forms: ``clutch``, ``in the clutch``, ``clutch time``,
    ``late-game`` / ``late game``.
    """
    return bool(
        re.search(r"\bclutch\b|\bin\s+the\s+clutch\b|\bclutch\s+time\b|\blate[- ]game\b", text)
    )


def detect_back_to_back(text: str) -> bool:
    """Detect back-to-back schedule context filters."""
    return bool(
        re.search(
            r"\b(?:back[- ]to[- ]backs?|b2b)\b"
            r"|\bsecond\s+of\s+(?:a\s+)?(?:back[- ]to[- ]back|b2b)\b",
            text,
        )
    )


def detect_rest_days(text: str) -> str | int | None:
    """Detect rest-context filters.

    Returns ``"advantage"`` / ``"disadvantage"`` for relative rest phrases,
    or an integer for specific-day-rest phrases such as ``on 2 days rest``.
    """
    if re.search(r"\brest\s+advantage\b", text):
        return "advantage"
    if re.search(r"\brest\s+disadvantage\b", text):
        return "disadvantage"
    if re.search(r"\b(?:on|with|after)\s+no\s+rest\b", text):
        return 0

    number_words = {
        "zero": 0,
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
    }
    word_pattern = "|".join(number_words)

    m = re.search(r"\b(?:on|with|after)\s+(\d+)\s+days?\s+rest\b", text)
    if m:
        return int(m.group(1))

    m = re.search(rf"\b(?:on|with|after)\s+({word_pattern})\s+days?\s+rest\b", text)
    if m:
        return number_words[m.group(1)]

    return None


def detect_one_possession(text: str) -> bool:
    """Detect one-possession game context filters."""
    return bool(
        re.search(
            r"\bone[- ]possession(?:\s+games?)?\b|\bwithin\s+one\s+possession\b",
            text,
        )
    )


def detect_nationally_televised(text: str) -> bool:
    """Detect national-TV context filters."""
    return bool(
        re.search(
            r"\bnationally\s+televised\b|\bon\s+national\s+tv\b|\bnational\s+tv\b",
            text,
        )
    )


def detect_role(text: str) -> str | None:
    """Detect starter/bench role filters for player-context queries."""
    if re.search(r"\bas\s+(?:a\s+)?starter\b|\bstarting\b|\bstarters?\b", text):
        return "starter"
    if re.search(r"\boff\s+the\s+bench\b|\bcoming\s+off\s+the\s+bench\b", text):
        return "bench"
    if re.search(r"\bbench\b|\breserve\b", text):
        return "bench"
    return None


def detect_quarter(text: str) -> str | None:
    """Detect quarter-level context filters.

    Surface forms: ``1st quarter`` / ``first quarter`` through
    ``4th quarter`` / ``fourth quarter``, plus ``overtime`` / ``OT``.
    """
    patterns = (
        (r"\b(?:1st|first)\s+quarter\b|\bq1\b", "1"),
        (r"\b(?:2nd|second)\s+quarter\b|\bq2\b", "2"),
        (r"\b(?:3rd|third)\s+quarter\b|\bq3\b", "3"),
        (r"\b(?:4th|fourth)\s+quarter\b|\bq4\b", "4"),
        (r"\b(?:overtime|ot)\b", "OT"),
    )
    for pattern, value in patterns:
        if re.search(pattern, text):
            return value
    return None


def detect_half(text: str) -> str | None:
    """Detect half-level context filters.

    Surface forms: ``first half`` / ``1st half`` and
    ``second half`` / ``2nd half``.
    """
    if re.search(r"\b(?:1st|first)\s+half\b", text):
        return "first"
    if re.search(r"\b(?:2nd|second)\s+half\b", text):
        return "second"
    return None


def build_period_filter_note(
    quarter: str | None = None,
    half: str | None = None,
) -> str | None:
    """Describe quarter/half filters that cannot execute on a selected route.

    The parser recognizes these surface forms. Unsupported route combinations
    fail closed with ``filter_not_supported`` instead of returning unfiltered
    full-game results.
    """
    if quarter is not None:
        return (
            "quarter filter is not supported with current data; try removing this filter "
            "or asking for full-game stats."
        )
    if half is not None:
        return (
            "half filter is not supported with current data; try removing this filter "
            "or asking for full-game stats."
        )
    return None


def detect_on_off(text: str) -> dict | None:
    """Detect single-player on/off phrasing."""
    player_fragment = r"[\w .&'\-]+?"
    phrase_patterns = (
        (rf"\bwith\s+({player_fragment})\s+on\s+(?:the\s+)?floor\b", "on"),
        (rf"\bwith\s+({player_fragment})\s+on\s+court\b", "on"),
        (rf"\bwithout\s+({player_fragment})\s+on\s+(?:the\s+)?floor\b", "off"),
        (rf"\bwithout\s+({player_fragment})\s+on\s+court\b", "off"),
        (rf"\b({player_fragment})\s+on\s+court\b", "on"),
        (rf"\b({player_fragment})\s+off\s+court\b", "off"),
        (rf"\b({player_fragment})\s+sitting\b", "off"),
    )

    for pattern, presence_state in phrase_patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        player = detect_player(match.group(1).strip())
        if player:
            if presence_state == "on" and re.search(
                r"\b(?:vs\.?|versus)\s+off\s+(?:the\s+)?(?:floor|court)\b", text
            ):
                presence_state = "both"
            return {
                "lineup_members": [player],
                "presence_state": presence_state,
            }

    if re.search(r"\bon\s*(?:/|-|\s)\s*off\b", text):
        player = detect_player(text)
        if player:
            return {
                "lineup_members": [player],
                "presence_state": "both",
            }

    return None


def build_on_off_note(
    lineup_members: list[str] | None = None,
    presence_state: str | None = None,
) -> str | None:
    """Describe the coverage-gated on/off execution contract."""
    if not lineup_members or presence_state is None:
        return None
    return (
        "on_off: source-backed execution is coverage-gated; requests fail closed when "
        "trustworthy on/off rows are unavailable for the requested slice"
    )


DEFAULT_STRETCH_WINDOW = 10
_UNSIZED_STRETCH = re.compile(
    r"\b(?:best|hottest|worst|coldest|greatest|top|poorest|ugliest)\b"
    r"(?:\s+[a-z0-9%.'/-]+){0,3}?\s+stretch(?:es)?\b"
)
# "down the stretch" is late-game play and "stretch run" the end of a season.
_NOT_A_ROLLING_STRETCH = re.compile(
    r"\b(?:down|in)\s+the\s+stretch\b|\bstretch\s+run\b"
    # "stretch four" / "stretch big" are positions.
    r"|\bstretch\s+(?:four|4|five|5|bigs?|forwards?)\b"
)


def _extract_stretch_window_size(text: str) -> int | None:
    explicit = _extract_explicit_window_size(text)
    if explicit is not None:
        return explicit
    # "Celtics best stretch" names no length; rank 10-game windows and say so.
    if _UNSIZED_STRETCH.search(text) and not _NOT_A_ROLLING_STRETCH.search(text):
        return DEFAULT_STRETCH_WINDOW
    return None


def _extract_explicit_window_size(text: str) -> int | None:
    patterns = (
        r"\b(\d+)\s*(?:-\s*|\s+)games?(?:\s+[a-z0-9%.'/-]+){0,3}\s+stretch(?:es)?\b",
        r"\brolling\s+(\d+)\s*(?:-\s*|\s+)games?\b",
        r"\brolling\s+(\d+)\s+games?\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        value = int(match.group(1))
        return value if value > 0 else None
    return None


# Shooting rates only when "shooting" names the stretch ("3 point shooting
# stretch"), never "by a shooting guard" or "scoring stretch while shooting".
_SIZE_GAP = r"(?:\s+\d+\s*(?:-\s*|\s+)games?)?\s+"
_STRETCH_SHOOTING_PATTERNS = (
    (rf"\btrue\s+shooting{_SIZE_GAP}stretch", "ts_pct"),
    (rf"\beffective\s+(?:field\s+goal\s+)?shooting{_SIZE_GAP}stretch", "efg_pct"),
    (rf"\b(?:3|three)[\s-]?(?:point|pt)?s?\s+shooting{_SIZE_GAP}stretch", "fg3_pct"),
    (rf"\bfree[\s-]?throw\s+shooting{_SIZE_GAP}stretch", "ft_pct"),
    (rf"\bshooting{_SIZE_GAP}stretch", "fg_pct"),
)
_STRETCH_GROUP_WORDS = (
    r"(?:rookies?|sophomores?|(?:point|shooting)\s+guards?|guards?"
    r"|(?:small|power)\s+forwards?|forwards?|centers?|bigs?|wings?|bench\s+players?"
    r"|reserves?|starters?)"
)
# Player groups a player stretch ranking cannot filter to, named as the subject:
# "by a rookie", "among guards", "which centers", "rookie's best stretch".
_STRETCH_PLAYER_GROUP = re.compile(
    rf"\b(?:by|for|among|of|from)\s+(?:a|an|the|all|any)?\s*{_STRETCH_GROUP_WORDS}\b"
    rf"|\b(?:which|what)\s+{_STRETCH_GROUP_WORDS}\b"
    rf"|^(?:the\s+)?{_STRETCH_GROUP_WORDS}(?:'s)?\s+(?:with\s+the\s+)?"
    r"(?:best|top|hottest|worst|coldest)\b"
)
# Worst grades the stretch unless it describes the opponent: "LeBron worst 5
# game 3 point shooting stretch", not "best stretch against the worst teams".
_OPPONENT_GRADE = re.compile(
    r"\b(?:against|vs\.?|versus|facing|over|beating|beat)\s+(?:the\s+)?"
    r"(?:worst|coldest|poorest|ugliest|bad|best|good|top|bottom|weak|strong|elite|tough)\b"
)


def stretch_text_without_opponent_grades(text: str) -> str:
    """The question with opponent grades ("against the worst teams") removed."""
    return _OPPONENT_GRADE.sub(" ", text)


_STRETCH_GRADE = re.compile(r"\b(?:(worst|coldest|poorest|ugliest|bad)|best|hottest|greatest)\b")
_STRETCH_ANCHOR = re.compile(r"\bstretch(?:es)?\b|\brolling\b")


def stretch_grade_is_worst(text: str, *, team: bool = False) -> bool | None:
    """True for worst, False for best, None when no grade is named.

    The grade nearest before the stretch ("LeBron best 5 game stretch with the
    worst teammates" is best) decides; with none there, the first grade left
    after opponent grades are removed.
    """
    graded = stretch_text_without_opponent_grades(text)
    anchor = _STRETCH_ANCHOR.search(graded)
    grades = [m for m in _STRETCH_GRADE.finditer(graded) if team or m.group(0) != "bad"]
    before = [m for m in grades if anchor and m.start() < anchor.start()]
    chosen = before[-1] if before else (grades[0] if grades else None)
    if chosen is None:
        return None
    return chosen.group(1) is not None


# Opponent descriptions no filter understands ("against the worst defenses").
_STRETCH_OPPONENT_DESCRIPTION = re.compile(
    r"\b(?:against|vs\.?|versus|facing|over|beating|beat)\s+(?:the\s+)?"
    r"(?:worst|best|bad|good|top|bottom|weak|strong|elite|tough)\s+[a-z-]+"
)


def detect_stretch_query(text: str) -> dict | None:
    """Detect rolling-window stretch leaderboard queries."""
    stretch_marker = bool(re.search(r"\bstretch(?:es)?\b", text))
    rolling_marker = bool(re.search(r"\brolling\b", text))
    if not stretch_marker and not rolling_marker:
        return None

    window_size = _extract_stretch_window_size(text)
    if window_size is None:
        return None

    if re.search(r"\b(?:winning|losing)\s+streak\b", text):
        return None

    shooting = next(
        (key for pattern, key in _STRETCH_SHOOTING_PATTERNS if re.search(pattern, text)), None
    )
    if re.search(r"\bgame\s+score\b", text):
        stretch_metric = "game_score"
    elif shooting is not None:
        # "best 3 point shooting stretch" is 3P%, not points.
        stretch_metric = shooting
    else:
        explicit_stat = detect_stat(text)
        if explicit_stat is not None:
            stretch_metric = explicit_stat
        elif re.search(r"\b(?:efficient|efficiency)\b", text):
            stretch_metric = "ts_pct"
        else:
            stretch_metric = "game_score"

    return {
        "window_size": window_size,
        "stretch_metric": stretch_metric,
        "window_defaulted": _extract_explicit_window_size(text) is None,
        "worst": bool(stretch_grade_is_worst(text)),
        "opponent_description": (
            desc.group(0).strip()
            if (desc := _STRETCH_OPPONENT_DESCRIPTION.search(text))
            and detect_opponent_quality(text) is None
            else None
        ),
        "player_group": (
            re.search(_STRETCH_GROUP_WORDS, group.group(0)).group(0)
            if (group := _STRETCH_PLAYER_GROUP.search(text))
            else None
        ),
    }


def detect_team_rolling_stretch_boundary(text: str) -> bool:
    """Detect explicit team-scoped rolling-stretch wording.

    Team rolling-window leaderboards do not have a route/result contract yet.
    This detector only covers clear generic team scope so player rolling-stretch
    queries continue to use ``player_stretch_leaderboard``.
    """
    if detect_stretch_query(text) is None:
        return False

    team_scope_patterns = (
        r"\bwhich\s+teams?\b",
        r"\bteams?\s+have\b",
        r"\bteam\s+\d+\s*(?:-\s*|\s+)games?\b",
        r"\b\d+\s*(?:-\s*|\s+)games?\s+team\b",
        r"\bstretch(?:es)?\s+by\s+(?:a\s+)?team\b",
        r"\bby\s+(?:a\s+|any\s+)?team\b",
        r"\bteams?\s+with\b",
        r"\bteams?\s+(?:best|top|hottest|worst|coldest|longest)\b",
        # "best team shooting stretch"
        r"\b(?:best|top|worst|hottest|coldest)\s+team\s+(?:[a-z0-9%-]+\s+){0,3}stretch(?:es)?\b",
    )
    return any(re.search(pattern, text) for pattern in team_scope_patterns)


_TEAM_STRETCH_METRIC_PATTERNS = (
    (r"\bnet\s+rating\b", "net_rating"),
    (r"\b(?:offensive|off)\s+rating\b", "off_rating"),
    (r"\b(?:defensive|def)\s+rating\b", "def_rating"),
    (r"\b(?:points?\s+allowed|allow(?:ed|ing)?|defen[cs]e|defensive)\b", "opp_pts"),
    (
        r"\b(?:point\s+differential|differential|margin|plus[\s-]?minus|\+/-)\b",
        "plus_minus",
    ),
    (
        r"\b(?:3|three)[\s-]?(?:point|pt)?\s+(?:shooting|percentage|pct)\b|\b3p%|\bfg3\s*%",
        "fg3_pct",
    ),
    (r"\bthrees\b|\b3s\b|\b(?:3|three)[\s-]?pointers\b", "fg3m"),
    (r"\bfree[\s-]?throw\b", "ft_pct"),
    (r"\b(?:efficient|efficiency|true\s+shooting)\b", "ts_pct"),
    (r"\bshooting\b", "fg_pct"),
    (r"\b(?:scoring|offensive|offense|points?)\b", "pts"),
    (r"\brebound(?:ing|s)?\b", "reb"),
    (r"\bassists?\b", "ast"),
    (r"\bturnovers?\b", "tov"),
    (r"\bsteals?\b", "stl"),
    (r"\bblocks?\b", "blk"),
)
# "lowest"/"most" name the end of the raw number, not good or bad.
_TEAM_STRETCH_LOW = re.compile(r"\b(?:lowest|fewest|least|min(?:imum)?)\b")
# "most defensive"/"least efficient" grade the team, not the raw number.
_TEAM_STRETCH_QUALITY = re.compile(
    r"\b(most|least)\s+(?:efficient|efficiency|defensive|offensive|dominant)\b"
)
_TEAM_STRETCH_HIGH = re.compile(
    r"\b(?:highest|most|max(?:imum)?)\b(?!\s+(?:efficient|efficiency|defensive|offensive))"
)
_TEAM_STRETCH_LOWER_IS_BETTER = {"opp_pts", "tov", "def_rating"}


def detect_team_stretch_request(text: str) -> dict | None:
    """Metric and direction of a team rolling stretch ("Celtics best 10 game stretch").

    A team's "best stretch" with no stat named means its best record over the
    window. A named stat the team route cannot rank (Game Score, minutes) is
    passed through so the route refuses it rather than ranking by record.
    ``None`` when the text is not a rolling-stretch query.
    """
    if detect_stretch_query(text) is None:
        return None
    if re.search(r"\bgame\s+score\b", text):
        metric = "game_score"
    else:
        metric = next(
            (key for pattern, key in _TEAM_STRETCH_METRIC_PATTERNS if re.search(pattern, text)),
            detect_stat(text) or "wins",
        )
    quality = _TEAM_STRETCH_QUALITY.search(text)
    grade = stretch_grade_is_worst(text, team=True)
    if grade is True:
        worst = True
    elif quality:
        worst = quality.group(1) == "least"
    elif grade is False:
        worst = False
    elif _TEAM_STRETCH_LOW.search(text):
        worst = metric not in _TEAM_STRETCH_LOWER_IS_BETTER
    elif _TEAM_STRETCH_HIGH.search(text):
        worst = metric in _TEAM_STRETCH_LOWER_IS_BETTER
    else:
        worst = False
    return {"metric": metric, "worst": worst}


_LINEUP_MEMBER_SPAN_RE = re.compile(
    r"\b(?:with|featuring|including)\s+(.+?)"
    r"(?=\s+(?:in|during|for|since|this|last|over|at|on|from|who|that|together"
    r"|lineups?|units?|combos?|minimum|min|playing|play|played)\b|\s+\d|[?!,.;]?$)"
)
_LINEUP_MEMBER_SPLIT_RE = re.compile(r"\s*(?:,|&|\band\b|\bplus\b)\s*")


def _lineup_member_phrases(text: str) -> list[tuple[int, str]]:
    """Phrases listed after "with" ("with brunson and hart" -> brunson, hart)."""
    match = _LINEUP_MEMBER_SPAN_RE.search(text)
    if not match:
        return []
    phrases = []
    span_start = match.start(1)
    for piece in _LINEUP_MEMBER_SPLIT_RE.split(match.group(1)):
        piece = piece.strip()
        if piece:
            phrases.append((text.find(piece, span_start), piece))
    return phrases


def _extract_player_mentions(text: str) -> list[str]:
    """Lineup members, in question order, resolved by the shared resolver.

    Full names and aliases anywhere in the question count. A listed member
    phrase ("with brunson and hart") that is only a last name resolves through
    ``resolve_player``; when that name belongs to several players it is kept as
    typed, so the lineup keeps its size and matches no real unit instead of
    silently answering for the members that did resolve.
    """
    players = resolve_players_in_query(text)
    extra: list[tuple[int, str]] = []
    for position, phrase in _lineup_member_phrases(text):
        if resolve_players_in_query(phrase):
            continue
        result = resolve_player(phrase)
        if result.is_confident:
            extra.append((position, result.resolved))
        elif result.is_ambiguous or len(player_last_name_candidates(phrase)) > 1:
            extra.append((position, phrase))
    if not extra:
        return players
    # Members found by the full scan keep their order; each phrase-resolved
    # member goes where its phrase sits in the question.
    ordered: list[tuple[int, str]] = []
    for name in players:
        ordered.append((_mention_position(text, name), name))
    ordered.extend(extra)
    result_names: list[str] = []
    for _, name in sorted(ordered, key=lambda item: item[0]):
        if name not in result_names:
            result_names.append(name)
    return result_names


def _mention_position(text: str, name: str) -> int:
    """Earliest position in ``text`` of any word of ``name`` (accents folded)."""
    folded = _normalize_for_matching(text)
    hits = [folded.find(word) for word in _normalize_for_matching(name).split()]
    hits = [hit for hit in hits if hit >= 0]
    return min(hits) if hits else len(text)


def detect_lineup_query(text: str) -> dict | None:
    """Detect lineup and unit phrasing that should route to lineup routes."""
    lineup_marker = bool(re.search(r"\b(?:lineups?|units?|combos?)\b", text))
    together_marker = bool(re.search(r"\btogether\b", text))
    leaderboard_marker = bool(re.search(r"\b(?:best|top|leaders?|highest|lowest)\b", text))
    with_lineup_marker = bool(re.search(r"\blineups?\s+with\b", text))

    if not lineup_marker and not together_marker and not with_lineup_marker:
        return None

    unit_size_match = re.search(r"\b([235])\s*(?:-\s*|\s+)man\b", text)
    unit_size = int(unit_size_match.group(1)) if unit_size_match else None

    minute_patterns = (
        r"\bat\s+least\s+(\d+)\+?\s+minutes\b",
        r"\bwith\s+(\d+)\+?\s+minutes\b",
        r"\b(\d+)\+\s+minutes\b",
        r"\b(\d+)\s+minutes\b",
    )
    minute_minimum = None
    for pattern in minute_patterns:
        match = re.search(pattern, text)
        if match:
            minute_minimum = int(match.group(1))
            break

    lineup_members = _extract_player_mentions(text)
    if not lineup_marker and not together_marker and len(lineup_members) < 2:
        return None

    route = "lineup_leaderboard"
    if lineup_members and (with_lineup_marker or together_marker) and not leaderboard_marker:
        route = "lineup_summary"

    if unit_size is None and lineup_members:
        unit_size = len(lineup_members)

    return {
        "route": route,
        "lineup_members": lineup_members,
        "unit_size": unit_size,
        "minute_minimum": minute_minimum,
    }


def build_lineup_note(
    lineup_members: list[str] | None = None,
    unit_size: int | None = None,
    minute_minimum: int | None = None,
) -> str | None:
    """Describe missing lineup coverage honestly."""
    if not lineup_members and unit_size is None and minute_minimum is None:
        return None
    return (
        "lineup: trusted league_lineup_viz coverage is unavailable for the requested slice; "
        "unsupported route response returned"
    )


def build_game_context_filter_notes(
    *,
    back_to_back: bool = False,
    rest_days: str | int | None = None,
    one_possession: bool = False,
    nationally_televised: bool = False,
) -> list[str]:
    """Describe schedule-context filters that cannot execute on a route.

    Unsupported route combinations fail closed with ``filter_not_supported``;
    these notes explain how to retry without the blocked filter.
    """
    notes: list[str] = []

    if back_to_back:
        notes.append(
            "back_to_back filter is not supported with current data; try removing this "
            "filter or asking for games without schedule-context filters."
        )
    if rest_days is not None:
        notes.append(
            "rest filter is not supported with current data; try removing this filter "
            "or asking for games without schedule-context filters."
        )
    if one_possession:
        notes.append(
            "one_possession filter is not supported with current data; try removing this "
            "filter or asking for games without close-game filters."
        )
    if nationally_televised:
        notes.append(
            "national_tv filter is not supported with current data; try removing this "
            "filter or asking for games without national-TV filters."
        )

    return notes


def build_role_filter_note(role: str | None = None) -> str | None:
    """Describe a starter/bench role filter blocked on the selected route."""
    if role is None:
        return None
    return (
        f"role filter ({role}) is not supported with current data; try removing this "
        "filter or asking for player stats without starter/bench role filters."
    )


def wants_summary(text: str) -> bool:
    # Word-bounded so `record` does not match `recorded` etc.
    if re.search(
        r"\bsummary\b|\bsummarize\b|\baverage\b|\baverages\b|\bavg\b"
        r"|\brecord\b|\bwhat is the record\b|\bwhat was the record\b",
        text,
    ):
        return True
    # Verb-phrase triggers for summary intent. Word-bounded so that
    # substrings like `perform` don't accidentally match `form`, and tight
    # enough not to pick up `how many` / `how often` (which are counting
    # intents, handled elsewhere).
    if re.search(
        r"\bhow\s+(?:has|have|did|do|does)\s+(?:the\s+)?[\w'\-]+"
        r"(?:\s+[\w'\-]+){0,4}\s+"
        r"(?:perform|performs|performed|play|plays|played|shoot|shoots|shot"
        r"|score|scores|scored|rebound|rebounds|rebounded|done|fared|fare)\b",
        text,
    ):
        return True
    if re.search(r"\brecent\s+form\b|\bform\b", text):
        # Preserve pre-existing `form` / `recent form` detection, but guard
        # with a word boundary so substrings like `perform` do not count.
        return True
    # Per-game-average phrasing ("points per game", "Jokic ppg") asks for
    # averages, not a game list.
    if re.search(r"\bper\s+game\b|\bppg\b|\brpg\b|\bapg\b", text):
        return True
    return False


def wants_finder(text: str) -> bool:
    """Detect explicit list/finder intent.

    Triggers on phrases like 'show me', 'list', 'find', 'give me',
    'what games', 'which games', 'show all', 'show every', 'show games'.
    """
    return bool(
        re.search(
            r"\b(show\s+me|list|find|give\s+me|what\s+games|which\s+games"
            r"|show\s+all|show\s+every|show\s+games)\b",
            text,
        )
    )


def wants_count(text: str) -> bool:
    """Detect explicit count intent.

    Triggers on phrases like 'how many', 'how often', 'count', 'number of',
    'total number', 'total count', 'total games'.
    """
    # "how many points does X average" asks for a per-game rate, not a
    # count of games — that is summary intent, handled by wants_summary.
    if re.search(r"\bhow\s+many\b[\w\s'\-]*\b(?:do|does|did)\b[\w\s'\-]*\baverages?\b", text):
        return False
    return bool(
        re.search(
            r"\b(how\s+many|how\s+often|count|number\s+of|total\s+(?:number|count|games))\b",
            text,
        )
    )


def detect_season_high_intent(text: str) -> bool:
    """Detect single-game-best / season-high intent.

    Triggers on:
    - 'season high' / 'season-high'
    - 'best game' / 'best single game'
    - 'highest game' / 'highest single game'
    - 'game high' / 'game-high'
    - 'best scoring game(s)'
    - 'top/highest scoring game(s)'
    - 'biggest scoring game(s)'
    - 'most dominant game(s)'
    """
    # The season-type qualifier ("playoff(s)"/"postseason") is captured
    # separately; strip it so it does not split phrases like "best playoff
    # games" / "best playoff performances".
    scan = re.sub(r"\b(?:playoffs?|postseason)\b", " ", text)
    scan = re.sub(r"\s+", " ", scan).strip()

    if re.search(
        r"\b(?:season|career)[- ]?highs?\b"
        r"|\b(?:best|highest)\s+(?:single[- ]?)?games?\b"
        rf"|\b(?:top|best|highest)\s+(?:single[- ]?)?(?:(?:team|player)\s+)?"
        rf"{STAT_PATTERN}\s+(?:(?:team|player)\s+)?games?\b"
        r"|\bbiggest\s+(?:single\s+)?(?:scoring\s+|triple[- ]double\s+)?games?\b"
        r"|\bmost\s+dominant\s+(?:single\s+)?games?\b"
        r"|\bgame[- ]?high\b"
        # "best/top performances" is the same top-single-game concept as
        # "best games", phrased differently.
        r"|\b(?:best|top|highest|biggest|greatest)\s+(?:single[- ]?)?(?:scoring\s+)?performances?\b"
        r"|\bsingle[- ]?game\s+(?:high|best|record)\b",
        scan,
    ):
        return True

    if detect_stat(scan) is None:
        return False

    single_game_marker = re.search(r"\bin a game\b|\bsingle[- ]game\b", scan)
    ranking_marker = re.search(
        r"\b(?:most|highest|biggest|best|top|leaders?)\b",
        scan,
    )
    if single_game_marker and ranking_marker:
        return True

    stat_games_marker = re.search(
        rf"\b(?:highest|biggest|best)\s+{STAT_PATTERN}\s+games?\b",
        scan,
    )
    return bool(stat_games_marker)


def detect_distinct_player_count(text: str) -> bool:
    """Detect 'how many players' / 'number of players' counting intent.

    Triggers on queries asking for count of distinct players meeting a condition.
    Example: 'How many players have recorded 10+ assists in a game this year?'
    """
    return bool(
        re.search(
            r"\bhow\s+many\s+players?\b"
            r"|\bnumber\s+of\s+players?\b"
            r"|\bcount\s+(?:of\s+)?(?:distinct\s+)?players?\b",
            text,
        )
    )


def detect_distinct_team_count(text: str) -> bool:
    """Detect 'how many teams' counting intent."""
    return bool(
        re.search(
            r"\bhow\s+many\s+teams?\b"
            r"|\bnumber\s+of\s+teams?\b"
            r"|\bcount\s+(?:of\s+)?(?:distinct\s+)?teams?\b",
            text,
        )
    )


def wants_recent_form(text: str) -> bool:
    return bool(re.search(r"\b(recent form|form)\b", text))


def wants_split_summary(text: str) -> bool:
    return "split" in text or detect_split_type(text) is not None


# -- Playoff series situations --------------------------------------------

_SERIES_GAME_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
}
_SERIES_GAME_TOKEN = r"(?:[1-7]|one|two|three|four|five|six|seven)"
# What follows a game number when it is a count or a stat, not a series game:
# "game 5 3 pointers", "games 2 and 3 steals", "game 3 times". A year
# ("game 7s 2016") or "2 seasons ago" is not a count.
_NOT_A_SERIES_GAME_TAIL = (
    r"(?!\s*(?:\+|-|\.\d|\d(?!\d{3}\b|\d{3}-|\s+(?:seasons?|years?|postseasons?)\s+ago\b)|"
    r"or\s+(?:more|fewer|less)|times?\b|straight\b|in\s+a\s+row\b|made\b|from\s+(?:three|3)\b|"
    rf"games?\b|days?\b|seasons?\b|{STAT_PATTERN}))"
)
# "game 7", "game sevens", "a game 6". "games 5 3 pointers" and "last 10
# games 3 pointers" are counts, so a lone number takes the singular "game".
_SERIES_GAME_NUMBER = re.compile(
    rf"\bgame\s*(?:#\s*)?({_SERIES_GAME_TOKEN})(?:s|es)?\b" + _NOT_A_SERIES_GAME_TAIL
)
# "games 2 and 3", "game 6 or game 7", "games 1 through 5", "games 5-7".
_SERIES_GAME_SET = re.compile(
    rf"\bgames?\s*({_SERIES_GAME_TOKEN})(?:s|es)?\s*"
    r"(?:(,|and|&|or)\s*(?:game\s*)?|(through|thru|to|-|–)\s*(?:game\s*)?)"
    rf"({_SERIES_GAME_TOKEN})(?:s|es)?\b" + _NOT_A_SERIES_GAME_TAIL
)
_SERIES_ELIMINATION = re.compile(
    r"\b(?:elimination\s+games?|facing\s+elimination|faced\s+elimination|"
    r"on\s+the\s+brink\s+of\s+elimination|do[\s-]or[\s-]die|must[\s-]win\s+games?|"
    r"with\s+(?:their|his|the)\s+season\s+on\s+the\s+line)\b"
)
_SERIES_CLOSEOUT = re.compile(
    r"\b(?:close[\s-]?out\s+games?|closeout\s+opportunit(?:y|ies)|"
    r"(?:series[\s-])?clinching\s+games?|chances?\s+to\s+(?:close\s+out|clinch)(?:\s+a\s+series)?)\b"
)
_SERIES_DECIDING = re.compile(
    r"\b(?:winner[\s-]take[\s-]all(?:\s+games?)?|deciding\s+games?|decisive\s+games?)\b"
)
_SERIES_SCORE = re.compile(
    r"\b(?:(leading|up|ahead)|(trailing|down|behind)|(tied))"
    r"(?:\s+in\s+(?:the|a)\s+series)?\s+([0-3])\s*[-–]\s*([0-3])\b"
    r"(?!\s*(?:in\s+(?:the\s+)?(?:first|second|third|fourth|1st|2nd|3rd|4th)\s+quarter|run\b))"
)
# "game 2 of a back to back", "game 3 of the road trip" are not series games.
_NOT_A_SERIES_GAME = re.compile(
    r"\s+(?:of|in)\s+(?:a|an|the|this|their|his)?\s*"
    r"(?:back[\s-]to[\s-]backs?|b2bs?|road\s+trips?|homestands?|home\s+stands?|trips?|seasons?)\b"
    r"|\s+of\s+(?:the|their|his|its)\s+(?:last|past)\b"
)
# "up 2-0 in the season series" or "on the season" is not a playoff series;
# "tied 2-2 after the first quarter" and "down 0-3 in their last 3" are not either.
_NOT_A_SERIES_SCORE = re.compile(
    r"\s+(?:(?:in|on|for)\s+(?:the|their|a)\s+season\b"
    r"|(?:in|after|through|at)\s+(?:the\s+)?(?:first|second|third|fourth|1st|2nd|3rd|4th)\b"
    r"|(?:at|by)\s+(?:the\s+)?half(?:time)?\b"
    r"|in\s+(?:the|their|his|its)\s+(?:last|past|first)\b"
    r"|(?:in|on|over)\s+(?:the|their|this|a)\s+(?:road\s+trip|homestand|stretch|month|week)\b)"
)
# Series-level outcomes: "came back from 3-1 down", "blew a 3-1 lead".
_SERIES_SCORE_TEXT = r"([0-3])\s*[-–]\s*([0-3])"
_SERIES_COMEBACK = re.compile(
    r"\b(?:came\s+back\s+from|come\s+back\s+from|comebacks?\s+from|overc[ao]me|"
    r"rallied\s+from|rally\s+from)\b[^.?!]{0,25}?\b" + _SERIES_SCORE_TEXT + r"\b"
    r"|\b" + _SERIES_SCORE_TEXT + r"\s+(?:series\s+)?comebacks?\b"
)
_SERIES_BLOWN = re.compile(
    r"\b(?:blew|blown|blow|blowing|squandered|collapsed?\s+(?:from|after))\b"
    r"[^.?!]{0,25}?\b" + _SERIES_SCORE_TEXT + r"\b"
    r"|\b" + _SERIES_SCORE_TEXT + r"\s+(?:series\s+)?(?:collapses?|leads?\s+blown)\b"
)


#: Wording a resolved series situation accounts for (leaderboard residual check).
SERIES_SITUATION_PATTERNS: tuple[str, ...] = (
    _SERIES_GAME_SET.pattern,
    r"\bgames?\s*(?:#\s*)?(?:[1-7]|one|two|three|four|five|six|seven)(?:s|es)?\b",
    _SERIES_ELIMINATION.pattern,
    _SERIES_CLOSEOUT.pattern,
    _SERIES_DECIDING.pattern,
    r"\b(?:leading|up|ahead|trailing|down|behind|tied)(?:\s+in\s+(?:the|a)\s+series)?"
    r"\s+[0-3]\s*[-–]\s*[0-3]\b",
    r"\b(?:when|while|with|of\s+(?:a|the)\s+series|in\s+(?:a|the)\s+series)\b",
)


def detect_series_comeback(text: str) -> dict | None:
    """Series comeback or collapse wording, with the series score it turned on.

    "came back from 3-1 down" is ``{"wins": 1, "losses": 3, "blown": False}``
    (the team trailed 1-3 and won the series); "blew a 3-1 lead" is
    ``{"wins": 3, "losses": 1, "blown": True}`` (led 3-1 and lost it).
    """
    lowered = text.lower()
    for pattern, blown in ((_SERIES_BLOWN, True), (_SERIES_COMEBACK, False)):
        match = pattern.search(lowered)
        if not match:
            continue
        a, b = (int(n) for n in match.groups() if n is not None)
        if a == b:
            return None
        high, low = max(a, b), min(a, b)
        if blown:
            return {"wins": high, "losses": low, "blown": True}
        return {"wins": low, "losses": high, "blown": False}
    return None


def detect_series_situation(text: str) -> str | None:
    """Playoff series situation named in ``text``, as a code.

    ``game_N`` (game N of a series; ``game_2_3`` for games 2 and 3),
    ``elimination`` (one loss from going home), ``closeout`` (one win from
    taking the series), ``deciding`` (both teams one win away), or
    ``score_W_L`` (the team's series wins and losses before the game: "up 3-1"
    is ``score_3_1``, "down 3-1" and "trailing 1-3" ``score_1_3``).
    """
    lowered = text.lower()
    if detect_series_comeback(lowered):
        return None
    if _SERIES_DECIDING.search(lowered):
        return "deciding"
    if _SERIES_ELIMINATION.search(lowered):
        return "elimination"
    if _SERIES_CLOSEOUT.search(lowered):
        return "closeout"
    score = _SERIES_SCORE.search(lowered)
    if score and not _NOT_A_SERIES_SCORE.match(lowered, score.end()):
        a, b = int(score.group(4)), int(score.group(5))
        if score.group(3):
            if a != b:
                return None
            wins = losses = a
        elif score.group(1):
            wins, losses = max(a, b), min(a, b)
        else:
            wins, losses = min(a, b), max(a, b)
        if score.group(3) is None and wins == losses:
            return None
        return f"score_{wins}_{losses}"
    games = _SERIES_GAME_SET.search(lowered)
    if games and not _NOT_A_SERIES_GAME.match(lowered, games.end()):
        first, last = (_series_game_value(games.group(n)) for n in (1, 4))
        if games.group(3):
            numbers = list(range(min(first, last), max(first, last) + 1))
        else:
            numbers = sorted({first, last})
        return "game_" + "_".join(str(n) for n in numbers)
    number = _SERIES_GAME_NUMBER.search(lowered)
    if number and not _NOT_A_SERIES_GAME.match(lowered, number.end()):
        return f"game_{_series_game_value(number.group(1))}"
    return None


def _series_game_value(token: str) -> int:
    return int(token) if token.isdigit() else _SERIES_GAME_WORDS[token]
