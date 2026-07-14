from __future__ import annotations

from pathlib import Path

import pytest

import nbatools.query_service as query_service
from nbatools.commands import entity_resolution
from nbatools.commands.structured_results import NoResult
from nbatools.data_source import (
    ACTIVE_GENERATION_PATH,
    DATA_GENERATION_ENV,
    LOCAL_DATA_ROOT_ENV,
    current_data_generation,
    data_source_cache_key,
    reset_data_source_cache,
)

pytestmark = pytest.mark.engine


def test_natural_and_structured_entrypoints_pin_one_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[tuple[str, str]] = []
    monkeypatch.setenv(DATA_GENERATION_ENV, "request-one")

    def fake_natural(query: str) -> query_service.QueryResult:
        observed.append(("natural-start", current_data_generation()))
        first_key = data_source_cache_key()
        monkeypatch.setenv(DATA_GENERATION_ENV, "request-two")
        observed.append(("natural-end", current_data_generation()))
        assert data_source_cache_key() == first_key
        return query_service.QueryResult(
            result=NoResult(query_class="unknown", reason="no_match"),
            query=query,
        )

    def fake_structured(route: str, **kwargs: object) -> query_service.QueryResult:
        observed.append(("structured", current_data_generation()))
        return query_service.QueryResult(
            result=NoResult(query_class="unknown", reason="no_match"),
            query=f"structured:{route}",
            route=route,
        )

    monkeypatch.setattr(query_service, "_execute_natural_query_in_generation", fake_natural)
    monkeypatch.setattr(
        query_service,
        "_execute_structured_query_in_generation",
        fake_structured,
    )

    query_service.execute_natural_query("anything")
    query_service.execute_structured_query("anything")

    assert observed == [
        ("natural-start", "request-one"),
        ("natural-end", "request-one"),
        ("structured", "request-two"),
    ]


def test_entity_cache_is_generation_keyed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(DATA_GENERATION_ENV, raising=False)
    monkeypatch.setenv(LOCAL_DATA_ROOT_ENV, str(tmp_path))
    pointer = tmp_path / "data" / ACTIVE_GENERATION_PATH
    pointer.parent.mkdir(parents=True)
    pointer.write_text('{"generation_id":"identity-one"}')
    for generation, player_id in (("identity-one", 101), ("identity-two", 202)):
        roster = tmp_path / "data" / "generations" / generation / "raw" / "rosters" / "2099-00.csv"
        roster.parent.mkdir(parents=True)
        roster.write_text(f"player_id,player_name\n{player_id},Same Player\n")
    reset_data_source_cache()
    query_service._player_identity_lookup.cache_clear()
    monkeypatch.setattr(
        query_service,
        "_execute_build_result",
        lambda route, kwargs, *args: NoResult(query_class="summary", reason="no_match"),
    )

    first = query_service.execute_structured_query("player_game_summary", player="Same Player")
    pointer.write_text('{"generation_id":"identity-two"}')
    second = query_service.execute_structured_query("player_game_summary", player="Same Player")

    assert first.metadata["player_context"] == {
        "player_id": 101,
        "player_name": "Same Player",
    }
    assert second.metadata["player_context"] == {
        "player_id": 202,
        "player_name": "Same Player",
    }


def test_parser_entity_index_is_generation_keyed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(DATA_GENERATION_ENV, raising=False)
    monkeypatch.setenv(LOCAL_DATA_ROOT_ENV, str(tmp_path))
    pointer = tmp_path / "data" / ACTIVE_GENERATION_PATH
    pointer.parent.mkdir(parents=True)
    pointer.write_text('{"generation_id":"players-one"}')
    for generation, player_name in (
        ("players-one", "Alpha Zorplin"),
        ("players-two", "Beta Zorplin"),
    ):
        games = (
            tmp_path
            / "data"
            / "generations"
            / generation
            / "raw"
            / "player_game_stats"
            / "2099-00_regular_season.csv"
        )
        games.parent.mkdir(parents=True)
        games.write_text(f"player_name\n{player_name}\n")
    reset_data_source_cache()
    entity_resolution.reset_player_index()

    first = entity_resolution.resolve_player("zorplin")
    pointer.write_text('{"generation_id":"players-two"}')
    second = entity_resolution.resolve_player("zorplin")

    assert first.resolved == "Alpha Zorplin"
    assert second.resolved == "Beta Zorplin"
