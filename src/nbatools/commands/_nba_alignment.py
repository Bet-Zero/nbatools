"""NBA conference and division alignment by season, keyed by franchise team id.

The served ``team_conference_membership`` table only covers recent seasons.
Alignment is historical reference data (it cannot be derived from box
scores), so the full 1996-97 onward record lives here, keyed by the stable
NBA franchise ``team_id`` rather than by abbreviation (abbreviations change:
NJN/BKN, SEA/OKC, VAN/MEM, CHH/CHA, NOH/NOK/NOP).

Eras:

- 1996-97 to 2001-02: two divisions per conference (Atlantic and Central in
  the East, Midwest and Pacific in the West); the original Charlotte Hornets
  (franchise id 1610612766) play in the Central.
- 2002-03 and 2003-04: the Hornets move to New Orleans (franchise id
  1610612740) and stay in the East's Central division.
- 2004-05 onward: 30 teams in six divisions; Charlotte (1610612766) returns
  in the Southeast, New Orleans joins the Southwest and Toronto moves to the
  Atlantic.
"""

from __future__ import annotations

ATL = 1610612737
BOS = 1610612738
CLE = 1610612739
NOP = 1610612740  # New Orleans Hornets/Pelicans (and 2005-07 Oklahoma City stint)
CHI = 1610612741
DAL = 1610612742
DEN = 1610612743
GSW = 1610612744
HOU = 1610612745
LAC = 1610612746
LAL = 1610612747
MIA = 1610612748
MIL = 1610612749
MIN = 1610612750
BKN = 1610612751  # New Jersey/Brooklyn Nets
NYK = 1610612752
ORL = 1610612753
IND = 1610612754
PHI = 1610612755
PHX = 1610612756
POR = 1610612757
SAC = 1610612758
SAS = 1610612759
OKC = 1610612760  # Seattle SuperSonics/Oklahoma City Thunder
TOR = 1610612761
UTA = 1610612762
MEM = 1610612763  # Vancouver/Memphis Grizzlies
WAS = 1610612764
DET = 1610612765
CHA = 1610612766  # Charlotte Hornets (1988-2002), Bobcats/Hornets (2004-)

EARLIEST_ALIGNMENT_SEASON = "1996-97"

_TWO_DIVISION_WEST = {
    "Midwest": (DAL, DEN, HOU, MIN, SAS, UTA, MEM),
    "Pacific": (GSW, LAC, LAL, PHX, POR, SAC, OKC),
}

_ERAS: list[tuple[str, dict[str, dict[str, tuple[int, ...]]]]] = [
    (
        "1996-97",
        {
            "East": {
                "Atlantic": (BOS, MIA, BKN, NYK, ORL, PHI, WAS),
                "Central": (ATL, CHA, CHI, CLE, DET, IND, MIL, TOR),
            },
            "West": _TWO_DIVISION_WEST,
        },
    ),
    (
        "2002-03",
        {
            "East": {
                "Atlantic": (BOS, MIA, BKN, NYK, ORL, PHI, WAS),
                "Central": (ATL, NOP, CHI, CLE, DET, IND, MIL, TOR),
            },
            "West": _TWO_DIVISION_WEST,
        },
    ),
    (
        "2004-05",
        {
            "East": {
                "Atlantic": (BOS, BKN, NYK, PHI, TOR),
                "Central": (CHI, CLE, DET, IND, MIL),
                "Southeast": (ATL, CHA, MIA, ORL, WAS),
            },
            "West": {
                "Northwest": (DEN, MIN, OKC, POR, UTA),
                "Pacific": (GSW, LAC, LAL, PHX, SAC),
                "Southwest": (DAL, HOU, MEM, NOP, SAS),
            },
        },
    ),
]

DIVISIONS_BY_ERA = {
    start: {division for divisions in alignment.values() for division in divisions}
    for start, alignment in _ERAS
}


def _season_start(season: str) -> int:
    return int(str(season)[:4])


def historical_alignment(season: str) -> dict[int, tuple[str, str]]:
    """``team_id -> (conference, division)`` for a season, or {} before 1996-97."""
    start = _season_start(season)
    if start < _season_start(EARLIEST_ALIGNMENT_SEASON):
        return {}
    chosen = None
    for era_start, alignment in _ERAS:
        if start >= _season_start(era_start):
            chosen = alignment
    if chosen is None:
        return {}
    return {
        team_id: (conference, division)
        for conference, divisions in chosen.items()
        for division, team_ids in divisions.items()
        for team_id in team_ids
    }
