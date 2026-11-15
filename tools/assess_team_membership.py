"""Offline bulk-source qualification report. Never emit accepted tenure or DNPs.

The conditional model asks what an opening list plus the observed changes would
imply IF both were complete/correct. It is deliberately separate from the
existing resolver's exact-game facts and cannot be loaded as membership CSV.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

from nbatools.commands._dated_membership import COLUMNS, calendar_date, membership_on_date


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def name_key(text):
    # PDF kerning can split a word ("V anVleet"); fail on ambiguous IDs rather
    # than picking the player with most appearances or guessing a name alias.
    return re.sub(
        r"[^a-z0-9]",
        "",
        unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower(),
    )


def opening_2023_release(raw, teams, identities):
    """Read selected columns from the retained frozen NBA release, including IL.

    This is one qualified FORMAT adapter, not acceptance of the roster's facts.
    New documents/formats must be inspected before extending its native hash.
    Header coordinates keep empty cells from shifting a name to another club.
    """
    if sha(raw) != "c122900f6a322dc7aac4aa5d1096d185e652bd439d79595106bc35eb130178f7":
        raise ValueError("Uninspected opening-release format/body")
    index = defaultdict(set)
    for player, name in identities:
        index[name_key(name)].add(int(player))
    pdf = PdfReader(io.BytesIO(raw))
    result = {}
    for page in pdf.pages:
        parts = []

        def visit(text, cm, tm, font, size):
            if text.strip():
                parts.append((round(tm[4], 1), round(tm[5], 1), text.strip()))

        page.extract_text(visitor_text=visit)
        rows = defaultdict(list)
        for x, y, text in parts:
            rows[y].append((x, text))
        # All six header rows have five uppercase team labels at the native
        # column starts. Titles and the shared inactive heading do not match.
        headers = {
            y: sorted(cells)
            for y, cells in rows.items()
            if len(cells) == 5 and all(t == t.upper() for _, t in cells)
        }
        for y, cells in headers.items():
            for column, (left, label) in enumerate(cells):
                if label not in teams:
                    continue
                tid = teams[label]
                if tid in result:
                    raise ValueError("Duplicate opening team column")
                bottom = max((v for v in headers if v < y), default=0)
                right = cells[column + 1][0] if column < 4 else 600
                players = []
                for row_y, texts in sorted(rows.items(), reverse=True):
                    if not bottom < row_y < y:
                        continue
                    texts = [(x, t) for x, t in texts if left - 0.5 <= x < right - 0.5]
                    text = " ".join(t for x, t in sorted(texts))
                    if not text or "INACTIVE/TWO-WAY LISTS" in text:
                        continue
                    ids = index[name_key(text)]
                    if len(ids) != 1:
                        raise ValueError(f"Unresolved/ambiguous opening identity: {label}: {text}")
                    players.append(
                        dict(
                            player_id=next(iter(ids)),
                            source_name=text.lstrip("*"),
                            two_way=text.startswith("*"),
                        )
                    )
                if not 12 <= len(players) <= 21:
                    raise ValueError("Unexpected opening column population")
                result[tid] = players
    if set(result) != set(teams.values()):
        raise ValueError("Missing requested opening team column")
    return result


def normalize_movements(document, teams, start, end):
    """Native NBA feed: Trade rows identify receiver AND sender, not two adds."""
    native = document["NBA_Player_Movement"]
    required = {
        "Transaction_Type",
        "TRANSACTION_DATE",
        "TRANSACTION_DESCRIPTION",
        "TEAM_ID",
        "TEAM_SLUG",
        "PLAYER_ID",
        "PLAYER_SLUG",
        "Additional_Sort",
        "GroupSort",
    }
    if {c["Name"] for c in native["columns"]} != required or not native["rows"]:
        raise ValueError("Unrecognized native movement schema")
    events, ignored, days = [], [], []
    for index, row in enumerate(native["rows"]):
        if set(row) != required:
            raise ValueError("Incomplete native movement row")
        stamp = row["TRANSACTION_DATE"]
        if not isinstance(stamp, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T00:00:00", stamp):
            raise ValueError("Movement timestamp is not an unambiguous date")
        day = calendar_date(stamp[:10])
        days.append(day)
        kind = row["Transaction_Type"]
        team, player, sender = row["TEAM_ID"], row["PLAYER_ID"], row["Additional_Sort"]
        if (
            any(
                type(v) not in (int, float) or not math.isfinite(v) or v < 0 or v != int(v)
                for v in (team, player, sender)
            )
            or not team
        ):
            raise ValueError("Invalid native movement identities")
        team, player, sender = map(int, (team, player, sender))
        targets = {team} & set(teams)
        if kind == "Trade":
            if not sender or sender == team:
                raise ValueError("Invalid trade sender/receiver")
            targets |= {sender} & set(teams)
        if not targets or not start <= day <= end:
            continue
        base = dict(
            native_row=index,
            date=day.isoformat(),
            player_id=player,
            player_slug=row["PLAYER_SLUG"],
            kind=kind,
            description=row["TRANSACTION_DESCRIPTION"],
            group=row["GroupSort"],
        )
        if player == 0:
            ignored.append(dict(base, reason="nonplayer_transaction"))
            continue
        for target in sorted(targets):
            action = {
                "Signing": "member",
                "Waive": "not_member",
                "ContractConverted": "status_only",
                "AwardOnWaivers": "member",
            }.get(kind, "unknown")
            if kind == "Trade":
                action = "member" if target == team else "not_member"
            events.append(
                dict(
                    base,
                    team_id=target,
                    action=action,
                    temporary=kind == "Signing" and "10-Day" in base["description"],
                )
            )
    return dict(
        events=events,
        ignored=ignored,
        native_row_count=len(days),
        earliest=min(days).isoformat(),
        latest=max(days).isoformat(),
    )


def assess_team(
    *,
    team_id,
    opening,
    document_date,
    anchor_date,
    end_date,
    events,
    games,
    appearances,
    disputes=(),
):
    """Measure a finite whole-team population without closing source gaps.

    Opening identities must come from a frozen enumerated source, NOT a season
    roster. Appearances add validation targets/exact-game facts only; they never
    supply tenure. Date-only changes leave their affected game-day unresolved.
    """
    document_day, anchor, end = map(calendar_date, (document_date, anchor_date, end_date))
    if document_day > anchor or anchor > end:
        raise ValueError("Invalid source document/claimed effective window")
    baseline = {r["player_id"] for r in opening}
    if not baseline or len(baseline) != len(opening):
        raise ValueError("Missing or duplicate opening identities")
    selected = [e for e in events if e["team_id"] == team_id]
    positive = appearances.loc[pd.to_numeric(appearances.minutes, errors="coerce").gt(0)]
    appeared = {(int(r.game_id), int(r.player_id)) for r in positive.itertuples()}
    universe = (
        baseline | {e["player_id"] for e in selected} | set(appearances.player_id.astype(int))
    )
    orphan = sorted(
        set(appearances.player_id.astype(int)) - baseline - {e["player_id"] for e in selected}
    )
    if games.game_id.duplicated().any() or games.empty:
        raise ValueError("Missing or duplicate team games")
    catalog = dict(zip(games.game_id.astype(int), games.game_date.astype(str)))
    if appearances.duplicated(["game_id", "player_id"]).any() or any(
        catalog.get(int(r.game_id)) != str(r.game_date) for r in appearances.itertuples()
    ):
        raise ValueError("Appearance/catalog identity or date mismatch")
    by_player = defaultdict(list)
    for event in selected:
        if not document_date <= event["date"] <= end_date:
            raise ValueError("Event outside assessed source window")
        by_player[event["player_id"]].append(event)
    conflicts, models, uncertain = [], [], []
    day_after = timedelta(days=1)
    for player in sorted(universe):
        changes = sorted(by_player[player], key=lambda e: e["date"])
        before = [e for e in changes if e["date"] < anchor_date and e["action"] != "status_only"]
        # The release CLAIMS opening-night membership; preserve that claim and
        # compare it with changes since publication, never silently repair it.
        prior_actions = (
            {e["action"] for e in before if e["date"] == max(x["date"] for x in before)}
            if before
            else set()
        )
        state = "member" if player in baseline else "not_member"
        problem = "unexplained_appearance" if player in orphan else None
        if prior_actions and prior_actions != {state}:
            conflicts.append(dict(player_id=player, roster_state=state, events=before))
            problem = "opening_source_conflict"
        if before and any(e["temporary"] for e in before if e["date"] == before[-1]["date"]):
            problem = problem or "temporary_contract_end_missing"
        start = anchor
        groups = defaultdict(list)
        for event in changes:
            if event["date"] >= anchor_date:
                groups[event["date"]].append(event)
        for day_text, group in sorted(groups.items()):
            day = calendar_date(day_text)
            actions = {e["action"] for e in group if e["action"] != "status_only"}
            if not actions and state == "member" and not problem:
                continue
            if start <= day - day_after:
                if problem:
                    uncertain.append(
                        dict(player_id=player, start=start, end=day - day_after, reason=problem)
                    )
                else:
                    models.append(
                        dict(
                            player_id=player,
                            team_id=team_id,
                            start_date=start,
                            end_date=day - day_after,
                            membership_state=state,
                            source_sha256="conditional",
                        )
                    )
            # Unknown kinds and conflicting same-day actions poison continuity
            # until the next unambiguous dated change. Conversion alone is not
            # an acquisition (and cannot repair a missing starting anchor).
            if actions:
                uncertain.append(
                    dict(player_id=player, start=day, end=day, reason="event_day_time_unknown")
                )
                if len(actions) != 1 or "unknown" in actions:
                    problem = "unrecognized_or_unordered_changes"
                else:
                    state = next(iter(actions))
                    problem = (
                        "temporary_contract_end_missing"
                        if any(e["temporary"] for e in group)
                        else None
                    )
            elif state != "member" or problem:
                problem = problem or "conversion_without_membership_anchor"
                uncertain.append(dict(player_id=player, start=day, end=day, reason=problem))
            start = day + day_after
        if start <= end:
            if problem:
                uncertain.append(dict(player_id=player, start=start, end=end, reason=problem))
            else:
                models.append(
                    dict(
                        player_id=player,
                        team_id=team_id,
                        start_date=start,
                        end_date=end,
                        membership_state=state,
                        source_sha256="conditional",
                    )
                )
    model = pd.DataFrame(models, columns=COLUMNS)
    empty = pd.DataFrame(columns=COLUMNS)
    cells, contradictions = [], []
    for game in games.sort_values(["game_date", "game_id"]).itertuples():
        day = calendar_date(str(game.game_date))
        if not anchor <= day <= end:
            raise ValueError("Game outside assessed window")
        for player in sorted(universe):
            conditional = membership_on_date(model, player, day, team_id).state
            reasons = [
                u["reason"]
                for u in uncertain
                if u["player_id"] == player and u["start"] <= day <= u["end"]
            ]
            for dispute in disputes:
                if dispute["player_id"] == player and calendar_date(
                    dispute["start_date"]
                ) <= day <= calendar_date(dispute["end_date"]):
                    conditional = "unknown"
                    reasons.append("disputed_event_date")
            played = (int(game.game_id), player) in appeared
            if played and conditional == "not_member":
                contradictions.append(dict(game_id=int(game.game_id), player_id=player))
                conditional = "unknown"
                reasons.append("appearance_contradicts_model")
            # Actual resolver gets ONLY exact-game positive facts. It never
            # receives the conditional model as accepted dated evidence.
            fact = membership_on_date(
                empty, player, day, team_id, exact_team_id=team_id if played else None
            )
            cells.append(
                dict(
                    game_id=int(game.game_id),
                    date=day.isoformat(),
                    player_id=player,
                    conditional_membership=conditional,
                    uncertainty=reasons,
                    membership_from_appearance=fact.state,
                    participation="played" if played else "unknown",
                )
            )
    contradicted = {c["player_id"] for c in contradictions}
    for cell in cells:
        if cell["player_id"] in contradicted:
            cell["conditional_membership"] = "unknown"
            cell["uncertainty"].append("source_model_contradiction")
    return dict(
        team_id=team_id,
        classification="provisional_source_assessment_only",
        complete_membership=False,
        accepted_intervals=[],
        verified_missed_games=None,
        missing_evidence=[
            "qualified_complete_opening_anchor",
            "qualified_complete_dated_contract_ledger",
        ],
        document_date=document_date,
        claimed_opening_date=anchor_date,
        opening=opening,
        observed_games=len(games),
        candidate_people=len(universe),
        played_people=int(appearances.player_id.nunique()),
        zero_appearance_candidates=sorted(universe - set(appearances.player_id.astype(int))),
        opening_conflicts=conflicts,
        unexplained_appearance_people=orphan,
        appearance_contradictions=contradictions,
        events=selected,
        conditional_cells=dict(Counter(c["conditional_membership"] for c in cells)),
        exact_game_membership_cells=dict(Counter(c["membership_from_appearance"] for c in cells)),
        participation_cells=dict(Counter(c["participation"] for c in cells)),
        cells=cells,
    )


def build_assessment(request_path, sources, games_path, stats_path):
    request = json.loads(request_path.read_bytes())
    paths = {
        "opening-2023.pdf": sources / "opening-2023.pdf",
        "player-movement.json": sources / "player-movement.json",
        "games": games_path,
        "appearances": stats_path,
    }
    provenance = json.loads((sources / "sources.json").read_bytes())
    for name, path in paths.items():
        if path.is_symlink() or sha(path.read_bytes()) != request["input_sha256"][name]:
            raise ValueError("Retained input hash differs from request")
        if name in {"games", "appearances"}:
            continue
        record = provenance[name]
        if (
            record["sha256"] != request["input_sha256"][name]
            or record["size_bytes"] != path.stat().st_size
            or record["complete"] is not True
            or record["http_status"] != 200
            or not record["url"].startswith("https://")
            or datetime.fromisoformat(record["retrieved_at"]).tzinfo is None
        ):
            raise ValueError("Incomplete original source provenance")
    movement = paths["player-movement.json"]
    raw = movement.read_bytes()
    document = json.loads(raw)
    normalized = normalize_movements(
        document,
        [t["team_id"] for t in request["teams"]],
        calendar_date(request["document_date"]),
        calendar_date(request["end_date"]),
    )
    games, stats = pd.read_csv(games_path), pd.read_csv(stats_path)
    for frame in (games, stats):
        if not (frame.season.eq(request["season"]) & frame.season_type.eq("Regular Season")).all():
            raise ValueError("Canonical input scope mismatch")
    identities = list(
        stats[["player_id", "player_name"]].drop_duplicates().itertuples(index=False, name=None)
    )
    identities += [
        (r["PLAYER_ID"], r["PLAYER_SLUG"])
        for r in document["NBA_Player_Movement"]["rows"]
        if r["PLAYER_ID"]
    ]
    opening = opening_2023_release(
        paths["opening-2023.pdf"].read_bytes(),
        {t["header"]: t["team_id"] for t in request["teams"]},
        identities,
    )
    reports = []
    for team in request["teams"]:
        tid = team["team_id"]
        reports.append(
            assess_team(
                team_id=tid,
                opening=opening[tid],
                document_date=request["document_date"],
                anchor_date=request["claimed_opening_date"],
                end_date=request["end_date"],
                events=normalized["events"],
                games=games.loc[games.home_team_id.eq(tid) | games.away_team_id.eq(tid)],
                appearances=stats.loc[stats.team_id.eq(tid)],
                disputes=team.get("date_disputes", []),
            )
        )
    return dict(
        classification="provisional_source_assessment_only",
        source=normalized,
        inputs={
            str(p): sha(p.read_bytes())
            for p in [request_path, sources / "sources.json", *paths.values()]
        },
        original_source_captures=provenance,
        teams=reports,
        production_writes=0,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--games", type=Path, required=True)
    parser.add_argument("--appearances", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_assessment(args.request, args.sources, args.games, args.appearances)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
