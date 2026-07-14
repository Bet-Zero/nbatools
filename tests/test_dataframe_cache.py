from __future__ import annotations

import json
import subprocess
import sys
import textwrap
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock

import pandas as pd
import pytest

from nbatools.commands import data_utils
from nbatools.dataframe_cache import BoundedDataFrameCache

pytestmark = pytest.mark.engine


def _frame(values: int) -> pd.DataFrame:
    return pd.DataFrame({"value": range(values)})


def test_entry_budget_evicts_least_recently_used_frame() -> None:
    cache = BoundedDataFrameCache(max_entries=2, max_bytes=1_000_000)
    loads: list[str] = []

    def load(key: str) -> pd.DataFrame:
        loads.append(key)
        return _frame(10)

    first = cache.get_or_load("first", lambda: load("first"))
    cache.get_or_load("second", lambda: load("second"))
    assert cache.get_or_load("first", lambda: load("first-again")) is first
    cache.get_or_load("third", lambda: load("third"))
    cache.get_or_load("second", lambda: load("second-reloaded"))

    info = cache.info()
    assert loads == ["first", "second", "third", "second-reloaded"]
    assert info.current_entries == 2
    assert info.evictions == 2
    assert info.hits == 1


def test_byte_budget_evicts_and_skips_oversize_frames() -> None:
    small = _frame(100)
    small_bytes = int(small.memory_usage(index=True, deep=True).sum())
    cache = BoundedDataFrameCache(max_entries=10, max_bytes=small_bytes * 2)

    cache.get_or_load("one", lambda: small)
    cache.get_or_load("two", lambda: small.copy())
    cache.get_or_load("three", lambda: small.copy())
    cache.get_or_load("oversize", lambda: _frame(10_000))

    info = cache.info()
    assert info.current_entries == 2
    assert info.current_bytes <= info.max_bytes
    assert info.evictions == 1
    assert info.oversize_skips == 1


def test_concurrent_same_key_load_is_coalesced() -> None:
    cache = BoundedDataFrameCache(max_entries=4, max_bytes=1_000_000)
    calls = 0

    def loader() -> pd.DataFrame:
        nonlocal calls
        calls += 1
        time.sleep(0.05)
        return _frame(100)

    with ThreadPoolExecutor(max_workers=8) as executor:
        frames = list(executor.map(lambda _: cache.get_or_load("shared", loader), range(8)))

    assert calls == 1
    assert all(frame is frames[0] for frame in frames)
    info = cache.info()
    assert info.misses == 1
    assert info.coalesced == 7
    assert info.current_entries == 1


def test_cache_load_failure_is_shared_and_retryable() -> None:
    cache = BoundedDataFrameCache(max_entries=4, max_bytes=1_000_000)
    calls = 0

    def failing_loader() -> pd.DataFrame:
        nonlocal calls
        calls += 1
        time.sleep(0.05)
        raise ValueError("broken frame")

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(cache.get_or_load, "shared", failing_loader) for _ in range(4)]
        for future in futures:
            with pytest.raises(ValueError, match="broken frame"):
                future.result()

    recovered = cache.get_or_load("shared", lambda: _frame(2))
    assert calls == 1
    assert recovered["value"].tolist() == [0, 1]


def test_clear_isolates_post_clear_caller_from_inflight_load() -> None:
    cache = BoundedDataFrameCache(max_entries=4, max_bytes=1_000_000)
    old_started = Event()
    release_old = Event()

    def load_old() -> pd.DataFrame:
        old_started.set()
        assert release_old.wait(timeout=2)
        return pd.DataFrame({"value": ["old"]})

    with ThreadPoolExecutor(max_workers=2) as executor:
        old_future = executor.submit(cache.get_or_load, "shared", load_old)
        assert old_started.wait(timeout=2)

        cache.clear()
        post_clear = cache.get_or_load("shared", lambda: pd.DataFrame({"value": ["new"]}))
        release_old.set()
        pre_clear = old_future.result(timeout=2)

    assert pre_clear["value"].tolist() == ["old"]
    assert post_clear["value"].tolist() == ["new"]
    retained = cache.get_or_load("shared", lambda: pd.DataFrame({"value": ["wrong"]}))
    assert retained["value"].tolist() == ["new"]
    info = cache.info()
    assert info.current_entries == 1
    assert info.misses == 1
    assert info.hits == 1


