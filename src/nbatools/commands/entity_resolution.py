"""Entity resolution layer for players and teams.

Resolves user input (last names, nicknames, abbreviations, aliases)
to canonical player names and team abbreviations used in the data.

Resolution result types:
- ``Confident``  — exactly one match, use it
- ``Ambiguous``  — multiple candidates, surface them to the user
- ``NoMatch``    — nothing matched

The module builds a data-driven player index from CSV files so that
last-name resolution stays current with whatever seasons are loaded.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Resolution result types
# ---------------------------------------------------------------------------


@dataclass
class ResolutionResult:
    """Result of an entity resolution attempt."""

    resolved: str | None = None
    candidates: list[str] = field(default_factory=list)
    confidence: str = "none"  # "confident" | "ambiguous" | "none"
    source: str = ""  # how it was resolved: "alias", "last_name", "nickname", etc.

    @property
    def is_confident(self) -> bool:
        return self.confidence == "confident"

    @property
    def is_ambiguous(self) -> bool:
        return self.confidence == "ambiguous"


def _no_match() -> ResolutionResult:
    return ResolutionResult(confidence="none")


def _confident(name: str, source: str) -> ResolutionResult:
    return ResolutionResult(resolved=name, candidates=[name], confidence="confident", source=source)


def _ambiguous(candidates: list[str], source: str) -> ResolutionResult:
    return ResolutionResult(candidates=sorted(candidates), confidence="ambiguous", source=source)


# ---------------------------------------------------------------------------
# Curated player aliases (nicknames, acronyms, short names)
#
# Only grounded, widely recognized aliases.  No speculative/meme mappings.
# ---------------------------------------------------------------------------

CURATED_PLAYER_ALIASES: dict[str, str] = {
    "kobe": "Kobe Bryant",
    "lebron": "LeBron James",
    "jokic": "Nikola Jokić",
    "nikola jokic": "Nikola Jokić",
    "embiid": "Joel Embiid",
    "joel embiid": "Joel Embiid",
    "luka": "Luka Dončić",
    "harden": "James Harden",
    "iverson": "Allen Iverson",
    "dirk": "Dirk Nowitzki",
    "rodman": "Dennis Rodman",
    "tim duncan": "Tim Duncan",
}

PLAYER_NICKNAME_ALIASES: dict[str, str] = {
    # Initials / acronyms
    "sga": "Shai Gilgeous-Alexander",
    "kd": "Kevin Durant",
    "cp3": "Chris Paul",
    "ad": "Anthony Davis",
    "anthony davis": "Anthony Davis",
    "pg": "Paul George",
    "rj": "RJ Barrett",
    "cj": "CJ McCollum",
    "tj": "T.J. McConnell",
    "aj": "AJ Griffin",
    "pj": "P.J. Washington",
    "og": "OG Anunoby",
    "rui": "Rui Hachimura",
    # Common nicknames
    "bron": "LeBron James",
    "king james": "LeBron James",
    "the king": "LeBron James",
    "ant": "Anthony Edwards",
    "ant-man": "Anthony Edwards",
    "ant man": "Anthony Edwards",
    "greek freak": "Giannis Antetokounmpo",
    "the greek freak": "Giannis Antetokounmpo",
    "giannis": "Giannis Antetokounmpo",
    "steph": "Stephen Curry",
    "chef curry": "Stephen Curry",
    "dame": "Damian Lillard",
    "dame time": "Damian Lillard",
    "bam": "Bam Adebayo",
    "kat": "Karl-Anthony Towns",
    "melo": "Carmelo Anthony",
    "ja": "Ja Morant",
    "zo": "Lonzo Ball",
    "zion": "Zion Williamson",
    "trae": "Trae Young",
    "ice trae": "Trae Young",
    "spida": "Donovan Mitchell",
    "book": "Devin Booker",
    "d-book": "Devin Booker",
    "slim reaper": "Kevin Durant",
    "the beard": "James Harden",
    "the claw": "Kawhi Leonard",
    "kawhi": "Kawhi Leonard",
    "jimmy buckets": "Jimmy Butler",
    "jimmy butler": "Jimmy Butler",
    "joker": "Nikola Jokić",
    "the joker": "Nikola Jokić",
    "big honey": "Nikola Jokić",
    "sengun": "Alperen Sengun",
    "wemby": "Victor Wembanyama",
    "wemb": "Victor Wembanyama",
    "chet": "Chet Holmgren",
    "fox": "De'Aaron Fox",
    "herb": "Herbert Jones",
    "maxey": "Tyrese Maxey",
    "tyrese maxey": "Tyrese Maxey",
    "halliburton": "Tyrese Haliburton",
    "hali": "Tyrese Haliburton",
    "paolo": "Paolo Banchero",
    "scottie": "Scottie Barnes",
    # Historical nicknames
    "mamba": "Kobe Bryant",
    "black mamba": "Kobe Bryant",
    "the answer": "Allen Iverson",
    "ai": "Allen Iverson",
    "the big fundamental": "Tim Duncan",
    "flash": "Dwyane Wade",
    "d-wade": "Dwyane Wade",
    "dwade": "Dwyane Wade",
    "big ticket": "Kevin Garnett",
    "kg": "Kevin Garnett",
    "shaq": "Shaquille O'Neal",
    "diesel": "Shaquille O'Neal",
    "the diesel": "Shaquille O'Neal",
    "truth": "Paul Pierce",
    "the truth": "Paul Pierce",
    "tmac": "Tracy McGrady",
    "t-mac": "Tracy McGrady",
    "vince": "Vince Carter",
    "vinsanity": "Vince Carter",
    "dirk": "Dirk Nowitzki",
    "the big aristotle": "Shaquille O'Neal",
    "nash": "Steve Nash",
    "russ": "Russell Westbrook",
    "brodie": "Russell Westbrook",
    "the brodie": "Russell Westbrook",
    "westbrook": "Russell Westbrook",
    "draymond": "Draymond Green",
    "klay": "Klay Thompson",
    "splash brother": "Stephen Curry",
    # Common first-name only (where unambiguous in NBA context)
    "luka": "Luka Dončić",
    "nikola": "Nikola Jokić",  # Jokić is the dominant "Nikola" in modern NBA
    "lebron": "LeBron James",
    "kyrie": "Kyrie Irving",
    "jaylen": "Jaylen Brown",
    "jayson": "Jayson Tatum",
    "demar": "DeMar DeRozan",
    "lamelo": "LaMelo Ball",
    "dejounte": "Dejounte Murray",
    # Dominant last-name aliases (where one player is the overwhelming modern reference)
    "tatum": "Jayson Tatum",
    "brunson": "Jalen Brunson",
    "booker": "Devin Booker",
    "curry": "Stephen Curry",
    "harden": "James Harden",
    "embiid": "Joel Embiid",
    "butler": "Jimmy Butler",
    "mitchell": "Donovan Mitchell",
    "lillard": "Damian Lillard",
    "morant": "Ja Morant",
    "durant": "Kevin Durant",
    "irving": "Kyrie Irving",
    "leonard": "Kawhi Leonard",
    "george": "Paul George",
    "adebayo": "Bam Adebayo",
    "towns": "Karl-Anthony Towns",
    "anthony": "Carmelo Anthony",
    "simmons": "Ben Simmons",
    "williamson": "Zion Williamson",
    "ingram": "Brandon Ingram",
    "randle": "Julius Randle",
    "derozan": "DeMar DeRozan",
    "simons": "Anfernee Simons",
    "reaves": "Austin Reaves",
    "edwards": "Anthony Edwards",
    "barnes": "Scottie Barnes",
    "banchero": "Paolo Banchero",
    "wembanyama": "Victor Wembanyama",
    "holmgren": "Chet Holmgren",
    "garland": "Darius Garland",
    "mobley": "Evan Mobley",
    "cunningham": "Cade Cunningham",
    "doncic": "Luka Dončić",
    "antetokounmpo": "Giannis Antetokounmpo",
    "jokic": "Nikola Jokić",
    "iverson": "Allen Iverson",
    "bryant": "Kobe Bryant",
    "wade": "Dwyane Wade",
    "pierce": "Paul Pierce",
    "garnett": "Kevin Garnett",
    "nowitzki": "Dirk Nowitzki",
    "duncan": "Tim Duncan",
    "carter": "Vince Carter",
    "mcgrady": "Tracy McGrady",
    "o'neal": "Shaquille O'Neal",
    "oneal": "Shaquille O'Neal",
    "rodman": "Dennis Rodman",
    "pippen": "Scottie Pippen",
    "stockton": "John Stockton",
    "malone": "Karl Malone",
    "barkley": "Charles Barkley",
    "olajuwon": "Hakeem Olajuwon",
    "ewing": "Patrick Ewing",
    "robinson": "David Robinson",
    "payton": "Gary Payton",
    "kidd": "Jason Kidd",
    "drummond": "Andre Drummond",
    "sabonis": "Domantas Sabonis",
    "haliburton": "Tyrese Haliburton",
    "bronny": "Bronny James",
    "bronny james": "Bronny James",
}

# Full-name aliases with accent normalization
PLAYER_FULL_NAME_ALIASES: dict[str, str] = {
    "nikola jokic": "Nikola Jokić",
    "luka doncic": "Luka Dončić",
    "bogdan bogdanovic": "Bogdan Bogdanović",
    "bojan bogdanovic": "Bojan Bogdanović",
    "jonas valanciunas": "Jonas Valančiūnas",
    "dario saric": "Dario Šarić",
    "jusuf nurkic": "Jusuf Nurkić",
    "nikola vucevic": "Nikola Vučević",
    "kristaps porzingis": "Kristaps Porziņģis",
    "davis bertans": "Dāvis Bertāns",
    "goran dragic": "Goran Dragić",
    "dennis schroder": "Dennis Schröder",
    "dennis schroeder": "Dennis Schröder",
    "alperen sengun": "Alperen Şengün",
    "vasilije micic": "Vasilije Micić",
    "sandro mamukelashvili": "Sandro Mamukelashvili",
}

# ---------------------------------------------------------------------------
# Curated team aliases (expanded)
# ---------------------------------------------------------------------------

CURATED_TEAM_ALIASES: dict[str, str] = {
    "atlanta": "ATL",
    "hawks": "ATL",
    "boston": "BOS",
    "celtics": "BOS",
    "brooklyn": "BKN",
    "nets": "BKN",
    "charlotte": "CHA",
    "hornets": "CHA",
    "chicago": "CHI",
    "bulls": "CHI",
    "cleveland": "CLE",
    "cavs": "CLE",
    "cavaliers": "CLE",
    "dallas": "DAL",
    "mavericks": "DAL",
    "mavs": "DAL",
    "denver": "DEN",
    "nuggets": "DEN",
    "detroit": "DET",
    "pistons": "DET",
    "golden state": "GSW",
    "warriors": "GSW",
    "houston": "HOU",
    "rockets": "HOU",
    "indiana": "IND",
    "pacers": "IND",
    "clippers": "LAC",
    "la clippers": "LAC",
    "los angeles clippers": "LAC",
    "lakers": "LAL",
    "la lakers": "LAL",
    "los angeles lakers": "LAL",
    "memphis": "MEM",
    "grizzlies": "MEM",
    "miami": "MIA",
    "heat": "MIA",
    "milwaukee": "MIL",
    "bucks": "MIL",
    "minnesota": "MIN",
    "wolves": "MIN",
    "timberwolves": "MIN",
    "new orleans": "NOP",
    "pelicans": "NOP",
    "new york": "NYK",
    "knicks": "NYK",
    "oklahoma city": "OKC",
    "thunder": "OKC",
    "orlando": "ORL",
    "magic": "ORL",
    "philadelphia": "PHI",
    "sixers": "PHI",
    "76ers": "PHI",
    "phoenix": "PHX",
    "suns": "PHX",
    "portland": "POR",
    "blazers": "POR",
    "trail blazers": "POR",
    "sacramento": "SAC",
    "kings": "SAC",
    "san antonio": "SAS",
    "spurs": "SAS",
    "toronto": "TOR",
    "raptors": "TOR",
    "utah": "UTA",
    "jazz": "UTA",
    "washington": "WAS",
    "wizards": "WAS",
}

TEAM_ALIASES_EXPANDED: dict[str, str] = {
    # Standard city / nickname mappings (existing)
    "atlanta": "ATL",
    "hawks": "ATL",
    "boston": "BOS",
    "celtics": "BOS",
    "brooklyn": "BKN",
    "nets": "BKN",
    "charlotte": "CHA",
    "hornets": "CHA",
    "chicago": "CHI",
    "bulls": "CHI",
    "cleveland": "CLE",
    "cavs": "CLE",
    "cavaliers": "CLE",
    "dallas": "DAL",
    "mavericks": "DAL",
    "mavs": "DAL",
    "denver": "DEN",
    "nuggets": "DEN",
    "detroit": "DET",
    "pistons": "DET",
    "golden state": "GSW",
    "warriors": "GSW",
    "houston": "HOU",
    "rockets": "HOU",
    "indiana": "IND",
    "pacers": "IND",
    "clippers": "LAC",
    "la clippers": "LAC",
    "los angeles clippers": "LAC",
    "lakers": "LAL",
    "la lakers": "LAL",
    "los angeles lakers": "LAL",
    "memphis": "MEM",
    "grizzlies": "MEM",
    "miami": "MIA",
    "heat": "MIA",
    "milwaukee": "MIL",
    "bucks": "MIL",
    "minnesota": "MIN",
    "wolves": "MIN",
    "timberwolves": "MIN",
    "new orleans": "NOP",
    "pelicans": "NOP",
    "new york": "NYK",
    "knicks": "NYK",
    "oklahoma city": "OKC",
    "thunder": "OKC",
    "orlando": "ORL",
    "magic": "ORL",
    "philadelphia": "PHI",
    "sixers": "PHI",
    "76ers": "PHI",
    "phoenix": "PHX",
    "suns": "PHX",
    "portland": "POR",
    "blazers": "POR",
    "trail blazers": "POR",
    "sacramento": "SAC",
    "kings": "SAC",
    "san antonio": "SAS",
    "spurs": "SAS",
    "toronto": "TOR",
    "raptors": "TOR",
    "utah": "UTA",
    "jazz": "UTA",
    "washington": "WAS",
    "wizards": "WAS",
    # --- 3-letter abbreviations ---
    "atl": "ATL",
    "bos": "BOS",
    "bkn": "BKN",
    "cha": "CHA",
    "chi": "CHI",
    "cle": "CLE",
    "dal": "DAL",
    "den": "DEN",
    "det": "DET",
    "gsw": "GSW",
    "hou": "HOU",
    "ind": "IND",
    "lac": "LAC",
    "lal": "LAL",
    "mem": "MEM",
    "mia": "MIA",
    "mil": "MIL",
    "min": "MIN",
    "nop": "NOP",
    "nyk": "NYK",
    "okc": "OKC",
    "orl": "ORL",
    "phi": "PHI",
    "phx": "PHX",
    "por": "POR",
    "sac": "SAC",
    "sas": "SAS",
    "tor": "TOR",
    "uta": "UTA",
    "was": "WAS",
    # --- Common informal nicknames ---
    "dubs": "GSW",
    "c's": "BOS",
    "cs": "BOS",
    "philly": "PHI",
    "nola": "NOP",
    "pels": "NOP",
    "clips": "LAC",
    "grizz": "MEM",
    "t-wolves": "MIN",
    "twolves": "MIN",
    "t wolves": "MIN",
    "nugs": "DEN",
    "raps": "TOR",
    "wiz": "WAS",
    # --- Possessive team names (common in queries) ---
    "celtics'": "BOS",
    "lakers'": "LAL",
    "warriors'": "GSW",
    "knicks'": "NYK",
    "sixers'": "PHI",
    "bucks'": "MIL",
    # --- Full formal names ---
    "atlanta hawks": "ATL",
    "boston celtics": "BOS",
    "brooklyn nets": "BKN",
    "charlotte hornets": "CHA",
    "chicago bulls": "CHI",
    "cleveland cavaliers": "CLE",
    "dallas mavericks": "DAL",
    "denver nuggets": "DEN",
    "detroit pistons": "DET",
    "golden state warriors": "GSW",
    "houston rockets": "HOU",
    "indiana pacers": "IND",
    "memphis grizzlies": "MEM",
    "miami heat": "MIA",
    "milwaukee bucks": "MIL",
    "minnesota timberwolves": "MIN",
    "new orleans pelicans": "NOP",
    "new york knicks": "NYK",
    "oklahoma city thunder": "OKC",
    "orlando magic": "ORL",
    "philadelphia 76ers": "PHI",
    "phoenix suns": "PHX",
    "portland trail blazers": "POR",
    "sacramento kings": "SAC",
    "san antonio spurs": "SAS",
    "toronto raptors": "TOR",
    "utah jazz": "UTA",
    "washington wizards": "WAS",
}


def _merge_alias_maps(*alias_maps: dict[str, str]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for alias_map in alias_maps:
        for key, value in alias_map.items():
            merged.setdefault(key, value)
    return merged


# Backward-compatible merged alias maps used by natural-query helpers.
PLAYER_ALIASES: dict[str, str] = _merge_alias_maps(
    CURATED_PLAYER_ALIASES,
    PLAYER_NICKNAME_ALIASES,
    PLAYER_FULL_NAME_ALIASES,
)

TEAM_ALIASES: dict[str, str] = _merge_alias_maps(CURATED_TEAM_ALIASES, TEAM_ALIASES_EXPANDED)

# All 30 canonical abbreviations
ALL_TEAM_ABBRS: set[str] = {
    "ATL",
    "BOS",
    "BKN",
    "CHA",
    "CHI",
    "CLE",
    "DAL",
    "DEN",
    "DET",
    "GSW",
    "HOU",
    "IND",
    "LAC",
    "LAL",
    "MEM",
    "MIA",
    "MIL",
    "MIN",
    "NOP",
    "NYK",
    "OKC",
    "ORL",
    "PHI",
    "PHX",
    "POR",
    "SAC",
    "SAS",
    "TOR",
    "UTA",
    "WAS",
}


# ---------------------------------------------------------------------------
# Accent / Unicode normalization helpers
# ---------------------------------------------------------------------------


def _strip_accents(text: str) -> str:
    """Remove accents/diacritics from text for matching purposes."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _normalize_for_matching(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace."""
    return " ".join(_strip_accents(text).lower().strip().split())


