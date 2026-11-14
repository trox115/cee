from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from . import checksums, identity, metadata, wordcount
from .context import read_binding
from .fsutil import read_text
from .packet import Case, Dataset, duplicates
from .schema import validate


class BindingError(ValueError):
    pass


def _pct(a: int | None, b: int | None) -> float | None:
    if a is None or not b:
        return None
    return round(100 * (a - b) / b, 1)


def _variant_texts(case: Case, variant_id: str) -> tuple[dict[str, str], dict[str, int | None], dict]:
    v = case.variants[variant_id]
    texts, reported = {}, {}
    for it in v["items"]:
        texts[it["item_id"]] = read_text(case.root, it["path"])
        reported[it["item_id"]] = it.get("reported_words")
    meta = {k: v.get(k) for k in ("variant_id", "status", "cee_version", "model", "provenance")}
    meta["source"] = "dataset"
    meta["binding"] = "none: dataset variant imported from earlier reports (legacy, incomplete provenance)"
    return texts, reported, meta


def verify_generation_binding(gen: dict, ds: Dataset, case: Case, spec_root: Path | None,
                              contexts_root: Path | None) -> list[str]:
    p: list[str] = []
    b = gen.get("binding")
    if b is None:
        return ["generation/2 requires a binding"]
    if b["dataset_id"] != ds.data["dataset_id"]:
        p.append(f"dataset_id {b['dataset_id']} != {ds.data['dataset_id']}")
    if b["dataset_manifest_sha256"] != checksums.manifest_digest(ds.root):
        p.append("dataset manifest digest does not match the dataset on disk")
    if b["case_id"] != case.case_id or gen["case_id"] != case.case_id:
        p.append("case binding does not match")
    ids = [it["item_id"] for it in gen["items"]]
    if set(b["contexts"]) != set(ids):
        p.append(f"binding.contexts covers {sorted(b['contexts'])}, items are {sorted(ids)}")
    if b["runner_fingerprint"] != identity.fingerprint()["sha256"]:
        p.append("runner fingerprint differs from the current runner implementation")
    if gen["cee"]["version"] != b["spec"]["version"] or (
        gen["cee"].get("spec_commit") is not None
        and gen["cee"]["spec_commit"] != b["spec"]["commit"]
    ):
        p.append("generation specification metadata conflicts with its binding")
    spec = metadata.spec(spec_root)
    if spec_root is None:
        p.append("--spec-root is required to verify the specification binding")
    elif (b["spec"]["version"], b["spec"]["commit"]) != (spec["version"], spec["commit"]) or spec["dirty"]:
        p.append(f"spec binding {b['spec']} does not match {spec['version']} {spec['commit']} (dirty={spec['dirty']})")
    if contexts_root is None:
        p.append("--contexts-root is required to verify context digests")
    else:
        for iid, digest in b["contexts"].items():
            try:
                actual, ctx = read_binding(contexts_root / iid)
            except (OSError, ValueError) as e:
                p.append(f"context {iid}: {e}")
                continue
            if actual != digest:
                p.append(f"context {iid}: digest mismatch")
            cb = ctx["binding"]
            if (cb["dataset_id"], cb["dataset_manifest_sha256"], cb["case_id"]) != (b["dataset_id"], b["dataset_manifest_sha256"], b["case_id"]):
                p.append(f"context {iid}: bound to another dataset or case")
            if cb["runner_fingerprint"] != b["runner_fingerprint"]:
                p.append(f"context {iid}: runner fingerprint mismatch")
            if iid not in ctx["targets"] or ctx["audience"] != "generator":
                p.append(f"context {iid}: not a generator context for this item")
    return p


def _generation_texts(path: Path, ds: Dataset, case: Case, spec_root: Path | None, contexts_root: Path | None,
                      allow_legacy: bool) -> tuple[dict[str, str], dict]:
    gen = json.loads(path.read_text(encoding="utf-8"))
    validate(gen, "generation")
    if gen["case_id"] != case.case_id:
        raise BindingError(f"{path}: case_id {gen['case_id']} != {case.case_id}")
    ids = [it["item_id"] for it in gen["items"]]
    dup = duplicates(ids)
    if dup:
        raise BindingError(f"{path}: duplicate item ids {dup}")
    items = case.items_by_id()
    unknown = [i for i in ids if i not in items or items[i]["task"] != "rewrite"]
    if unknown:
        raise BindingError(f"{path}: items not in the case or not rewrite targets: {unknown}")
    legacy = gen["schema"] == "ceebench/generation/1"
    if legacy and not allow_legacy:
        raise BindingError(f"{path}: generation/1 has no binding; pass --allow-legacy to import it with incomplete provenance")
    if not legacy:
        problems = verify_generation_binding(gen, ds, case, spec_root, contexts_root)
        if problems:
            raise BindingError(f"{path}: " + "; ".join(problems))
    meta = {"variant_id": gen["variant_id"], "status": "generation", "cee_version": gen["cee"]["version"],
            "spec_commit": gen["cee"].get("spec_commit"), "model": gen["model"], "source": str(path),
            "publishable": gen["publishable"],
            "binding": "legacy import: provenance incomplete, not verified" if legacy else "verified"}
    return {it["item_id"]: it["text"] for it in gen["items"]}, meta


