"""Official NBA Final Box scorer report: game-day played, DNP and inactive.

The NBA's historical one-page PDF is different from a current injury feed.
Validate date, home/visitor identity, and BOTH final scores against the local
NBA game log before recording anything. Map every named player unambiguously to
an NBA player ID. Do not infer nonparticipation from a missing game-log row.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from nbatools.commands.pipeline.player_game_availability_espn import (
    _name,
    _nba_players,
    _nba_teams,
)

SOURCE_ROOT = "https://statsdmz.nba.com/pdfs"
STATUS = re.compile(
    r"^\s*\d{1,3}\s+(.+?)\s+(DNP|DND|NWT|DID NOT PLAY|DID NOT DRESS)"
    r"\s*(?:-\s*)?(.*?)\s*$",
    re.I,
)
TOTAL = re.compile(r"^\s*\d{3}:00\b.*\s(\d+)\s*$")
PLAYED = re.compile(r"^\s*\d{1,3}\s+(.+?)\s+(?:[CFG](?:-[CFG])?\s+)?(\d{1,3}:\d{2})\s+")
HEADING = re.compile(r"^\s*(VISITOR|HOME):\s*(.+?)\s+\(\d+-\d+\)", re.I)
DATE = re.compile(
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+"
    r"([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})\b"
)


def _archive_report(content: bytes, url: str, directory: Path) -> None:
    """Retain the original scorer report and a reproducible checksum receipt."""
    directory.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(content).hexdigest()
    raw = directory / f"{digest}.pdf"
    if not raw.exists():
        temporary = raw.with_suffix(".tmp")
        temporary.write_bytes(content)
        temporary.replace(raw)
    elif hashlib.sha256(raw.read_bytes()).hexdigest() != digest:
        raise ValueError("Archived NBA report checksum mismatch")
    receipt = directory / f"{Path(url).stem}.json"
    payload = {
        "source_url": url,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "sha256": digest,
        "size_bytes": len(content),
        "raw_file": raw.name,
    }
    temporary = receipt.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True) + "\n")
    temporary.replace(receipt)


def _fetch_report_text(url: str, *, archive: Path | None = None) -> str:
    from pypdf import PdfReader

    request = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (NBATools official box-score ingest)"}
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        if "application/pdf" not in response.headers.get("Content-Type", ""):
            raise ValueError("Official NBA final box returned a non-PDF response")
        content = response.read(1_500_001)
    if not content.startswith(b"%PDF") or len(content) > 1_500_000:
        raise ValueError("Invalid NBA official scorer PDF")
    reader = PdfReader(io.BytesIO(content), strict=True)
    if len(reader.pages) != 1:
        raise ValueError("Official NBA Final Box must be one PDF page")
    text = reader.pages[0].extract_text(extraction_mode="layout")
    if "NATIONAL BASKETBALL ASSOCIATION" not in text or "FINAL BOX" not in text:
        raise ValueError("Source is not an NBA Final Box scorer report")
    if archive is not None:
        _archive_report(content, url, archive)
    return text


def _parse_sections(text: str, game_date: str) -> tuple[list[str], list[list[str]], list[str]]:
    match = DATE.search(text)
    if match is None:
        raise ValueError("Final Box lacks a report game date")
    month, day, year = match.groups()
    date = datetime.strptime(f"{month} {day} {year}", "%B %d %Y")
    if date.strftime("%Y-%m-%d") != game_date:
        raise ValueError("Official report date differs from NBA game catalog")
    lines = text.splitlines()
    positions = []
    for index, line in enumerate(lines):
        match = HEADING.match(line)
        if match:
            positions.append((index, match.group(1).upper(), match.group(2).strip()))
    if len(positions) != 2 or [v[1] for v in positions] != ["VISITOR", "HOME"]:
        raise ValueError("Final Box missing distinct VISITOR and HOME team headings")
    finish = next(
        (i for i in range(positions[1][0] + 1, len(lines)) if "SCORE BY PERIOD" in lines[i]), None
    )
    if finish is None:
        raise ValueError("Final Box missing scoreboard section")
    sections = [lines[positions[0][0] + 1 : positions[1][0]], lines[positions[1][0] + 1 : finish]]
    return [p[2] for p in positions], sections, lines


def _score(lines: list[str]) -> int:
    scores = [int(m.group(1)) for line in lines if (m := TOTAL.match(line))]
    if len(scores) != 1:
        raise ValueError("Final Box missing an unambiguous team point total")
    return scores[0]


def _split_inactives(record: str) -> list[tuple[str, str]]:
    if record.strip().upper() in {"NONE", "N/A"}:
        return []
    tokens, current, depth = [], "", 0
    for char in record:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise ValueError("Corrupt inactive status parentheses")
        if char == "," and depth == 0:
            tokens.append(current.strip())
            current = ""
        else:
            current += char
    if depth:
        raise ValueError("Unclosed inactive status parentheses")
    tokens.append(current.strip())
    result = []
    for entry in tokens:
        match = re.fullmatch(r"(.+?)\s+\((.+)\)", entry)
        if match is None:
            raise ValueError(f"Unrecognized official inactive row: {entry}")
        result.append((match.group(1).strip(), "INACTIVE - " + match.group(2).strip()))
    return result


def _inactives(lines: list[str]) -> list[tuple[str, list[tuple[str, str]]]]:
    groups = []
    for index, line in enumerate(lines):
        match = re.match(r"^\s*Inactive:\s*(.+?)\s+-\s+(.*)$", line, re.I)
        if match is None:
            continue
        team, first = match.groups()
        joined = [first]
        for value in lines[index + 1 : index + 5]:
            part = value.strip()
            if not part or re.match(
                r"^(Inactive:|Points in the Paint|2nd Chance Points|"
                r"Fast Break Points|Biggest Lead|Technical fouls|Lead Changes)",
                part,
                re.I,
            ):
                break
            joined.append(part)
        groups.append((team, _split_inactives(" ".join(joined))))
    if len(groups) != 2:
        raise ValueError("Final Box must contain both teams' inactive lists")
    return groups


def _nba_team_names(root: Path, season: str, safe: str, game_id: int) -> dict[int, str]:
    path = root / "raw/team_game_stats" / f"{season}_{safe}.csv"
    df = pd.read_csv(path, dtype={"game_id": str})
    if not {"game_id", "team_id", "team_name"}.issubset(df.columns):
        raise ValueError("NBA names required to validate official PDF teams")
    df = df[df.game_id.map(int).eq(game_id)]
    if len(df) != 2 or df.team_id.nunique() != 2:
        raise ValueError("NBA PDF team names are not game-specific")
    return dict(zip(df.team_id.astype(int), df.team_name.astype(str)))


def _identify(
    people: pd.DataFrame, team_id: int, name: str, used: set[int], *, surname: bool
) -> tuple[int, str]:
    normalized = _name(name)
    subset = people[people.team_id.eq(team_id) & people.normalized.eq(normalized)]
    if subset.player_id.nunique() != 1 and surname:
        subset = people[
            people.team_id.eq(team_id)
            & people.normalized.map(lambda n: bool(n) and n.split()[-1] == normalized)
            & ~people.player_id.isin(used)
        ]
    ids = subset.player_id.unique()
    if len(ids) != 1:
        raise ValueError(
            f"Official scorer identity unresolved: {name!r} team={team_id}, "
            f"candidate IDs={len(ids)}"
        )
    ident = int(ids[0])
    if ident in used:
        raise ValueError("Contradictory played/DNP/inactive NBA player records")
    return ident, str(subset[subset.player_id.eq(ident)].iloc[0].player_name)


def _record(
    game_id: int, team_id: int, abbr: str, ident: int, name: str, minutes: object, reason: str
) -> dict:
    first, _, rest = str(name).partition(" ")
    return {
        "gameId": game_id,
        "teamId": team_id,
        "teamTricode": abbr,
        "personId": ident,
        "firstName": first,
        "familyName": rest or first,
        "minutes": minutes,
        "comment": reason,
    }


def official_report_as_v3(
    *,
    game_id: int,
    game_date: str,
    season: str,
    season_type: str,
    home_team_id: int,
    away_team_id: int,
    data_root: Path,
) -> tuple[pd.DataFrame, str]:
    """Build source-listed played/DNP/inactive rows for one verified NBA report."""
    safe = season_type.lower().replace(" ", "_")
    teams = _nba_teams(data_root, season, safe, game_id)
    by_id = {team_id: (abbr, pts) for abbr, (team_id, pts) in teams.items()}
    if set(by_id) != {home_team_id, away_team_id}:
        raise ValueError("Game roster/source team IDs disagree")
    away, home = by_id[away_team_id][0], by_id[home_team_id][0]
    ref = f"{game_date.replace('-', '')}_{away}{home}"
    url = f"{SOURCE_ROOT}/{game_date.replace('-', '')}/{ref}.pdf"
    text = _fetch_report_text(url, archive=data_root / "raw/player_game_availability_sources")
    headings, sections, all_lines = _parse_sections(text, game_date)
    expected_names = _nba_team_names(data_root, season, safe, game_id)
    team_ids = (away_team_id, home_team_id)
    for name, section, ident in zip(headings, sections, team_ids):
        if not _name(expected_names[ident]).endswith(_name(name)):
            raise ValueError(f"Final Box team heading mismatch: {name}")
        if _score(section) != by_id[ident][1]:
            raise ValueError("Final Box score differs from canonical NBA game points")
    inactives = _inactives(all_lines)
    people = _nba_players(data_root, season, safe)
    source = data_root / "raw/player_game_stats" / f"{season}_{safe}.csv"
    played = pd.read_csv(source, dtype={"game_id": str})
    played = played[played.game_id.map(int).eq(game_id)]
    used: set[int] = set()
    rows = []
    for ident, section in zip(team_ids, sections):
        abbr = by_id[ident][0]
        report_ids = set()
        for line in section:
            match = PLAYED.match(line)
            if match is None:
                continue
            name, minutes = match.groups()
            nba_id, full_name = _identify(people, ident, name, used, surname=False)
            used.add(nba_id)
            report_ids.add(nba_id)
            rows.append(_record(game_id, ident, abbr, nba_id, full_name, minutes, ""))
        expected = played[played.team_id.eq(ident)].player_id.astype(int)
        if expected.duplicated().any() or not report_ids or report_ids != set(expected):
            raise ValueError("Final Box played identities differ from canonical NBA game rows")
    for ident, section in zip(team_ids, sections):
        for line in section:
            match = STATUS.match(line)
            if match is None:
                continue
            name, status, reason = match.groups()
            nba_id, full_name = _identify(people, ident, name, used, surname=False)
            used.add(nba_id)
            rows.append(
                _record(
                    game_id,
                    ident,
                    by_id[ident][0],
                    nba_id,
                    full_name,
                    None,
                    status.upper() + " - " + reason,
                )
            )
    for ident, (label, absent) in zip(team_ids, inactives):
        if not _name(expected_names[ident]).endswith(_name(label)):
            raise ValueError("Final Box inactive list assigned to wrong team")
        for name, reason in absent:
            nba_id, full_name = _identify(people, ident, name, used, surname=True)
            used.add(nba_id)
            rows.append(_record(game_id, ident, by_id[ident][0], nba_id, full_name, None, reason))
    if not rows or {row["teamId"] for row in rows} != set(team_ids):
        raise ValueError("No trustworthy game-day NBA report rows for both teams")
    frame = pd.DataFrame(rows)
    receipt = data_root / "raw/player_game_availability_sources" / f"{ref}.json"
    if receipt.exists():
        frame.attrs["source_sha256"] = json.loads(receipt.read_text())["sha256"]
    return frame, ref
