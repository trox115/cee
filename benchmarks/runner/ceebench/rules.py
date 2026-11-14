from __future__ import annotations

import re
from pathlib import Path

_RULE = re.compile(r"\*\*([A-Z]+-\d{3}) \((MUST NOT|MUST|SHOULD|MAY)\):\*\*")
SPEC_FILES = ("core.md", "reviews.md", "replies.md", "taxonomy.md", "agents.md")


def catalog(spec_root: Path) -> dict[str, str]:
    rules: dict[str, str] = {}
    for name in SPEC_FILES:
        f = spec_root / "spec" / name
        if not f.exists():
            continue
        for rid, level in _RULE.findall(f.read_text(encoding="utf-8")):
            if rid in rules and rules[rid] != level:
                raise ValueError(f"rule {rid} declared with two levels")
            rules[rid] = level
    if not rules:
        raise ValueError(f"no rules found under {spec_root}/spec")
    return rules


REVIEW_ROLES = {"review_comment", "review_segment", "reviewer_reply"}
REPLY_ROLES = {"author_reply"}


def applicable(rules: dict[str, str], role: str) -> set[str]:
    out = {r for r in rules if r.startswith("CORE-")}
    if "AI-007" in rules:
        out.add("AI-007")
    if role in REVIEW_ROLES:
        out |= {r for r in rules if r.startswith("REV-")}
    if role in REPLY_ROLES:
        out |= {r for r in rules if r.startswith("REPLY-")}
    return out
