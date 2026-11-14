from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import checksums, identity
from .fsutil import UnsafePath, check_relative, read_bytes, read_text, safe_join, walk_files
from .schema import SchemaError, validate

TIER_DIRS = {
    "generator": "generator_input",
    "evidence": "review_time",
    "reference": "evaluator_only",
    "outcomes": "outcome",
}
GENERATOR_TIERS = {"generator_input", "review_time"}
AUDIENCES = ("generator", "evaluator")
CASE_FILE = "case.json"
DATASET_FILE = "dataset.json"
SAMPLE_FILE = "reference/sample.json"
VARIANTS_DIR = "reference/variants"
BLOB_DIR = "evidence/blobs"
CASE_V1 = "ceebench/case/1"
CASE_V2 = "ceebench/case/2"
_REF = re.compile(r"^(candidate:|prior:|diff:)?(.+)$")


def ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_json(root: Path, rel: str) -> dict:
    return json.loads(read_text(root, rel))


def duplicates(values) -> list:
    return sorted(v for v, n in Counter(values).items() if n > 1)


@dataclass
class Case:
    root: Path
    data: dict
    sample: dict | None = None
    variants: dict[str, dict] = field(default_factory=dict)

    @property
    def case_id(self) -> str:
        return self.data["case_id"]

    @property
    def version(self) -> int:
        return 2 if self.data["schema"] == CASE_V2 else 1

    def item(self, item_id: str) -> dict:
        for it in self.data["items"]:
            if it["item_id"] == item_id:
                return it
        raise KeyError(f"{self.case_id}: unknown item {item_id}")

    def items_by_id(self) -> dict[str, dict]:
        return {it["item_id"]: it for it in self.data["items"]}

    def files_by_path(self) -> dict[str, dict]:
        return {f["path"]: f for f in self.data["files"]}

    def ancestors(self, item_id: str) -> list[str]:
        items = self.items_by_id()
        out, cur, seen = [], items[item_id].get("parent_item"), set()
        while cur and cur not in seen:
            seen.add(cur)
            out.append(cur)
            cur = items[cur].get("parent_item")
        return out


@dataclass
class Dataset:
    root: Path
    data: dict
    cases: dict[str, Case]


def load_case(root: Path) -> Case:
    data = load_json(root, CASE_FILE)
    validate(data, "case")
    case = Case(root, data)
    if (root / SAMPLE_FILE).exists() or (root / SAMPLE_FILE).is_symlink():
        case.sample = load_json(root, SAMPLE_FILE)
        validate(case.sample, "sample")
    seen: dict[str, str] = {}
    for rel in walk_files(root):
        if re.fullmatch(rf"{VARIANTS_DIR}/[^/]+/variant\.json", rel):
            v = load_json(root, rel)
            validate(v, "variant")
            vid = v["variant_id"]
            if vid in seen:
                raise SchemaError([f"{root}: variant_id {vid!r} declared in {seen[vid]} and {rel}"])
            seen[vid] = rel
            case.variants[vid] = v
    return case


def load_dataset(root: Path) -> Dataset:
    if root.is_symlink():
        raise UnsafePath(f"{root}: symlinked dataset root")
    root = root.resolve()
    data = load_json(root, DATASET_FILE)
    validate(data, "dataset")
    errs = [f"duplicate case_id {c}" for c in duplicates(e["case_id"] for e in data["cases"])]
    errs += [f"duplicate case path {p}" for p in duplicates(e["path"] for e in data["cases"])]
    if errs:
        raise SchemaError([f"{root / DATASET_FILE}: {e}" for e in errs])
    cases = {}
    for entry in data["cases"]:
        case_root = safe_join(root, entry["path"])
        if not case_root.is_dir():
            raise SchemaError([f"{entry['path']}: not a directory"])
        case = load_case(case_root)
        if case.case_id != entry["case_id"]:
            raise SchemaError([f"{entry['path']}: case_id {case.case_id!r} != manifest {entry['case_id']!r}"])
        cases[case.case_id] = case
    return Dataset(root, data, cases)


def _check_ref(ref: str, items: set[str]) -> bool:
    m = _REF.match(ref)
    prefix, rest = m.group(1), m.group(2)
    if prefix in ("candidate:",):
        return rest in items
    if prefix in ("prior:", "diff:"):
        return bool(rest)
    return ref in items


