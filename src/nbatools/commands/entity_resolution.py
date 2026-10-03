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
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from nbatools.data_source import data_glob, data_read_csv, data_source_cache_key

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
    "shai": "Shai Gilgeous-Alexander",
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
    "dbook": "Devin Booker",
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
    "jamal": "Jamal Murray",
    "jamal murray": "Jamal Murray",
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


_LETTER_PERIOD_RE = re.compile(r"(?<=[a-z])\.")


def _normalize_for_matching(text: str) -> str:
    """Lowercase, strip accents, and erase punctuation that varies within names.

    Hyphens become spaces and periods after letters are dropped, so
    "Karl-Anthony Towns" / "karl anthony towns", "Tim Hardaway Jr." /
    "tim hardaway jr" and "P.J. Tucker" / "pj tucker" each share one key.
    Without this, the unpunctuated spelling missed the data-backed full name
    and fell through to a shorter alias inside it ("anthony" -> Carmelo
    Anthony, "tim hardaway" -> Tim Hardaway Sr.). Decimal points survive.
    """
    text = _strip_accents(text).lower().replace("-", " ")
    return " ".join(_LETTER_PERIOD_RE.sub("", text).split())


# ---------------------------------------------------------------------------
# Data-driven player index (built from CSV data)
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"

_FALLBACK_PLAYER_NAMES: set[str] = {
    # Keep data-free CI/unit runs aligned with parser expectations. The
    # data-backed index still extends this set whenever game logs are present.
    "Anthony Edwards",
    "Bruce Brown",
    "Jaylen Brown",
}


def _read_player_names(data_dir: Path | None = None) -> set[str]:
    """Read canonical player names (and their ids) from player game stats CSVs."""
    global _player_names_cache, _player_ids_by_name_cache, _player_name_by_id_cache
    if data_dir is None:
        _ensure_player_index_generation()
    if data_dir is None and _player_names_cache is not None:
        return set(_player_names_cache)

    names: set[str] = set(_FALLBACK_PLAYER_NAMES)
    if data_dir is None:
        csv_paths = sorted(data_glob("raw/player_game_stats/*.csv"), key=str)
        read_csv = data_read_csv
    else:
        stats_dir = data_dir / "raw" / "player_game_stats"
        if not stats_dir.exists():
            return names
        csv_paths = sorted(stats_dir.glob("*.csv"))
        read_csv = pd.read_csv

    ids_by_name: dict[str, set[str]] = {}
    # Files sort by season, so the last spelling seen is the most recent one.
    name_by_id: dict[str, str] = {}
    for csv_path in csv_paths:
        try:
            df = read_csv(
                csv_path,
                usecols=lambda column: column in {"player_id", "player_name"},
                dtype=str,
            )
        except Exception:
            continue
        if "player_name" not in df.columns:
            continue
        names.update(df["player_name"].dropna().unique())
        if "player_id" in df.columns:
            pairs = df[["player_name", "player_id"]].dropna().drop_duplicates()
            for name, player_id in pairs.itertuples(index=False):
                ids_by_name.setdefault(_normalize_for_matching(name), set()).add(player_id)
                name_by_id[player_id] = _preferred_spelling(name_by_id.get(player_id), name)
    if data_dir is None:
        _player_names_cache = set(names)
        _player_ids_by_name_cache = {key: frozenset(ids) for key, ids in ids_by_name.items()}
        _player_name_by_id_cache = name_by_id
    return names


def _preferred_spelling(previous: str | None, current: str) -> str:
    """The later spelling, unless it only drops the earlier one's accents."""
    if previous is None or previous == current:
        return current
    if _strip_accents(previous) == current:
        return previous
    return current


def canonical_player_names_by_id() -> dict[str, str]:
    """One display name per ``player_id``: the most recent spelling in the data.

    A spelling that only drops diacritics ("Jonas Valanciunas") keeps the
    accented form. Several players changed spelling inside a season ("Bobby
    Portis" -> "Bobby Portis Jr." during 2024-25), so grouping by name split them.
    """
    _read_player_names()
    return dict(_player_name_by_id_cache or {})


def player_ids_for_name(name: str) -> frozenset[str]:
    """Every ``player_id`` the loaded data records under ``name``.

    Keys use the same normalization as name matching, so "Bobby Portis" also
    finds the rows later stored as "Bobby Portis Jr." once both spellings share
    an id, and "Jonas Valanciunas" finds the accented rows. A name shared by
    two different players returns both ids; callers pick one with
    ``_player_identity.select_player_rows``. IDs are strings, as read.
    """
    _read_player_names()
    if _player_ids_by_name_cache is None:
        return frozenset()
    return _player_ids_by_name_cache.get(_normalize_for_matching(name), frozenset())