def compute(ds: Dataset, case_id: str, variant_ids: list[str], generations: list[Path],
            options: wordcount.Options, spec_root: Path | None, contexts_root: Path | None = None,
            allow_legacy: bool = False) -> dict:
    case = ds.cases[case_id]
    items = case.items_by_id()
    groups: dict[str, tuple[str, str]] = {}
    if case.sample:
        for s in case.sample["samples"]:
            for it in s["items"]:
                groups[it["item_id"]] = (s["sample_id"], it["group"])
    excluded = {e["item_id"]: e["reason"] for e in (case.sample or {}).get("excluded", [])}
    if duplicates(variant_ids):
        raise BindingError(f"duplicate --variant {duplicates(variant_ids)}")

    inputs = [{"path": f"{case.root.relative_to(ds.root).as_posix()}/{checksums.MANIFEST}",
               "sha256": checksums.manifest_digest(case.root)}]
    texts: dict[str, dict[str, str]] = {}
    reported: dict[str, dict[str, int | None]] = {}
    variants_meta = []

    texts["original"] = {iid: read_text(case.root, it["original"]) for iid, it in items.items()}
    if "original" in case.variants:
        _, reported["original"], m = _variant_texts(case, "original")
        variants_meta.append(m)
    else:
        variants_meta.append({"variant_id": "original", "status": "original", "source": "dataset"})
    for vid in variant_ids:
        if vid == "original":
            continue
        texts[vid], reported[vid], m = _variant_texts(case, vid)
        variants_meta.append(m)
    for g in generations:
        t, m = _generation_texts(g, ds, case, spec_root, contexts_root, allow_legacy)
        if m["variant_id"] in texts:
            raise BindingError(f"duplicate variant id {m['variant_id']}")
        texts[m["variant_id"]] = t
        variants_meta.append(m)
        inputs.append({"path": str(g), "sha256": checksums.sha256_file(g)})

    rows = []
    mismatches = []
    checked = matched = 0
    for iid in items:
        sample_id, group = groups.get(iid, (None, None))
        row = {"item_id": iid, "sample": sample_id, "group": group, "excluded_reason": excluded.get(iid),
               "counts": {}, "reported": {}, "reproduced": {}}
        for vid, vt in texts.items():
            if iid not in vt:
                row["counts"][vid] = None
                continue
            c = wordcount.count(vt[iid], options)
            row["counts"][vid] = asdict(c)
            rep = reported.get(vid, {}).get(iid)
            if rep is not None:
                row["reported"][vid] = rep
                ok = rep == c.words
                row["reproduced"][vid] = ok
                checked += 1
                matched += ok
                if not ok:
                    mismatches.append({"item_id": iid, "variant_id": vid, "reported": rep, "recounted": c.words})
        rows.append(row)

    totals: dict = {}
    for row in rows:
        if row["sample"] is None:
            continue
        bucket = totals.setdefault(row["sample"], {})
        for key in (row["group"], "all"):
            g = bucket.setdefault(key, {"items": 0, "words": {}})
            g["items"] += 1
            for vid in texts:
                c = row["counts"].get(vid)
                cur = g["words"].get(vid, 0)
                g["words"][vid] = None if (c is None or cur is None) else cur + c["words"]
    for bucket in totals.values():
        for g in bucket.values():
            w = g["words"]
            base = w.get("original")
            g["delta_vs_original_pct"] = {vid: _pct(n, base) for vid, n in w.items() if vid != "original"}

    result = {
        "schema": "ceebench/metrics/1",
        "publishable": bool(case.data["publishable"] and ds.data["publishable"]
                            and all(m.get("publishable", True) for m in variants_meta)),
        "generated_at": metadata.now(),
        "runner": metadata.runner(),
        "spec": metadata.spec(spec_root),
        "word_count": wordcount.describe(options),
        "dataset": {"dataset_id": ds.data["dataset_id"], "manifest_sha256": checksums.manifest_digest(ds.root)},
        "case_id": case_id,
        "inputs": inputs,
        "variants": variants_meta,
        "items": rows,
        "totals": totals,
        "reproduction": {"checked": checked, "matched": matched, "mismatches": mismatches},
    }
    validate(result, "metrics")
    return result


def write(result: dict, out: Path) -> str:
    if out.exists() or out.is_symlink():
        raise FileExistsError(f"{out} exists; metrics files are never overwritten")
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return checksums.sha256_file(out)
