import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ceebench import checksums, context, evaluation, identity, metrics, packet, wordcount
from ceebench.fsutil import UnsafePath
from ceebench.schema import SchemaError

T0 = "2030-01-01T08:00:00Z"
T_REV1 = "2030-01-01T09:00:00Z"
T_I1 = "2030-01-01T10:00:00Z"
T_CI1 = "2030-01-01T09:30:00Z"
T_REV2 = "2030-01-01T12:00:00Z"
T_I2 = "2030-01-01T13:00:00Z"
T_CI2 = "2030-01-01T14:00:00Z"

DIFF1 = "diff --git a/src/a.py b/src/a.py\n+def f(): return None\ndiff --git a/src/z.py b/src/z.py\n+UNRELATED = 1\n"
DIFF2 = "diff --git a/src/a.py b/src/a.py\n+def f(): return 1\ndiff --git a/src/z.py b/src/z.py\n+UNRELATED = 2\n"


def write(root: Path, rel: str, data) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        data = data.encode()
    p.write_bytes(data)


def blob(case: Path, content: str) -> str:
    h = hashlib.sha256(content.encode()).hexdigest()
    write(case, f"evidence/blobs/{h}", content)
    return h


def sel(sid, h, rev, at, path, basis, method, ref, relevant, availability="verified", kind="file_snapshot"):
    return {"selection_id": sid, "blob": h, "kind": kind, "repository": "example/repo", "revision": rev, "source_path": path,
            "basis": basis, "method": method, "referenced_by": ref, "relevant_items": relevant, "available_at": at,
            "availability_basis": availability}


