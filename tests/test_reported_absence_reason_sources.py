"""Reason provenance replays originals; binary facts never change or need PDF tools."""

import hashlib
import json

import pandas as pd
import pytest

from nbatools.commands import _reported_absence_reasons as reasons
from nbatools.commands.pipeline import reported_absence_reasons as producer
from nbatools.data_source import reset_data_source_cache
from nbatools.dataframe_cache import clear_frame_cache
from tests.test_structured_participation import run
from tests.test_structured_participation import source as _source

source = _source
pytestmark = pytest.mark.engine
SUFFIX = "2025-26_regular_season.csv"


@pytest.fixture
def staged(source):
    root, original, _, traditional, _ = source
    traditional["boxScoreTraditional"]["homeTeam"]["players"][1]["comment"] = "DNP - Rest"
    run(source)
    path = root / "raw/team_game_stats" / SUFFIX
    teams = pd.read_csv(path)
    teams["game_date"] = "2025-10-21"
    teams["team_name"] = ["A Team", "B Team"]
    teams.to_csv(path, index=False)
    packet = json.loads(
        next((root / "raw/player_game_availability_sources").glob("*.structured.json")).read_bytes()
    )
    captured = packet["sources"]["boxscoretraditionalv3"]
    receipt = root.parent / "sources.json"
    receipt.write_text(json.dumps({"files": {"boxscoretraditionalv3_0022500002.json": captured}}))
    return root, original, receipt


def _stage(staged, **extra):
    root, original, receipt = staged
    return producer.stage_observation(
        root,
        season="2025-26",
        season_type="Regular Season",
        game_id=22500002,
        team_id=1,
        player_id=12,
        source_kind="nba_stats_structured_archive",
        source_file=original,
        source_receipt=receipt,
        **extra,
    )


def _binary_bytes(root):
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for folder in ("player_game_availability", "player_game_availability_sources")
        for p in (root / "raw" / folder).rglob("*")
        if p.is_file()
    }


def _manifest(root, monkeypatch):
    entries = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name != "generation_manifest.json":
            raw = p.read_bytes()
            entries.append(
                dict(
                    path=p.relative_to(root).as_posix(),
                    sha256=hashlib.sha256(raw).hexdigest(),
                    size_bytes=len(raw),
                )
            )
    metadata = root / "metadata"
    metadata.mkdir(exist_ok=True)
    (metadata / "generation_manifest.json").write_text(
        json.dumps(dict(generation_id="legacy", files=entries))
    )
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root.parent))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    clear_frame_cache()


def test_original_replay_idempotence_and_runtime_without_conversion(staged, monkeypatch):
    root, _, _ = staged
    before = _binary_bytes(root)
    row = _stage(staged)
    assert row["reported_reason"] == "reported_rest" and row["reason_text"] == "DNP - Rest"
    _stage(staged)
    producer.validate_publication(root)
    assert _binary_bytes(root) == before
    _manifest(root, monkeypatch)
    monkeypatch.setattr(
        producer.report, "_report_text", lambda *_: pytest.fail("Runtime must not convert PDFs")
    )
    observed = reasons.load_observations(["2025-26"], "Regular Season")
    assert list(observed.reported_reason) == ["reported_rest"]
    assert list(observed.player_id) == [12]
    clear_frame_cache()
    reset_data_source_cache()


def test_jointly_forged_csv_and_ledger_still_fail_original_replay(staged):
    root, _, _ = staged
    _stage(staged)
    path = root / reasons.DIRECTORY / SUFFIX
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    frame.loc[0, ["reported_reason", "reason_text"]] = ["reported_other", "Personal"]
    ledger_path = path.with_suffix(".imports.json")
    ledger = json.loads(ledger_path.read_bytes())
    ledger[reasons.key(frame.iloc[0])]["row_sha256"] = reasons.row_digest(frame.iloc[0])
    frame.to_csv(path, index=False)
    ledger_path.write_text(json.dumps(ledger))
    with pytest.raises(ValueError, match="original evidence"):
        producer.validate_publication(root)


@pytest.mark.parametrize(
    "damage", ["original", "receipt", "binary_identity", "identity_import", "unmanifested"]
)
def test_original_receipt_identity_and_manifest_tampering_rejected(staged, monkeypatch, damage):
    root, original, receipt = staged
    _stage(staged)
    path = root / reasons.DIRECTORY / SUFFIX
    ledger = json.loads(path.with_suffix(".imports.json").read_bytes())
    record = next(iter(ledger.values()))
    if damage in {"original", "receipt"}:
        target = root / record["source_file" if damage == "original" else "source_receipt"]["path"]
        target.write_bytes(target.read_bytes() + b" ")
        with pytest.raises(ValueError, match="source binding"):
            producer.validate_publication(root)
        return
    _manifest(root, monkeypatch)
    if damage == "binary_identity":
        binary = root / "raw/player_game_availability" / SUFFIX
        frame = pd.read_csv(binary, dtype=str, keep_default_na=False)
        frame.loc[frame.player_id.eq("12"), "participation_state"] = "played"
        frame.to_csv(binary, index=False)
        _manifest(root, monkeypatch)
    elif damage == "identity_import":
        imports = root / "raw/player_game_availability" / SUFFIX.replace(".csv", ".imports.json")
        value = json.loads(imports.read_bytes())
        value[str(22500002)]["sha256"] = "0" * 64
        imports.write_text(json.dumps(value))
        _manifest(root, monkeypatch)
    else:
        manifest = root / "metadata/generation_manifest.json"
        value = json.loads(manifest.read_bytes())
        value["files"] = [
            r for r in value["files"] if r["path"] != path.relative_to(root).as_posix()
        ]
        manifest.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        reasons.load_observations(["2025-26"], "Regular Season")
    clear_frame_cache()
    reset_data_source_cache()


