from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import checksums, context, evaluation, identity, metadata, metrics, packet, wordcount
from .fsutil import UnsafePath
from .schema import SchemaError, validate


def _fail(problems: list[str]) -> int:
    for p in problems:
        print(f"ERROR {p}", file=sys.stderr)
    return 1


def _load(path: str) -> packet.Dataset:
    return packet.load_dataset(Path(path))


def cmd_validate(a: argparse.Namespace) -> int:
    ds = _load(a.dataset)
    problems = packet.check_dataset(ds, verify_checksums=not a.no_checksums)
    if problems:
        return _fail(problems)
    print(f"OK {ds.data['dataset_id']}: {len(ds.cases)} cases, "
          f"{sum(len(c.data['items']) for c in ds.cases.values())} items, "
          f"manifest {checksums.manifest_digest(ds.root)}")
    return 0


def cmd_seal(a: argparse.Namespace) -> int:
    ds = _load(a.dataset)
    problems = packet.check_dataset(ds, verify_checksums=False)
    if problems:
        return _fail(problems)
    digest = packet.seal(ds)
    print(f"SEALED {ds.data['dataset_id']} manifest {digest}")
    return 0


def cmd_view(a: argparse.Namespace) -> int:
    ds = _load(a.dataset)
    problems = packet.check_dataset(ds)
    if problems:
        return _fail(problems)
    case = ds.cases[a.case]
    targets = [it["item_id"] for it in case.data["items"] if it["task"] == "rewrite"] if a.all else [a.item]
    if not a.all and not a.item:
        return _fail(["give --item or --all"])
    out = Path(a.out)
    summary = {}
    for iid in targets:
        dest = out / iid if a.all else out
        summary[iid] = packet.export_view(case, iid, dest, a.audience)
    print(json.dumps(summary, indent=2))
    return 0


def cmd_count(a: argparse.Namespace) -> int:
    opts = wordcount.Options(fenced_code=a.fenced_code, images=a.images)
    sources = a.files or ["-"]
    for s in sources:
        text = sys.stdin.read() if s == "-" else Path(s).read_text(encoding="utf-8")
        c = wordcount.count(text, opts)
        print(f"{c.words}\t{s}\tfenced_blocks={c.fenced_blocks} fenced_words={c.fenced_words} images={c.images} image_tokens={c.image_tokens}")
    return 0


def cmd_freeze(a: argparse.Namespace) -> int:
    path = Path(a.file)
    if a.schema:
        validate(json.loads(path.read_text(encoding="utf-8")), a.schema)
    digest = checksums.freeze(path)
    problems = checksums.verify_frozen(path)
    if problems:
        return _fail(problems)
    print(f"FROZEN {digest}  {path.name}")
    return 0


def cmd_verify_frozen(a: argparse.Namespace) -> int:
    problems = [p for f in a.files for p in checksums.verify_frozen(Path(f))]
    if problems:
        return _fail(problems)
    print(f"OK {len(a.files)} frozen file(s)")
    return 0


def cmd_metrics(a: argparse.Namespace) -> int:
    ds = _load(a.dataset)
    problems = packet.check_dataset(ds)
    if problems:
        return _fail(problems)
    for g in a.generation:
        if a.require_frozen:
            problems += checksums.verify_frozen(Path(g))
    if problems:
        return _fail(problems)
    opts = wordcount.Options(fenced_code=a.fenced_code, images=a.images)
    cases = list(ds.cases) if a.case == "all" else [a.case]
    results = {}
    for cid in cases:
        variants = a.variant if a.variant else [v for v in ds.cases[cid].variants if v != "original"]
        gens = [Path(g) for g in a.generation if json.loads(Path(g).read_text(encoding="utf-8"))["case_id"] == cid]
        results[cid] = metrics.compute(ds, cid, variants, gens, opts, Path(a.spec_root) if a.spec_root else None,
                                       Path(a.contexts_root) if a.contexts_root else None, a.allow_legacy)
    out = Path(a.out)
    if a.case == "all":
        out.mkdir(parents=True, exist_ok=True)
        for cid, r in results.items():
            digest = metrics.write(r, out / f"{cid}.metrics.json")
            rep = r["reproduction"]
            print(f"{cid}: {out / (cid + '.metrics.json')} sha256 {digest} reproduction {rep['matched']}/{rep['checked']}")
    else:
        r = results[a.case]
        digest = metrics.write(r, out)
        rep = r["reproduction"]
        print(f"{a.case}: {out} sha256 {digest} reproduction {rep['matched']}/{rep['checked']}")
    return 0


def cmd_meta(a: argparse.Namespace) -> int:
    print(json.dumps({"runner": metadata.runner(), "implementation": identity.fingerprint(),
                      "spec": metadata.spec(Path(a.spec_root) if a.spec_root else None),
                      "word_count": wordcount.describe()}, indent=2))
    return 0


def _candidates(case: packet.Case, variant: str | None, generation: str | None) -> dict[str, str] | None:
    if variant and generation:
        raise ValueError("give --candidate-variant or --candidate-generation, not both")
    if variant:
        v = case.variants[variant]
        return {it["item_id"]: packet.read_text(case.root, it["path"]) for it in v["items"]}
    if generation:
        g = json.loads(Path(generation).read_text(encoding="utf-8"))
        validate(g, "generation")
        if g["case_id"] != case.case_id:
            raise ValueError("candidate generation belongs to another case")
        return {it["item_id"]: it["text"] for it in g["items"]}
    return None


