"""Fixed combined package entry point for the existing protected publisher.

Its fixed inventory binds the accepted combined source run and exact output
checksums. The protected workflow additionally requires a reviewed registry-bound
publisher revision; this entry point does not authorize production publication.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def main() -> None:
    directory = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(
        "reviewed_availability_publisher", directory / "publish-opening-availability.py"
    )
    publisher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(publisher)
    publisher.main(
        inventory_path=directory / "combined-availability-inventory.json",
        default_generation="availability-opening-s4-v1-20261017",
    )


if __name__ == "__main__":
    main()
