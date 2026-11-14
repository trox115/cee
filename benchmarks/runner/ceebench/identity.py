from __future__ import annotations

import hashlib
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
RUNNER_ROOT = PACKAGE.parent


def _members() -> list[Path]:
    files = sorted(PACKAGE.glob("*.py")) + sorted((RUNNER_ROOT / "schemas").glob("*.schema.json"))
    return [f for f in files if f.is_file() and not f.is_symlink()]


def fingerprint() -> dict:
    h = hashlib.sha256()
    listing = []
    for f in _members():
        rel = f.relative_to(RUNNER_ROOT).as_posix()
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        listing.append(rel)
        h.update(f"{digest}  {rel}\n".encode("utf-8"))
    return {"algorithm": "sha256 over '<sha256>  <path>' lines of ceebench/*.py and schemas/*.schema.json, sorted",
            "sha256": h.hexdigest(), "files": len(listing)}


def file_fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
