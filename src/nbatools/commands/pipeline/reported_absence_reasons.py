"""Offline reason companions: replay originals without replacing availability facts."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from nbatools.commands import _reported_absence_reasons as reasons
from nbatools.commands.pipeline import player_game_availability_report as report
from nbatools.commands.pipeline.pull_player_game_availability import _game_digest


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _paths(season, kind):
    if re.fullmatch(r"\d{4}-\d{2}", season) is None or kind not in {"Regular Season", "Playoffs"}:
        raise ValueError("Invalid reported-reason season/type")
    suffix = f"{season}_{kind.lower().replace(' ', '_')}.csv"
    relative = reasons.DIRECTORY + suffix
    return suffix, relative, relative.removesuffix(".csv") + ".imports.json"


def _identity(root, season, kind, gid, tid, pid):
    suffix, _, _ = _paths(season, kind)
    path = root / "raw/player_game_availability" / suffix
    binary = pd.read_csv(path, dtype=str, keep_default_na=False)
    group = binary.loc[pd.to_numeric(binary.game_id).eq(gid)]
    target = group.loc[
        pd.to_numeric(group.team_id).eq(tid) & pd.to_numeric(group.player_id).eq(pid)
    ]
    if len(target) != 1 or target.participation_state.item() != "did_not_play":
        raise ValueError("Reported reason requires an existing exact-game qualified DNP")
    row = target.iloc[0]
    if not (group.season.eq(season) & group.season_type.eq(kind)).all():
        raise ValueError("Reported-reason identity scope differs")
    imported = json.loads(path.with_suffix(".imports.json").read_bytes())[str(gid)]
    if imported["sha256"] != _game_digest(group):
        raise ValueError("Reported-reason identity import digest differs")
    if not str(row.source).startswith(("nba_official_finalbox:", "nba_stats_structured_archive:")):
        raise ValueError("Opaque legacy participation cannot qualify a reason identity")
    people = group[["team_id", "player_id", "player_name"]].copy()
    people[["team_id", "player_id"]] = people[["team_id", "player_id"]].astype(int)
    people["normalized"] = people.player_name.map(report._name)
    return row, imported, people


def _envelope(root, season, kind, gid):
    suffix, _, _ = _paths(season, kind)
    catalog = pd.read_csv(root / "raw/games" / suffix)
    selected = catalog.loc[pd.to_numeric(catalog.game_id).eq(gid)]
    if len(selected) != 1:
        raise ValueError("Reported reason requires unique canonical game")
    game = selected.iloc[0]
    if (
        str(game.is_final).lower() not in {"true", "1"}
        or game.season != season
        or game.season_type != kind
    ):
        raise ValueError("Reported-reason game/date/type is not final canonical scope")
    teams = pd.read_csv(root / "raw/team_game_stats" / suffix)
    teams = teams.loc[pd.to_numeric(teams.game_id).eq(gid)]
    if (
        len(teams) != 2
        or set(teams.team_id) != {int(game.home_team_id), int(game.away_team_id)}
        or not teams.game_date.eq(game.game_date).all()
    ):
        raise ValueError("Reported-reason canonical sides/date disagree")
    return game, teams.set_index("team_id")


def _observe(
    root, *, season, season_type, game_id, team_id, player_id, source_kind, source_raw, receipt_raw
):
    observed, imported, people = _identity(root, season, season_type, game_id, team_id, player_id)
    game, teams = _envelope(root, season, season_type, game_id)
    if observed.game_date != str(game.game_date):
        raise ValueError("Reported reason and DNP game dates differ")
    receipt = json.loads(receipt_raw)
    source_hash = _sha(source_raw)
    if source_kind == "nba_official_finalbox":
        stamp = str(game.game_date).replace("-", "")
        away, home = int(game.away_team_id), int(game.home_team_id)
        away_abbr, home_abbr = teams.loc[away, "team_abbr"], teams.loc[home, "team_abbr"]
        url = f"{report.SOURCE_ROOT}/{stamp}/{stamp}_{away_abbr}{home_abbr}.pdf"
        if (
            receipt["source_url"] != url
            or receipt["sha256"] != source_hash
            or receipt["size_bytes"] != len(source_raw)
            or receipt["raw_file"] != source_hash + ".pdf"
            or datetime.fromisoformat(receipt["retrieved_at"]).tzinfo is None
            or len(source_raw) > 1_500_000
        ):
            raise ValueError("Reported-reason PDF receipt differs from original")
        text = report._report_text(source_raw)
        headings, sections, lines = report._parse_sections(text, str(game.game_date))
        for heading, section, tid in zip(headings, sections, (away, home), strict=True):
            if not report._name(heading).endswith(
                report._name(teams.loc[tid, "team_name"])
            ) or report._score(section) != int(teams.loc[tid, "pts"]):
                raise ValueError("Reported-reason PDF side or score mismatch")
        facts = []
        target_names = {report._name(observed.player_name), report._surname(observed.player_name)}
        selected_name = teams.loc[team_id, "team_name"]
        for label, entries in report._inactives(lines, team_name=selected_name):
            tid = team_id
            for name, reason in entries:
                if report._name(name) not in target_names:
                    continue
                ident, _ = report._identify(people, tid, name, set(), surname=True)
                if ident == player_id:
                    facts.append(
                        (
                            reason.removeprefix("INACTIVE - "),
                            dict(section="inactive_footer", team_id=tid, name=name),
                        )
                    )
        for tid, section in zip((away, home), sections, strict=True):
            if tid != team_id:
                continue
            for line in section:
                match = report.STATUS.match(line)
                if match:
                    name, _, reason = match.groups()
                    if report._name(name) not in target_names:
                        continue
                    ident, _ = report._identify(people, tid, name, set(), surname=True)
                    if ident == player_id:
                        facts.append((reason, dict(section="status_row", team_id=tid, name=name)))
        if len(facts) != 1:
            raise ValueError("Reported reason has missing or ambiguous same-game source identity")
        literal, locator = facts[0]
        extension = ".pdf"
    elif source_kind == "nba_stats_structured_archive":
        packet = (
            root
            / "raw/player_game_availability_sources"
            / (str(observed.source_sha256) + ".structured.json")
        )
        packet_raw = packet.read_bytes()
        if _sha(packet_raw) != observed.source_sha256:
            raise ValueError("Reported-reason structured identity packet differs")
        packet = json.loads(packet_raw)
        original = packet["sources"]["boxscoretraditionalv3"]
        url = original["url"]
        if original["sha256"] != source_hash or original["size_bytes"] != len(source_raw):
            raise ValueError("Reason JSON is not the qualified participation original")
        filename = f"boxscoretraditionalv3_{game_id:010d}.json"
        captured = receipt["files"][filename]
        if (
            captured["url"] != url
            or captured["sha256"] != source_hash
            or captured["size_bytes"] != len(source_raw)
        ):
            raise ValueError("Reported-reason archive capture binding differs")
        document = json.loads(source_raw)["boxScoreTraditional"]
        if (
            int(document["gameId"]) != game_id
            or int(document["homeTeamId"]) != int(game.home_team_id)
            or int(document["awayTeamId"]) != int(game.away_team_id)
        ):
            raise ValueError("Reported-reason JSON envelope differs")
        facts = []
        for side in ("homeTeam", "awayTeam"):
            team = document[side]
            if int(team["statistics"]["points"]) != int(teams.loc[int(team["teamId"]), "pts"]):
                raise ValueError("Reported-reason JSON score differs")
            for index, person in enumerate(team["players"]):
                if int(person["personId"]) == player_id:
                    if int(team["teamId"]) != team_id:
                        raise ValueError("Reported-reason JSON player has wrong side")
                    facts.append(
                        (
                            str(person.get("comment", "")),
                            dict(
                                json_path=f"$.boxScoreTraditional.{side}.players[{index}].comment"
                            ),
                        )
                    )
        if len(facts) != 1:
            raise ValueError("Reported-reason JSON identity is missing or duplicated")
        literal, locator = facts[0]
        extension = ".json"
    else:
        raise ValueError("Unsupported reported-reason source")
    row = dict(
        game_id=f"{game_id:010d}",
        game_date=str(game.game_date),
        season=season,
        season_type=season_type,
        team_id=str(team_id),
        player_id=str(player_id),
        player_name=str(observed.player_name),
        reported_reason=reasons.classify_reason(literal, source_kind),
        reason_text=literal,
        source_kind=source_kind,
        source_url=url,
        source_sha256=source_hash,
        source_locator=json.dumps(locator, sort_keys=True),
        identity_source_sha256=str(observed.source_sha256),
        coverage_scope=reasons.SCOPE,
    )
    return row, imported, extension


def stage_observation(
    root: Path,
    *,
    season: str,
    season_type: str,
    game_id: int,
    team_id: int,
    player_id: int,
    source_kind: str,
    source_file: Path,
    source_receipt: Path,
):
    """Add one source-reported observation; never rewrite any availability path."""
    raw, receipt_raw = source_file.read_bytes(), source_receipt.read_bytes()
    row, imported, extension = _observe(
        root,
        season=season,
        season_type=season_type,
        game_id=game_id,
        team_id=team_id,
        player_id=player_id,
        source_kind=source_kind,
        source_raw=raw,
        receipt_raw=receipt_raw,
    )
    bindings = {}
    for field, content, suffix in [
        ("source_file", raw, extension),
        ("source_receipt", receipt_raw, ".receipt.json"),
    ]:
        relative = reasons.SOURCES + _sha(content) + suffix
        path = root / relative
        if path.exists() and path.read_bytes() != content:
            raise ValueError("Reported-reason source collision")
        bindings[field] = dict(path=relative, sha256=_sha(content), size_bytes=len(content))
    _, relative, lineage = _paths(season, season_type)
    path, ledger_path = root / relative, root / lineage
    if path.exists() != ledger_path.exists():
        raise ValueError("Reported-reason table/lineage must be jointly present")
    frame = (
        pd.read_csv(path, dtype=str, keep_default_na=False)
        if path.exists()
        else pd.DataFrame(columns=reasons.COLUMNS)
    )
    ledger = json.loads(ledger_path.read_bytes()) if ledger_path.exists() else {}
    record = dict(row_sha256=reasons.row_digest(row), identity_import=imported, **bindings)
    ident = reasons.key(row)
    if ident in ledger:
        old = frame.loc[frame.apply(reasons.key, axis=1).eq(ident)]
        if len(old) != 1 or old.iloc[0].to_dict() != row or ledger[ident] != record:
            raise ValueError("Reported-reason replacement or contradiction is forbidden")
        return row
    for field, content in [("source_file", raw), ("source_receipt", receipt_raw)]:
        target = root / bindings[field]["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(content)
    frame = pd.concat([frame, pd.DataFrame([row])], ignore_index=True)
    ledger[ident] = record
    reasons.validate_rows(
        frame,
        ledger,
        source_entry=lambda p: next(
            v
            for r in ledger.values()
            for k, v in r.items()
            if k in {"source_file", "source_receipt"} and v["path"] == p
        ),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")
    return row


def validate_publication(root: Path):
    """Rebuild every companion observation from original bytes before publication."""
    directory = root / reasons.DIRECTORY
    if not directory.exists():
        return
    if {p.stem for p in directory.glob("*.csv")} != {
        p.name.removesuffix(".imports.json") for p in directory.glob("*.imports.json")
    }:
        raise ValueError("Reported-reason table/lineage scopes differ")
    for path in directory.glob("*.csv"):
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        ledger = json.loads(path.with_suffix(".imports.json").read_bytes())

        def source_entry(relative):
            raw = (root / relative).read_bytes()
            return dict(path=relative, sha256=_sha(raw), size_bytes=len(raw))

        reasons.validate_rows(frame, ledger, source_entry=source_entry)
        for row in frame.to_dict("records"):
            if path.name != _paths(row["season"], row["season_type"])[0]:
                raise ValueError("Reported-reason path differs from row season/type")
            record = ledger[reasons.key(row)]
            rebuilt, imported, _ = _observe(
                root,
                season=row["season"],
                season_type=row["season_type"],
                game_id=int(row["game_id"]),
                team_id=int(row["team_id"]),
                player_id=int(row["player_id"]),
                source_kind=row["source_kind"],
                source_raw=(root / record["source_file"]["path"]).read_bytes(),
                receipt_raw=(root / record["source_receipt"]["path"]).read_bytes(),
            )
            if row != rebuilt or record["identity_import"] != imported:
                raise ValueError("Reported-reason rows or receipts differ from original evidence")