def test_public_loader_reuses_overlapping_seasons_and_returns_caller_owned_frames(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = BoundedDataFrameCache(max_entries=8, max_bytes=1_000_000)
    reads: Counter[str] = Counter()

    monkeypatch.setattr(data_utils, "FRAME_CACHE", cache)
    monkeypatch.setattr(data_utils, "data_source_cache_key", lambda: "generation-one")
    monkeypatch.setattr(data_utils, "data_exists", lambda _: True)

    def read_csv(path: str) -> pd.DataFrame:
        reads[path] += 1
        season = path.rsplit("/", 1)[-1].split("_", 1)[0]
        return pd.DataFrame({"season": [season], "value": [reads[path]]})

    monkeypatch.setattr(data_utils, "data_read_csv", read_csv)

    first = data_utils.load_team_games_for_seasons(["2022-23", "2023-24"], "Regular Season")
    second = data_utils.load_team_games_for_seasons(["2023-24", "2024-25"], "Regular Season")

    first.loc[first["season"] == "2022-23", "value"] = 999
    second.loc[second["season"] == "2023-24", "value"] = 999
    reloaded = data_utils.load_team_games_for_seasons(["2022-23", "2023-24"], "Regular Season")

    assert reads == {
        "data/raw/team_game_stats/2022-23_regular_season.csv": 1,
        "data/raw/team_game_stats/2023-24_regular_season.csv": 1,
        "data/raw/team_game_stats/2024-25_regular_season.csv": 1,
    }
    assert reloaded.to_dict("records") == [
        {"season": "2022-23", "value": 1},
        {"season": "2023-24", "value": 1},
    ]
    info = cache.info()
    assert info.current_entries == 3
    assert info.current_bytes <= info.max_bytes
    assert info.misses == 3
    assert info.hits == 3


def test_public_loader_obeys_entry_budget_and_evicts_oldest_season(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = BoundedDataFrameCache(max_entries=2, max_bytes=1_000_000)
    reads: Counter[str] = Counter()

    monkeypatch.setattr(data_utils, "FRAME_CACHE", cache)
    monkeypatch.setattr(data_utils, "data_source_cache_key", lambda: "generation-one")
    monkeypatch.setattr(data_utils, "data_exists", lambda _: True)

    def read_csv(path: str) -> pd.DataFrame:
        reads[path] += 1
        return pd.DataFrame({"path": [path]})

    monkeypatch.setattr(data_utils, "data_read_csv", read_csv)

    for season in ("2021-22", "2022-23", "2023-24"):
        data_utils.load_team_games_for_seasons([season], "Regular Season")
    data_utils.load_team_games_for_seasons(["2021-22"], "Regular Season")

    info = cache.info()
    assert info.current_entries == 2
    assert info.current_bytes <= info.max_bytes
    assert info.evictions == 2
    assert reads["data/raw/team_game_stats/2021-22_regular_season.csv"] == 2


def test_strict_public_loader_preserves_all_missing_season_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(data_utils, "data_source_cache_key", lambda: "generation-one")
    monkeypatch.setattr(data_utils, "data_exists", lambda _: False)

    with pytest.raises(FileNotFoundError) as excinfo:
        data_utils.load_player_game_period_stats_for_seasons(
            ["2022-23", "2023-24"], "Regular Season"
        )

    assert str(excinfo.value) == (
        "Missing player_game_period_stats files for requested slice: "
        "data/raw/player_game_period_stats/2022-23_regular_season.csv, "
        "data/raw/player_game_period_stats/2023-24_regular_season.csv"
    )


def test_public_loader_coalesces_concurrent_season_reads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = BoundedDataFrameCache(max_entries=4, max_bytes=1_000_000)
    calls = 0
    calls_lock = Lock()

    monkeypatch.setattr(data_utils, "FRAME_CACHE", cache)
    monkeypatch.setattr(data_utils, "data_source_cache_key", lambda: "generation-one")
    monkeypatch.setattr(data_utils, "data_exists", lambda _: True)

    def read_csv(_: str) -> pd.DataFrame:
        nonlocal calls
        with calls_lock:
            calls += 1
        time.sleep(0.05)
        return pd.DataFrame({"season": ["2024-25"]})

    monkeypatch.setattr(data_utils, "data_read_csv", read_csv)

    with ThreadPoolExecutor(max_workers=8) as executor:
        frames = list(
            executor.map(
                lambda _: data_utils.load_team_games_for_seasons(["2024-25"], "Regular Season"),
                range(8),
            )
        )

    assert calls == 1
    assert all(frame.to_dict("records") == [{"season": "2024-25"}] for frame in frames)
    assert len({id(frame) for frame in frames}) == 8
    info = cache.info()
    assert info.misses == 1
    assert info.coalesced == 7
    assert info.current_entries == 1


def test_bounded_cache_subprocess_rss_budget() -> None:
    script = textwrap.dedent(
        """
        import json
        import resource
        import sys

        import pandas as pd

        from nbatools.dataframe_cache import BoundedDataFrameCache

        def rss_bytes():
            value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            return int(value if sys.platform == "darwin" else value * 1024)

        cache = BoundedDataFrameCache(max_entries=2, max_bytes=12 * 1024 * 1024)
        baseline = rss_bytes()
        for index in range(40):
            cache.get_or_load(index, lambda index=index: pd.DataFrame({"value": range(500_000)}))
        info = cache.info()
        print(json.dumps({
            "rss_growth": rss_bytes() - baseline,
            "entries": info.current_entries,
            "bytes": info.current_bytes,
            "evictions": info.evictions,
        }))
        """
    )

    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert result["entries"] <= 2
    assert result["bytes"] <= 12 * 1024 * 1024
    assert result["evictions"] >= 38
    assert result["rss_growth"] < 96 * 1024 * 1024
