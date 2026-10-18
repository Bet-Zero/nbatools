import csv
import json
import re
import unicodedata
from pathlib import Path

base = Path(__file__).resolve().parent
text = (base / "independent-pdftotext.txt").read_text()
with (
    base / "acquired_data/canonical_selected/player_game_stats/2025-26_regular_season.csv"
).open() as stream:
    raw = [r for r in csv.DictReader(stream) if int(r["game_id"]) == 22500702]


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().casefold()
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return re.sub(r"\s+(?:jr|sr|ii|iii|iv)$", "", s).strip()


subject = None
parsed = []
for line in text.splitlines():
    if line.startswith("VISITOR:"):
        subject = "MIL"
    if line.startswith("HOME:"):
        subject = "BOS"
    if line.lstrip().startswith("SCORE BY"):
        break
    m = re.match(r"^\s*\d{1,3}\s+(.+?)\s+(?:[FCG]\s+)?(\d{2}:\d{2})\s+(.+)$", line)
    if not m:
        continue
    name, clock, stats = m.groups()
    values = [int(x) for x in stats.split()]
    assert len(values) == 16, (name, values)
    candidates = [
        r for r in raw if r["team_abbr"] == subject and norm(r["player_name"]) == norm(name)
    ]
    assert len(candidates) == 1, (name, candidates)
    r = candidates[0]
    minutes, seconds = map(int, clock.split(":"))
    total = minutes * 60 + seconds
    assert abs(total - float(r["minutes"]) * 60) <= 30, (name, clock, r["minutes"])
    assert values[-1] == int(r["pts"])
    parsed.append((subject, int(r["player_id"]), r["player_name"], clock, total, values[-1]))
assert len(parsed) == 24 and {(s, p) for s, p, *_ in parsed} == {
    (r["team_abbr"], int(r["player_id"])) for r in raw
}
for subject, points in [("MIL", 79), ("BOS", 107)]:
    selected = [r for r in parsed if r[0] == subject]
    assert (
        len(selected) == 12
        and sum(r[4] for r in selected) == 240 * 60
        and sum(r[5] for r in selected) == points
    )
    print(subject, len(selected), "played;seconds", sum(r[4] for r in selected), "points", points)
    for row in selected:
        print(row[:4])
# Explicit nonplayed population counted from original text, independent of importer.
dnp = re.findall(r"^\s*\d+\s+(.+?)\s+DNP\s+-\s+(.+)$", text, re.M)
assert dnp == [("Chris Boucher", "Coach's Decision"), ("Xavier Tillman", "Coach's Decision")]
assert (
    "Inactive: Celtics - Harper Jr. (G League - Two-Way), "
    "Shulga (G League - Two-Way), Tatum (Injury/Illness - Right Achilles; Repair)"
    in text
)
assert text.count("Antetokounmpo (") == 2
print(
    "24 played identities/minute-seconds/points, 2 explicit DNP and 8 inactive entries checked. "
    "Two inactive Antetokounmpo entries remain ambiguous; full 34-row import is unaccepted."
)
assert parsed == [
    tuple(row) for row in json.loads((base / "independent-played-review.json").read_text())
]
