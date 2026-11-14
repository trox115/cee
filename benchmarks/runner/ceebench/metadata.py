from __future__ import annotations

import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import __version__, identity


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def runner() -> dict:
    return {"name": "ceebench", "version": __version__, "python": platform.python_version(),
            "fingerprint": identity.fingerprint()["sha256"]}


def _git(root: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def spec(spec_root: Path | None) -> dict:
    if spec_root is None:
        return {"version": None, "commit": None, "dirty": None, "source": "not provided"}
    version_file = spec_root / "VERSION"
    version = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else None
    commit = _git(spec_root, "rev-parse", "HEAD")
    status = _git(spec_root, "status", "--porcelain", "--", "spec", "skills", "VERSION")
    return {
        "version": version,
        "commit": commit,
        "dirty": None if status is None else bool(status),
        "source": "VERSION file and git",
    }