def _build_player_index(data_dir: Path | None = None) -> dict[str, list[str]]:
    """Build a last-name → list[full-name] index from player game stats CSVs.

    Scans all available season files to capture the broadest set of
    player names.  Returns a dict mapping lowercased last names to
    lists of canonical full names (as they appear in the data).
    """
    all_names = _read_player_names(data_dir)

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
_player_full_name_index: dict[str, str] | None = None
_player_full_name_keys: tuple[str, ...] | None = None
_player_first_name_index: dict[str, list[str]] | None = None
_player_names_cache: set[str] | None = None
_player_ids_by_name_cache: dict[str, frozenset[str]] | None = None
_player_name_by_id_cache: dict[str, str] | None = None
_player_index_generation_key: str | None = None


def _ensure_player_index_generation() -> None:
    """Invalidate data-backed entity indexes when the source generation changes."""
    global _player_index_generation_key
    generation_key = data_source_cache_key()
    if _player_index_generation_key == generation_key:
        return
    reset_player_index()
    _player_index_generation_key = generation_key


def _get_player_index() -> dict[str, list[str]]:
    """Get (or build) the cached player last-name index."""
    global _player_last_name_index
    _ensure_player_index_generation()
    if _player_last_name_index is None:
        _player_last_name_index = _build_player_index()
    return _player_last_name_index


def _build_player_full_name_index(data_dir: Path | None = None) -> dict[str, str]:
    """Build a normalized full-name → canonical full-name index from game stats."""
    return {_normalize_for_matching(name): name for name in _read_player_names(data_dir)}


def _get_player_full_name_index() -> dict[str, str]:
    """Get (or build) the cached player full-name index."""
    global _player_full_name_index
    _ensure_player_index_generation()
    if _player_full_name_index is None:
        _player_full_name_index = _build_player_full_name_index()
    return _player_full_name_index


def _build_player_first_name_index(data_dir: Path | None = None) -> dict[str, list[str]]:
    """Build a first-name → list[full-name] index from player game stats CSVs.

    A unique first name ("shai", "giannis") identifies its player as well
    as a unique last name does; shared first names ("anthony", "jalen")
    stay ambiguous and never auto-resolve.
    """
    first_name_index: dict[str, list[str]] = {}
    for name in sorted(_read_player_names(data_dir)):
        parts = name.strip().split()
        if len(parts) < 2:
            continue
        key = _strip_accents(parts[0]).lower()
        if len(key) < 3:
            # Initials-style first names ("CJ", "TJ") are curated aliases,
            # not data-driven lookups.
            continue
        if key not in first_name_index:
            first_name_index[key] = []
        if name not in first_name_index[key]:
            first_name_index[key].append(name)
    return first_name_index


def _get_player_first_name_index() -> dict[str, list[str]]:
    """Get (or build) the cached player first-name index."""
    global _player_first_name_index
    _ensure_player_index_generation()
    if _player_first_name_index is None:
        _player_first_name_index = _build_player_first_name_index()
    return _player_first_name_index


def _get_player_full_name_keys() -> tuple[str, ...]:
    """Return data-backed full names sorted longest-first for query scanning."""
    global _player_full_name_keys
    _ensure_player_index_generation()
    if _player_full_name_keys is None:
        _player_full_name_keys = tuple(
            sorted(_get_player_full_name_index().keys(), key=len, reverse=True)
        )
    return _player_full_name_keys


def reset_player_index() -> None:
    """Force rebuild of the player index (for testing)."""
    global _player_last_name_index, _player_full_name_index, _player_full_name_keys
    global _player_names_cache, _player_first_name_index, _player_index_generation_key
    global _player_ids_by_name_cache, _player_name_by_id_cache
    _player_last_name_index = None
    _player_ids_by_name_cache = None
    _player_name_by_id_cache = None
    _player_full_name_index = None
    _player_full_name_keys = None
    _player_names_cache = None
    _player_first_name_index = None
    _player_index_generation_key = None


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


