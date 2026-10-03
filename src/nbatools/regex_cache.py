"""Keep the engine's regular expressions compiled across queries.

Parsing one query builds over a thousand distinct patterns (many per known
player or team name), more than the standard library's 512-entry ``re`` cache.
The cache then evicts in a cycle and every query recompiles nearly all of them,
which is most of the parse time. A larger cache keeps them compiled for the
life of the process. ``re._MAXCACHE`` is read at call time on Python 3.11
through 3.13; if a future version drops it, this is a no-op and only speed is
affected.
"""

from __future__ import annotations

import re

ENGINE_REGEX_CACHE_SIZE = 32_768


def ensure_regex_cache_capacity(size: int = ENGINE_REGEX_CACHE_SIZE) -> None:
    current = getattr(re, "_MAXCACHE", None)
    if isinstance(current, int) and current < size:
        re._MAXCACHE = size  # type: ignore[attr-defined]
