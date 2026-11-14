from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from . import checksums, identity
from .fsutil import check_relative, read_bytes
from .packet import (BLOB_DIR, Case, Dataset, GENERATOR_TIERS, selection_allowed, selection_view_path, ts,
                     unit_check)

PRIORITIES = ("required", "supporting", "optional")
WEAK_METHODS = {"changed_file", "php_use_dependency"}
GAP_STATUSES = {"unresolved", "ambiguous", "omitted_size", "inaccessible", "not_retrieved", "not_located", "failed"}
_DIFF_HEAD = re.compile(r"^diff --git a/(\S+) b/(\S+)$", re.M)


class InsufficientBudget(Exception):
    pass


@dataclass
class Entry:
    rel: str
    data: bytes
    kind: str
    priority: str
    reason: str
    meta: dict

    @property
    def chars(self) -> int:
        return len(self.data.decode("utf-8", errors="replace"))


def split_diff(text: str) -> list[tuple[str, str]]:
    heads = list(_DIFF_HEAD.finditer(text))
    out = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        out.append((m.group(2), text[m.start():end]))
    return out


def _rev_match(a: str | None, b: str) -> bool:
    return bool(a) and (a.startswith(b[:12]) or b.startswith(a[:12]))


def build(ds: Dataset, case: Case, targets: list[str], audience: str, out: Path,
          budget: int | None = None, candidates: dict[str, str] | None = None) -> dict:
    if case.version != 2:
        raise ValueError(f"{case.case_id}: focused contexts require ceebench/case/2")
    if audience not in ("generator", "evaluator"):
        raise ValueError("audience must be generator or evaluator")
    if audience == "generator" and candidates:
        raise ValueError("generator contexts never contain candidates")
    if not targets or len(targets) > 1:
        problem = unit_check(case, targets)
        if problem:
            raise ValueError(f"evaluation unit rejected: {problem}")
    if out.is_symlink() or (out.exists() and any(out.iterdir())):
        raise FileExistsError(f"{out} is not empty or is a symlink")
    items = case.items_by_id()
    for t in targets:
        if t not in items:
            raise KeyError(f"unknown item {t}")
    as_of_s = items[targets[0]]["posted_at"]
    as_of = ts(as_of_s)
    tset = set(targets)
    anc = []
    for t in targets:
        anc += [a for a in case.ancestors(t) if a not in tset and a not in anc]
    aset = set(anc)
    entries: list[Entry] = []
    omitted: list[dict] = []
    visible = {i for i, it in items.items() if ts(it["posted_at"]) <= as_of}

    for iid, it in sorted(items.items(), key=lambda kv: (kv[1]["posted_at"], kv[0])):
        t = ts(it["posted_at"])
        if t > as_of:
            continue
        data = read_bytes(case.root, it["original"])
        meta = {"item_id": iid, "role": it["role"], "posted_at": it["posted_at"]}
        if iid in tset:
            entries.append(Entry(f"items/{iid}.md", data, "target_original", "required", "target", meta))
        elif iid in aset:
            entries.append(Entry(f"items/{iid}.md", data, "discussion", "required", "ancestor of a target", meta))
        elif t == as_of:
            omitted.append({"ref": f"item {iid}", "priority": "-", "reason": "posted at the same instant but not part of the evaluation unit", "chars": len(data)})
        else:
            entries.append(Entry(f"items/{iid}.md", data, "discussion", "optional", "earlier discussion, not an ancestor", meta))
    for t in targets:
        if candidates and t in candidates:
            entries.append(Entry(f"candidates/{t}.md", candidates[t].encode("utf-8"), "candidate", "required", "candidate rewrite of a target", {"item_id": t}))

    target_revs = {items[t]["reviewed_revision"] for t in targets}
    focus = {items[i]["anchor"]["path"] for i in tset | aset if items[i].get("anchor", {}).get("path")}

    by_path: dict[tuple[str, str], list[dict]] = {}
    for s in case.data.get("selections", []):
        if selection_allowed(case, s, as_of, visible, audience):
            by_path.setdefault((s["repository"], s["source_path"]), []).append(s)

    def sel_priority(s: dict) -> tuple[str, str]:
        ref, rel_items = s["referenced_by"], set(s["relevant_items"])
        weak = s["method"] in WEAK_METHODS
        if ref.startswith("prior:"):
            return "optional", "selected from a prior report, not attributed to a specific target claim"
        if weak:
            return "optional", f"{s['method']}: incidental selection, not a direct claim reference"
        if ref in tset or (ref.startswith("candidate:") and ref.split(":", 1)[1] in tset):
            return "required", f"referenced by {ref}"
        if not weak and rel_items & tset:
            return "required", f"{s['method']} attributed to a target ({ref.split(':')[0]})"
        if ref in aset or (not weak and rel_items & aset):
            return "supporting", f"referenced in the preceding discussion ({ref if ref in aset else ref.split(':')[0]})"
        if s["method"] == "changed_file" and any(_rev_match(s["revision"], r) for r in target_revs):
            return "optional", "file changed by the diff under review, not referenced"
        if s["method"] == "php_use_dependency":
            return "optional", "code dependency of a changed file, not referenced"
        return "optional", f"{s['method']} not attributed to the target ({ref.split(':')[0]})"

    for key, sels in sorted(by_path.items()):
        latest_t = max(ts(s["available_at"]) for s in sels)
        current = [s for s in sels if ts(s["available_at"]) == latest_t]
        for s in sels:
            if ts(s["available_at"]) < latest_t:
                omitted.append({"ref": f"{s['repository']}:{s['source_path']}@{s['revision'][:12]}", "priority": "-",
                                "reason": f"superseded by revision {current[0]['revision'][:12]}", "chars": None})
        ranked = sorted((sel_priority(s) + (s,) for s in current), key=lambda x: PRIORITIES.index(x[0]))
        pr, reason, s = ranked[0]
        rel = selection_view_path(s)
        data = read_bytes(case.root, f"{BLOB_DIR}/{s['blob']}")
        if pr == "optional":
            omitted.append({"ref": rel, "priority": pr,
                            "reason": "not referenced by the target or required discussion", "chars": len(data.decode("utf-8", errors="replace"))})
            continue
        if pr == "required":
            focus.add(s["source_path"])
        entries.append(Entry(rel, data, s["kind"], pr, reason,
                             {"repository": s["repository"], "revision": s["revision"], "source_path": s["source_path"],
                              "available_at": s["available_at"], "availability_basis": s["availability_basis"],
                              "selections": sorted(x["selection_id"] for x in current)}))

    latest: dict[str, dict] = {}
    for f in case.data["files"]:
        if f["tier"] not in GENERATOR_TIERS or f["kind"] == "blob" or f["path"].startswith("generator/items/"):
            continue
        if ts(f["available_at"]) > as_of or f.get("availability_basis") == "unknown":
            continue
        if f["kind"] == "diff":
            if not any(_rev_match(f.get("revision"), r) for r in target_revs):
                omitted.append({"ref": f["path"], "priority": "-", "reason": "cumulative diff of an earlier or other head; superseded by the target head diff", "chars": None})
                continue
            text = read_bytes(case.root, f["path"]).decode("utf-8")
            sections = split_diff(text)
            has_focus = any(path in focus for path, _ in sections)
            for path, section in sections:
                if has_focus and path not in focus:
                    omitted.append({"ref": f"{f['path']}:{path}", "priority": "optional",
                                    "reason": "diff section outside the target's referenced files", "chars": len(section)})
                    continue
                pr = "required" if path in focus else "supporting"
                why = "diff section of a referenced or anchored file" if pr == "required" else "target revision diff; no changed path maps directly to the target"
                entries.append(Entry(f"diff/{f.get('revision', 'head')[:12]}/{path}.diff", section.encode("utf-8"), "diff_section", pr, why,
                                     {"revision": f.get("revision"), "file": path, "available_at": f["available_at"]}))
            continue
        if f["kind"] == "ci_status" and not any(_rev_match(f.get("revision"), r) for r in target_revs):
            omitted.append({"ref": f["path"], "priority": "-", "reason": "CI status of another revision", "chars": None})
            continue
        key = f["kind"] if f["kind"] in ("pr_description", "ticket_version") else f["path"]
        prev = latest.get(key)
        if prev is None or ts(f["available_at"]) > ts(prev["available_at"]):
            if prev is not None:
                omitted.append({"ref": prev["path"], "priority": "-", "reason": f"superseded by {f['path']}", "chars": None})
            latest[key] = f
        else:
            omitted.append({"ref": f["path"], "priority": "-", "reason": f"superseded by {prev['path']}", "chars": None})
    for f in latest.values():
        entries.append(Entry(f["path"], read_bytes(case.root, f["path"]), f["kind"], "supporting", "latest version available at the target time",
                             {"available_at": f["available_at"], "availability_basis": f.get("availability_basis")}))

    required = [e for e in entries if e.priority == "required"]
    req_chars = sum(e.chars for e in required)
    if budget is not None and req_chars > budget:
        raise InsufficientBudget(f"required evidence is {req_chars} characters, above the budget of {budget}: "
                                 + ", ".join(f"{e.rel} ({e.chars})" for e in sorted(required, key=lambda e: -e.chars)[:8]))
    included = list(required)
    used = req_chars
    for pr in ("supporting", "optional"):
        for e in sorted((e for e in entries if e.priority == pr), key=lambda e: (e.chars, e.rel)):
            if budget is None or used + e.chars <= budget:
                included.append(e)
                used += e.chars
            else:
                omitted.append({"ref": e.rel, "priority": pr, "reason": "context budget", "chars": e.chars})

    gaps = []
    ids = tset | aset
    for s in case.data.get("selections", []):
        if s["availability_basis"] == "unknown" and set(s["relevant_items"]) & ids:
            gaps.append({"target": f"{s['repository']}:{s['source_path']}@{s['revision'][:12]}",
                         "status": "unresolved", "note": "availability unknown; excluded"})
    for g in case.data.get("retrieval_log", []):
        if g["status"] not in GAP_STATUSES:
            continue
        note = g.get("note", "")
        mentions = set(re.findall(r"(?:candidate:)?([A-Za-z0-9]+)@", note))
        if mentions & ids or not mentions:
            gaps.append({"target": g["target"], "status": g["status"], "note": note})

    # Several logical selections can describe the same omitted physical revision.
    # Keep provenance in the dataset; report that physical omission only once.
    omitted = list({json.dumps(o, sort_keys=True): o for o in omitted}.values())

    out.mkdir(parents=True, exist_ok=True)
    for e in included:
        check_relative(e.rel)
        dst = out / "files" / e.rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(e.data)
    by_pr = {p: sum(e.chars for e in included if e.priority == p) for p in PRIORITIES}
    doc = {
        "schema": "ceebench/context/1",
        "binding": {"dataset_id": ds.data["dataset_id"], "dataset_manifest_sha256": checksums.manifest_digest(ds.root),
                    "case_id": case.case_id, "runner_fingerprint": identity.fingerprint()["sha256"]},
        "targets": targets, "audience": audience, "as_of": as_of_s, "budget_chars": budget,
        "sizes": {"included_chars": used, "included_by_priority": by_pr, "required_chars": req_chars,
                  "omitted_for_budget_chars": sum(o["chars"] or 0 for o in omitted if o["reason"] == "context budget")},
        "included": [{"path": f"files/{e.rel}", "kind": e.kind, "priority": e.priority, "reason": e.reason, "chars": e.chars, **e.meta}
                     for e in sorted(included, key=lambda e: (PRIORITIES.index(e.priority), e.rel))],
        "omitted": sorted(omitted, key=lambda o: (o["reason"], o["ref"])),
        "gaps": gaps,
        "coverage": "insufficient_evidence" if gaps else (
            "reduced_by_budget" if any(o["reason"] == "context budget" for o in omitted)
            else "complete_within_selection"),
    }
    (out / "context.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    digest = checksums.write_manifest(out, checksums.list_files(out))
    return {"context_digest": digest, "included": len(included), "omitted": len(omitted), "chars": used}


def read_binding(ctx_dir: Path) -> tuple[str, dict]:
    problems = checksums.verify_manifest(ctx_dir)
    if problems:
        raise ValueError("; ".join(problems))
    return checksums.manifest_digest(ctx_dir), json.loads((ctx_dir / "context.json").read_text(encoding="utf-8"))
