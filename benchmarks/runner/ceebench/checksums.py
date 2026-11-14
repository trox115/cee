from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path

from .fsutil import IGNORED_NAMES, UnsafePath, safe_join, walk_files

MANIFEST = "checksums.sha256"
__all__ = ["MANIFEST", "IGNORED_NAMES", "sha256_file", "sha256_bytes", "list_files", "write_manifest",
           "read_manifest", "verify_manifest", "manifest_digest", "freeze", "verify_frozen"]


def sha256_file(path: Path) -> str:
    if path.is_symlink():
        raise UnsafePath(f"{path}: symlink")
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def list_files(root: Path, exclude: tuple[str, ...] = (MANIFEST,)) -> list[str]:
    return [f for f in walk_files(root) if f not in exclude]


def write_manifest(root: Path, files: list[str]) -> str:
    target = root / MANIFEST
    if target.is_symlink():
        raise UnsafePath(f"{target}: symlink")
    lines = [f"{sha256_file(safe_join(root, f))}  {f}" for f in sorted(files)]
    body = "\n".join(lines) + "\n"
    target.write_text(body, encoding="utf-8")
    return sha256_bytes(body.encode("utf-8"))


def read_manifest(root: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in safe_join(root, MANIFEST).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, _, name = line.partition("  ")
        if name in entries:
            raise ValueError(f"{root / MANIFEST}: duplicate entry {name}")
        entries[name] = digest
    return entries


def verify_manifest(root: Path) -> list[str]:
    if not (root / MANIFEST).exists():
        return [f"{root}: missing {MANIFEST}"]
    try:
        entries = read_manifest(root)
        on_disk = set(list_files(root))
    except (UnsafePath, ValueError) as e:
        return [str(e)]
    problems = []
    for name, digest in entries.items():
        try:
            p = safe_join(root, name)
        except FileNotFoundError:
            problems.append(f"{root / name}: listed but missing")
            continue
        except UnsafePath as e:
            problems.append(str(e))
            continue
        if sha256_file(p) != digest:
            problems.append(f"{root / name}: checksum mismatch")
    for name in sorted(on_disk - set(entries)):
        problems.append(f"{root / name}: present but not in {MANIFEST}")
    return problems


def manifest_digest(root: Path) -> str:
    return sha256_file(safe_join(root, MANIFEST))


def freeze(path: Path) -> str:
    if path.is_symlink():
        raise UnsafePath(f"{path}: symlink")
    digest = sha256_file(path)
    side = path.with_name(path.name + ".sha256")
    if side.exists() or side.is_symlink():
        raise FileExistsError(f"{side} exists; frozen files are never rewritten")
    side.write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    for p in (path, side):
        os.chmod(p, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    return digest


def verify_frozen(path: Path) -> list[str]:
    side = path.with_name(path.name + ".sha256")
    if path.is_symlink() or side.is_symlink():
        return [f"{path}: symlinked frozen file or checksum"]
    if not side.exists():
        return [f"{side}: missing"]
    expected, _, name = side.read_text(encoding="utf-8").strip().partition("  ")
    problems = []
    if name != path.name:
        problems.append(f"{side}: names {name!r}, expected {path.name!r}")
    if sha256_file(path) != expected:
        problems.append(f"{path}: checksum mismatch")
    for p in (path, side):
        if os.stat(p).st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
            problems.append(f"{p}: writable; frozen files must be read-only")
    return problems