def check_case(case: Case) -> list[str]:
    p: list[str] = []
    cid = case.case_id
    d = case.data
    p += [f"{cid}: duplicate item id {i}" for i in duplicates(it["item_id"] for it in d["items"])]
    p += [f"{cid}: duplicate file entry {f}" for f in duplicates(f["path"] for f in d["files"])]
    p += [f"{cid}: duplicate snapshot id {s}" for s in duplicates(s["snapshot_id"] for s in d.get("snapshots", []))]
    p += [f"{cid}: duplicate selection id {s}" for s in duplicates(s["selection_id"] for s in d.get("selections", []))]
    if case.version == 1 and d.get("selections"):
        p.append(f"{cid}: selections require {CASE_V2}")
    files = case.files_by_path()
    items = case.items_by_id()
    try:
        on_disk = set(checksums.list_files(case.root, exclude=(checksums.MANIFEST, CASE_FILE)))
    except UnsafePath as e:
        return p + [f"{cid}: {e}"]
    for path in sorted(on_disk - set(files)):
        p.append(f"{cid}: {path} is not declared in case.json files")
    blobs_used = {s["blob"] for s in d.get("selections", [])}
    for path, f in files.items():
        try:
            safe_join(case.root, path)
        except FileNotFoundError:
            p.append(f"{cid}: declared file {path} is missing")
        except UnsafePath as e:
            p.append(f"{cid}: {e}")
            continue
        top = path.split("/", 1)[0]
        expected = TIER_DIRS.get(top)
        if expected is None:
            p.append(f"{cid}: {path} is outside the tier directories {sorted(TIER_DIRS)}")
        elif f["tier"] != expected:
            p.append(f"{cid}: {path} declares tier {f['tier']} but lives in {top}/ ({expected})")
        is_blob = case.version == 2 and path.startswith(BLOB_DIR + "/")
        if is_blob:
            name = path[len(BLOB_DIR) + 1:]
            if f["kind"] != "blob" or "available_at" in f:
                p.append(f"{cid}: {path} must have kind 'blob' and no available_at (availability belongs to selections)")
            if path in on_disk and checksums.sha256_bytes(read_bytes(case.root, path)) != name:
                p.append(f"{cid}: {path} content does not match its name")
            if name not in blobs_used:
                p.append(f"{cid}: {path} is not referenced by any selection")
        elif f["tier"] in GENERATOR_TIERS and "available_at" not in f:
            p.append(f"{cid}: {path} ({f['tier']}) needs available_at")
        if case.version == 2 and not is_blob and f["tier"] in GENERATOR_TIERS and "availability_basis" not in f:
            p.append(f"{cid}: {path} needs availability_basis in {CASE_V2}")
        for iid in f.get("item_ids", []):
            if iid not in items:
                p.append(f"{cid}: {path} references unknown item {iid}")
        sel = f.get("selection")
        if sel is not None:
            if case.version == 2:
                p.append(f"{cid}: {path} uses the legacy per-file selection; use selections in {CASE_V2}")
            if f["tier"] != "review_time":
                p.append(f"{cid}: {path} has a selection record but is not review_time evidence")
            if sel["basis"] == "secondary" and not sel.get("referenced_by"):
                p.append(f"{cid}: {path} is secondary evidence without referenced_by provenance")
            for ref in sel.get("referenced_by", []):
                if ref not in items and not ref.startswith("prior:") and not ref.startswith("candidate:"):
                    p.append(f"{cid}: {path} referenced_by {ref} is not an item, 'candidate:<item>' or 'prior:<document>'")
    for s in d.get("selections", []):
        sid = s["selection_id"]
        if f"{BLOB_DIR}/{s['blob']}" not in files:
            p.append(f"{cid}: selection {sid} blob {s['blob'][:12]} is not declared")
        try:
            check_relative(s["source_path"].rstrip("/"))
        except UnsafePath as e:
            p.append(f"{cid}: selection {sid} source_path {e}")
        ref = s["referenced_by"]
        if not _check_ref(ref, set(items)):
            p.append(f"{cid}: selection {sid} referenced_by {ref} is not an item, candidate:<item>, prior:<doc> or diff:<revision>")
        secondary_ref = ref.startswith(("candidate:", "prior:"))
        if s["basis"] == "secondary" and not secondary_ref:
            p.append(f"{cid}: selection {sid} is secondary but referenced_by {ref} is not a candidate or prior document")
        if s["basis"] == "primary" and secondary_ref:
            p.append(f"{cid}: selection {sid} is primary but referenced_by {ref} is a candidate or prior document")
        for iid in s["relevant_items"]:
            if iid not in items:
                p.append(f"{cid}: selection {sid} relevant to unknown item {iid}")
    for iid, it in items.items():
        f = files.get(it["original"])
        if f is None:
            p.append(f"{cid}: item {iid} original {it['original']} is not declared")
        elif f["tier"] != "generator_input":
            p.append(f"{cid}: item {iid} original must be generator_input")
        elif ts(f["available_at"]) > ts(it["posted_at"]):
            p.append(f"{cid}: item {iid} original is available after the item was posted")
        parent = it.get("parent_item")
        if parent is not None:
            if parent not in items:
                p.append(f"{cid}: item {iid} has unknown parent {parent}")
            elif ts(items[parent]["posted_at"]) > ts(it["posted_at"]):
                p.append(f"{cid}: item {iid} is posted before its parent {parent}")
    for s in d.get("snapshots", []):
        for iid in s.get("item_ids", []):
            if iid not in items:
                p.append(f"{cid}: snapshot {s['snapshot_id']} references unknown item {iid}")
    if case.sample is not None:
        if case.sample["case_id"] != cid:
            p.append(f"{cid}: sample.json case_id mismatch")
        p += [f"{cid}: duplicate sample id {s}" for s in duplicates(s["sample_id"] for s in case.sample["samples"])]
        members = [it["item_id"] for s in case.sample["samples"] for it in s["items"]]
        p += [f"{cid}: item {i} appears more than once across samples" for i in duplicates(members)]
        excluded = [e["item_id"] for e in case.sample.get("excluded", [])]
        p += [f"{cid}: duplicate excluded item {i}" for i in duplicates(excluded)]
        p += [f"{cid}: item {i} is both in a sample and excluded" for i in sorted(set(members) & set(excluded))]
        for i in sorted(set(members) | set(excluded)):
            if i not in items:
                p.append(f"{cid}: sample references unknown item {i}")
    for vid, v in case.variants.items():
        if v["case_id"] != cid:
            p.append(f"{cid}: variant {vid} case_id mismatch")
        p += [f"{cid}: variant {vid} has duplicate item {i}" for i in duplicates(it["item_id"] for it in v["items"])]
        for it in v["items"]:
            if it["item_id"] not in items:
                p.append(f"{cid}: variant {vid} references unknown item {it['item_id']}")
            f = files.get(it["path"])
            if f is None:
                p.append(f"{cid}: variant {vid} text {it['path']} is not declared")
            elif v["status"] == "reported_output" and f["tier"] != "evaluator_only":
                p.append(f"{cid}: variant {vid} text {it['path']} must be evaluator_only")
    return p


