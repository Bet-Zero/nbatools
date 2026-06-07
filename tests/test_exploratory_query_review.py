import json

import pytest

from tools import exploratory_query_review as review


def _write_json(path, data) -> None:
    path.write_text(json.dumps(data) + "\n")


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

    assert summary["case_count"] == 3
    assert summary["result_status_counts"] == {"error": 1, "no_result": 1, "ok": 1}
    assert summary["route_counts"] == {"<none>": 1, "season_leaders": 1, "team_record": 1}
    assert summary["query_class_counts"] == {"<none>": 1, "leaderboard": 1, "summary": 1}
    assert summary["no_result_case_ids"] == ["no_result_case"]
    assert summary["error_case_ids"] == ["exception_case"]
    assert summary["suspicious_case_count"] == 0
    assert summary["review_flag_counts"] == {"exception": 1, "no_result": 1}
    assert rows[0]["payload"]["route"] == "team_record"
    assert len(rows[0]["section_summaries"]["game_log"]["top_rows"]) == 1
    assert rows[0]["section_summaries"]["game_log"]["top_rows"][0]["game_date"] == "2026-01-01"
    assert "Reviewer status:" in markdown
    assert "Raw QA promotion draft:" in markdown
    assert "The Lakers went 2-1 on the road." in markdown
    assert "2026-01-02" not in markdown


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
