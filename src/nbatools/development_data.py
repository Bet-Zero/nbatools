"""Explicit, process-local selection of immutable provisional development data.

There is no environment flag or HTTP parameter that enables this selection.
Only the loopback development launcher (or a controlled test) opens this context.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

MANIFEST = Path("data/metadata/development_snapshot.json")
_UNAVAILABLE: ContextVar[tuple[str, ...]] = ContextVar("development_unavailable", default=())
_SELECTED: ContextVar[DevelopmentSnapshot | None] = ContextVar("development_snapshot", default=None)


class DevelopmentDataUnavailable(ValueError):
    """A consumed provisional file cannot support a complete calculation."""


def clear_query_issues() -> None:
    _UNAVAILABLE.set(())


def selected_snapshot() -> DevelopmentSnapshot | None:
    return _SELECTED.get()


def require_local_development() -> None:
    if (
        os.environ.get("VERCEL")
        or os.environ.get("VERCEL_ENV")
        or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
        or os.environ.get("ENVIRONMENT", "").lower() in {"preview", "production", "prod"}
        or os.environ.get("DATA_SOURCE", "local").lower() != "local"
    ):
        raise ValueError("Provisional snapshots require isolated local development")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def safe_file(root: Path, relative: str) -> Path:
    path = Path(relative)
    if (
        path.is_absolute()
        or "\\" in relative
        or ":" in relative
        or any(p in {"", ".", ".."} for p in relative.split("/"))
        or not relative.startswith("data/")
    ):
        raise ValueError("Unsafe development data path")
    target = root / path
    if any(p.is_symlink() for p in [target, *target.parents]):
        raise ValueError("Development data must not contain symlinks")
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("Development data escapes snapshot")
    return target


class DevelopmentSnapshot:
    def __init__(self, root: Path, manifest_sha256: str):
        require_local_development()
        self.root = root.resolve()
        raw = safe_file(self.root, MANIFEST.as_posix()).read_bytes()
        if sha256(raw) != manifest_sha256:
            raise ValueError("Development manifest hash mismatch")
        self.document = json.loads(raw)
        self.manifest_sha256 = manifest_sha256
        if (
            self.document.get("schema_version") != 1
            or self.document.get("quality") != "provisional"
            or not self.document.get("version")
            or not self.document.get("scope")
            or not self.document.get("source_evidence")
            or not self.document.get("validation_reports")
            or not isinstance(self.document.get("exceptions"), list)
        ):
            raise ValueError("Incomplete development snapshot contract")
        self.files = self.document["files"]
        if not self.files or not isinstance(self.files, dict):
            raise ValueError("Empty development snapshot")
        actual = {
            p.relative_to(self.root).as_posix()
            for p in (self.root / "data").rglob("*")
            if p.is_file() or p.is_symlink()
        }
        if actual != set(self.files) | {MANIFEST.as_posix()}:
            raise ValueError("Unmanifested or missing development files")
        for path in self.files:
            self._verified_path(path)

    @staticmethod
    def _relative(path: str | Path) -> str:
        text = str(path)
        return text if text.startswith("data/") else "data/" + text

    def _verified_path(self, path: str | Path) -> Path:
        require_local_development()
        relative = self._relative(path)
        if relative not in self.files:
            raise FileNotFoundError(f"Path absent from pinned development snapshot: {path}")
        target = safe_file(self.root, relative)
        if sha256(target.read_bytes()) != self.files[relative]:
            raise ValueError(f"Pinned development bytes changed: {relative}")
        return target

    def resolve_path(self, path: str | Path) -> Path:
        target = self._verified_path(path)
        if target.suffix == ".csv":
            import pandas as pd

            frame = pd.read_csv(target)
            # Conservative file-level guard covers direct pandas mean/sum/fill
            # paths as well as shared aggregators, before any row can disappear.
            numeric = frame.select_dtypes(include="number")
            nonmetrics = {"start_position", "comment", "jersey_number", "weight", "height"}
            if "/rosters/" in str(path) or "/teams/" in str(path):
                nonmetrics.update(numeric.columns)
            family = Path(self._relative(path)).parent.name
            if family == "games":
                # Canonical game identity deliberately leaves unsupported catalog
                # metadata blank. Pandas infers an all-blank text column as float;
                # this does not make it a statistical input to a record/count.
                nonmetrics.update(
                    {
                        "game_datetime",
                        "arena",
                        "city",
                        "attendance",
                        "overtime_periods",
                        "playoff_round",
                        "series_id",
                        "series_game_number",
                    }
                )
            elif family == "player_game_availability":
                nonmetrics.update({"source_comment", "identity_source_sha256"})
            numeric = numeric.drop(columns=list(nonmetrics & set(numeric.columns)))
            missing = numeric.isna()
            if family == "player_game_availability" and "source_minutes" in missing:
                # Explicit nonparticipation has no played clock. Leave the null
                # intact; played/unknown rows still cannot lose a numeric input.
                missing["source_minutes"] &= ~frame["participation_state"].eq("did_not_play")
            # A 0/0 shooting ratio has no attempts, rather than an unknown
            # source count. Preserve its null; complete counts still aggregate.
            for ratio, made, attempts in (
                ("fg_pct", "fgm", "fga"),
                ("fg3_pct", "fg3m", "fg3a"),
                ("ft_pct", "ftm", "fta"),
            ):
                if {ratio, made, attempts} <= set(numeric.columns):
                    missing[ratio] &= ~(numeric[made].eq(0) & numeric[attempts].eq(0))
            if missing.any().any():
                fields = list(missing.columns[missing.any()])
                message = f"Provisional input has unknown numeric fields: {fields}"
                _UNAVAILABLE.set((*_UNAVAILABLE.get(), message))
                raise DevelopmentDataUnavailable(message)
        return target

    def exists(self, path: str | Path) -> bool:
        if self._relative(path) not in self.files:
            return False
        self.resolve_path(path)
        return True

    def glob(self, pattern: str | Path) -> list[Path]:
        return [
            Path(p) for p in sorted(self.files) if fnmatch.fnmatchcase(p, self._relative(pattern))
        ]

    def status(self) -> dict:
        return {
            "state": "provisional",
            "snapshot": self.document["version"],
            "manifest_sha256": self.manifest_sha256,
            "scope": self.document["scope"],
            "source_evidence": self.document["source_evidence"],
            "exceptions": self.document["exceptions"],
            "validation_reports": self.document["validation_reports"],
            "fixture": self.document.get("fixture", False),
            "numerical_acceptance": False,
            "production_accepted": False,
        }


@contextmanager
def development_snapshot(root: Path, manifest_sha256: str):
    """Select a hash-bound snapshot without mutating process configuration."""
    snapshot = DevelopmentSnapshot(root, manifest_sha256)
    token = _SELECTED.set(snapshot)
    try:
        yield snapshot
    finally:
        _SELECTED.reset(token)


def label_result(result):
    snapshot = selected_snapshot()
    if snapshot is not None:
        if _UNAVAILABLE.get():
            from nbatools.commands.structured_results import NoResult

            result.result = NoResult(
                query_class="unknown",
                reason="no_data",
                result_status="no_result",
                result_reason="no_data",
                notes=list(dict.fromkeys(_UNAVAILABLE.get())),
            )
        result.metadata["data_quality"] = snapshot.status()
        notice = (
            f"PROVISIONAL development data — {snapshot.document['version']}; "
            f"{snapshot.document['scope']}. NBA accuracy is not certified. "
            f"Exceptions: {', '.join(snapshot.document['exceptions']) or 'qualification pending'}."
        )
        result.result.notes = [notice, *result.result.notes]
    return result
