"""Offline assessment of all required readiness datasets, without acceptance.

Materializes retained source projections and existing processed builders into a
new isolated copy of a qualified period stage. Reports literal validator failures;
never writes a passed receipt, production object or completeness override.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import shutil
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path

import pandas as pd

from tools.qualify_readiness_partial import REFRESH_SHA
from tools.qualify_readiness_recovery import (
    PARTIAL,
    RECOVERY,
    SUPPLEMENT_SHA,
    _require,
    authenticate,
    checked_archive,
)
from tools.qualify_rollover_q1 import EVIDENCE, _local_stage

SEASON = "2026-27"
KIND = "Regular Season"
SUFFIX = "2026-27_regular_season.csv"
ROLES_SHA = "255ec5a2c14e0fdc163bdf07a446c0273047f8f1e3dfb54e555ec148dc1999b3"
ROSTER_SHA = "6a4f136a4488a8be5ae49117160c5bc21c5ea43b3b1f3082b872153e099ef8c8"
CURRENT_SHA = "24d041dce0dc568802a4a2664dc2d40c1a4ed7ef4ddb96dc56c826d56587b3c4"


def _checked_csv(path, expected):
    raw = path.read_bytes()
    _require(
        hashlib.sha256(raw).hexdigest() == expected, f"Retained projection differs: {path.name}"
    )
    return pd.read_csv(io.BytesIO(raw))


def _write(root, name, frame, *, layer="raw", suffix=SUFFIX):
    path = root / "data" / layer / name / suffix
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def _hash_files(root):
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*.csv"))
        if p.is_file()
    }


def materialize_sources(root, source_output):
    """Use established normalizers; source projection is not full qualification."""
    from nba_api.stats.endpoints import BoxScoreTraditionalV3

    from nbatools.commands.pipeline import (
        pull_player_season_advanced,
        pull_standings_snapshots,
        pull_team_season_advanced,
    )
    from nbatools.commands.pipeline.official_schedule import normalize_official_schedule
    from nbatools.commands.pipeline.pull_player_game_starter_roles import (
        add_trust_validation,
        normalize_boxscore_player_roles,
    )
    from nbatools.commands.pipeline.structured_participation import _table
    from tools.stage_rollover_periods import _endpoint

    auth = authenticate(RECOVERY / "collection.zip", source_output)
    with checked_archive(RECOVERY / "supplementary-sources.zip", SUPPLEMENT_SHA) as z:
        raw = z.read("schedule-current.json")
        schedule_metadata = json.loads(z.read("current-schedule-metadata.json"))
    _require(
        hashlib.sha256(raw).hexdigest() == schedule_metadata["capture"]["sha256"],
        "Schedule differs from bound source",
    )
    schedule = normalize_official_schedule(raw, SEASON)
    _write(root, "schedule", schedule)
    retained = EVIDENCE / "readiness-reassessment"
    rosters = _checked_csv(retained / "roster-candidate-30-teams.csv", ROSTER_SHA)
    _write(root, "rosters", rosters, suffix="2026-27.csv")
    roles = _checked_csv(retained / "starter-role-candidate-81-games.csv", ROLES_SHA)
    context = pd.read_csv(root / "data/raw/player_game_stats" / SUFFIX)
    keys = ["game_id", "team_id", "player_id"]
    canonical_keys = context[keys].drop_duplicates()
    _require(len(canonical_keys) == len(context), "Duplicate canonical player context")
    old_games = set(roles.game_id)
    new_games = set(context.game_id) - old_games
    _require(
        len(old_games) == 81 and len(new_games) == 11,
        "Expected preserved81 and appended11 role games",
    )
    whole = {}
    with checked_archive(EVIDENCE / "period-milestone/archive-refresh.zip", REFRESH_SHA) as z:
        for gid in range(147, 154):
            ident = f"0022600{gid}"
            whole[ident] = z.read(f"boxscoretraditionalv3_{ident}.json")
    with checked_archive(PARTIAL / "current-sources.zip", CURRENT_SHA) as z:
        for gid in range(154, 158):
            ident = f"0022600{gid}"
            whole[ident] = z.read(f"boxscoretraditionalv3-{ident}.json")
        standings = _table(json.loads(z.read("leaguestandingsv3-regular-season.json")), "Standings")
    new_roles = []
    role_sources = []
    for gid, body in sorted(whole.items()):
        endpoint = _endpoint(BoxScoreTraditionalV3, body, gid)
        frame = normalize_boxscore_player_roles(endpoint.player_stats.get_data_frame())
        frame[keys] = frame[keys].apply(pd.to_numeric, errors="raise").astype("int64")
        # Canonical positive participant identities define the role projection;
        # malformed numeric clocks never establish or negate a POS marker.
        frame = frame.merge(canonical_keys, on=keys, how="inner", validate="one_to_one")
        frame["season"], frame["season_type"] = SEASON, KIND
        frame = add_trust_validation(frame)
        _require(frame.role_source_trusted.eq(1).all(), "Untrusted appended POS projection")
        new_roles.append(frame)
        role_sources.append(
            dict(
                game_id=gid,
                source_sha256=hashlib.sha256(body).hexdigest(),
                rows=len(frame),
                scope="literal_POS_only_not_clock_qualification",
            )
        )
    combined = pd.concat([roles, *new_roles], ignore_index=True)
    _require(
        set(map(tuple, combined[keys].to_numpy())) == set(map(tuple, canonical_keys.to_numpy())),
        "Role participant population differs",
    )
    _require(not combined.duplicated(keys).any(), "Duplicate combined role keys")
    _write(root, "player_game_starter_roles", combined)
    snapshot_sources = []
    for endpoint, table, name, normalizer in [
        (
            "leaguedashplayerstats",
            "LeagueDashPlayerStats",
            "player_season_advanced",
            pull_player_season_advanced.normalize,
        ),
        (
            "leaguedashteamstats",
            "LeagueDashTeamStats",
            "team_season_advanced",
            pull_team_season_advanced.normalize,
        ),
    ]:
        item = next(s for s in auth["sources"] if s["job"]["endpoint"] == endpoint)
        body = (source_output / item["job"]["source_file"]).read_bytes()
        frame = normalizer(_table(json.loads(body), table), SEASON, KIND, "2026-11-01")
        _write(root, name, frame)
        snapshot_sources.append(
            dict(
                dataset=name,
                source_sha256=item["sha256"],
                request=item["job"],
                as_of_date="2026-11-01",
            )
        )
    _write(
        root,
        "standings_snapshots",
        pull_standings_snapshots.normalize(standings, SEASON, KIND, "2026-11-01"),
    )
    return dict(
        schedule=schedule_metadata,
        roster_projection_sha256=ROSTER_SHA,
        preserved_role_projection_sha256=ROLES_SHA,
        appended_role_sources=role_sources,
        snapshots=snapshot_sources,
        original_source_capture_time="unverified for archive sources",
        raw_projection_does_not_establish_source_basis_acceptance=True,
    )


def source_basis_report(root):
    """Retain disagreement cells; never replace counts or source Advanced values."""
    player = pd.read_csv(root / "data/raw/player_game_stats" / SUFFIX)
    adv = pd.read_csv(root / "data/raw/player_season_advanced" / SUFFIX)
    keys = ["player_id"]
    totals = player.groupby(keys)[["pts", "fga", "fta"]].sum()
    snapshot = adv.set_index("player_id")
    _require(
        not snapshot.index.has_duplicates and set(totals.index) == set(snapshot.index),
        "Advanced/core player population differs",
    )
    denom = 2 * (totals.fga + 0.44 * totals.fta)
    expected = totals.pts.div(denom.where(denom.ne(0))).fillna(0)
    differences = []
    for pid in totals.index:
        actual = float(snapshot.loc[pid, "ts_pct"])
        if abs(float(expected.loc[pid]) - actual) > 0.0005:
            differences.append(
                dict(
                    player_id=int(pid),
                    name=snapshot.loc[pid, "player_name"],
                    pts=int(totals.loc[pid, "pts"]),
                    fga=int(totals.loc[pid, "fga"]),
                    fta=int(totals.loc[pid, "fta"]),
                    expected_ts=float(expected.loc[pid]),
                    source_ts=actual,
                )
            )
    return dict(
        formula="PTS/(2*(FGA+0.44*FTA)); zero denominator -> 0",
        source_precision=3,
        unchanged_tolerance=0.0005,
        compared_player_ids=len(totals),
        ts_conflicts=differences,
        usage_source_range_check=bool(adv.usage_rate.between(0, 1).all()),
        usage_independent_numeric_basis="not established by a range check",
        source_values_rewritten=False,
        full_source_coherence=False,
    )


def minute_mean_interval(tokens):
    """Bound serialization ambiguity without inventing source clock resolution.

    A CSV decimal token and the rounding cell of its nearest binary64 value
    delimit the representational information available here. Use exact rational
    midpoints to adjacent floats, not a numeric epsilon. A source comparison
    crossing either unchanged acceptance boundary remains an unmet obligation;
    this interval neither repairs a clock nor establishes its true precision.
    """
    tokens = list(tokens)
    _require(bool(tokens), "Cannot compare an empty minute population")
    lower = upper = Fraction(0)
    for token in tokens:
        value = float(token)
        _require(math.isfinite(value) and value >= 0, "Invalid serialized minute value")
        center = Fraction.from_float(value)
        before, after = math.nextafter(value, -math.inf), math.nextafter(value, math.inf)
        _require(math.isfinite(before) and math.isfinite(after), "Unbounded minute serialization")
        decimal = Fraction(str(token))
        lower += min(decimal, (Fraction.from_float(before) + center) / 2)
        upper += max(decimal, (center + Fraction.from_float(after)) / 2)
    return lower / len(tokens), upper / len(tokens)


def snapshot_record_checks(root, source_output=None):
    """Apply existing exact count/record and net-rating consistency rules."""
    players = pd.read_csv(root / "data/raw/player_game_stats" / SUFFIX, dtype={"minutes": str})
    teams = pd.read_csv(root / "data/raw/team_game_stats" / SUFFIX)
    player_adv = pd.read_csv(root / "data/raw/player_season_advanced" / SUFFIX)
    team_adv = pd.read_csv(root / "data/raw/team_season_advanced" / SUFFIX)
    standings = pd.read_csv(root / "data/raw/standings_snapshots" / SUFFIX)
    expected_players = players.groupby("player_id").size().to_frame("games_played")
    if source_output is not None:
        from nbatools.commands.pipeline.structured_participation import _table

        original = _table(
            json.loads(
                (
                    source_output / "sources/leaguedashplayerstats_advanced_through_20261101.json"
                ).read_bytes()
            ),
            "LeagueDashPlayerStats",
        )
        player_adv = player_adv.merge(
            original[["PLAYER_ID", "W", "L"]].rename(
                columns={"PLAYER_ID": "player_id", "W": "wins", "L": "losses"}
            ),
            on="player_id",
            validate="one_to_one",
        )
        played = players.merge(
            teams[["game_id", "team_id", "wl"]], on=["game_id", "team_id"], validate="many_to_one"
        )
        records = (
            played.assign(wins=played.wl.eq("W").astype(int), losses=played.wl.eq("L").astype(int))
            .groupby("player_id")[["wins", "losses"]]
            .sum()
        )
        expected_players = expected_players.join(records)
    team_records = (
        teams.assign(
            games_played=1, wins=teams.wl.eq("W").astype(int), losses=teams.wl.eq("L").astype(int)
        )
        .groupby("team_id")[["games_played", "wins", "losses"]]
        .sum()
    )
    conflicts = []
    for name, source, identity, expected in [
        (
            "player_season_advanced",
            player_adv,
            "player_id",
            expected_players,
        ),
        ("team_season_advanced", team_adv, "team_id", team_records),
        ("standings_snapshots", standings, "team_id", team_records[["wins", "losses"]]),
    ]:
        if source.duplicated(identity).any() or set(source[identity]) != set(expected.index):
            conflicts.append(dict(dataset=name, field="identity_population", error="keys differ"))
            continue
        indexed = source.set_index(identity)
        for ident, row in expected.iterrows():
            for field, value in row.items():
                actual = indexed.loc[ident, field]
                if actual != value:
                    conflicts.append(
                        dict(
                            dataset=name,
                            identity=int(ident),
                            field=field,
                            expected=int(value),
                            source=float(actual),
                        )
                    )
    minute_checked = 0
    precision_boundary_unresolved = []
    if "minutes" in players and "minutes_per_game" in player_adv:
        indexed = player_adv.set_index("player_id")
        for pid, rows in players.groupby("player_id"):
            if pid not in indexed.index:
                continue
            source_minutes = Fraction(str(indexed.loc[pid, "minutes_per_game"]))
            _require(
                (source_minutes * 10).denominator == 1,
                "Player Advanced minutes precision differs from one decimal",
            )
            mean_lower, mean_upper = minute_mean_interval(rows.minutes)
            serialized_mean = sum((Fraction(str(v)) for v in rows.minutes), Fraction(0)) / len(rows)
            minute_checked += 1
            allowed_lower, allowed_upper = (
                source_minutes - Fraction(1, 20),
                source_minutes + Fraction(1, 20),
            )
            details = dict(
                dataset="player_season_advanced",
                identity=int(pid),
                field="minutes_per_game",
                serialized_mean_minutes=float(serialized_mean),
                source=float(source_minutes),
                representational_mean_interval=dict(lower=str(mean_lower), upper=str(mean_upper)),
            )
            if mean_upper < allowed_lower or mean_lower > allowed_upper:
                conflicts.append(
                    dict(
                        details,
                        absolute_residual_minutes=float(abs(source_minutes - serialized_mean)),
                    )
                )
            elif mean_lower < allowed_lower or mean_upper > allowed_upper:
                precision_boundary_unresolved.append(
                    dict(
                        details,
                        reason=(
                            "serialized source clock precision cannot resolve "
                            "inclusive rounding boundary"
                        ),
                    )
                )
    rating_residual = (team_adv.off_rating - team_adv.def_rating - team_adv.net_rating).abs()
    for index in team_adv.index[~rating_residual.lt(0.5)]:
        conflicts.append(
            dict(
                dataset="team_season_advanced",
                identity=int(team_adv.loc[index, "team_id"]),
                field="net_rating",
                absolute_residual=float(rating_residual.loc[index]),
            )
        )
    return dict(
        player_ids=len(expected_players),
        team_ids=len(team_records),
        conflicts=conflicts,
        passed=not (conflicts or precision_boundary_unresolved),
        precision_boundary_unresolved=precision_boundary_unresolved,
        count_and_record_tolerance=0,
        minutes_compared_player_ids=minute_checked,
        minutes_source_precision=1,
        minutes_rounding_half_step=0.05,
        minutes_serialization_policy=(
            "exact decimal/binary64 rounding-cell interval; boundary straddles remain unresolved"
        ),
        net_rating_tolerance_exclusive=0.5,
        statistical_scope="retained92game_population_not_fresh_due_completeness",
    )


def due_population(root, checked_at):
    from nbatools.readiness import _missing_due_game_ids

    schedule = pd.read_csv(root / "data/raw/schedule" / SUFFIX)
    games = pd.read_csv(root / "data/raw/games" / SUFFIX)
    empty_games = games.iloc[:0].copy()
    due = _missing_due_game_ids(schedule, empty_games, checked_at, SEASON, KIND)
    missing = _missing_due_game_ids(schedule, games, checked_at, SEASON, KIND)
    _require(due is not None and missing is not None, "Exact due population cannot be verified")
    return dict(
        checked_at=checked_at.isoformat(),
        lag_hours=24,
        due_game_ids=list(due),
        missing_due_game_ids=list(missing),
        observed_final_games=int(games.is_final.eq(1).sum()),
        population_current_against_retained_schedule=True,
        final_acceptance_requires_new_freshness_check=True,
    )


def assess(stage: Path, output: Path, *, checked_at=None):
    """Attempt the normal full dataset gates without accepting their failures."""
    from nbatools.commands.pipeline import (
        build_game_features,
        build_league_season_stats,
        build_player_game_features,
        build_schedule_context_features,
        build_team_game_features,
        validate_raw,
    )
    from nbatools.commands.validation_control import (
        DATASET_SPECS,
        build_slice_manifest,
        validate_manifest_document,
    )

    stage, output = stage.resolve(), output.resolve()
    _require(not output.exists(), "Assessment output must be a fresh isolated directory")
    checked_at = checked_at or datetime.now(UTC)
    _require(checked_at.tzinfo is not None, "Assessment time requires a timezone")
    source_hashes = _hash_files(stage)
    output.mkdir(parents=True)
    root = output / "stage"
    shutil.copytree(stage, root)
    provenance = materialize_sources(root, output / "original")
    stages = []
    with _local_stage(root):
        for name, fn in [
            ("validate_raw", validate_raw.run),
            ("build_team_game_features", build_team_game_features.run),
            ("build_game_features", build_game_features.run),
            ("build_schedule_context_features", build_schedule_context_features.run),
            ("build_player_game_features", build_player_game_features.run),
            ("build_league_season_stats", build_league_season_stats.run),
        ]:
            try:
                fn(SEASON, KIND)
            except Exception as exc:
                stages.append(dict(name=name, state="failed", error=f"{type(exc).__name__}: {exc}"))
            else:
                stages.append(dict(name=name, state="passed"))
        manifest = build_slice_manifest(
            SEASON,
            KIND,
            data_root=root / "data",
            generation_id="unpublished-readiness-recovery-assessment",
            generated_at=checked_at.isoformat(),
        )
        manifest_errors = validate_manifest_document(manifest)
    required_specs = [s for s in DATASET_SPECS if s.required and s.applies(KIND)]
    required = {s.name: s for s in required_specs}
    _require(
        sum(s.layer == "raw" for s in required_specs) == 11
        and sum(s.layer == "processed" for s in required_specs) == 5,
        "Required dataset contract changed",
    )
    records = [r for r in manifest["datasets"] if r["name"] in required]
    _require(len(records) == 16, "Required dataset denominator must remain sixteen")
    _require(_hash_files(stage) == source_hashes, "Assessment mutated the input stage")
    report = dict(
        classification="all_required_datasets_assessed_not_accepted_or_published",
        season=SEASON,
        season_type=KIND,
        checked_at=checked_at.isoformat(),
        input_stage_file_sha256=source_hashes,
        source_provenance=provenance,
        required_raw=11,
        required_processed=5,
        required_records=records,
        required_present=sum(bool(r["file_sha256"]) for r in records),
        required_passed=sum(r["validation"]["state"] == "passed" for r in records),
        validator_stages=stages,
        manifest_state=manifest["validation_state"],
        manifest_validation_errors=manifest_errors,
        numerical_source_basis=source_basis_report(root),
        snapshot_record_consistency=snapshot_record_checks(root, output / "original"),
        exact_due_population=due_population(root, checked_at),
        source_input_preserved=True,
        full_snapshot_accepted=False,
        readiness_accepted=False,
        production_writes=0,
        trusted_acceptance_receipt_created=False,
    )
    (output / "dataset-manifest-assessment.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (output / "assessment.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = assess(args.stage, args.output)
    print(
        json.dumps(
            {
                k: result[k]
                for k in [
                    "required_raw",
                    "required_processed",
                    "required_present",
                    "required_passed",
                    "manifest_state",
                    "full_snapshot_accepted",
                ]
            },
            indent=2,
        )
    )