def build_v2(root: Path, mutate=None) -> Path:
    case = root / "cases/c"
    write(case, "generator/items/I1.md", "`src/a.py` returns None.")
    write(case, "generator/items/I2.md", "Fixed in rev2.")
    write(case, "generator/items/I3.md", "Another reply at the same instant.")
    write(case, "generator/context/description-01.md", "first description")
    write(case, "generator/context/description-02.md", "second description")
    write(case, "evidence/diffs/rev1.diff", DIFF1)
    write(case, "evidence/diffs/rev2.diff", DIFF2)
    write(case, "evidence/ci/rev1.json", '{"state": "SUCCESSFUL"}')
    write(case, "evidence/ci/rev2.json", '{"state": "FAILED-LATER"}')
    write(case, "outcomes/merge.json", '{"merged": true}')
    write(case, "reference/sample.json", json.dumps({"schema": "ceebench/sample/1", "case_id": "c", "status": "reported_judgment",
                                                     "samples": [{"sample_id": "s", "items": [{"item_id": "I1", "group": "finding"}]}]}))
    write(case, "reference/variants/v/I1.md", "candidate one")
    write(case, "reference/variants/v/I2.md", "candidate two LATER")
    write(case, "reference/variants/v/variant.json", json.dumps({"schema": "ceebench/variant/1", "case_id": "c", "variant_id": "v",
        "status": "reported_output", "items": [{"item_id": "I1", "path": "reference/variants/v/I1.md"},
                                               {"item_id": "I2", "path": "reference/variants/v/I2.md"}]}))
    a1 = blob(case, "def f(): return None\n")
    a2 = blob(case, "def f(): return 1\n")
    shared = blob(case, "SHARED CONTENT\n")
    dep = blob(case, "DEPENDENCY " * 50 + "\n")
    ext = blob(case, "external\n")
    unk = blob(case, "unknown availability\n")
    selections = [
        sel("s-a1", a1, "rev1", T_REV1, "src/a.py", "primary", "path_reference", "I1", ["I1"]),
        sel("s-a2", a2, "rev2", T_REV2, "src/a.py", "primary", "changed_file", "diff:rev2", ["I2"]),
        sel("s-sh1", shared, "rev1", T_REV1, "src/shared.py", "secondary", "path_reference", "prior:report.md", ["I1"]),
        sel("s-sh2", shared, "rev2", T_REV2, "src/shared.py", "primary", "path_reference", "I2", ["I2"]),
        sel("s-dep", dep, "rev1", T_REV1, "src/dep.py", "primary", "php_use_dependency", "diff:rev1", ["I1"]),
        sel("s-ext", ext, "erev", "2030-01-01T07:00:00Z", "lib/x.c", "primary", "path_reference_external", "I1", ["I1"], "reconstructed"),
        sel("s-unk", unk, "urev", "2030-01-01T07:00:00Z", "lib/u.c", "primary", "path_reference_external", "I1", ["I1"], "unknown"),
    ]
    blobs = sorted({s["blob"] for s in selections})
    V = {"availability_basis": "verified"}
    files = [
        {"path": "generator/items/I1.md", "tier": "generator_input", "kind": "original", "available_at": T_I1, "item_ids": ["I1"], **V},
        {"path": "generator/items/I2.md", "tier": "generator_input", "kind": "original", "available_at": T_I2, "item_ids": ["I2"], **V},
        {"path": "generator/items/I3.md", "tier": "generator_input", "kind": "original", "available_at": T_I2, "item_ids": ["I3"], **V},
        {"path": "generator/context/description-01.md", "tier": "generator_input", "kind": "pr_description", "available_at": T0, **V},
        {"path": "generator/context/description-02.md", "tier": "generator_input", "kind": "pr_description", "available_at": T_REV2, **V},
        {"path": "evidence/diffs/rev1.diff", "tier": "review_time", "kind": "diff", "available_at": T_REV1, "revision": "rev1", **V},
        {"path": "evidence/diffs/rev2.diff", "tier": "review_time", "kind": "diff", "available_at": T_REV2, "revision": "rev2", **V},
        {"path": "evidence/ci/rev1.json", "tier": "review_time", "kind": "ci_status", "available_at": T_CI1, "revision": "rev1", **V},
        {"path": "evidence/ci/rev2.json", "tier": "review_time", "kind": "ci_status", "available_at": T_CI2, "revision": "rev2", **V},
        {"path": "outcomes/merge.json", "tier": "outcome", "kind": "merge"},
        {"path": "reference/sample.json", "tier": "evaluator_only", "kind": "sample"},
        {"path": "reference/variants/v/I1.md", "tier": "evaluator_only", "kind": "variant_text"},
        {"path": "reference/variants/v/I2.md", "tier": "evaluator_only", "kind": "variant_text"},
        {"path": "reference/variants/v/variant.json", "tier": "evaluator_only", "kind": "variant"},
    ] + [{"path": f"evidence/blobs/{h}", "tier": "review_time", "kind": "blob"} for h in blobs]
    data = {
        "schema": "ceebench/case/2", "case_id": "c", "publishable": True,
        "source": {"system": "synthetic", "repository": "example/repo", "change_id": "1"},
        "items": [
            {"item_id": "I1", "role": "review_comment", "author_role": "reviewer", "posted_at": T_I1, "reviewed_revision": "rev1",
             "anchor": {"path": "src/a.py", "line": 1}, "original": "generator/items/I1.md", "task": "rewrite"},
            {"item_id": "I2", "parent_item": "I1", "role": "author_reply", "author_role": "author", "posted_at": T_I2,
             "reviewed_revision": "rev2", "original": "generator/items/I2.md", "task": "rewrite"},
            {"item_id": "I3", "role": "review_comment", "author_role": "reviewer", "posted_at": T_I2,
             "reviewed_revision": "rev2", "original": "generator/items/I3.md", "task": "rewrite"}],
        "files": files, "selections": selections,
        "retrieval_log": [{"target": "symbol Foo", "status": "unresolved", "note": "I1@rev1"},
                          {"target": "symbol Bar", "status": "unresolved", "note": "I2@rev2"}]}
    if mutate:
        mutate(data, case)
    write(case, "case.json", json.dumps(data))
    write(root, "dataset.json", json.dumps({"schema": "ceebench/dataset/1", "dataset_id": "d", "publishable": True,
                                             "cases": [{"case_id": "c", "path": "cases/c"}]}))
    return root


