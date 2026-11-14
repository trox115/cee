from __future__ import annotations

import os
from pathlib import Path, PurePosixPath

IGNORED_NAMES = {".DS_Store"}


class UnsafePath(Exception):
    pass


def check_relative(rel: str) -> PurePosixPath:
    p = PurePosixPath(rel)
    if not rel or p.is_absolute() or rel.startswith("/") or "\\" in rel:
        raise UnsafePath(f"{rel!r}: not a relative POSIX path")
    if any(part in ("", ".", "..") for part in rel.split("/")):
        raise UnsafePath(f"{rel!r}: empty, '.' or '..' component")
    return p


def safe_join(root: Path, rel: str, must_exist: bool = True) -> Path:
    check_relative(rel)
    if root.is_symlink():
        raise UnsafePath(f"{root}: symlinked root")
    base = root.resolve()
    cur = base
    for part in rel.split("/"):
        cur = cur / part
        if cur.is_symlink():
            raise UnsafePath(f"{root}/{rel}: symlink component {cur.name!r}")
    if must_exist and not cur.exists():
        raise FileNotFoundError(f"{root}/{rel}")
    resolved = cur.resolve()
    if resolved != base and base not in resolved.parents:
        raise UnsafePath(f"{root}/{rel}: resolves outside {root}")
    return cur


def walk_files(root: Path) -> list[str]:
    if root.is_symlink():
        raise UnsafePath(f"{root}: symlinked root")
    base = root.resolve()
    out = []
    for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
        d = Path(dirpath)
        for name in list(dirnames):
            if (d / name).is_symlink():
                raise UnsafePath(f"{d / name}: symlinked directory")
        for name in filenames:
            p = d / name
            if p.is_symlink():
                raise UnsafePath(f"{p}: symlink")
            if name in IGNORED_NAMES:
                continue
            if not p.is_file():
                raise UnsafePath(f"{p}: not a regular file")
            out.append(p.relative_to(base).as_posix())
    return sorted(out)


def read_bytes(root: Path, rel: str) -> bytes:
    return safe_join(root, rel).read_bytes()


def read_text(root: Path, rel: str) -> str:
    return read_bytes(root, rel).decode("utf-8")