def check_dataset(ds: Dataset, verify_checksums: bool = True) -> list[str]:
    problems: list[str] = []
    for case in ds.cases.values():
        problems += check_case(case)
        if verify_checksums:
            problems += checksums.verify_manifest(case.root)
    if verify_checksums:
        problems += verify_root(ds)
    return problems


def _root_entries(ds: Dataset) -> list[str]:
    return [DATASET_FILE] + [f"{e['path']}/{checksums.MANIFEST}" for e in ds.data["cases"]]


def verify_root(ds: Dataset) -> list[str]:
    if not (ds.root / checksums.MANIFEST).exists():
        return [f"{ds.root / checksums.MANIFEST}: missing"]
    try:
        listed = checksums.read_manifest(ds.root)
    except (UnsafePath, ValueError) as e:
        return [str(e)]
    expected = set(_root_entries(ds))
    problems = [f"{ds.root / n}: not in dataset manifest" for n in sorted(expected - set(listed))]
    problems += [f"{ds.root / n}: listed in dataset manifest but not part of the dataset" for n in sorted(set(listed) - expected)]
    for name, digest in listed.items():
        try:
            path = safe_join(ds.root, name)
        except FileNotFoundError:
            problems.append(f"{ds.root / name}: listed but missing")
            continue
        except UnsafePath as e:
            problems.append(str(e))
            continue
        if checksums.sha256_file(path) != digest:
            problems.append(f"{path}: checksum mismatch")
    return problems


def seal(ds: Dataset) -> str:
    existing = [str(c.root / checksums.MANIFEST) for c in ds.cases.values() if (c.root / checksums.MANIFEST).exists()]
    if (ds.root / checksums.MANIFEST).exists():
        existing.append(str(ds.root / checksums.MANIFEST))
    if existing:
        raise FileExistsError("dataset is already sealed (" + ", ".join(existing) + "); "
                              "changes require a new dataset version in a new directory")
    for case in ds.cases.values():
        checksums.write_manifest(case.root, checksums.list_files(case.root))
    return checksums.write_manifest(ds.root, _root_entries(ds))


def unit_check(case: Case, item_ids: list[str]) -> str | None:
    if not item_ids:
        return "empty evaluation unit"
    if len(set(item_ids)) != len(item_ids):
        return "duplicate item in unit"
    items = case.items_by_id()
    for iid in item_ids:
        if iid not in items:
            return f"unknown item {iid}"
    times = {items[i]["posted_at"] for i in item_ids}
    if len(times) > 1:
        return ("items were posted at different times " + ", ".join(f"{i}={items[i]['posted_at']}" for i in item_ids)
                + "; an earlier item would see later items. Evaluate them separately.")
    if len({items[i]["reviewed_revision"] for i in item_ids}) > 1:
        return "items have conflicting reviewed revisions; evaluate them separately"
    return None


