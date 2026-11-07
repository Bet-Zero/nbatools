"""Private Mac runtime preparation for the existing finite laptop collector.

This standard-library bootstrap also runs on macOS's older Python 3.9. It never
contacts NBA, installs globally, deletes an environment or retries a source job.
"""

import hashlib
import json
import os
import shutil
import subprocess
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REQUEST = None  # Embedded by build_owner_bundle; never supplied by the owner.
NBA_API = "1.11.4"  # Same SDK as the retained cloud parameter preflight.
PROBE = """import sys, runpy, json
from importlib.metadata import version
assert (3, 11) <= sys.version_info[:2] <= (3, 13), 'Unsupported Python'
scope = runpy.run_path(sys.argv[1], run_name='offline_environment_check')
assert scope['validate_request'](scope['EMBEDDED_REQUEST']) == scope['EMBEDDED_SHA256']
installed = version('nba_api')
for job in scope['EMBEDDED_REQUEST']['jobs']:
    scope['_client'](job)  # get_request=False; validates every exact SDK parameter.
print(json.dumps({'python': sys.version.split()[0], 'nba_api': installed}))
"""


def candidates(root):
    """Finite known locations, including the earlier local/parent venv approach."""
    values = [root / ".nba-tools-env/bin/python"]
    if os.environ.get("VIRTUAL_ENV"):
        values.append(Path(os.environ["VIRTUAL_ENV"]) / "bin/python")
    for folder in (root, root.parent):
        for name in (".venv", "venv", ".nba-tools-env"):
            values.append(folder / name / "bin/python")
    for name in ("python3.11", "python3.12", "python3.13", "python3", "python"):
        located = shutil.which(name)
        if located:
            values.append(Path(located))
    for prefix in (Path("/opt/homebrew"), Path("/usr/local")):
        for minor in (11, 12, 13):
            values.extend(
                (
                    prefix / f"bin/python3.{minor}",
                    prefix / f"opt/python@3.{minor}/bin/python3.{minor}",
                )
            )
    for minor in (11, 12, 13):
        values.append(Path(f"/Library/Frameworks/Python.framework/Versions/3.{minor}/bin/python3"))
    # Find retained sibling capture environments without recursively crawling home.
    for folder in sorted(root.parent.iterdir())[:100]:
        if folder.is_dir() and not folder.is_symlink():
            for name in (".venv", "venv", ".nba-tools-env"):
                path = folder / name / "bin/python"
                if path.is_file():
                    values.append(path)
    seen = set()
    for path in values:
        # Keep venv paths intact: resolving symlinks would lose their isolation.
        key = str(path.absolute())
        if key == "/usr/bin/python3" and not Path("/Library/Developer/CommandLineTools").is_dir():
            continue
        if key not in seen and path.is_file() and os.access(path, os.X_OK):
            seen.add(key)
            yield key


def run(arguments, timeout):
    return subprocess.run(arguments, capture_output=True, text=True, timeout=timeout)


def probe(runtime, script):
    try:
        result = run([runtime, "-I", "-c", PROBE, str(script)], 15)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return None