# ---------------------------------------------------------------------------
# Data-driven player index (built from CSV data)
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"


def _build_player_index(data_dir: Path | None = None) -> dict[str, list[str]]:
    """Build a last-name → list[full-name] index from player game stats CSVs.

    Scans all available season files to capture the broadest set of
    player names.  Returns a dict mapping lowercased last names to
    lists of canonical full names (as they appear in the data).
    """
    if data_dir is None:
        data_dir = _DATA_DIR

    stats_dir = data_dir / "raw" / "player_game_stats"
    if not stats_dir.exists():
        return {}

    all_names: set[str] = set()
    for csv_path in stats_dir.glob("*.csv"):
        try:
            df = pd.read_csv(csv_path, usecols=["player_name"], dtype=str)
            all_names.update(df["player_name"].dropna().unique())
        except Exception:
            continue

    # Build last-name index
    last_name_index: dict[str, list[str]] = {}
    for name in sorted(all_names):
        parts = name.strip().split()
        if len(parts) < 2:
            continue

        # Handle "Jr.", "III", "II", "IV" suffixes
        last = parts[-1]
        if last.rstrip(".").lower() in ("jr", "sr", "ii", "iii", "iv", "v"):
            if len(parts) >= 3:
                last = parts[-2]
            else:
                continue

        key = _strip_accents(last).lower()
        if key not in last_name_index:
            last_name_index[key] = []
        if name not in last_name_index[key]:
            last_name_index[key].append(name)

    return last_name_index