def selection_view_path(s: dict) -> str:
    suffix = ".listing.txt" if s["kind"] == "tree_listing" else ""
    repo = s["repository"].rsplit("/", 1)[-1]
    rel = f"evidence/selected/{repo}/{s['revision'][:12]}/{s['source_path'].rstrip('/')}{suffix}"
    check_relative(rel)
    return rel


def selection_allowed(case: Case, s: dict, as_of: datetime, visible: set[str], audience: str) -> bool:
    if s["availability_basis"] == "unknown" or ts(s["available_at"]) > as_of:
        return False
    ref = s["referenced_by"]
    if s["basis"] == "secondary":
        if audience != "evaluator":
            return False
        if ref.startswith("candidate:"):
            return ref.split(":", 1)[1] in visible
        return True
    if ref.startswith("diff:"):
        return True
    return ref in visible


def _write(out: Path, rel: str, data: bytes) -> None:
    check_relative(rel)
    dst = out / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)


def export_view(case: Case, item_id: str, out: Path, audience: str = "generator") -> dict:
    if audience not in AUDIENCES:
        raise ValueError(f"audience must be one of {AUDIENCES}")
    target = case.item(item_id)
    as_of = ts(target["posted_at"])
    if out.is_symlink() or (out.exists() and any(out.iterdir())):
        raise FileExistsError(f"{out} is not empty or is a symlink")
    visible = [it for it in case.data["items"] if ts(it["posted_at"]) <= as_of]
    visible_ids = {it["item_id"] for it in visible}
    selected, gaps = [], []
    for f in case.data["files"]:
        if f["tier"] not in GENERATOR_TIERS or f.get("kind") == "blob":
            continue
        if ts(f["available_at"]) > as_of:
            continue
        if f.get("availability_basis") == "unknown":
            gaps.append(f"{f['path']}: availability unknown; excluded")
            continue
        scope = f.get("item_ids")
        if scope and not (set(scope) & visible_ids):
            continue
        if audience == "generator" and f.get("selection", {}).get("basis") == "secondary":
            continue
        selected.append(f)
    sels = {}
    for s in case.data.get("selections", []):
        if s["availability_basis"] == "unknown" and ts(s["available_at"]) <= as_of:
            gaps.append(f"{s['repository']}:{s['source_path']}@{s['revision'][:12]}: availability unknown; excluded")
        if selection_allowed(case, s, as_of, visible_ids, audience):
            sels.setdefault(selection_view_path(s), s)
    for f in selected:
        if f["tier"] not in GENERATOR_TIERS or ts(f["available_at"]) > as_of:
            raise AssertionError(f"leak guard: {f['path']}")
        if audience == "generator" and f.get("selection", {}).get("basis") == "secondary":
            raise AssertionError(f"leak guard: secondary evidence {f['path']} in a generator view")
    out.mkdir(parents=True, exist_ok=True)
    for f in selected:
        _write(out / "files", f["path"], read_bytes(case.root, f["path"]))
    for rel, s in sels.items():
        _write(out / "files", rel, read_bytes(case.root, f"{BLOB_DIR}/{s['blob']}"))
    file_entries = [{"path": f"files/{f['path']}", "kind": f["kind"], "available_at": f["available_at"],
                     **({"availability_basis": f["availability_basis"]} if "availability_basis" in f else {})}
                    for f in selected]
    file_entries += [{"path": f"files/{rel}", "kind": s["kind"], "available_at": s["available_at"],
                      "availability_basis": s["availability_basis"], "revision": s["revision"],
                      "source_path": s["source_path"]} for rel, s in sorted(sels.items())]
    view = {
        "schema": "ceebench/view/1",
        "runner_fingerprint": identity.fingerprint()["sha256"],
        "case_id": case.case_id,
        "target_item": item_id,
        "audience": audience,
        "as_of": target["posted_at"],
        "source": {"system": case.data["source"]["system"], "change_id": case.data["source"]["change_id"]},
        "items": [
            {k: it[k] for k in ("item_id", "role", "author_role", "posted_at", "reviewed_revision", "anchor", "parent_item", "segment", "task") if k in it}
            | {"original": f"files/{it['original']}", "is_target": it["item_id"] == item_id}
            for it in sorted(visible, key=lambda x: (x["posted_at"], x["item_id"]))
        ],
        "files": file_entries,
        "snapshots": [
            {k: s[k] for k in ("snapshot_id", "repository", "revision", "available_at", "availability_basis") if k in s}
            for s in case.data.get("snapshots", [])
            if ts(s["available_at"]) <= as_of and s.get("availability_basis") != "unknown"
            and (not s.get("item_ids") or set(s["item_ids"]) & visible_ids)
        ],
        "gaps": gaps,
    }
    (out / "view.json").write_text(json.dumps(view, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    digest = checksums.write_manifest(out, checksums.list_files(out))
    return {"view_digest": digest, "files": len(file_entries), "items": len(visible)}
