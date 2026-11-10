"""Explicit, process-local selection of immutable provisional development data.

There is no environment flag or HTTP parameter that enables this selection.
Only the loopback development launcher (or a controlled test) opens this context.
"""

from __future__ import annotations

import fnmatch
import hashlib
import io
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

    def __init__(self, message: str):
        # A failed branch cannot disappear inside OR/count/result composition.
        if message not in _UNAVAILABLE.get():
            _UNAVAILABLE.set((*_UNAVAILABLE.get(), message))
        super().__init__(message)


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
            elif family == "player_game_starter_roles":
                # Successful trust checks deliberately have a blank text reason.
                # Required role flags and trust indicators stay numeric inputs.
                nonmetrics.add("role_validation_reason")
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

    def player_period_qualification(self, path: str | Path) -> dict | None:
        """Authenticate an optional, source-qualified dependency-reading companion.

        Old snapshots keep the original strict path behavior. A structural pass
        alone cannot qualify non-null values from an older provisional version.
        """
        relative = self._relative(path)
        if Path(relative).parent.as_posix() != "data/raw/player_game_period_stats":
            raise ValueError("Dependency reading is restricted to player-period inputs")
        target = self._verified_path(relative)  # Also executed before cache hits.
        reports = [
            r
            for r in self.document["validation_reports"]
            if r.get("kind") == "player_period_inputs" and r.get("dataset_path") == relative
        ]
        if not reports:
            return None
        if len(reports) != 1:
            raise ValueError("Ambiguous player-period qualification")
        record = reports[0]
        raw = self._verified_path(record["path"]).read_bytes()
        if sha256(raw) != record["sha256"]:
            raise ValueError("Player-period qualification hash mismatch")
        proof = json.loads(raw)
        from nbatools.commands.aggregate_metrics import METRIC_DESCRIPTORS, AggregationKind

        rates = {k for k, v in METRIC_DESCRIPTORS.items() if v.kind == AggregationKind.AVERAGE_ONLY}
        if (
            proof.get("schema_version") != 1
            or proof.get("kind") != "player_period_inputs"
            or proof.get("dataset_path") != relative
            or proof.get("dataset_sha256") != sha256(target.read_bytes())
            or set(proof.get("deferred_columns", [])) != rates
            or not proof.get("source_qualification")
        ):
            raise ValueError("Invalid player-period dependency qualification")
        parent_raw = self._verified_path(proof["origin_manifest_path"]).read_bytes()
        if sha256(parent_raw) != proof["origin_manifest_sha256"]:
            raise ValueError("Player-period origin manifest changed")
        parent = json.loads(parent_raw)
        if parent["files"].get(relative) != proof["dataset_sha256"]:
            raise ValueError("Qualified player-period origin differs")
        if any(self.files.get(p) != digest for p, digest in parent["files"].items()):
            raise ValueError("Dependency companion changed its qualified parent inputs")
        return proof

    def read_player_period_frame(self, path: str | Path):
        """Keep source rate nulls for checked consumers; expose no permissive path."""
        import numpy as np
        import pandas as pd

        proof = self.player_period_qualification(path)
        if proof is None:
            return pd.read_csv(self.resolve_path(path))  # Preserve old-version refusal.
        raw = self._verified_path(path).read_bytes()
        if sha256(raw) != proof["dataset_sha256"]:
            raise ValueError("Qualified player-period bytes changed")
        frame = pd.read_csv(io.BytesIO(raw))
        from nbatools.commands.aggregate_metrics import METRIC_DESCRIPTORS
        from nbatools.commands.pipeline.validate_raw import validate_player_game_period_stats_df

        numeric = set(METRIC_DESCRIPTORS) & set(frame)
        numeric.update(
            {
                "game_id",
                "team_id",
                "opponent_team_id",
                "player_id",
                "source_start_period",
                "source_end_period",
                "is_home",
                "is_away",
            }
        )
        deferred = set(proof["deferred_columns"])
        for field in numeric:
            if field not in frame:
                raise DevelopmentDataUnavailable(f"Missing required player-period input: {field}")
            values = pd.to_numeric(frame[field], errors="coerce")
            malformed = frame[field].notna() & values.isna()
            if malformed.any() or np.isinf(values).any():
                raise DevelopmentDataUnavailable(f"Invalid player-period numeric input: {field}")
            if field not in deferred and values.isna().any():
                raise DevelopmentDataUnavailable(f"Unknown required player-period input: {field}")
        for field in (
            "game_date",
            "season",
            "season_type",
            "player_name",
            "team_abbr",
            "opponent_team_abbr",
            "wl",
        ):
            if field not in frame or frame[field].isna().any():
                raise DevelopmentDataUnavailable(f"Unknown player-period identity/scope: {field}")
        if pd.to_datetime(frame.game_date, errors="coerce").isna().any():
            raise DevelopmentDataUnavailable("Invalid player-period date scope")
        validate_player_game_period_stats_df(frame)
        ot = frame.loc[frame.period_family.eq("overtime"), ["game_id", "team_id", "player_id"]]
        actual_ot = sorted([list(map(int, row)) for row in ot.itertuples(index=False, name=None)])
        if actual_ot != proof.get("overtime_player_keys"):
            raise DevelopmentDataUnavailable("Qualified overtime source population differs")
        return frame

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