# Module-level cache (built lazily)
_player_last_name_index: dict[str, list[str]] | None = None


def _get_player_index() -> dict[str, list[str]]:
    """Get (or build) the cached player last-name index."""
    global _player_last_name_index
    if _player_last_name_index is None:
        _player_last_name_index = _build_player_index()
    return _player_last_name_index


def reset_player_index() -> None:
    """Force rebuild of the player index (for testing)."""
    global _player_last_name_index
    _player_last_name_index = None


# ---------------------------------------------------------------------------
# Ambiguous last names that should never auto-resolve because they are
# too common or refer to very different players across eras.
# We still allow them if they appear in curated aliases (which are explicit).
# ---------------------------------------------------------------------------

NEVER_AUTO_RESOLVE_LAST_NAMES: set[str] = {
    "james",  # LeBron James, but also other James
    "green",  # Draymond, Danny, Jeff, AJ, etc.
    "johnson",  # many
    "williams",  # many
    "smith",  # many
    "jones",  # many
    "brown",  # many
    "davis",  # Anthony Davis, but also others
    "thomas",  # many
    "thompson",  # Klay, Tristan, Amen, Ausar, etc.
    "harris",  # many
    "robinson",  # many
    "martin",  # many
    "jackson",  # many
    "washington",  # also a team name
    "holiday",  # Jrue, Aaron, Justin
    "ball",  # LaMelo, Lonzo
    "walker",  # many
    "gordon",  # Aaron, Eric
    "murray",  # Dejounte, Jamal
    "young",  # Trae, Thaddeus
    "wright",  # many
    "porter",  # Michael, Otto, Kevin
    "grant",  # Jerami, others
    "white",  # Derrick, Coby, etc.
    "ross",  # many
    "anderson",  # many
    "lee",  # many
    "king",  # many
    "moore",  # many
    "wells",  # many
    "brooks",  # many
    "hill",  # many
    "powell",  # many
    "long",  # many
}

