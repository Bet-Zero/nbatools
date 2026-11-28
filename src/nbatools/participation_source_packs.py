"""Bounded storage for original availability evidence, with unchanged logical names."""

from __future__ import annotations

import hashlib
import io
import json
import re
import stat
import tempfile
from collections import defaultdict
from collections.abc import Callable, Collection, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile, ZipInfo

from nbatools.generation_manifest import GenerationFile, parse_generation_files

SOURCE_DIR = "raw/player_game_availability_sources"
PACK_DIR = "raw/player_game_availability_source_packs"
INDEX = f"{PACK_DIR}/index.json"
MAX_INDEX_BYTES = 5_000_000
MAX_PACK_BYTES = 20_000_000
MAX_EXPANDED_BYTES = 16_000_000
MAX_TOTAL_EXPANDED_BYTES = 100_000_000
MAX_MEMBERS = 256
_DIGEST = re.compile(r"[0-9a-f]{64}")
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.(?:json|pdf|html)")


@dataclass(frozen=True)
class PackedSource:
    pack: str
    size_bytes: int
    sha256: str


def _unique(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("Duplicate participation source index key")
    return result


def _checked_bytes(raw: bytes, size: int, digest: str, label: str) -> bytes:
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError(f"Participation source bytes differ from their inventory: {label}")
    return raw


def _name(relative: str) -> str:
    prefix = SOURCE_DIR + "/"
    name = relative.removeprefix(prefix)
    if not relative.startswith(prefix) or not _NAME.fullmatch(name) or ".." in name:
        raise ValueError(f"Invalid participation source path: {relative}")
    return name


def read_source_index(
    physical: Mapping[str, GenerationFile], read: Callable[[str], bytes]
) -> dict[str, PackedSource]:
    """Authenticate member metadata using the physical generation inventory."""
    packs = {relative for relative in physical if relative.startswith(PACK_DIR + "/")}
    if not packs:
        return {}
    if INDEX not in packs or not 0 < physical[INDEX].size_bytes <= MAX_INDEX_BYTES:
        raise ValueError("Missing or oversized participation source index")
    meta = physical[INDEX]
    doc = json.loads(
        _checked_bytes(read(INDEX), meta.size_bytes, meta.sha256, INDEX),
        object_pairs_hook=_unique,
    )
    if (
        not isinstance(doc, dict)
        or set(doc) != {"schema_version", "files"}
        or type(doc["schema_version"]) is not int
        or doc["schema_version"] != 1
        or not isinstance(doc["files"], dict)
        or not doc["files"]
    ):
        raise ValueError("Invalid participation source index")
    index = {}
    populations = defaultdict(list)
    for relative, item in doc["files"].items():
        _name(relative)
        if (
            relative in physical
            or not isinstance(item, dict)
            or set(item) != {"pack", "sha256", "size_bytes"}
            or not isinstance(item["pack"], str)
            or item["pack"] not in packs
            or item["pack"] == INDEX
            or type(item["size_bytes"]) is not int
            or not 0 < item["size_bytes"] <= MAX_EXPANDED_BYTES
            or not isinstance(item["sha256"], str)
            or not _DIGEST.fullmatch(item["sha256"])
        ):
            raise ValueError(f"Invalid or overlapping participation source entry: {relative}")
        record = PackedSource(**item)
        if (
            record.pack != f"{PACK_DIR}/{physical[record.pack].sha256}.zip"
            or not 0 < physical[record.pack].size_bytes <= MAX_PACK_BYTES
        ):
            raise ValueError("Invalid participation source pack identity")
        index[relative] = record
        populations[record.pack].append(record.size_bytes)
    if (
        packs != {INDEX, *populations}
        or sum(item.size_bytes for item in index.values()) > MAX_TOTAL_EXPANDED_BYTES
        or any(
            len(sizes) > MAX_MEMBERS or sum(sizes) > MAX_EXPANDED_BYTES
            for sizes in populations.values()
        )
    ):
        raise ValueError("Participation source pack inventory exceeds bounds or has unused packs")
    return index


def packed_sources_from_manifest(manifest: dict, read: Callable[[str], bytes]):
    """Read the optional index while retaining loose historical inventories."""
    if not any(item["path"].startswith(PACK_DIR + "/") for item in manifest["files"]):
        return {}, {}
    physical = parse_generation_files(manifest, manifest["generation_id"])
    return physical, read_source_index(physical, read)


def unpack_sources(
    index: Mapping[str, PackedSource],
    physical: Mapping[str, GenerationFile],
    read: Callable[[str], bytes],
    *,
    selected: Collection[str] | None = None,
) -> Iterator[tuple[str, bytes]]:
    """Replay every archived original, one bounded pack at a time."""
    by_pack = defaultdict(dict)
    for relative, item in index.items():
        by_pack[item.pack][_name(relative)] = (relative, item)
    for pack, expected in sorted(by_pack.items()):
        if selected is not None and not any(name in selected for name, _ in expected.values()):
            continue
        entry = physical[pack]
        archive = _checked_bytes(read(pack), entry.size_bytes, entry.sha256, pack)
        try:
            with ZipFile(io.BytesIO(archive)) as zipped:
                members = zipped.infolist()
                if (
                    len(members) != len(expected)
                    or {m.filename for m in members} != expected.keys()
                ):
                    raise ValueError("Participation source ZIP inventory differs from index")
                for member in members:
                    relative, item = expected[member.filename]
                    if (
                        member.is_dir()
                        or stat.S_ISLNK(member.external_attr >> 16)
                        or member.flag_bits & 1
                        or member.compress_type != ZIP_DEFLATED
                        or member.file_size != item.size_bytes
                    ):
                        raise ValueError(f"Invalid participation source ZIP member: {relative}")
                    if selected is None or relative in selected:
                        with zipped.open(member) as body:
                            raw = body.read(item.size_bytes + 1)
                        yield relative, _checked_bytes(raw, item.size_bytes, item.sha256, relative)
        except BadZipFile as exc:
            raise ValueError(f"Malformed participation source ZIP: {pack}") from exc


def read_disk(root: Path, relative: str) -> bytes:
    path = root / relative
    if (
        path.resolve() != root.resolve() / relative
        or not path.is_file()
        or path.stat().st_size > MAX_PACK_BYTES
    ):
        raise ValueError(f"Indirect or missing participation source input: {relative}")
    return path.read_bytes()


@contextmanager
def expanded_source_tree(
    root: Path, physical: Mapping[str, GenerationFile], index: Mapping[str, PackedSource]
) -> Iterator[Path]:
    """Build a temporary validation view without changing the physical snapshot."""
    if not index:
        yield root
        return
    with tempfile.TemporaryDirectory(prefix="nbatools-source-packs-") as directory:
        view = Path(directory)
        for item in root.resolve().iterdir():
            if item.name != "raw":
                (view / item.name).symlink_to(item)
        (view / "raw").mkdir()
        target = view / SOURCE_DIR
        target.mkdir()
        for item in (root.resolve() / "raw").iterdir():
            if item.name == Path(SOURCE_DIR).name:
                for original in item.iterdir():
                    name = original.relative_to(root.resolve()).as_posix()
                    record = physical.get(name)
                    if record is None:
                        raise ValueError(f"Unmanifested loose participation source: {name}")
                    raw = _checked_bytes(
                        read_disk(root, name), record.size_bytes, record.sha256, name
                    )
                    (target / _name(name)).write_bytes(raw)
            elif item.name != Path(PACK_DIR).name:
                (view / "raw" / item.name).symlink_to(item)
        for relative, raw in unpack_sources(index, physical, lambda name: read_disk(root, name)):
            with (view / relative).open("xb") as f:
                f.write(raw)
        yield view


def pack_sources(
    root: Path, existing: Mapping[str, PackedSource]
) -> tuple[dict[str, PackedSource], set[str]]:
    """Append deterministic packs to a disposable preparation tree."""
    source = root / SOURCE_DIR
    directory = root / PACK_DIR
    if source.is_symlink() or directory.is_symlink() or (root / INDEX).is_symlink():
        raise ValueError("Indirect participation source packing path")
    if not source.exists():
        return dict(existing), set()
    files = sorted(source.iterdir())
    if not files:
        return dict(existing), set()
    groups = []
    current, size = [], 0
    total = sum(item.size_bytes for item in existing.values())
    for path in files:
        relative = path.relative_to(root).as_posix()
        _name(relative)
        if relative in existing or path.is_symlink() or not path.is_file():
            raise ValueError(
                f"Conflicting or indirect participation source for packing: {relative}"
            )
        length = path.stat().st_size
        if not 0 < length <= MAX_EXPANDED_BYTES:
            raise ValueError(f"Participation original exceeds pack bound: {relative}")
        total += length
        if total > MAX_TOTAL_EXPANDED_BYTES:
            raise ValueError("Expanded participation originals exceed the existing overlay bound")
        if len(current) == MAX_MEMBERS or size + length > MAX_EXPANDED_BYTES:
            groups.append(current)
            current, size = [], 0
        current.append(path)
        size += length
    groups.append(current)
    directory.mkdir(parents=True, exist_ok=True)
    index, changed = dict(existing), {INDEX}
    for group in groups:
        output = io.BytesIO()
        members = {}
        with ZipFile(output, "w", compression=ZIP_DEFLATED) as zipped:
            for path in group:
                relative = path.relative_to(root).as_posix()
                raw = read_disk(root, relative)
                zipped.writestr(ZipInfo(path.name), raw, compress_type=ZIP_DEFLATED)
                members[relative] = (len(raw), hashlib.sha256(raw).hexdigest())
        raw = output.getvalue()
        pack = f"{PACK_DIR}/{hashlib.sha256(raw).hexdigest()}.zip"
        if len(raw) > MAX_PACK_BYTES:
            raise ValueError("Compressed participation pack exceeds bound")
        with (root / pack).open("xb") as f:
            f.write(raw)
        changed.add(pack)
        index.update(
            {name: PackedSource(pack, length, digest) for name, (length, digest) in members.items()}
        )
    document = {
        "schema_version": 1,
        "files": {
            name: dict(pack=item.pack, size_bytes=item.size_bytes, sha256=item.sha256)
            for name, item in index.items()
        },
    }
    raw = (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if len(raw) > MAX_INDEX_BYTES:
        raise ValueError("Participation source index exceeds bound")
    (root / INDEX).write_bytes(raw)
    for path in files:
        path.unlink()
    return index, changed
