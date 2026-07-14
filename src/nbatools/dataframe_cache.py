"""Bounded process-local cache for immutable, generation-keyed DataFrames."""

from __future__ import annotations

import os
from collections import OrderedDict
from collections.abc import Callable, Hashable
from concurrent.futures import Future
from dataclasses import dataclass
from threading import RLock

import pandas as pd

FRAME_CACHE_MAX_ENTRIES_ENV = "NBATOOLS_FRAME_CACHE_MAX_ENTRIES"
FRAME_CACHE_MAX_BYTES_ENV = "NBATOOLS_FRAME_CACHE_MAX_BYTES"
DEFAULT_FRAME_CACHE_MAX_ENTRIES = 16
DEFAULT_FRAME_CACHE_MAX_BYTES = 128 * 1024 * 1024


@dataclass(frozen=True)
class FrameCacheInfo:
    """Snapshot of bounded-cache capacity and activity."""

    hits: int
    misses: int
    coalesced: int
    evictions: int
    oversize_skips: int
    current_entries: int
    current_bytes: int
    max_entries: int
    max_bytes: int


class BoundedDataFrameCache:
    """Thread-safe LRU bounded by both entry count and retained deep bytes."""

    def __init__(self, *, max_entries: int, max_bytes: int) -> None:
        if max_entries < 0:
            raise ValueError("max_entries must be nonnegative")
        if max_bytes < 0:
            raise ValueError("max_bytes must be nonnegative")
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self._entries: OrderedDict[Hashable, tuple[pd.DataFrame, int]] = OrderedDict()
        self._inflight: dict[tuple[int, Hashable], Future[pd.DataFrame]] = {}
        self._lock = RLock()
        self._current_bytes = 0
        self._hits = 0
        self._misses = 0
        self._coalesced = 0
        self._evictions = 0
        self._oversize_skips = 0
        self._epoch = 0

    def get_or_load(
        self,
        key: Hashable,
        loader: Callable[[], pd.DataFrame],
    ) -> pd.DataFrame:
        """Return a cached frame or coalesce one load for concurrent callers."""
        with self._lock:
            cached = self._entries.get(key)
            if cached is not None:
                self._entries.move_to_end(key)
                self._hits += 1
                return cached[0]

            load_epoch = self._epoch
            inflight_key = (load_epoch, key)
            future = self._inflight.get(inflight_key)
            if future is None:
                future = Future()
                self._inflight[inflight_key] = future
                self._misses += 1
                leader = True
            else:
                self._coalesced += 1
                leader = False

        if not leader:
            return future.result()

        try:
            frame = loader()
            if not isinstance(frame, pd.DataFrame):
                raise TypeError("DataFrame cache loaders must return pandas DataFrame values")
            frame_bytes = _frame_bytes(frame)
            with self._lock:
                if load_epoch == self._epoch:
                    self._store(key, frame, frame_bytes)
            future.set_result(frame)
            return frame
        except BaseException as exc:
            future.set_exception(exc)
            raise
        finally:
            with self._lock:
                self._inflight.pop(inflight_key, None)

    def clear(self) -> None:
        """Drop retained frames and reset counters without disrupting active loads."""
        with self._lock:
            self._entries.clear()
            self._current_bytes = 0
            self._hits = 0
            self._misses = 0
            self._coalesced = 0
            self._evictions = 0
            self._oversize_skips = 0
            self._epoch += 1

    def info(self) -> FrameCacheInfo:
        """Return a consistent cache-stat snapshot."""
        with self._lock:
            return FrameCacheInfo(
                hits=self._hits,
                misses=self._misses,
                coalesced=self._coalesced,
                evictions=self._evictions,
                oversize_skips=self._oversize_skips,
                current_entries=len(self._entries),
                current_bytes=self._current_bytes,
                max_entries=self.max_entries,
                max_bytes=self.max_bytes,
            )

    def _store(self, key: Hashable, frame: pd.DataFrame, frame_bytes: int) -> None:
        if self.max_entries == 0 or self.max_bytes == 0 or frame_bytes > self.max_bytes:
            self._oversize_skips += 1
            return

        while self._entries and (
            len(self._entries) >= self.max_entries
            or self._current_bytes + frame_bytes > self.max_bytes
        ):
            _, (_, evicted_bytes) = self._entries.popitem(last=False)
            self._current_bytes -= evicted_bytes
            self._evictions += 1

        self._entries[key] = (frame, frame_bytes)
        self._current_bytes += frame_bytes


def _frame_bytes(frame: pd.DataFrame) -> int:
    return int(frame.memory_usage(index=True, deep=True).sum())


def _env_nonnegative_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a nonnegative integer") from exc
    if value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


FRAME_CACHE = BoundedDataFrameCache(
    max_entries=_env_nonnegative_int(
        FRAME_CACHE_MAX_ENTRIES_ENV,
        DEFAULT_FRAME_CACHE_MAX_ENTRIES,
    ),
    max_bytes=_env_nonnegative_int(
        FRAME_CACHE_MAX_BYTES_ENV,
        DEFAULT_FRAME_CACHE_MAX_BYTES,
    ),
)


def frame_cache_info() -> FrameCacheInfo:
    """Return global query-loader cache statistics."""
    return FRAME_CACHE.info()


def clear_frame_cache() -> None:
    """Clear the global query-loader cache."""
    FRAME_CACHE.clear()
