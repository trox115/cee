from __future__ import annotations

import re
from pathlib import Path

from . import checksums, identity, metadata, rules
from .context import read_binding
from .packet import Dataset, duplicates
from .schema import SchemaError, validate

_NEGATIVE = re.compile(r"\b(incorrect|is wrong|are wrong|contradict\w*|not supported|unsupported|fails?)\b", re.I)


def check(ev: dict, ds: Dataset, spec_root: Path, contexts_root: Path | None,
          expected_items: list[str] | None = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        validate(ev, "evaluation")
    except SchemaError as e:
        return {"errors": e.errors, "warnings": []}
    b = ev["binding"]
    case = ds.cases.get(b["case_id"])
    if case is None:
        return {"errors": [f"unknown case {b['case_id']}"], "warnings": []}
    if b["dataset_id"] != ds.data["dataset_id"]:
        errors.append(f"binding dataset_id {b['dataset_id']} != {ds.data['dataset_id']}")
    if b["dataset_manifest_sha256"] != checksums.manifest_digest(ds.root):
        errors.append("binding dataset manifest digest does not match the dataset on disk")
    spec = metadata.spec(spec_root)
    if (b["spec"]["version"], b["spec"]["commit"]) != (spec["version"], spec["commit"]) or spec["dirty"]:
        errors.append(f"binding spec {b['spec']} does not match {spec['version']} {spec['commit']} (dirty={spec['dirty']})")
    if b["runner_fingerprint"] != identity.fingerprint()["sha256"]:
        errors.append("binding runner fingerprint differs from the current runner implementation")
    for key in ("prompt_builder_sha256", "instructions_sha256"):
        if key not in b:
            errors.append(f"binding lacks {key}")

    ids = [it["item_id"] for it in ev["items"]]
    if expected_items is None and contexts_root is not None:
        expected_items = sorted(p.name for p in contexts_root.iterdir() if (p / "context.json").is_file())
    if expected_items is not None and (set(ids) != set(expected_items) or duplicates(expected_items)):
        errors.append(f"evaluation items {sorted(ids)} do not match expected items {sorted(expected_items)}")
    errors += [f"duplicate evaluation item {i}" for i in duplicates(ids)]
    if set(ids) != set(b["contexts"]):
        errors.append(f"items {sorted(ids)} do not match bound contexts {sorted(b['contexts'])}")
    items = case.items_by_id()
    for i in ids:
        if i not in items:
            errors.append(f"item {i} is not in case {case.case_id}")
    if contexts_root is None:
        errors.append("contexts root not given; context bindings are unverified")
    else:
        for iid, digest in b["contexts"].items():
            try:
                actual, ctx = read_binding(contexts_root / iid)
            except (OSError, ValueError) as e:
                errors.append(f"context {iid}: {e}")
                continue
            if actual != digest:
                errors.append(f"context {iid}: digest mismatch")
            if ctx["audience"] != "evaluator" or iid not in ctx["targets"]:
                errors.append(f"context {iid}: not an evaluator context for this item")
            cb = ctx["binding"]
            if any(cb[key] != b[key] for key in ("dataset_id", "dataset_manifest_sha256", "case_id")):
                errors.append(f"context {iid}: bound to another dataset or case")
            if cb["runner_fingerprint"] != b["runner_fingerprint"]:
                errors.append(f"context {iid}: runner fingerprint mismatch")

    catalog = rules.catalog(spec_root)
    for it in ev["items"]:
        iid = it["item_id"]
        role = items.get(iid, {}).get("role", "")
        rr_ids = [r["rule_id"] for r in it["rule_results"]]
        errors += [f"{iid}: duplicate rule result {r}" for r in duplicates(rr_ids)]
        rr = {r["rule_id"]: r for r in it["rule_results"]}
        for rid, r in rr.items():
            if rid not in catalog:
                errors.append(f"{iid}: unknown rule {rid}")
            elif r["level"] != catalog[rid]:
                errors.append(f"{iid}: {rid} level {r['level']} != specification {catalog[rid]}")
        missing = sorted(rules.applicable(catalog, role) - set(rr))
        if missing:
            errors.append(f"{iid}: missing applicable rule results {missing}")
        vrules = set()
        for v in it["violations"]:
            vrules.add(v["rule_id"])
            if v["rule_id"] not in catalog:
                errors.append(f"{iid}: violation of unknown rule {v['rule_id']}")
            elif v["level"] != catalog[v["rule_id"]]:
                errors.append(f"{iid}: violation {v['rule_id']} reported as {v['level']}, specification says {catalog[v['rule_id']]}")
            if rr.get(v["rule_id"], {}).get("result") != "fail":
                errors.append(f"{iid}: violation {v['rule_id']} without a failed rule result")
        for rid, r in rr.items():
            if r["result"] == "fail" and rid not in vrules:
                errors.append(f"{iid}: rule result {rid}=fail without a violation record")
        claims = it["claims"]
        for c in claims:
            if c["evidence_sufficiency"] == "fail" and c["technical_correctness"] != "unverifiable":
                errors.append(f"{iid}: claim marked insufficiently evidenced but decided as {c['technical_correctness']}: {c['text'][:60]!r}")
            if c["origin"] == "not_a_claim" and c["technical_correctness"] != "not_applicable":
                errors.append(f"{iid}: non-claim with technical_correctness {c['technical_correctness']}: {c['text'][:60]!r}")
            if (c["technical_correctness"] == "not_applicable") != (c["evidence_sufficiency"] == "not_applicable"):
                errors.append(f"{iid}: claim applicability disagrees with evidence sufficiency")
        failed = [c for c in claims if c["technical_correctness"] == "fail"]
        unverifiable = [c for c in claims if c["technical_correctness"] == "unverifiable"]
        ta = it["dimensions"]["technical_accuracy"]
        insufficient = [c for c in claims if c["evidence_sufficiency"] == "fail"]
        support = it["dimensions"]["evidence_support"]
        if insufficient and (support["status"] == "pass" or support.get("score") == 5):
            errors.append(f"{iid}: evidence_support pass or score 5 with insufficiently evidenced claims")
        for corrected in it["corrected_errors"]:
            if corrected.get("rule_id") and corrected["rule_id"] not in catalog:
                errors.append(f"{iid}: corrected error references unknown rule {corrected['rule_id']}")
        if failed and ta["status"] == "pass":
            errors.append(f"{iid}: technical_accuracy pass with {len(failed)} failed claim(s)")
        if failed and ta.get("score") == 5:
            errors.append(f"{iid}: technical_accuracy score 5 with {len(failed)} failed claim(s)")
        listed = set(it["unverifiable_claims"])
        for c in unverifiable:
            if c["text"] not in listed:
                warnings.append(f"{iid}: unverifiable claim not listed in unverifiable_claims: {c['text'][:60]!r}")
        score = ta.get("score")
        if score is not None and score <= 3 and not failed and not unverifiable and not it["violations"]:
            warnings.append(f"{iid}: technical_accuracy score {score} without a failed or unverifiable claim or a violation")
        for name, dim in it["dimensions"].items():
            m = _NEGATIVE.search(dim.get("rationale", "") or "")
            if dim.get("status") == "pass" and m:
                warnings.append(f"{iid}: {name} pass but rationale contains {m.group(0)!r} (keyword heuristic; review manually)")
    return {"errors": errors, "warnings": warnings}