def fake_spec(root: Path) -> Path:
    write(root, "VERSION", "9.9.9\n")
    write(root, "spec/core.md", "- **CORE-001 (MUST):** a\n- **CORE-008 (SHOULD):** b\n")
    write(root, "spec/reviews.md", "- **REV-001 (MUST):** c\n")
    write(root, "spec/replies.md", "- **REPLY-002 (MUST):** d\n")
    write(root, "spec/agents.md", "- **AI-007 (MUST NOT):** e\n")
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
    for cmd in (["init", "-q"], ["add", "."], ["commit", "-q", "-m", "spec"]):
        subprocess.run(["git", "-C", str(root), *cmd], check=True, env=env, capture_output=True)
    return root


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)
        self.root = build_v2(self.t / "ds")
        packet.seal(packet.load_dataset(self.root))
        self.ds = packet.load_dataset(self.root)
        self.case = self.ds.cases["c"]

    def tearDown(self):
        for p in self.t.rglob("*"):
            if p.is_file() and not p.is_symlink():
                os.chmod(p, 0o600)
        self.tmp.cleanup()

    def files(self, out: Path) -> set[str]:
        return {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}


class F02Seal(Base):
    def test_valid_and_sealed(self):
        self.assertEqual(packet.check_dataset(self.ds), [])

    def test_reseal_refused(self):
        with self.assertRaises(FileExistsError):
            packet.seal(self.ds)

    def test_tamper_detected_and_not_resealable(self):
        (self.case.root / "evidence/diffs/rev1.diff").write_text("tampered")
        self.assertTrue(any("checksum mismatch" in p for p in packet.check_dataset(packet.load_dataset(self.root))))
        with self.assertRaises(FileExistsError):
            packet.seal(packet.load_dataset(self.root))


class F04Symlinks(Base):
    def test_symlinked_dataset_root_rejected(self):
        alias = self.t / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(UnsafePath):
            packet.load_dataset(alias)
        self.assertTrue(any("symlinked root" in p for p in checksums.verify_manifest(alias)))

    def test_symlinked_file_rejected_and_not_exported(self):
        outside = self.t / "secret.txt"
        outside.write_text("SECRET")
        target = self.case.root / "evidence/diffs/rev1.diff"
        target.unlink()
        os.symlink(outside, target)
        with self.assertRaises(UnsafePath):
            packet.load_dataset(self.root)
        with self.assertRaises(UnsafePath):
            packet.export_view(self.case, "I1", self.t / "v")
        self.assertFalse((self.t / "v/files/evidence/diffs/rev1.diff").exists())

    def test_symlinked_directory_rejected(self):
        os.symlink(self.case.root / "reference", self.case.root / "evidence/ref")
        with self.assertRaises(UnsafePath):
            packet.load_dataset(self.root)
        self.assertTrue(any("symlink" in p for p in packet.check_case(self.case)))

    def test_symlinked_case_json_rejected(self):
        real = self.case.root / "case.json"
        copy_ = self.t / "case.json"
        copy_.write_bytes(real.read_bytes())
        real.unlink()
        os.symlink(copy_, real)
        with self.assertRaises(UnsafePath):
            packet.load_dataset(self.root)

    def test_unsafe_relative_paths_rejected(self):
        from ceebench.fsutil import check_relative
        for bad in ("../x", "a/../b", "/abs", "a//b", "./a", "a\\b"):
            with self.assertRaises(UnsafePath):
                check_relative(bad)