def prepare(root, diagnostics):
    script = root / "run_capture.py"
    compatible = None
    started = time.monotonic()
    for runtime in candidates(root):
        if time.monotonic() - started > 120:
            break
        details = probe(runtime, script)
        if details:
            diagnostics.update(status="existing_environment_ready", **details)
            return runtime
        try:
            result = run(
                [
                    runtime,
                    "-I",
                    "-c",
                    "import sys, venv; assert (3,11) <= sys.version_info[:2] <= (3,13)",
                ],
                10,
            )
            if result.returncode == 0 and compatible is None:
                compatible = runtime
        except (OSError, subprocess.SubprocessError):
            pass
    if compatible is None:
        raise RuntimeError("NoCompatiblePython311To313")
    environment = root / ".nba-tools-env"
    if environment.exists() or environment.is_symlink():
        # Never replace, repair or delete an existing environment automatically.
        raise RuntimeError("ExistingPrivateEnvironmentUnusable")
    print("Preparing a private Python environment in this folder. Please wait.", flush=True)
    result = run([compatible, "-I", "-m", "venv", str(environment)], 60)
    if result.returncode:
        diagnostics["setup_exit_code"] = result.returncode
        raise RuntimeError("PrivateEnvironmentCreationFailed")
    runtime = str(environment / "bin/python")
    result = run(
        [
            runtime,
            "-I",
            "-m",
            "pip",
            "--isolated",
            "install",
            "--index-url",
            "https://pypi.org/simple",
            "--disable-pip-version-check",
            "--no-input",
            "--only-binary=:all:",
            "--retries",
            "0",
            "--timeout",
            "15",
            f"nba_api=={NBA_API}",
        ],
        180,
    )
    if result.returncode:
        diagnostics["setup_exit_code"] = result.returncode
        raise RuntimeError("PrivateDependencyInstallationFailed")
    details = probe(runtime, script)
    if not details:
        raise RuntimeError("PrivateEnvironmentPreflightFailed")
    diagnostics.update(status="private_environment_ready", **details)
    return runtime


def failure_receipt(root, diagnostics):
    """Existing data-only transfer protocol, with zero attempts and no source rows."""
    output = root / "readiness-capture"
    if output.exists() or output.is_symlink():
        print("Existing capture preserved; return its collection.zip. No requests made.")
        return
    output.mkdir()
    (output / "sources").mkdir()
    request_sha = hashlib.sha256(
        json.dumps(REQUEST, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    report = dict(
        classification="unvalidated_laptop_source_capture_not_publication",
        source="NBA Stats",
        captured_at=datetime.now(timezone.utc).isoformat(),  # noqa: UP017 - bootstrap supports Python3.8
        parameters="exact fixed request; no requests attempted",
        request=REQUEST,
        request_sha256=request_sha,
        nba_api_version=None,
        attempts=[],
        production_writes=0,
        canonical_period_accepted=False,
        transport_finished=False,
        stop_reason="environment_setup_failed_return_output_do_not_retry",
        error_type="EnvironmentSetupError",
        environment=diagnostics,
        unattempted_jobs=REQUEST["jobs"],
    )
    raw = (json.dumps(report, indent=2) + "\n").encode()
    files = {}
    for name in ("acquisition.json", "sources/capture-attempt.json"):
        (output / name).write_bytes(raw)
        files[name] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    manifest = dict(
        schema_version=1,
        classification="unvalidated_development_collection",
        request=REQUEST,
        request_sha256=request_sha,
        files=files,
        production_writes=0,
    )
    with zipfile.ZipFile(output / "collection.zip", "x", zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            archive.write(output / name, name)
        archive.writestr("collection-manifest.json", json.dumps(manifest, indent=2) + "\n")


def main():
    root = Path(__file__).absolute().parent
    diagnostics = {
        "stage": "environment_preflight",
        "nba_requests_attempted": 0,
        "production_writes": 0,
    }
    try:
        # An existing result is custody evidence, never an invitation to repair/retry.
        if (root / "readiness-capture").exists() or (root / "readiness-capture").is_symlink():
            print("Existing capture preserved. Return readiness-capture/collection.zip.")
            return 1
        runtime = prepare(root, diagnostics)
    except Exception as exc:
        diagnostics.update(status="failed", error_type=type(exc).__name__, reason=str(exc)[:120])
        failure_receipt(root, diagnostics)
        print("Environment setup stopped safely. Return readiness-capture/collection.zip.")
        return 1
    print("Environment verified; starting the fixed collection.", flush=True)
    # One collector invocation only. Its existing timeout/body/receipt protections own transport.
    return subprocess.call([runtime, "-I", str(root / "run_capture.py")], cwd=str(root))


if __name__ == "__main__":
    raise SystemExit(main())