# Words that are team aliases and should never be used for player last-name
# resolution in a full query context (they would collide with team names).
_TEAM_ALIAS_WORDS: set[str] = set()
for _ta_key in TEAM_ALIASES_EXPANDED:
    for _w in _ta_key.lower().split():
        if len(_w) >= 3:  # skip very short fragments
            _TEAM_ALIAS_WORDS.add(_w)


# ---------------------------------------------------------------------------
# Core resolution functions
# ---------------------------------------------------------------------------


def resolve_player(text: str) -> ResolutionResult:
    """Resolve a player reference from arbitrary user text.

    Resolution order:
    1. Curated full-name aliases (accent normalization)
    2. Curated nickname/acronym aliases
    3. Data-driven last-name lookup (single word)
    4. No match

    Parameters
    ----------
    text : str
        The user's text fragment that should refer to a player.
        Already expected to be lowercased / normalized.

    Returns
    -------
    ResolutionResult
        Confident if exactly one match, ambiguous if multiple,
        none if nothing matched.
    """
    q = _normalize_for_matching(text)
    if not q:
        return _no_match()

    # 1. Curated full-name aliases (handles accent variants)
    if q in PLAYER_FULL_NAME_ALIASES:
        return _confident(PLAYER_FULL_NAME_ALIASES[q], source="full_name_alias")

    # 2. Curated nickname / acronym aliases (longest match first)
    for key in sorted(PLAYER_NICKNAME_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", q):
            return _confident(PLAYER_NICKNAME_ALIASES[key], source="nickname")

    # 3. Data-driven last-name lookup
    # Only attempt for single words or clear last-name patterns
    words = q.split()
    if len(words) == 1:
        last_name = words[0]
        if last_name not in NEVER_AUTO_RESOLVE_LAST_NAMES:
            index = _get_player_index()
            candidates = index.get(last_name, [])
            if len(candidates) == 1:
                return _confident(candidates[0], source="last_name")
            if len(candidates) > 1:
                return _ambiguous(candidates, source="last_name")

    return _no_match()


def resolve_player_in_query(text: str) -> ResolutionResult:
    """Try to resolve a player from a full query string.

    Scans the query for known aliases (longest first), then falls back
    to single-word last-name resolution.

    This is the main entry point used by the parser.
    """
    q = _normalize_for_matching(text)
    if not q:
        return _no_match()

    # 1. Try curated full-name aliases (longest first)
    for key in sorted(PLAYER_FULL_NAME_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", q):
            return _confident(PLAYER_FULL_NAME_ALIASES[key], source="full_name_alias")

    # 2. Try curated nickname/acronym aliases (longest first)
    for key in sorted(PLAYER_NICKNAME_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", q):
            return _confident(PLAYER_NICKNAME_ALIASES[key], source="nickname")

    # 3. Try data-driven last-name on each word (skip common stopwords)
    _stop = {
        "last",
        "past",
        "recent",
        "games",
        "game",
        "vs",
        "versus",
        "against",
        "summary",
        "average",
        "averages",
        "record",
        "home",
        "away",
        "road",
        "wins",
        "win",
        "loss",
        "losses",
        "playoff",
        "playoffs",
        "postseason",
        "career",
        "season",
        "seasons",
        "from",
        "to",
        "in",
        "on",
        "at",
        "with",
        "for",
        "during",
        "over",
        "under",
        "between",
        "and",
        "or",
        "the",
        "top",
        "best",
        "worst",
        "most",
        "least",
        "highest",
        "lowest",
        "points",
        "point",
        "rebounds",
        "rebound",
        "assists",
        "assist",
        "steals",
        "steal",
        "blocks",
        "block",
        "threes",
        "scoring",
        "split",
        "streak",
        "straight",
        "consecutive",
        "finder",
        "count",
        "list",
        "show",
        "leaders",
        "leader",
        "leaderboard",
        "comparisons",
        "compare",
        "comparison",
        "head",
        "since",
        "before",
        "after",
        "all",
        "time",
        "regular",
        "form",
        "stats",
        "stat",
        "statistics",
        "rating",
        "rated",
        "ranked",
        "rank",
        "ranking",
        "made",
        "missed",
        "pct",
        "percentage",
        "per",
        "total",
    }
    words = q.split()
    for word in words:
        if word in _stop:
            continue
        if re.match(r"^\d", word):
            continue
        if len(word) < 2:
            continue
        # Skip words that are team aliases (e.g. "boston", "miami", "houston")
        if word in _TEAM_ALIAS_WORDS:
            continue
        if word in NEVER_AUTO_RESOLVE_LAST_NAMES:
            # Check the curated aliases first (they ARE allowed)
            # Already checked above, so this is a true ambiguity
            index = _get_player_index()
            candidates = index.get(word, [])
            if len(candidates) > 1:
                return _ambiguous(candidates, source="last_name")
            continue

        index = _get_player_index()
        candidates = index.get(word, [])
        if len(candidates) == 1:
            return _confident(candidates[0], source="last_name")
        if len(candidates) > 1:
            return _ambiguous(candidates, source="last_name")

    return _no_match()


def resolve_team(text: str) -> ResolutionResult:
    """Resolve a team reference from user text.

    Uses the expanded team alias dictionary.  Team resolution is
    generally unambiguous since team names and abbreviations are unique.

    Parameters
    ----------
    text : str
        The user's text fragment that should refer to a team.

    Returns
    -------
    ResolutionResult
    """
    q = " ".join(text.lower().strip().split())
    if not q:
        return _no_match()

    # Check if it's already a canonical abbreviation
    upper = q.upper()
    if upper in ALL_TEAM_ABBRS:
        return _confident(upper, source="abbreviation")

    # Longest-key-first matching in expanded aliases
    for key in sorted(TEAM_ALIASES_EXPANDED.keys(), key=len, reverse=True):
        if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", q):
            return _confident(TEAM_ALIASES_EXPANDED[key], source="team_alias")

    return _no_match()


def resolve_team_in_query(text: str) -> ResolutionResult:
    """Resolve a team from a full query string.

    Scans for team aliases longest-first to avoid partial matches.
    """
    q = " ".join(text.lower().strip().split())
    if not q:
        return _no_match()

    for key in sorted(TEAM_ALIASES_EXPANDED.keys(), key=len, reverse=True):
        if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", q):
            return _confident(TEAM_ALIASES_EXPANDED[key], source="team_alias")

    return _no_match()


def resolve_stat(stat_value: str | None) -> ResolutionResult:
    """Return a resolution result for a detected stat value.

    *stat_value* is the canonical stat code already resolved by
    ``detect_stat`` (e.g. ``"pts"``, ``"reb"``).  A non-None value
    means the alias was recognized → confident.  ``None`` means no
    stat was detected → no-match.
    """
    if stat_value is not None:
        return _confident(stat_value, source="stat_alias")
    return _no_match()


# ---------------------------------------------------------------------------
# Comparison extraction with entity resolution
# ---------------------------------------------------------------------------


def extract_player_comparison_resolved(
    text: str,
) -> tuple[ResolutionResult, ResolutionResult]:
    """Extract two players from a 'player_a vs player_b' pattern.

    Returns two ResolutionResults.  Both may be confident, ambiguous,
    or no-match independently.
    """
    q = _normalize_for_matching(text)

    # Remove head-to-head noise
    q = re.sub(r"(?<!\w)(?:head\s*-?\s*to\s*-?\s*head|h2h|matchup|matchups)(?!\w)", " ", q)
    q = " ".join(q.split())

    # Try to split on vs/versus
    m = re.search(
        r"(.+?)\s+(?:vs\.?|versus)\s+(.+?)(?:\s+(?:from|to|in|on|since|last|past|playoff|playoffs|postseason|home|away|career|summary|split)\b|$)",
        q,
    )
    if not m:
        # Simpler pattern without trailing context
        m = re.search(r"(.+?)\s+(?:vs\.?|versus)\s+(.+)", q)
    if not m:
        return _no_match(), _no_match()

    phrase_a = m.group(1).strip()
    phrase_b = m.group(2).strip()

    result_a = resolve_player(phrase_a)
    result_b = resolve_player(phrase_b)

    # If phrase_b didn't resolve as player, it might contain trailing context
    if not result_b.is_confident and not result_b.is_ambiguous:
        # Try just the first word(s) of phrase_b
        words_b = phrase_b.split()
        for i in range(min(3, len(words_b)), 0, -1):
            sub = " ".join(words_b[:i])
            result_b = resolve_player(sub)
            if result_b.is_confident or result_b.is_ambiguous:
                break

    return result_a, result_b


def extract_team_comparison_resolved(
    text: str,
) -> tuple[ResolutionResult, ResolutionResult]:
    """Extract two teams from a 'team_a vs team_b' pattern."""
    q = " ".join(text.lower().strip().split())

    q = re.sub(r"(?<!\w)(?:head\s*-?\s*to\s*-?\s*head|h2h|matchup|matchups)(?!\w)", " ", q)
    q = " ".join(q.split())

    m = re.search(
        r"(.+?)\s+(?:vs\.?|versus)\s+(.+?)(?:\s+(?:from|to|in|on|since|last|past|playoff|playoffs|postseason|home|away|career|summary|split)\b|$)",
        q,
    )
    if not m:
        m = re.search(r"(.+?)\s+(?:vs\.?|versus)\s+(.+)", q)
    if not m:
        return _no_match(), _no_match()

    phrase_a = m.group(1).strip()
    phrase_b = m.group(2).strip()

    result_a = resolve_team(phrase_a)
    result_b = resolve_team(phrase_b)

    # Try shorter substrings of phrase_b if needed
    if not result_b.is_confident:
        words_b = phrase_b.split()
        for i in range(min(4, len(words_b)), 0, -1):
            sub = " ".join(words_b[:i])
            result_b = resolve_team(sub)
            if result_b.is_confident:
                break

    return result_a, result_b


# ---------------------------------------------------------------------------
# Formatted ambiguity message (for notes/caveats)
# ---------------------------------------------------------------------------


def format_ambiguity_message(
    input_text: str, candidates: list[str], entity_type: str = "player"
) -> str:
    """Build a human-readable ambiguity message."""
    names = ", ".join(candidates[:10])
    suffix = f" (and {len(candidates) - 10} more)" if len(candidates) > 10 else ""
    return (
        f"Ambiguous {entity_type}: '{input_text}' could refer to: "
        f"{names}{suffix}. Please use a more specific name."
    )