@pytest.mark.parametrize(
    "literal, expected",
    [
        ("Rest", "reported_rest"),
        ("INACTIVE - Rest", "reported_rest"),
        ("Injury/Illness - Left hamstring; Strain", "reported_other"),
        ("NWT - League Suspension", "reported_other"),
        ("Personal", "reported_other"),
        ("INACTIVE", "unknown"),
        ("Rest or injury", "unknown"),
        ("", "unknown"),
    ],
)
def test_source_field_classification_never_infers_health(literal, expected):
    assert reasons.classify_reason(literal) == expected


def _pdf(
    staged, monkeypatch, *, reason="Rest", duplicate=False, bare_opponent=False, bare_selected=False
):
    root, _, _ = staged
    raw = b"%PDF-controlled-source-field-fixture"
    pdf = root.parent / "original.pdf"
    pdf.write_bytes(raw)
    receipt = root.parent / "pdf-receipt.json"
    receipt.write_text(
        json.dumps(
            dict(
                source_url=producer.report.SOURCE_ROOT + "/20251021/20251021_BBBAAA.pdf",
                sha256=hashlib.sha256(raw).hexdigest(),
                size_bytes=len(raw),
                retrieved_at="2026-11-01T00:00:00+00:00",
                raw_file=hashlib.sha256(raw).hexdigest() + ".pdf",
            )
        )
    )
    text = (
        "Tuesday, October 21, 2025\nVISITOR: B Team (0-0)\n240:00 8\n"
        "HOME: A Team (0-0)\n240:00 10\n"
        + ("12 DNP Player DNP - Rest\n" if duplicate else "")
        + "SCORE BY PERIOD\nInactive: B Team - "
        + ("Unrelated" if bare_opponent else "NONE")
        + "\n\n"
        + (
            "Inactive: A Team - DNP Player\n\n"
            if bare_selected
            else f"Inactive: A Team - DNP Player ({reason}), Unrelated Unindexed (Personal)\n\n"
        )
    )
    monkeypatch.setattr(
        producer.report,
        "_report_text",
        lambda content: text if content == raw else pytest.fail("Original PDF bytes changed"),
    )
    return dict(
        root=root,
        season="2025-26",
        season_type="Regular Season",
        game_id=22500002,
        team_id=1,
        player_id=12,
        source_kind="nba_official_finalbox",
        source_file=pdf,
        source_receipt=receipt,
    )


def test_pdf_literal_reason_identity_and_unrelated_name_do_not_change_binary(staged, monkeypatch):
    before = _binary_bytes(staged[0])
    args = _pdf(staged, monkeypatch, reason="Injury/Illness - Left hamstring; Strain")
    row = producer.stage_observation(**args)
    assert row["reason_text"] == "Injury/Illness - Left hamstring; Strain"
    assert row["reported_reason"] == "reported_other"
    producer.validate_publication(staged[0])
    assert _binary_bytes(staged[0]) == before


def test_pdf_duplicate_target_reason_cannot_qualify(staged, monkeypatch):
    args = _pdf(staged, monkeypatch, duplicate=True)
    with pytest.raises(ValueError, match="ambiguous same-game"):
        producer.stage_observation(**args)
    assert not (staged[0] / reasons.DIRECTORY).exists()


def test_ambiguous_pdf_reason_is_retained_unknown_not_rest(staged, monkeypatch):
    args = _pdf(staged, monkeypatch, reason="Rest or injury")
    row = producer.stage_observation(**args)
    assert row["reported_reason"] == "unknown"
    producer.validate_publication(staged[0])


def test_selected_footer_reason_does_not_require_opponent_reason_fields(staged, monkeypatch):
    args = _pdf(staged, monkeypatch, bare_opponent=True)
    row = producer.stage_observation(**args)
    assert row["reported_reason"] == "reported_rest"
    producer.validate_publication(staged[0])
    text = producer.report._report_text(args["source_file"].read_bytes())
    with pytest.raises(ValueError, match="Unrecognized official inactive row"):
        producer.report._inactives(text.splitlines())


def test_selected_bare_inactive_cannot_be_promoted_to_other(staged, monkeypatch):
    args = _pdf(staged, monkeypatch, bare_selected=True)
    with pytest.raises(ValueError, match="Unrecognized official inactive row"):
        producer.stage_observation(**args)
    assert not (staged[0] / reasons.DIRECTORY).exists()
