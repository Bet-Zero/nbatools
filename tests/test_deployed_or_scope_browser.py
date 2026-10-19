"""Six public OR answers retain branch-local samples, bounds and visible labels."""

import hashlib
import json
import os
from datetime import date, datetime
from pathlib import Path

import pytest

from nbatools.data_source import data_path, data_read_csv
from tests.test_core_identity_find_count_browser import ROOT, _capture_browser
from tests.test_deployed_union_pair_browser import _qualify_sample, _table

pytestmark = [pytest.mark.needs_data, pytest.mark.query, pytest.mark.slow]
ORACLE = json.loads((ROOT / "tests/fixtures/or_list_scope/production.json").read_text())
PLAYER = 2544


def _cases():
    for path, digest in ORACLE["sources"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest
    cases = []
    for frozen in ORACLE["cases"]:
        selected = set()
        for branch in frozen["branches"]:
            scope, conditions = branch["scope"], branch["conditions"]
            season = scope["season"]
            suffix = f"{season}_regular_season.csv"
            players = data_read_csv(f"raw/player_game_stats/{suffix}")
            teams = data_read_csv(f"raw/team_game_stats/{suffix}")
            games = data_read_csv(f"raw/games/{suffix}")
            assert not games.game_id.duplicated().any()
            assert not teams.duplicated(["game_id", "team_id"]).any()
            opponents = scope["opponent"]
            if isinstance(opponents, str):
                opponents = [opponents]
            candidates = players.loc[
                players.player_id.eq(PLAYER) & players.opponent_team_abbr.isin(opponents)
            ]
            assert not candidates.empty
            assert not candidates.duplicated(["game_id", "team_id", "player_id"]).any()
            # Qualify the candidate population and reciprocal game identity
            # before evaluating branch predicates, independently of the engine.
            for row in candidates.itertuples():
                game = games.loc[games.game_id.eq(row.game_id)]
                team = teams.loc[teams.game_id.eq(row.game_id) & teams.team_id.eq(row.team_id)]
                assert len(game) == len(team) == 1
                game, team = game.iloc[0], team.iloc[0]
                assert str(game.is_final).lower() in {"true", "1"}
                assert game.season == season and game.season_type == "Regular Season"
                assert str(game.game_date) == str(row.game_date)
                assert {int(game.home_team_id), int(game.away_team_id)} == {
                    int(row.team_id),
                    int(row.opponent_team_id),
                }
                assert team.opponent_team_id == row.opponent_team_id
                assert team.opponent_team_abbr == row.opponent_team_abbr
            chosen = candidates.copy()
            for condition in conditions:
                if condition["min_value"] is not None:
                    chosen = chosen.loc[chosen[condition["stat"]].ge(condition["min_value"])]
                if condition["max_value"] is not None:
                    chosen = chosen.loc[chosen[condition["stat"]].le(condition["max_value"])]
            selected.update(zip(chosen.game_id.map(int), chosen.player_id.map(int)))
        assert selected == {(row["game_id"], row["player_id"]) for row in frozen["rows"]}
        keys = ["game_id", "team_id", "opponent_team_id", "player_id"]
        seasons = sorted({branch["scope"]["season"] for branch in frozen["branches"]})
        _qualify_sample(
            dict(
                keys=sorted([[row[key] for key in keys] for row in frozen["rows"]]),
                games=len(frozen["rows"]),
                sums=frozen["sums"],
            ),
            seasons,
            player=True,
        )
        for truth in frozen["rows"]:
            suffix = f"{truth['season']}_regular_season.csv"
            players = data_read_csv(f"raw/player_game_stats/{suffix}")
            teams = data_read_csv(f"raw/team_game_stats/{suffix}")
            player = players.loc[
                players.game_id.eq(truth["game_id"]) & players.player_id.eq(PLAYER)
            ]
            team = teams.loc[
                teams.game_id.eq(truth["game_id"]) & teams.team_id.eq(truth["team_id"])
            ]
            assert len(player) == len(team) == 1
            for key, value in truth.items():
                assert (team.iloc[0] if key == "wl" else player.iloc[0])[key] == value
        headline = "LeBron James had 2 games matching at least one condition"
        if frozen["season"]:
            headline += f" in {frozen['season']}"
        text = [headline + ".", "Any filter (OR)"]
        text += [frozen["description"]] if frozen["description"] else ["30+ PTS", "9+ AST"]
        cases.append(
            {**frozen, "text": text, "forbidden": ["highest-scoring", "had 2 games with 30"]}
        )
    assert {case["id"] for case in cases} == {
        "or-shared",
        "or-different-opponents",
        "or-different-seasons",
    }
    return cases


def _validate_answers(receipt, cases, output):
    by_id, seen = {case["id"]: case for case in cases}, set()
    assert not receipt["failures"]
    for item in receipt["receipts"]:
        pair = item["viewport"], item["id"]
        assert pair not in seen
        seen.add(pair)
        case = by_id[item["id"]]
        assert item["query"] == item["payload"]["query"] == case["query"]
        assert item["http"] == 200 and not item["errors"]
        assert not item["missing"] and not item["forbidden"] and not item["grainErrors"]
        assert item["overflow"]["document"] <= item["overflow"]["viewport"]
        assert f"{receipt['base']}/assets/{ORACLE['expected_asset']}" in item["assets"]
        assert all(text in item["text"] for text in case["text"])
        assert not any(text in item["text"] for text in case["forbidden"])
        for ready in [item["readinessBefore"], item["readinessAfter"]]:
            assert ready["ready"] is True and ready["status"] == "ready"
            assert ready["immutable_generation"] is True
            assert ready["active_generation"] == ORACLE["generation"]
            assert not ready.get("blockers")
        assert item["screenshot"] == f"{item['viewport']}-{item['id']}.png"
        assert (
            hashlib.sha256((output / item["screenshot"]).read_bytes()).hexdigest()
            == item["screenshotSha256"]
        )
        payload = item["payload"]
        assert payload["route"] == "player_game_finder" and payload["result_status"] == "ok"
        meta, sections = payload["result"]["metadata"], payload["result"]["sections"]
        assert meta["player"] == "LeBron James" and meta["player_context"]["player_id"] == PLAYER
        assert meta["team"] is None and not meta.get("team_context")
        assert meta["season"] == case["season"] and meta["season_type"] == "Regular Season"
        assert meta["boolean_filter_mode"] == "any" and not meta["grouped_boolean_used"]
        if case["opponents"]:
            assert meta["opponents"] == case["opponents"]
            assert meta["opponent"] == ", ".join(case["opponents"])
        else:
            assert meta["opponent"] is None and not meta.get("opponents")
        assert not meta.get("opponent_context")
        if case["description"]:
            assert meta["boolean_filter_branches"] == case["branches"]
            assert not meta["conditions"] and not meta["threshold_conditions"]
            assert not meta["extra_conditions"]
            assert meta["stat"] is None and meta["min_value"] is None and meta["max_value"] is None
            assert {
                "label": "Any branch (OR)",
                "kind": "boolean",
                "value": case["description"],
            } in meta["applied_filters"]
        else:
            assert not meta.get("boolean_filter_branches")
            assert meta["conditions"] == meta["threshold_conditions"]
            assert all(
                set(condition) <= {"stat", "min_value", "max_value", "text"}
                for condition in meta["conditions"]
            )
            assert [
                {key: condition.get(key) for key in ("stat", "min_value", "max_value")}
                for condition in meta["conditions"]
            ] == [branch["conditions"][0] for branch in case["branches"]]
        rows = sections["finder"]
        truth = {row["game_id"]: row for row in case["rows"]}
        assert len(rows) == len(truth) == 2
        assert {int(row["game_id"]) for row in rows} == set(truth)
        for row in rows:
            for key, value in truth[int(row["game_id"])].items():
                # Finder rows expose team abbreviations; source qualification
                # above binds these to exact canonical team/opponent IDs.
                if key == "game_date":
                    when = datetime.fromisoformat(str(row[key]).replace("Z", "+00:00"))
                    assert when.date().isoformat() == value
                elif key not in {"team_id", "opponent_team_id"}:
                    assert str(row[key]) == str(value)
        for stat, total in case["sums"].items():
            assert sum(row[stat] for row in rows) == total
        table = _table(item, "Game log")
        assert len(table["rows"]) == 2
        for displayed, expected in zip(
            table["rows"], sorted(case["rows"], key=lambda row: row["game_date"], reverse=True)
        ):
            cells = dict(zip(table["headers"], displayed))
            when = date.fromisoformat(expected["game_date"])
            assert cells["Date"] == f"{when:%b} {when.day}"
            assert expected["team_abbr"] in cells["TM"]
            assert expected["opponent_team_abbr"] in cells["Opp"]
            assert cells["W/L"] == expected["wl"]
            for stat in ("pts", "ast") + (("reb",) if item["viewport"] == "desktop" else ()):
                assert float(cells[stat.upper()]) == expected[stat]
    assert seen == {(viewport, ident) for viewport in ("desktop", "mobile") for ident in by_id}


def test_deployed_or_scope_desktop_and_mobile(tmp_path):
    cases = _cases()
    receipt = _capture_browser(cases, tmp_path, "or-scope-browser")
    assert receipt["base"] == "https://nbatools.vercel.app"
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / "or-scope-browser"
    _validate_answers(receipt, cases, output)