def cmd_context(a: argparse.Namespace) -> int:
    ds = _load(a.dataset)
    problems = packet.check_dataset(ds)
    if problems:
        return _fail(problems)
    case = ds.cases[a.case]
    cands = _candidates(case, a.candidate_variant, a.candidate_generation)
    out = Path(a.out)
    summary = {}
    if a.unit:
        targets = a.unit.split(",")
        summary[",".join(targets)] = context.build(ds, case, targets, a.audience, out, a.budget, cands)
    else:
        targets = a.item or [it["item_id"] for it in case.data["items"] if it["task"] == "rewrite"]
        for iid in targets:
            summary[iid] = context.build(ds, case, [iid], a.audience, out / iid, a.budget, cands)
    print(json.dumps(summary, indent=2))
    return 0


def cmd_check_evaluation(a: argparse.Namespace) -> int:
    ds = _load(a.dataset)
    problems = packet.check_dataset(ds)
    if problems:
        return _fail(problems)
    ev = json.loads(Path(a.file).read_text(encoding="utf-8"))
    report = evaluation.check(ev, ds, Path(a.spec_root), Path(a.contexts_root) if a.contexts_root else None, a.item)
    print(json.dumps(report, indent=2))
    return 1 if report["errors"] else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ceebench", description="CEE benchmark runner (MVP)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("validate", help="validate schemas, tiers and checksums of a dataset")
    s.add_argument("dataset")
    s.add_argument("--no-checksums", action="store_true")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("seal", help="write case and dataset checksum manifests")
    s.add_argument("dataset")
    s.set_defaults(func=cmd_seal)

    s = sub.add_parser("view", help="export the time-bounded generator view for an item")
    s.add_argument("dataset")
    s.add_argument("--case", required=True)
    s.add_argument("--item")
    s.add_argument("--all", action="store_true", help="one view per rewrite item, in <out>/<item_id>/")
    s.add_argument("--audience", choices=["generator", "evaluator"], default="generator",
                   help="generator views exclude secondary evidence (selected from candidates or prior evaluations)")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_view)

    for name, func, helptext in (("count", cmd_count, "count words in files or stdin"),):
        s = sub.add_parser(name, help=helptext)
        s.add_argument("files", nargs="*")
        s.add_argument("--fenced-code", choices=["exclude", "include"], default="exclude")
        s.add_argument("--images", choices=["exclude", "include"], default="exclude")
        s.set_defaults(func=func)

    s = sub.add_parser("freeze", help="write <file>.sha256 and make both read-only")
    s.add_argument("file")
    s.add_argument("--schema", choices=["generation", "metrics"], help="validate before freezing")
    s.set_defaults(func=cmd_freeze)

    s = sub.add_parser("verify-frozen", help="verify frozen files and their .sha256")
    s.add_argument("files", nargs="+")
    s.set_defaults(func=cmd_verify_frozen)

    s = sub.add_parser("metrics", help="compute structured word-count metrics")
    s.add_argument("dataset")
    s.add_argument("--case", required=True, help="case id or 'all'")
    s.add_argument("--variant", action="append", default=[], help="dataset variant id (default: all)")
    s.add_argument("--generation", action="append", default=[], help="generation.json produced outside the dataset")
    s.add_argument("--require-frozen", action="store_true", help="refuse generation files that are not frozen")
    s.add_argument("--contexts-root", help="directory with <item_id>/ generator contexts bound by generation/2 files")
    s.add_argument("--allow-legacy", action="store_true", help="accept generation/1 files as legacy imports with incomplete provenance")
    s.add_argument("--spec-root", help="CEE specification repository, for version and commit metadata")
    s.add_argument("--fenced-code", choices=["exclude", "include"], default="exclude")
    s.add_argument("--images", choices=["exclude", "include"], default="exclude")
    s.add_argument("--out", required=True, help="file, or directory when --case all")
    s.set_defaults(func=cmd_metrics)

    s = sub.add_parser("context", help="build focused, temporally isolated contexts (case/2 datasets)")
    s.add_argument("dataset")
    s.add_argument("--case", required=True)
    s.add_argument("--item", action="append", help="target item; repeat for several separate contexts (default: all rewrite items)")
    s.add_argument("--unit", help="comma-separated items evaluated together; accepted only if posted at the same instant")
    s.add_argument("--audience", choices=["generator", "evaluator"], default="generator")
    s.add_argument("--budget", type=int, default=None, help="character budget; required evidence is never dropped (the command fails instead)")
    s.add_argument("--candidate-variant", help="evaluator only: dataset variant whose target text is included")
    s.add_argument("--candidate-generation", help="evaluator only: generation file whose target text is included")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_context)

    s = sub.add_parser("check-evaluation", help="deterministic validation of an evaluation/1 file")
    s.add_argument("dataset")
    s.add_argument("file")
    s.add_argument("--spec-root", required=True)
    s.add_argument("--contexts-root", help="directory with <item_id>/ evaluator contexts bound by the evaluation")
    s.add_argument("--item", action="append", help="expected item; repeat for an explicit evaluation unit or subset")
    s.set_defaults(func=cmd_check_evaluation)

    s = sub.add_parser("meta", help="print runner, specification and word-count metadata")
    s.add_argument("--spec-root")
    s.set_defaults(func=cmd_meta)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except SchemaError as e:
        return _fail(e.errors)
    except context.InsufficientBudget as e:
        return _fail([f"insufficient coverage: {e}"])
    except (FileExistsError, FileNotFoundError, KeyError, ValueError, UnsafePath) as e:
        return _fail([str(e)])