class F05Duplicates(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_duplicate_case_entries(self):
        root = build_v2(self.t / "a")
        d = json.loads((root / "dataset.json").read_text())
        d["cases"].append(dict(d["cases"][0]))
        (root / "dataset.json").write_text(json.dumps(d))
        with self.assertRaises(SchemaError):
            packet.load_dataset(root)

    def test_duplicate_variant_id_across_files(self):
        def m(data, case):
            write(case, "reference/variants/w/variant.json", (case / "reference/variants/v/variant.json").read_text())
            data["files"].append({"path": "reference/variants/w/variant.json", "tier": "evaluator_only", "kind": "variant"})
        with self.assertRaises(SchemaError):
            packet.load_dataset(build_v2(self.t / "b", m))

    def test_duplicate_ids_reported(self):
        def m(data, case):
            data["selections"].append(copy.deepcopy(data["selections"][0]))
            data["snapshots"] = [{"snapshot_id": "x", "repository": "r", "revision": "rev1", "available_at": T0}] * 2
            s = json.loads((case / "reference/sample.json").read_text())
            s["samples"].append({"sample_id": "s", "items": [{"item_id": "I1", "group": "author_reply"}]})
            s["excluded"] = [{"item_id": "I3", "reason": "x"}, {"item_id": "I3", "reason": "y"}]
            write(case, "reference/sample.json", json.dumps(s))
            v = json.loads((case / "reference/variants/v/variant.json").read_text())
            v["items"].append(dict(v["items"][0]))
            write(case, "reference/variants/v/variant.json", json.dumps(v))
        ds = packet.load_dataset(build_v2(self.t / "c", m))
        text = "\n".join(packet.check_dataset(ds, verify_checksums=False))
        for needle in ("duplicate selection id", "duplicate snapshot id", "duplicate sample id",
                       "appears more than once across samples", "duplicate excluded item", "has duplicate item"):
            self.assertIn(needle, text)


class F06Fingerprint(Base):
    def test_deterministic_and_recorded(self):
        a, b = identity.fingerprint(), identity.fingerprint()
        self.assertEqual(a, b)
        self.assertRegex(a["sha256"], "^[0-9a-f]{64}$")
        packet.export_view(self.case, "I1", self.t / "v")
        self.assertEqual(json.loads((self.t / "v/view.json").read_text())["runner_fingerprint"], a["sha256"])


class F08Temporal(Base):
    def ctx(self, targets, audience="evaluator", budget=None, cands=True, name="x"):
        c = {"I1": "candidate one", "I2": "candidate two LATER", "I3": "candidate three LATER"} if cands and audience == "evaluator" else None
        out = self.t / name
        context.build(self.ds, self.case, targets, audience, out, budget, c)
        return out, json.loads((out / "context.json").read_text())

    def test_earlier_target_sees_nothing_later(self):
        out, doc = self.ctx(["I1"])
        blob = "".join(p.read_text(errors="replace") for p in out.rglob("*") if p.is_file())
        self.assertNotIn("Fixed in rev2", blob)
        self.assertNotIn("LATER", blob)
        self.assertNotIn("FAILED-LATER", blob)
        self.assertNotIn("return 1", blob)
        self.assertNotIn("second description", blob)
        self.assertFalse((out / "files/evidence/selected/repo/rev2").exists())

    def test_view_of_earlier_target_sees_nothing_later(self):
        out = self.t / "v"
        packet.export_view(self.case, "I1", out, "evaluator")
        blob = "".join(p.read_text(errors="replace") for p in out.rglob("*") if p.is_file())
        for later in ("Fixed in rev2", "FAILED-LATER", "return 1", "second description"):
            self.assertNotIn(later, blob)

    def test_unit_with_different_times_rejected(self):
        with self.assertRaises(ValueError):
            self.ctx(["I1", "I2"])

    def test_unit_with_same_instant_accepted(self):
        _, doc = self.ctx(["I2", "I3"], name="u")
        self.assertEqual(doc["targets"], ["I2", "I3"])

    def test_unit_with_conflicting_reviewed_revisions_rejected(self):
        self.case.item("I3")["reviewed_revision"] = "rev1"
        with self.assertRaises(ValueError):
            self.ctx(["I2", "I3"], name="conflict")

    def test_same_instant_non_member_excluded(self):
        out, doc = self.ctx(["I2"], name="s")
        self.assertFalse((out / "files/items/I3.md").exists())
        self.assertTrue(any("same instant" in o["reason"] for o in doc["omitted"]))


class F0311Focused(Base):
    def test_prior_report_selection_does_not_become_required(self):
        out = self.t / "prior"
        context.build(self.ds, self.case, ["I1"], "evaluator", out)
        doc = json.loads((out / "context.json").read_text())
        self.assertFalse(any(e.get("source_path") == "src/shared.py" for e in doc["included"]))
        self.assertTrue(any("shared.py" in o["ref"] for o in doc["omitted"]))

    def test_incidental_dependency_reference_is_optional(self):
        data = copy.deepcopy(self.case.data)
        dep = next(s for s in data["selections"] if s["selection_id"] == "s-dep")
        dep["referenced_by"] = "I1"
        case = packet.Case(self.case.root, data)
        out = self.t / "weak"
        context.build(self.ds, case, ["I1"], "generator", out)
        doc = json.loads((out / "context.json").read_text())
        self.assertFalse(any(e.get("source_path") == "src/dep.py" for e in doc["included"]))
        self.assertTrue(any("dep.py" in e["ref"] and e["reason"] == "not referenced by the target or required discussion" for e in doc["omitted"]))

    def test_only_target_revision_diff_and_latest_file(self):
        out = self.t / "c2"
        context.build(self.ds, self.case, ["I2"], "generator", out)
        doc = json.loads((out / "context.json").read_text())
        paths = [i["path"] for i in doc["included"]]
        self.assertFalse(any("/rev1/" in p and p.startswith("files/diff/") for p in paths))
        self.assertTrue(any(o["reason"].startswith("cumulative diff of an earlier") for o in doc["omitted"]))
        self.assertTrue(any(o["reason"].startswith("superseded by revision") for o in doc["omitted"]))
        self.assertTrue(any(o["reason"].startswith("CI status of another revision") for o in doc["omitted"]))
        self.assertIn("files/generator/context/description-02.md", paths)
        self.assertNotIn("files/generator/context/description-01.md", paths)

    def test_diff_sections_prioritised(self):
        out = self.t / "c1"
        context.build(self.ds, self.case, ["I1"], "generator", out)
        inc = {i["path"]: i["priority"] for i in json.loads((out / "context.json").read_text())["included"]}
        self.assertEqual(inc["files/diff/rev1/src/a.py.diff"], "required")
        self.assertNotIn("files/diff/rev1/src/z.py.diff", inc)

    def test_budget_drops_optional_with_reason_and_never_required(self):
        out = self.t / "b"
        unlimited = self.t / "unlimited"
        context.build(self.ds, self.case, ["I1"], "generator", unlimited)
        full = json.loads((unlimited / "context.json").read_text())
        context.build(self.ds, self.case, ["I1"], "generator", out, budget=full["sizes"]["required_chars"] + 1)
        doc = json.loads((out / "context.json").read_text())
        self.assertTrue(any(o["reason"] == "context budget" for o in doc["omitted"]))
        self.assertEqual(doc["coverage"], "insufficient_evidence")
        required = {i["path"] for i in json.loads((unlimited / "context.json").read_text())["included"]
                    if i["priority"] == "required"}
        self.assertTrue(required <= {i["path"] for i in doc["included"]})
        with self.assertRaises(context.InsufficientBudget):
            context.build(self.ds, self.case, ["I1"], "generator", self.t / "b2", budget=10)

    def test_gaps_are_item_scoped(self):
        out = self.t / "g"
        context.build(self.ds, self.case, ["I1"], "generator", out)
        gaps = [g["target"] for g in json.loads((out / "context.json").read_text())["gaps"]]
        self.assertIn("symbol Foo", gaps)
        self.assertNotIn("symbol Bar", gaps)
        self.assertEqual(json.loads((out / "context.json").read_text())["coverage"], "insufficient_evidence")

    def test_requires_case_v2(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import test_runner
        root = test_runner.build(self.t / "legacy")
        ds = packet.load_dataset(root)
        with self.assertRaises(ValueError):
            context.build(ds, ds.cases["demo-1"], ["C1"], "generator", self.t / "l")


class F09Availability(Base):
    def test_unknown_excluded_reconstructed_labelled(self):
        out = self.t / "a"
        context.build(self.ds, self.case, ["I1"], "generator", out)
        doc = json.loads((out / "context.json").read_text())
        inc = {i["path"]: i for i in doc["included"]}
        self.assertNotIn("files/evidence/selected/repo/urev/lib/u.c", inc)
        self.assertEqual(inc["files/evidence/selected/repo/erev/lib/x.c"]["availability_basis"], "reconstructed")
        self.assertTrue(any("availability unknown" in g["note"] for g in doc["gaps"]))
        v = self.t / "v"
        packet.export_view(self.case, "I1", v)
        view = json.loads((v / "view.json").read_text())
        self.assertTrue(any("availability unknown" in g for g in view["gaps"]))

    def test_case_v2_requires_availability_basis(self):
        def m(data, case):
            del data["files"][0]["availability_basis"]
        ds = packet.load_dataset(build_v2(self.t / "nb", m))
        self.assertTrue(any("needs availability_basis" in p for p in packet.check_dataset(ds, verify_checksums=False)))


class F10Dedup(Base):
    def test_earlier_secondary_not_promoted_by_later_primary(self):
        out = self.t / "g1"
        context.build(self.ds, self.case, ["I1"], "generator", out)
        self.assertNotIn("SHARED CONTENT", "".join(p.read_text(errors="replace") for p in out.rglob("*") if p.is_file()))
        v = self.t / "v1"
        packet.export_view(self.case, "I1", v, "generator")
        self.assertNotIn("SHARED CONTENT", "".join(p.read_text(errors="replace") for p in v.rglob("*") if p.is_file()))
        out2 = self.t / "g2"
        context.build(self.ds, self.case, ["I2"], "generator", out2)
        self.assertTrue((out2 / "files/evidence/selected/repo/rev2/src/shared.py").exists())

    def test_one_blob_two_selection_records(self):
        recs = [s for s in self.case.data["selections"] if s["source_path"] == "src/shared.py"]
        self.assertEqual(len(recs), 2)
        self.assertEqual(len({s["blob"] for s in recs}), 1)
        self.assertEqual({s["basis"] for s in recs}, {"primary", "secondary"})

    def test_basis_must_match_reference_kind(self):
        def m(data, case):
            data["selections"][2]["basis"] = "primary"
        ds = packet.load_dataset(build_v2(self.t / "p", m))
        self.assertTrue(any("is primary but referenced_by" in p for p in packet.check_dataset(ds, verify_checksums=False)))

    def test_blob_name_must_match_content(self):
        def m(data, case):
            h = data["selections"][0]["blob"]
            (case / f"evidence/blobs/{h}").write_text("changed")
        ds = packet.load_dataset(build_v2(self.t / "bn", m))
        self.assertTrue(any("does not match its name" in p for p in packet.check_dataset(ds, verify_checksums=False)))


def good_evaluation(binding: dict, item: str = "I1") -> dict:
    def d(s=4):
        return {"status": "pass", "score": s, "rationale": "ok"}
    return {"schema": "ceebench/evaluation/1", "publishable": False, "binding": binding,
            "evaluator": {"model_id": "m"},
            "items": [{"item_id": item,
                       "claims": [{"text": "c1", "technical_correctness": "pass", "evidence_sufficiency": "pass", "origin": "preserved"}],
                       "dimensions": {"technical_accuracy": d(), "evidence_support": d(), "trigger_preservation": {"status": "pass"},
                                      "unsupported_claims_and_commitments": {"status": "pass"}, "classification_and_severity": {"status": "pass"},
                                      "actionability": d(), "clarity_and_efficiency": d(), "relevance": {"score": 4}, "density": {"score": 4}},
                       "rule_results": [{"rule_id": r, "level": l, "result": "pass"} for r, l in
                                        (("CORE-001", "MUST"), ("CORE-008", "SHOULD"), ("REV-001", "MUST"), ("AI-007", "MUST NOT"))],
                       "violations": [], "corrected_errors": [], "unverifiable_claims": []}]}


class F01F13Binding(Base):
    def setUp(self):
        super().setUp()
        self.spec = fake_spec(self.t / "spec")
        commit = subprocess.run(["git", "-C", str(self.spec), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        self.ctxroot = self.t / "ctx"
        d1 = context.build(self.ds, self.case, ["I1"], "generator", self.ctxroot / "I1")["context_digest"]
        self.ectx = self.t / "ectx"
        e1 = context.build(self.ds, self.case, ["I1"], "evaluator", self.ectx / "I1", None, {"I1": "cand"})["context_digest"]
        base = {"dataset_id": "d", "dataset_manifest_sha256": checksums.manifest_digest(self.root), "case_id": "c",
                "spec": {"version": "9.9.9", "commit": commit}, "runner_fingerprint": identity.fingerprint()["sha256"]}
        self.gbind = {**base, "contexts": {"I1": d1}}
        self.ebind = {**base, "contexts": {"I1": e1}, "prompt_builder_sha256": "a" * 64, "instructions_sha256": "b" * 64}

    def gen(self, binding, items=None, schema="ceebench/generation/2"):
        g = {"schema": schema, "case_id": "c", "variant_id": "g", "cee": {"version": "9.9.9"}, "model": {"name": "m", "id": "m"},
             "generated_at": T_I2, "publishable": False, "binding": binding,
             "items": items or [{"item_id": "I1", "text": "rewritten"}]}
        p = self.t / f"gen-{len(list(self.t.glob('gen-*')))}.json"
        p.write_text(json.dumps(g))
        return p

    def compute(self, path, **kw):
        return metrics.compute(self.ds, "c", [], [path], wordcount.Options(), self.spec, self.ctxroot, **kw)

    def test_bound_generation_accepted(self):
        m = self.compute(self.gen(self.gbind))
        self.assertEqual(next(v for v in m["variants"] if v["variant_id"] == "g")["binding"], "verified")

    def test_mismatches_rejected(self):
        bad = [dict(self.gbind, dataset_manifest_sha256="0" * 64), dict(self.gbind, runner_fingerprint="0" * 64),
               dict(self.gbind, contexts={"I1": "0" * 64}), dict(self.gbind, spec={"version": "0.0.0", "commit": "x"}),
               dict(self.gbind, dataset_id="other")]
        for b in bad:
            with self.assertRaises(metrics.BindingError):
                self.compute(self.gen(b))

    def test_conflicting_specification_metadata_rejected(self):
        for cee in ({"version": "other"}, {"version": "9.9.9", "spec_commit": "other"}):
            path = self.gen(self.gbind)
            gen = json.loads(path.read_text())
            gen["cee"] = cee
            path.write_text(json.dumps(gen))
            with self.assertRaisesRegex(metrics.BindingError, "metadata conflicts"):
                self.compute(path)

    def test_context_binding_identity_rejected(self):
        for root, binding, audience in ((self.ctxroot, self.gbind, "generator"),
                                        (self.ectx, self.ebind, "evaluator")):
            for key in ("dataset_id", "case_id", "runner_fingerprint"):
                ctxdir = root / "I1"
                path = ctxdir / "context.json"
                original = path.read_text()
                ctx = json.loads(original)
                ctx["binding"][key] = "other"
                path.write_text(json.dumps(ctx))
                digest = checksums.write_manifest(ctxdir, checksums.list_files(ctxdir))
                altered = dict(binding, contexts={"I1": digest})
                if audience == "generator":
                    with self.assertRaises(metrics.BindingError):
                        self.compute(self.gen(altered))
                else:
                    self.assertTrue(self.check(good_evaluation(altered))["errors"])
                path.write_text(original)
                checksums.write_manifest(ctxdir, checksums.list_files(ctxdir))

    def test_unknown_and_duplicate_items_rejected(self):
        with self.assertRaises(metrics.BindingError):
            self.compute(self.gen(self.gbind, [{"item_id": "NOPE", "text": "x"}]))
        with self.assertRaises(metrics.BindingError):
            self.compute(self.gen(self.gbind, [{"item_id": "I1", "text": "x"}, {"item_id": "I1", "text": "y"}]))

    def test_legacy_requires_explicit_flag(self):
        p = self.gen(None, schema="ceebench/generation/1")
        data = json.loads(p.read_text())
        del data["binding"]
        p.write_text(json.dumps(data))
        with self.assertRaises(metrics.BindingError):
            self.compute(p)
        m = self.compute(p, allow_legacy=True)
        self.assertIn("legacy import", next(v for v in m["variants"] if v["variant_id"] == "g")["binding"])

    def check(self, ev):
        return evaluation.check(ev, self.ds, self.spec, self.ectx)

    def test_good_evaluation(self):
        self.assertEqual(self.check(good_evaluation(self.ebind))["errors"], [])

    def test_expected_coverage_cannot_be_redefined_by_output(self):
        ev = good_evaluation(self.ebind)
        result = evaluation.check(ev, self.ds, self.spec, self.ectx, ["I1", "I2"])
        self.assertTrue(any("expected items" in e for e in result["errors"]))

    def test_invalid_scores_statuses_and_claim_dimensions(self):
        for field, value in (("score", -1), ("score", 6), ("score", True), ("status", "maybe")):
            ev = good_evaluation(self.ebind)
            ev["items"][0]["dimensions"]["technical_accuracy"][field] = value
            self.assertTrue(self.check(ev)["errors"])
        ev = good_evaluation(self.ebind)
        ev["items"][0]["claims"][0].update(technical_correctness="unverifiable", evidence_sufficiency="fail")
        self.assertTrue(any("evidence_support" in e for e in self.check(ev)["errors"]))

    def test_evaluation_errors(self):
        cases = []
        e = good_evaluation(self.ebind); e["items"][0]["rule_results"][2]["level"] = "SHOULD"; cases.append((e, "level"))
        e = good_evaluation(self.ebind); e["items"][0]["rule_results"].pop(); cases.append((e, "missing applicable"))
        e = good_evaluation(self.ebind); e["items"][0]["rule_results"][0]["result"] = "fail"; cases.append((e, "without a violation"))
        e = good_evaluation(self.ebind); e["items"][0]["violations"].append({"rule_id": "CORE-008", "level": "MUST", "text": "t", "evidence": "e",
            "reasoning": "r", "confidence": "low", "comparative_status": "preserved"}); cases.append((e, "specification says SHOULD"))
        e = good_evaluation(self.ebind); e["items"][0]["claims"][0].update(evidence_sufficiency="fail"); cases.append((e, "insufficiently evidenced"))
        e = good_evaluation(self.ebind); e["items"].append(copy.deepcopy(e["items"][0])); cases.append((e, "duplicate evaluation item"))
        e = good_evaluation(self.ebind); e["binding"] = dict(self.ebind, contexts={"I1": "0" * 64}); cases.append((e, "digest mismatch"))
        e = good_evaluation(self.ebind); e["items"][0]["claims"][0]["technical_correctness"] = "fail"; cases.append((e, "pass with 1 failed"))
        for ev, needle in cases:
            errs = "\n".join(self.check(ev)["errors"])
            self.assertIn(needle, errs, needle)

    def test_zero_score_is_a_score(self):
        e = good_evaluation(self.ebind)
        e["items"][0]["dimensions"]["technical_accuracy"]["score"] = 0
        r = self.check(e)
        self.assertEqual(r["errors"], [])
        self.assertTrue(any("score 0" in w for w in r["warnings"]))

    def test_keyword_heuristic_is_warning_only(self):
        e = good_evaluation(self.ebind)
        e["items"][0]["dimensions"]["actionability"]["rationale"] = "nothing is incorrect here"
        r = self.check(e)
        self.assertEqual(r["errors"], [])
        self.assertTrue(any("keyword heuristic" in w for w in r["warnings"]))

    def test_preserved_violation_is_absolute(self):
        e = good_evaluation(self.ebind)
        e["items"][0]["rule_results"][0]["result"] = "fail"
        e["items"][0]["violations"].append({"rule_id": "CORE-001", "level": "MUST", "text": "t", "evidence": "e",
                                            "reasoning": "inherited from the original", "confidence": "high", "comparative_status": "preserved"})
        self.assertEqual(self.check(e)["errors"], [])


if __name__ == "__main__":
    unittest.main()