_PLAYER_REFERENCE_STOPWORDS: set[str] = {
    "after",
    "against",
    "all",
    "and",
    "are",
    "assist",
    "assists",
    "at",
    "average",
    "averages",
    "away",
    "before",
    "best",
    "between",
    "block",
    "blocks",
    "career",
    "compare",
    "comparison",
    "comparisons",
    "consecutive",
    "count",
    "did",
    "do",
    "does",
    "during",
    "finder",
    "for",
    "form",
    "from",
    "game",
    "games",
    "had",
    "has",
    "have",
    "head",
    "highest",
    "home",
    "in",
    "is",
    "last",
    "lead",
    "leader",
    "leaderboard",
    "leaders",
    "leading",
    "leads",
    "league",
    "least",
    "led",
    "list",
    "loss",
    "losses",
    "lowest",
    "made",
    "missed",
    "most",
    "nba",
    "on",
    "or",
    "over",
    "past",
    "pct",
    "per",
    "percentage",
    "playoff",
    "playoffs",
    "player",
    "players",
    "point",
    "points",
    "postseason",
    "rank",
    "ranked",
    "ranking",
    "rated",
    "rating",
    "rebound",
    "rebounds",
    "recent",
    "record",
    "regular",
    "road",
    "scoring",
    "season",
    "seasons",
    "show",
    "since",
    "split",
    "stat",
    "statistics",
    "stats",
    "steal",
    "steals",
    "straight",
    "streak",
    "the",
    "threes",
    "this",
    "time",
    "to",
    "top",
    "total",
    "under",
    "versus",
    "vs",
    "was",
    "were",
    "what",
    "when",
    "which",
    "who",
    "win",
    "wins",
    "with",
    "worst",
    "year",
}


def _player_reference_candidate_words(q: str) -> list[str]:
    """Return query words worth checking against the data-backed player index."""
    candidates: list[str] = []
    for raw_word in q.split():
        word = raw_word.strip(' .?!,;:"()[]{}')
        if word.endswith("'s"):
            word = word[:-2]
        if word in _PLAYER_REFERENCE_STOPWORDS:
            continue
        if re.match(r"^\d", word):
            continue
        if len(word) < 2:
            continue
        if word in _TEAM_ALIAS_WORDS:
            continue
        candidates.append(word)
    return candidates


# ---------------------------------------------------------------------------
# Name-specificity
#
# A short alias can sit inside another player's name: "anthony" (Carmelo
# Anthony) inside "Karl-Anthony Towns". Full names are matched first, from the
# data-backed index and from the curated canonical names, so the longer name
# wins its span. Neighbouring words alone are deliberately NOT used to veto an
# alias: ordinary words are also surnames (Day, May, Free, Christmas), so
# "lebron christmas day games" must stay LeBron.
# ---------------------------------------------------------------------------


