"""Repair wrappers around the frozen PR600 collector; never change source jobs."""

import hashlib
import tempfile
import zipfile
from pathlib import Path

from tools import mac_capture_environment
from tools.collect_rollover_readiness_laptop import validate_request

ORIGINAL_SHA = "5156e94b425ded08573ca8138d53d4a9cfb35e2aa856d3a902c654b4bb5b3e44"
REQUEST_SHA = "19cc7759dd2dec7676888538b574e3dd316d6b58712b2b30d42c9b92911a9a52"
COLLECTOR_SHA = "97bb73b6473fb532b249fa1daaa7f9089541d5b39b5d555bfac4248f9dce83e9"
MAC = r"""#!/bin/sh
cd -- "$(dirname -- "$0")" || exit 1
# Finder has a minimal PATH. Never invoke the Apple developer-tools stub.
found=0
set --
if [ -n "${VIRTUAL_ENV:-}" ]; then set -- "$VIRTUAL_ENV/bin/python"; fi
for runtime in "$@" .nba-tools-env/bin/python .venv/bin/python venv/bin/python \
    ../.venv/bin/python ../venv/bin/python python3.11 \
    /opt/homebrew/bin/python3.11 /usr/local/bin/python3.11 \
    /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 \
    python3.12 /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12 \
    /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
    python3.13 /opt/homebrew/bin/python3.13 /usr/local/bin/python3.13 \
    /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 python3 python; do
    case "$runtime" in
        python*)
            located=$(command -v "$runtime" 2>/dev/null) || continue
            if [ "$located" = /usr/bin/python3 ] &&
                [ ! -d /Library/Developer/CommandLineTools ]; then continue; fi
            ;;
    esac
    if "$runtime" -I -c 'import sys; assert sys.version_info >= (3, 8)' >/dev/null 2>&1; then
        "$runtime" -I prepare_environment.py
        found=1
        break
    fi
done
if [ "$found" -eq 0 ]; then
    if [ ! -e readiness-capture ]; then
        mkdir readiness-capture && cp environment-failure.zip readiness-capture/collection.zip
    fi
    printf '\nPython setup could not start. No NBA requests were attempted.\n'
fi
printf '\nReturn readiness-capture/collection.zip, including after a failure.\n'
printf 'Press Return to close.'
read -r ignored
"""


def build(original, request, destination):
    original = Path(original).read_bytes()
    if (
        hashlib.sha256(original).hexdigest() != ORIGINAL_SHA
        or validate_request(request) != REQUEST_SHA
    ):
        raise ValueError("Expected exact frozen PR600 package and 196-request plan")
    import io

    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        members = {entry.filename: (entry, archive.read(entry)) for entry in archive.infolist()}
    if hashlib.sha256(members["run_capture.py"][1]).hexdigest() != COLLECTOR_SHA:
        raise ValueError("Frozen collector differs")
    helper = (
        Path(mac_capture_environment.__file__)
        .read_text()
        .replace(
            "REQUEST = None  # Embedded by build_owner_bundle; never supplied by the owner.",
            "REQUEST = " + repr(request),
            1,
        )
    )
    with tempfile.TemporaryDirectory() as scratch:
        previous = mac_capture_environment.REQUEST
        try:
            mac_capture_environment.REQUEST = request
            mac_capture_environment.failure_receipt(
                Path(scratch),
                {
                    "stage": "bootstrap_selection",
                    "status": "no_bootstrap_python",
                    "receipt_time_basis": "package_preparation_not_laptop_capture",
                    "nba_requests_attempted": 0,
                    "production_writes": 0,
                },
            )
            fallback = (Path(scratch) / "readiness-capture/collection.zip").read_bytes()
        finally:
            mac_capture_environment.REQUEST = previous
    instructions = (
        "Extract into a NEW folder. Double-click Run Capture.command on Mac once.\n"
        "Keep the window open while it locates Python or prepares a private environment.\n"
        "No commands, global installation or administrator password are needed.\n"
        "Return readiness-capture/collection.zip even on failure. Keep all old capture folders.\n"
        "The exact 196 requests and collector are unchanged: "
        "one attempt/job, no retries, 30s timeout, "
        "1s minimum spacing, 1050s collection ceiling, "
        "original byte retention and bounded output.\n"
        "Setup may download nba_api==1.11.4 and its dependencies from PyPI into this folder only. "
        "Existing usable environments are preferred. No production data or settings are changed.\n"
    )
    with (
        Path(destination).open("xb") as handle,
        zipfile.ZipFile(handle, "w", zipfile.ZIP_DEFLATED) as archive,
    ):
        for name, (entry, raw) in members.items():
            if name == "Run Capture.command":
                raw = MAC.encode()
            elif name == "READ ME.txt":
                raw = instructions.encode()
            archive.writestr(entry, raw)
        archive.writestr("prepare_environment.py", helper)
        archive.writestr("environment-failure.zip", fallback)
    return dict(
        request_sha256=REQUEST_SHA,
        original_bundle_sha256=ORIGINAL_SHA,
        collector_sha256=COLLECTOR_SHA,
        environment_helper_sha256=hashlib.sha256(helper.encode()).hexdigest(),
        owner_bundle_sha256=hashlib.sha256(Path(destination).read_bytes()).hexdigest(),
        endpoint_jobs=196,
        nba_requests_executed=0,
        new_period_windows=0,
        production_writes=0,
    )
