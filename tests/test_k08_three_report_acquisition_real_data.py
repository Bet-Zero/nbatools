"""Owner-authorized capture of exactly three official PDFs, never publication.

Run through the existing targeted R2 workflow. Player qualification is separate
from acquisition so original evidence survives downstream findings.
"""

import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.pipeline import player_game_availability_report as report
from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
PACKET = Path(__file__).resolve().parents[1] / (
    "working/nba-tools-completion-program/collection-requests/lebron-participation-2025-26.json"
)
# Literal owner scope must not expand with a future packet edit.
AUTHORIZED = (
    (22500019, "2025-10-24", "20251024_MINLAL"),
    (22500113, "2025-10-26", "20251026_LALSAC"),
    (22500122, "2025-10-27", "20251027_PORLAL"),
)


@pytest.mark.parametrize("game_id,day,reference", AUTHORIZED)
def test_capture_authorized_official_report(tmp_path, monkeypatch, game_id, day, reference):
    url = f"https://statsdmz.nba.com/pdfs/{day.replace('-', '')}/{reference}.pdf"
    packet = json.loads(PACKET.read_text())
    requested = [r for r in packet["source_requests"] if int(r["game_id"]) == game_id]
    assert len(requested) == 1 and requested[0]["url"] == url
    evidence = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", tmp_path / "evidence"))
    directory = evidence / "raw/player_game_availability_sources"
    original_open = report.urllib.request.urlopen

    def only_authorized(request, **kwargs):
        assert request.full_url == url, "No identity, profile or other report fetch authorized"
        return original_open(request, **kwargs)

    monkeypatch.setattr(report.urllib.request, "urlopen", only_authorized)
    text = report._fetch_report_text(url, archive=directory)
    (directory / f"{reference}.extracted.txt").write_text(text)
    receipt = json.loads((directory / f"{reference}.json").read_text())
    original = directory / receipt["raw_file"]
    assert receipt["source_url"] == url
    assert hashlib.sha256(original.read_bytes()).hexdigest() == receipt["sha256"]
    assert original.stat().st_size == receipt["size_bytes"]
    canonical = {}
    for kind in ("games", "team_game_stats", "player_game_stats"):
        frame = data_read_csv(f"data/raw/{kind}/2025-26_regular_season.csv")
        selected = frame.loc[pd.to_numeric(frame.game_id).eq(game_id)]
        destination = evidence / "canonical_selected" / kind / "2025-26_regular_season.csv"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            selected = pd.concat([pd.read_csv(destination), selected]).drop_duplicates()
        selected.to_csv(destination, index=False)
        canonical[kind] = selected.loc[pd.to_numeric(selected.game_id).eq(game_id)]
    games = canonical["games"]
    assert len(games) == 1
    game = games.iloc[0]
    assert game.game_date == day and str(game.is_final).lower() in {"true", "1"}
    teams = canonical["team_game_stats"]
    assert len(teams) == 2 and teams.team_id.nunique() == 2
    teams = teams.set_index("team_id")
    names, sections, _ = report._parse_sections(text, day)
    for name, section, team_id in zip(
        names, sections, [int(game.away_team_id), int(game.home_team_id)]
    ):
        assert report._name(teams.loc[team_id, "team_name"]).endswith(report._name(name))
        assert report._score(section) == teams.loc[team_id, "pts"]
    result = dict(
        game_id=f"{game_id:010d}",
        game_date=day,
        source=receipt,
        base_generation=os.environ.get("NBATOOLS_DATA_GENERATION"),
        candidate_sha=os.environ.get("VALIDATION_SHA"),
        qualification="PDF game/date/sides/scores checked; independent player/state review pending",
        publication_state="staged_only",
        production_writes=0,
    )
    (evidence / f"{reference}.capture.json").write_text(json.dumps(result, indent=2) + "\n")
    print("AUTHORIZED_K08_CAPTURE " + json.dumps(result, sort_keys=True))