def _normalized_alias_map(alias_map: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in alias_map.items():
        normalized.setdefault(_normalize_for_matching(key), value)
    return normalized


_NORMALIZED_FULL_NAME_ALIASES = _normalized_alias_map(PLAYER_FULL_NAME_ALIASES)
_NORMALIZED_CURATED_ALIASES = _normalized_alias_map(CURATED_PLAYER_ALIASES)
_NORMALIZED_NICKNAME_ALIASES = _normalized_alias_map(PLAYER_NICKNAME_ALIASES)

# Every canonical name the curated maps resolve to, keyed by its normalized
# spelling. These are already the names those aliases answer with, so matching
# them in full adds no new identity: it only stops a shorter alias inside one
# ("anthony" in "karl anthony towns") from winning when the season data is not
# loaded or does not cover that player.
_CURATED_PLAYER_NAMES: dict[str, str] = {}
for _canonical in sorted(
    {
        *PLAYER_FULL_NAME_ALIASES.values(),
        *CURATED_PLAYER_ALIASES.values(),
        *PLAYER_NICKNAME_ALIASES.values(),
        *_FALLBACK_PLAYER_NAMES,
    }
):
    if len(_canonical.split()) >= 2:
        _CURATED_PLAYER_NAMES.setdefault(_normalize_for_matching(_canonical), _canonical)


def _first_alias_match(q: str, alias_map: dict[str, str]) -> str | None:
    """Canonical name for the longest alias found in ``q``."""
    for key in sorted(alias_map.keys(), key=len, reverse=True):
        if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", q):
            return alias_map[key]
    return None


# ---------------------------------------------------------------------------
# Core resolution functions
# ---------------------------------------------------------------------------


def resolve_player(text: str) -> ResolutionResult:
    """Resolve a player reference from arbitrary user text.

    Resolution order:
    1. Curated full-name aliases (accent normalization)
    2. Data-driven exact full-name lookup
    3. Curated common-name aliases
    4. Curated nickname/acronym aliases
    5. Data-driven last-name lookup (single word)
    6. No match

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
    if q in _NORMALIZED_FULL_NAME_ALIASES:
        return _confident(_NORMALIZED_FULL_NAME_ALIASES[q], source="full_name_alias")

    # 2. Data-backed exact full-name lookup. This must precede nickname
    # aliases so a full name like "Anthony Edwards" is not captured by the
    # broader single-token "anthony" alias.
    full_name_match = _get_player_full_name_index().get(q)
    if full_name_match:
        return _confident(full_name_match, source="full_name")

    # 2b. A curated canonical name in full ("karl anthony towns") is that
    # player even when the loaded data does not cover them.
    if q in _CURATED_PLAYER_NAMES:
        return _confident(_CURATED_PLAYER_NAMES[q], source="full_name_alias")

    # 3. Curated common-name aliases (longest match first)
    alias_match = _first_alias_match(q, _NORMALIZED_CURATED_ALIASES)
    if alias_match:
        return _confident(alias_match, source="alias")

    # 4. Curated nickname / acronym aliases (longest match first)
    nickname_match = _first_alias_match(q, _NORMALIZED_NICKNAME_ALIASES)
    if nickname_match:
        return _confident(nickname_match, source="nickname")

    # 5. Data-driven last-name lookup
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

    # 6. Data-driven first-name lookup (single word). A unique first name
    # ("shai") identifies its player as well as a unique last name does;
    # shared first names ("anthony") stay ambiguous and never auto-resolve.
    if len(words) == 1:
        first_name = words[0]
        index = _get_player_first_name_index()
        candidates = index.get(first_name, [])
        if len(candidates) == 1:
            return _confident(candidates[0], source="first_name")
        if len(candidates) > 1:
            return _ambiguous(candidates, source="first_name")

    return _no_match()


def allowed_player_reference_tokens(resolved_name: str) -> set[str]:
    """Tokens and alias keys that legitimately identify ``resolved_name``."""
    allowed: set[str] = set(_normalize_for_matching(resolved_name).split())
    for alias_map in (
        CURATED_PLAYER_ALIASES,
        PLAYER_NICKNAME_ALIASES,
        PLAYER_FULL_NAME_ALIASES,
    ):
        for key, name in alias_map.items():
            if name == resolved_name:
                normalized_key = _normalize_for_matching(key)
                allowed.add(normalized_key)
                allowed.update(normalized_key.split())
    return allowed


def phrase_has_partial_nickname_player_typo(phrase: str) -> bool:
    """True when a multi-word phrase resolves only via a partial nickname match.

    V1 does not fuzzy-correct first-name typos such as ``kevn durant`` or
    ``stephn curry``; those must not silently resolve through last-name/nickname
    aliases alone.
    """
    q = _normalize_for_matching(phrase)
    if not q:
        return False

    result = resolve_player(q)
    if not result.is_confident:
        return False
    if result.source in {"full_name", "full_name_alias", "last_name"}:
        return False

    # Season and number tokens ("2025-26", "30") are scope, not part of the
    # name, so "stephen curry 2025-26" is not a misspelled Stephen Curry.
    tokens = [token for token in q.split() if not token[0].isdigit()]
    if len(tokens) <= 1:
        return False

    allowed = allowed_player_reference_tokens(result.resolved)
    return any(token not in allowed for token in tokens)


def resolve_player_in_query(text: str) -> ResolutionResult:
    """Try to resolve a player from a full query string.

    Scans the query for known aliases and full names, preferring the earliest
    entity mention while letting full-name matches beat aliases at the same
    span, then falls back to single-word last-name resolution.

    This is the main entry point used by the parser.
    """
    q = _normalize_for_matching(text)
    if not q:
        return _no_match()

    matches: list[tuple[int, int, int, str, str]] = []
    candidate_words = _player_reference_candidate_words(q)

    def add_matches(alias_map: dict[str, str], source: str, priority: int) -> None:
        for key, resolved in alias_map.items():
            match = re.search(rf"(?<!\w){re.escape(key)}(?!\w)", q)
            if not match:
                continue
            matches.append(
                (match.start(), priority, -(match.end() - match.start()), resolved, source)
            )

    def add_full_name_matches(full_name_index: dict[str, str]) -> None:
        for key in _get_player_full_name_keys():
            match = re.search(rf"(?<!\w){re.escape(key)}(?!\w)", q)
            if not match:
                continue
            matches.append(
                (
                    match.start(),
                    0,
                    -(match.end() - match.start()),
                    full_name_index[key],
                    "full_name",
                )
            )

    # Prefer the earliest resolved entity in a full query. When two candidates
    # start at the same position, full-name/data-backed matches beat broad
    # single-token aliases inside that same span.
    add_matches(_NORMALIZED_FULL_NAME_ALIASES, "full_name_alias", 0)
    if len(candidate_words) >= 2:
        full_name_index = _get_player_full_name_index()
        add_full_name_matches(full_name_index)
        add_matches(_CURATED_PLAYER_NAMES, "full_name_alias", 0)
    add_matches(_NORMALIZED_CURATED_ALIASES, "alias", 1)
    add_matches(_NORMALIZED_NICKNAME_ALIASES, "nickname", 1)
    if matches:
        _, _, _, resolved, source = sorted(matches)[0]
        return _confident(resolved, source=source)

    # 5. Try data-driven last-name on each word (skip common stopwords)
    for word in candidate_words:
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


_LINEUP_SCAN_STOPWORDS: set[str] = {
    "combo",
    "combos",
    "lineup",
    "lineups",
    "man",
    "minute",
    "minutes",
    "net",
    "plus",
    "minus",
    "together",
    "unit",
    "units",
}


def resolve_players_in_query(text: str) -> list[str]:
    """Every player named in ``text``, in order, each resolved like a single name.

    Used where a question names several players at once ("lineups with Jalen
    Brunson and Josh Hart"). Full names from the data index and the curated
    canonical names beat shorter aliases on the same words, exactly as in
    ``resolve_player_in_query``; a word not covered by a name or alias resolves
    through a unique data last name. Shared last names never auto-resolve.
    """
    q = _normalize_for_matching(text)
    if not q:
        return []

    matches: list[tuple[int, int, int, int, str]] = []

    def add_matches(keys: Iterable[str], lookup: dict[str, str], priority: int) -> None:
        for key in keys:
            for match in re.finditer(rf"(?<!\w){re.escape(key)}(?!\w)", q):
                start, end = match.span()
                matches.append((start, priority, -(end - start), end, lookup[key]))

    add_matches(_NORMALIZED_FULL_NAME_ALIASES, _NORMALIZED_FULL_NAME_ALIASES, 0)
    full_name_index = _get_player_full_name_index()
    add_matches(
        (key for key in _get_player_full_name_keys() if " " in key and key in q),
        full_name_index,
        0,
    )
    add_matches(_CURATED_PLAYER_NAMES, _CURATED_PLAYER_NAMES, 0)
    add_matches(_NORMALIZED_CURATED_ALIASES, _NORMALIZED_CURATED_ALIASES, 1)
    add_matches(_NORMALIZED_NICKNAME_ALIASES, _NORMALIZED_NICKNAME_ALIASES, 1)

    taken: list[tuple[int, int, str]] = []
    for start, _priority, _neg_len, end, resolved in sorted(matches):
        if any(start < t_end and end > t_start for t_start, t_end, _ in taken):
            continue
        taken.append((start, end, resolved))

    last_name_index = _get_player_index()
    for word_match in re.finditer(r"[a-z][a-z']+", q):
        start, end = word_match.span()
        if any(start < t_end and end > t_start for t_start, t_end, _ in taken):
            continue
        word = word_match.group(0)
        if word.endswith("'s"):
            word = word[:-2]
        if (
            len(word) < 4
            or word in _PLAYER_REFERENCE_STOPWORDS
            or word in _LINEUP_SCAN_STOPWORDS
            or word in _TEAM_ALIAS_WORDS
            or word in NEVER_AUTO_RESOLVE_LAST_NAMES
        ):
            continue
        candidates = last_name_index.get(word, [])
        if len(candidates) == 1:
            taken.append((start, end, candidates[0]))

    players: list[str] = []
    for _start, _end, resolved in sorted(taken):
        if resolved not in players:
            players.append(resolved)
    return players


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


# ``was`` is both the Washington abbreviation and the English copula, so an
# availability clause - "while the player was injured", "when Curry was out" -
# resolved a Wizards subject nobody asked for and then answered a Washington
# question. Blank the verb reading before any alias scan sees it. Replaced with
# spaces of equal length so every span the caller computed stays valid.
_COPULA_WAS = re.compile(
    r"(?<!\w)was(?=\s+(?:not\s+)?(?:out|outs|injured|hurt|sidelined|available"
    r"|unavailable|active|inactive|healthy|playing|played|resting|rested|benched"
    r"|suspended|missing|missed|ejected|sick|the|a|an|his|her|their|its)\b)"
)


def mask_copula_team_lookalikes(text: str) -> str:
    """Blank team aliases that are plainly ordinary verbs in this sentence.

    Only ``was`` needs this today: it is the only abbreviation in the table
    that is also a high-frequency English copula. A team word the writer meant
    as a team ("was record this season") keeps resolving.
    """
    return _COPULA_WAS.sub("   ", text)


def resolve_team_in_query(text: str) -> ResolutionResult:
    """Resolve a team from a full query string.

    Scans for team aliases longest-first to avoid partial matches.
    """
    q = " ".join(mask_copula_team_lookalikes(text.lower()).strip().split())
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
