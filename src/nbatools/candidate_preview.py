"""Read-only, deployment-scoped candidate pin and cold-load evidence.

No HTTP parameter selects data. The nonsecret pin is set only in a reviewed,
protected preview deployment; a production deployment carrying it fails closed.
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from contextvars import ContextVar, copy_context

MANIFEST_ENV = "NBATOOLS_PREVIEW_CANDIDATE_MANIFEST"
_worker = uuid.uuid4().hex
_requests = 0
_current = ContextVar("candidate_cold_qualification", default=None)


def verify_pin(source, generation):
    expected = os.environ.get(MANIFEST_ENV, "")
    if MANIFEST_ENV not in os.environ:
        return
    from nbatools.data_source import (
        DataSourceConfigError,
        DataSourceError,
        _Generation,
        _R2DataSource,
        validate_data_generation_id,
    )

    if (
        os.environ.get("VERCEL_ENV") != "preview"
        or not isinstance(source, _R2DataSource)
        or os.environ.get("NBATOOLS_DATA_GENERATION") != generation
        or not re.fullmatch(r"[0-9a-f]{64}", expected)
    ):
        raise DataSourceConfigError("Candidate pin requires an explicit R2 preview deployment")
    try:
        source.verified_manifest(_Generation(validate_data_generation_id(generation), expected))
    except (DataSourceError, FileNotFoundError) as exc:
        raise DataSourceConfigError(
            "Preview candidate manifest checksum or inventory differs"
        ) from exc
    return expected


class ColdQualification:
    """Request-local preview headers; no production payload/behavior changes."""

    def __enter__(self):
        self.headers = {}
        self.token = None
        if MANIFEST_ENV not in os.environ:
            return self
        from nbatools.data_source import _get_data_source
        from nbatools.dataframe_cache import FRAME_CACHE

        global _requests
        _requests += 1
        source = _get_data_source()
        generation = os.environ.get("NBATOOLS_DATA_GENERATION", "")
        self.start = time.monotonic()
        self.evidence = dict(
            worker=_worker,
            invocation=_requests,
            generation=generation,
            manifest_sha256=os.environ[MANIFEST_ENV],
            frame_entries_before=FRAME_CACHE.info().current_entries,
            disk_cache_empty=not (source.cache_root / generation).exists(),
            appearance_loads=0,
            appearance_loads_completed=0,
        )
        # Verification is part of the timed request and cannot warm source data.
        verify_pin(source, generation)
        self.token = _current.set(self.evidence)
        return self

    def __exit__(self, kind, value, traceback):
        if self.token is not None:
            _current.reset(self.token)
            self.evidence["elapsed_ms"] = round((time.monotonic() - self.start) * 1000)
            self.evidence["succeeded"] = kind is None
            self.headers["X-NBATools-Candidate-Qualification"] = json.dumps(
                self.evidence, separators=(",", ":")
            )


def appearance_load_event(*, completed=False):
    evidence = _current.get()
    if evidence is not None:
        key = "appearance_loads_completed" if completed else "appearance_loads"
        evidence[key] += 1


def bind_qualification(callback):
    """Carry only enabled preview tracing through the admitted query executor."""
    if _current.get() is None:
        return callback
    context = copy_context()
    return lambda: context.run(callback)
