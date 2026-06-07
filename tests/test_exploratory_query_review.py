import json

import pytest

from tools import exploratory_query_review as review


def _write_json(path, data) -> None:
    path.write_text(json.dumps(data) + "\n")


def _write_text(path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _payload(
    *,
    query: str,
    route: str | None,
    status: str,
    reason: str | None = None,
    query_class: str | None = None,
    sections: dict | None = None,
    filters: list[dict] | None = None,
    answer_phrase: str | None = None,
) -> dict:
    metadata = {
        "query_class": query_class,
        "applied_filters": filters or [],
    }
    if answer_phrase:
        metadata["answer_phrase"] = answer_phrase
    return {
        "ok": status == "ok",
        "query": query,
        "route": route,
        "result_status": status,
        "result_reason": reason,
        "current_through": "2026-06-01",
        "confidence": "high",
        "intent": route,
        "alternates": [],
        "notes": [],
        "caveats": [],
        "result": {
            "query_class": query_class,
            "metadata": metadata,
            "sections": sections or {},
        },
    }


def test_load_samples_accepts_input_only_list_and_metadata(tmp_path) -> None:
    input_path = tmp_path / "samples.json"
    _write_json(
        input_path,
        {
            "version": 1,
            "samples": [
                "Who leads the NBA in points per game?",
                {
                    "id": "celtics_record",
                    "query": "Celtics record against playoff teams",
                    "category": "opponent_quality",
                    "priority": "p1",
                    "notes": "review season-type semantics",
                    "tags": ["beta"],
                },
            ],
        },
    )

    version, samples = review.load_samples(input_path)

    assert version == 1
    assert [sample["id"] for sample in samples] == ["sample_001", "celtics_record"]
    assert samples[1]["category"] == "opponent_quality"
    assert samples[1]["input_notes"] == "review season-type semantics"
    assert samples[1]["metadata"]["tags"] == ["beta"]


def test_load_samples_rejects_raw_qa_expectations(tmp_path) -> None:
    input_path = tmp_path / "samples.json"
    _write_json(
        input_path,
        {
            "samples": [
                {
                    "id": "bad_case",
                    "query": "Celtics record",
                    "expected_status": "ok",
                }
            ]
        },
    )

    with pytest.raises(ValueError, match="input-only"):
        review.load_samples(input_path)


def test_run_review_writes_reports_and_summary_counts(tmp_path, monkeypatch) -> None:
    ok_query = "Lakers road record last season"
    no_result_query = "best moonshot percentage"
    exception_query = "explode query"
    input_path = tmp_path / "samples.json"
    _write_json(
        input_path,
        {
            "samples": [
                {"id": "ok_case", "query": ok_query, "category": "record", "priority": "p1"},
                {"id": "no_result_case", "query": no_result_query, "category": "unsupported"},
                {"id": "exception_case", "query": exception_query},
            ]
        },
    )
    payloads = {
        ok_query: _payload(
            query=ok_query,
            route="team_record",
            status="ok",
            query_class="summary",
            sections={
                "summary": [{"team_abbr": "LAL", "games": 3, "wins": 2, "losses": 1}],
                "game_log": [
                    {"game_date": "2026-01-01", "team_abbr": "LAL", "wl": "W"},
                    {"game_date": "2026-01-02", "team_abbr": "LAL", "wl": "L"},
                ],
            },
            filters=[{"kind": "split", "label": "Location", "value": "Road"}],
            answer_phrase="The Lakers went 2-1 on the road.",
        ),
        no_result_query: _payload(
            query=no_result_query,
            route="season_leaders",
            status="no_result",
            reason="unsupported_metric",
            query_class="leaderboard",
        ),
    }

    def fake_execute_payload(query: str) -> dict:
        if query == exception_query:
            raise RuntimeError("boom")
        return payloads[query]

    monkeypatch.setattr(review, "execute_query_payload", fake_execute_payload)

    result = review.run_review(
        input_path=input_path,
        out_base=tmp_path / "out",
        run_id="review",
        overwrite_run_id=False,
        limit=None,
        top_rows=1,
    )

    run_dir = result["run_dir"]
    summary = json.loads((run_dir / "summary.json").read_text())
    rows = [json.loads(line) for line in (run_dir / "report.jsonl").read_text().splitlines()]
    markdown = (run_dir / "report.md").read_text()

    assert run_dir == tmp_path / "out/archive/runs/review__all"
    assert (tmp_path / "out/latest/report.md").read_text() == markdown
    assert (tmp_path / "out/index.md").exists()
    assert (tmp_path / "out/README.md").exists()
    assert sorted(path.name for path in (tmp_path / "out").iterdir()) == [
        "README.md",
        "archive",
        "index.md",
        "latest",
        "latest_by_slice",
    ]
    assert summary["case_count"] == 3
    assert summary["result_status_counts"] == {"error": 1, "no_result": 1, "ok": 1}
    assert summary["route_counts"] == {"<none>": 1, "season_leaders": 1, "team_record": 1}
    assert summary["query_class_counts"] == {"<none>": 1, "leaderboard": 1, "summary": 1}
    assert summary["display_shape_counts"] == {
        "no_result_message": 2,
        "team_record": 1,
    }
    assert summary["no_result_case_ids"] == ["no_result_case"]
    assert summary["error_case_ids"] == ["exception_case"]
    assert summary["suspicious_case_count"] == 0
    assert summary["review_flag_counts"] == {"exception": 1, "no_result": 1}
    assert rows[0]["payload"]["route"] == "team_record"
    assert rows[0]["search_box_preview"]["display_shape"] == {
        "key": "team_record",
        "name": "Team Record",
        "description": "Team record hero with a single-summary record table.",
    }
    assert rows[0]["search_box_preview"]["renderer_patterns"] == [
        {"type": "record", "mode": "team_record"},
        {
            "type": "game_log",
            "section_key": "game_log",
            "summary_key": "summary",
            "mode": "team",
            "show_summary_strip": False,
            "raw_detail_title": "Game Detail",
            "collapse_to_detail": True,
        },
    ]
    assert rows[0]["search_box_preview"]["answer_line"] == "The Lakers went 2-1 on the road."
    assert rows[0]["search_box_preview"]["primary_section"] == {
        "name": "summary",
        "row_count": 1,
        "kind": "hero_or_summary",
        "columns": ["team_abbr", "games", "wins", "losses"],
    }
    assert rows[0]["search_box_preview"]["visible_sections"][1]["name"] == "game_log"
    assert rows[1]["search_box_preview"]["display_shape"]["key"] == "no_result_message"
    assert len(rows[0]["section_summaries"]["game_log"]["top_rows"]) == 1
    assert rows[0]["section_summaries"]["game_log"]["top_rows"][0]["game_date"] == "2026-01-01"
    assert "does not grade correctness" in markdown
    assert "Backend `ok` means the query returned a structured backend result" in markdown
    assert "These are backend execution/result counts, not correctness counts." in markdown
    assert "A count of zero does not mean every answer is semantically correct." in markdown
    assert "Do not treat every backend `ok` as correct." in markdown
    query_pos = markdown.index(f"**QueryResponse.query:** `{ok_query}`")
    answer_pos = markdown.index(
        "**ResultHero.sentence / search_box_preview.answer_line:** The Lakers went 2-1 on the road."
    )
    section_pos = markdown.index(
        "**ResultTable / result.sections:** `result.sections.summary` "
        "(`1` row(s), `hero_or_summary`, `4` column(s))"
    )
    details_pos = markdown.index("<summary>Supporting details</summary>")
    assert query_pos < answer_pos < section_pos < details_pos
    assert "<details>" in markdown
    assert "Search Box Preview" in markdown
    assert "Display shape: `Team Record` (`team_record`)" in markdown
    assert "Primary section: `result.sections.summary`" in markdown
    assert "Visible sections/tables:" in markdown
    assert "Reviewer status:" in markdown
    assert "Raw QA promotion draft:" in markdown
    assert "The Lakers went 2-1 on the road." in markdown
    assert "2026-01-02" not in markdown


def test_slice_review_writes_slice_metadata_and_nested_reports(tmp_path, monkeypatch) -> None:
    slice_query = "Luka Doncic stats last 10 games"
    other_query = "LeBron James stats last 5 games"
    manifest_path = tmp_path / "qa/exploratory/manifest.yaml"
    slice_path = tmp_path / "qa/exploratory/slices/001_player_last_n.yaml"
    _write_text(
        manifest_path,
        """
slices:
  - id: 001_player_last_n
    file: slices/001_player_last_n.yaml
    status: pending_review
""".lstrip(),
    )
    _write_text(
        slice_path,
        f"""
id: 001_player_last_n
description: Player last-N game summaries
review_goal: Check player name parsing and last-N filters.
samples:
  - id: luka_last_10
    query: "{slice_query}"
  - id: lebron_last_5
    query: "{other_query}"
""".lstrip(),
    )

    resolved_path = review.resolve_slice_path(
        slice_id="001_player_last_n",
        manifest_path=manifest_path,
        slices_root=tmp_path / "qa/exploratory/slices",
    )
    _version, samples, slice_metadata = review.load_slice(
        resolved_path,
        requested_slice_id="001_player_last_n",
    )

    assert resolved_path == slice_path
    assert [sample["id"] for sample in samples] == ["luka_last_10", "lebron_last_5"]
    assert slice_metadata == {
        "slice_id": "001_player_last_n",
        "slice_description": "Player last-N game summaries",
        "slice_review_goal": "Check player name parsing and last-N filters.",
        "input_slice_path": str(slice_path),
        "slice_sample_count": 2,
    }

    payloads = {
        slice_query: _payload(
            query=slice_query,
            route="player_game_summary",
            status="ok",
            query_class="summary",
            sections={
                "summary": [{"player_name": "Luka Doncic", "games": 10}],
                "game_log": [{"game_date": "2026-01-01", "player_name": "Luka Doncic"}],
            },
            filters=[{"kind": "window", "label": "Last N games", "value": 10}],
        ),
        other_query: _payload(
            query=other_query,
            route="player_game_summary",
            status="ok",
            query_class="summary",
            sections={
                "summary": [{"player_name": "LeBron James", "games": 5}],
                "game_log": [{"game_date": "2026-01-01", "player_name": "LeBron James"}],
            },
            filters=[{"kind": "window", "label": "Last N games", "value": 5}],
        ),
    }

    monkeypatch.setattr(review, "execute_query_payload", lambda query: payloads[query])

    result = review.run_review(
        input_path=resolved_path,
        out_base=tmp_path / "out",
        run_id="review",
        overwrite_run_id=False,
        limit=1,
        top_rows=1,
        samples=samples,
        slice_metadata=slice_metadata,
    )

    run_dir = result["run_dir"]
    summary = json.loads((run_dir / "summary.json").read_text())
    rows = [json.loads(line) for line in (run_dir / "report.jsonl").read_text().splitlines()]
    markdown = (run_dir / "report.md").read_text()

    assert run_dir == tmp_path / "out/archive/runs/review__001_player_last_n"
    assert (tmp_path / "out/latest/report.md").read_text() == markdown
    assert (tmp_path / "out/latest_by_slice/001_player_last_n/report.md").read_text() == markdown
    index = (tmp_path / "out/index.md").read_text()
    assert "`review`" in index
    assert "`001_player_last_n`" in index
    assert "archive/runs/review__001_player_last_n/report.md" in index
    readme = (tmp_path / "out/README.md").read_text()
    assert "latest/report.md" in readme
    assert "Backend `ok` means a structured result was returned" in readme
    assert summary["slice_id"] == "001_player_last_n"
    assert summary["slice_description"] == "Player last-N game summaries"
    assert summary["slice_review_goal"] == "Check player name parsing and last-N filters."
    assert summary["input_slice_path"] == str(slice_path)
    assert summary["slice_sample_count"] == 2
    assert summary["case_count"] == 1
    assert rows[0]["slice_id"] == "001_player_last_n"
    assert rows[0]["slice_sample_count"] == 2
    assert rows[0]["id"] == "luka_last_10"
    assert "This is an exploratory slice report." in markdown
    assert "Slice ID: `001_player_last_n`" in markdown
    assert "Slice sample count: `2`" in markdown
    assert slice_query in markdown
    assert other_query not in markdown

    stale_path = run_dir / "stale.txt"
    stale_path.write_text("old")
    second = review.run_review(
        input_path=resolved_path,
        out_base=tmp_path / "out",
        run_id="review",
        overwrite_run_id=True,
        limit=1,
        top_rows=1,
        samples=samples,
        slice_metadata=slice_metadata,
    )

    assert second["run_dir"] == run_dir
    assert not stale_path.exists()


def test_player_last_n_summary_classifies_as_search_box_recent_games() -> None:
    query = "Luka stats last 10 games"
    payload = _payload(
        query=query,
        route="player_game_summary",
        status="ok",
        query_class="summary",
        sections={
            "summary": [{"player_name": "Luka Doncic", "pts_avg": 31.4}],
            "by_season": [{"season": "2025-26", "pts_avg": 31.4}],
            "game_log": [{"game_date": "2026-01-01", "player_name": "Luka Doncic"}],
        },
    )
    preview = review.build_search_box_preview(
        query=query,
        route=payload["route"],
        result_status=payload["result_status"],
        result_reason=payload["result_reason"],
        query_class="summary",
        answer_text=None,
        answer_text_source=None,
        answer_summary="Luka Doncic -- 10 games, 31.4 PPG",
        metadata=payload["result"]["metadata"],
        sections=payload["result"]["sections"],
        section_summaries=review.build_section_summaries(
            payload["result"]["sections"],
            top_rows=1,
        ),
    )

    assert preview["display_shape"]["key"] == "entity_summary_with_gamelog"
    assert preview["display_shape"]["name"] == "Entity Summary + Recent Games"
    assert preview["renderer_patterns"] == [
        {"type": "entity_summary", "section_key": "summary"},
        {
            "type": "game_log",
            "section_key": "game_log",
            "summary_key": "summary",
            "show_summary_strip": False,
        },
    ]
    assert preview["visible_sections"][2]["name"] == "game_log"
    assert preview["visible_sections"][2]["row_count"] == 1
    assert preview["primary_section"]["name"] == "game_log"
    assert preview["primary_section"]["kind"] == "table"


def test_named_run_requires_overwrite_for_existing_directory(tmp_path) -> None:
    input_path = tmp_path / "samples.json"
    _write_json(input_path, {"samples": []})
    out_base = tmp_path / "out"

    first = review.run_review(
        input_path=input_path,
        out_base=out_base,
        run_id="latest",
        overwrite_run_id=False,
        limit=None,
        top_rows=1,
    )
    stale_path = first["run_dir"] / "stale.txt"
    stale_path.write_text("old")

    with pytest.raises(ValueError, match="already exists"):
        review.run_review(
            input_path=input_path,
            out_base=out_base,
            run_id="latest",
            overwrite_run_id=False,
            limit=None,
            top_rows=1,
        )

    second = review.run_review(
        input_path=input_path,
        out_base=out_base,
        run_id="latest",
        overwrite_run_id=True,
        limit=None,
        top_rows=1,
    )

    assert second["run_dir"] == first["run_dir"]
    assert not stale_path.exists()
    assert (second["run_dir"] / "report.md").exists()


def test_scratch_run_ids_route_under_smoke_or_debug(tmp_path) -> None:
    input_path = tmp_path / "samples.json"
    _write_json(input_path, {"samples": []})

    smoke = review.run_review(
        input_path=input_path,
        out_base=tmp_path / "out",
        run_id="codex_slice_smoke",
        overwrite_run_id=False,
        limit=None,
        top_rows=1,
    )
    debug = review.run_review(
        input_path=input_path,
        out_base=tmp_path / "out",
        run_id="codex_result_terms_audit",
        overwrite_run_id=False,
        limit=None,
        top_rows=1,
    )

    assert smoke["run_dir"] == tmp_path / "out/archive/smoke/codex_slice_smoke"
    assert debug["run_dir"] == tmp_path / "out/archive/debug/codex_result_terms_audit"
    assert not (tmp_path / "out/codex_slice_smoke").exists()
    assert not (tmp_path / "out/codex_result_terms_audit").exists()


def test_organize_existing_outputs_moves_top_level_runs_without_deleting(tmp_path) -> None:
    out_base = tmp_path / "out"
    _write_text(out_base / "20260607T072615Z/report.md", "full report")
    _write_text(out_base / "20260607T072615Z/summary.json", json.dumps({"case_count": 1}))
    _write_text(out_base / "20260607T072615Z/report.jsonl", "{}\n")
    _write_text(out_base / "20260607T072530Z/001_player_last_n/report.md", "slice report")
    _write_text(
        out_base / "20260607T072530Z/001_player_last_n/summary.json",
        json.dumps({"case_count": 2, "slice_id": "001_player_last_n"}),
    )
    _write_text(out_base / "20260607T072530Z/001_player_last_n/report.jsonl", "{}\n")
    _write_text(out_base / "codex_slice_smoke/001_player_last_n/report.md", "smoke report")
    _write_text(out_base / "codex_result_terms_audit/report.md", "debug report")
    _write_text(out_base / "latest/report.md", "latest report")

    moved = review.organize_existing_outputs(out_base)

    assert moved
    assert (out_base / "archive/runs/20260607T072615Z__all/report.md").read_text() == (
        "full report"
    )
    assert (
        out_base / "archive/runs/20260607T072530Z__001_player_last_n/report.md"
    ).read_text() == "slice report"
    assert (
        out_base / "archive/smoke/codex_slice_smoke/001_player_last_n/report.md"
    ).read_text() == "smoke report"
    assert (out_base / "archive/debug/codex_result_terms_audit/report.md").read_text() == (
        "debug report"
    )
    assert (out_base / "latest/report.md").read_text() == "latest report"
    assert sorted(path.name for path in out_base.iterdir()) == [
        "README.md",
        "archive",
        "index.md",
        "latest",
        "latest_by_slice",
    ]
