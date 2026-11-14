import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ceebench import packet
from ceebench.schema import SchemaError

T_REV1 = "2030-01-01T09:00:00Z"
T_ITEM1 = "2030-01-01T10:00:00Z"
T_REV2 = "2030-01-01T12:00:00Z"
T_ITEM2 = "2030-01-01T13:00:00Z"
BLOB = "0" * 40


def write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def snapshot(path: str, rev: str, at: str, basis: str, refs: list[str]) -> dict:
    return {"path": path, "tier": "review_time", "kind": "file_snapshot", "available_at": at,
            "selection": {"basis": basis, "method": "test", "repository": "example/repo", "revision": rev,
                          "source_path": "src/a.py", "git_blob": BLOB, "referenced_by": refs}}


def build(root: Path, files_override=None) -> Path:
    case = root / "cases/c"
    write(case, "generator/items/I1.md", "`a.py` returns None.")
    write(case, "generator/items/I2.md", "Fixed in rev2.")
    write(case, "evidence/files/rev1/src/a.py", "def f(): return None\n")
    write(case, "evidence/files/rev2/src/a.py", "def f(): return 1\n")
    write(case, "evidence/files/rev1/src/b.py", "def g(): pass\n")
    write(case, "outcomes/merged/src/a.py", "def f(): return 2\n")
    write(case, "reference/sample.json", json.dumps({"schema": "ceebench/sample/1", "case_id": "c", "status": "reported_judgment",
                                                     "samples": [{"sample_id": "s", "items": [{"item_id": "I1", "group": "finding"}]}]}))
    files = files_override or [
        {"path": "generator/items/I1.md", "tier": "generator_input", "kind": "original", "available_at": T_ITEM1, "item_ids": ["I1"]},
        {"path": "generator/items/I2.md", "tier": "generator_input", "kind": "original", "available_at": T_ITEM2, "item_ids": ["I2"]},
        snapshot("evidence/files/rev1/src/a.py", "rev1", T_REV1, "primary", ["I1"]),
        snapshot("evidence/files/rev2/src/a.py", "rev2", T_REV2, "primary", ["I2"]),
        snapshot("evidence/files/rev1/src/b.py", "rev1", T_REV1, "secondary", ["candidate:I1", "prior:report.md"]),
        {"path": "outcomes/merged/src/a.py", "tier": "outcome", "kind": "file_snapshot"},
        {"path": "reference/sample.json", "tier": "evaluator_only", "kind": "sample"},
    ]
    write(case, "case.json", json.dumps({
        "schema": "ceebench/case/1", "case_id": "c", "publishable": True,
        "source": {"system": "synthetic", "repository": "example/repo", "change_id": "1"},
        "items": [
            {"item_id": "I1", "role": "review_comment", "author_role": "reviewer", "posted_at": T_ITEM1,
             "reviewed_revision": "rev1", "original": "generator/items/I1.md", "task": "rewrite"},
            {"item_id": "I2", "parent_item": "I1", "role": "author_reply", "author_role": "author", "posted_at": T_ITEM2,
             "reviewed_revision": "rev2", "original": "generator/items/I2.md", "task": "rewrite"}],
        "files": files, "retrieval_log": [{"target": "src/c.py", "status": "unresolved", "note": "not in repository"}]}))
    write(root, "dataset.json", json.dumps({"schema": "ceebench/dataset/1", "dataset_id": "d", "publishable": True,
                                             "cases": [{"case_id": "c", "path": "cases/c"}]}))
    return root


def view_files(out: Path) -> set[str]:
    return {p.relative_to(out / "files").as_posix() for p in (out / "files").rglob("*") if p.is_file()}


class EnrichmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = build(Path(self.tmp.name) / "ds")
        self.case = packet.load_dataset(self.root).cases["c"]

    def tearDown(self):
        self.tmp.cleanup()

    def out(self, name: str) -> Path:
        return Path(self.tmp.name) / name

    def test_valid(self):
        self.assertEqual(packet.check_dataset(packet.load_dataset(self.root), verify_checksums=False), [])

    def test_temporal_filter_selects_snapshot_revision(self):
        packet.export_view(self.case, "I1", self.out("v1"), "evaluator")
        files = view_files(self.out("v1"))
        self.assertIn("evidence/files/rev1/src/a.py", files)
        self.assertNotIn("evidence/files/rev2/src/a.py", files)
        packet.export_view(self.case, "I2", self.out("v2"), "evaluator")
        self.assertIn("evidence/files/rev2/src/a.py", view_files(self.out("v2")))

    def test_generator_view_excludes_secondary_evidence(self):
        packet.export_view(self.case, "I1", self.out("g"), "generator")
        packet.export_view(self.case, "I1", self.out("e"), "evaluator")
        self.assertNotIn("evidence/files/rev1/src/b.py", view_files(self.out("g")))
        self.assertIn("evidence/files/rev1/src/b.py", view_files(self.out("e")))

    def test_no_tier_leak_for_any_audience(self):
        for aud in packet.AUDIENCES:
            out = self.out(f"leak-{aud}")
            packet.export_view(self.case, "I2", out, aud)
            files = view_files(out)
            self.assertFalse(any(f.startswith(("outcomes/", "reference/")) for f in files), aud)

    def test_view_does_not_expose_provenance(self):
        packet.export_view(self.case, "I2", self.out("p"), "evaluator")
        text = (self.out("p") / "view.json").read_text()
        for key in ("selection", "basis", "referenced_by", "prior:", "candidate:", "git_blob"):
            self.assertNotIn(key, text)
        self.assertEqual(json.loads(text)["audience"], "evaluator")

    def test_secondary_without_provenance_rejected(self):
        files = json.loads((self.root / "cases/c/case.json").read_text())["files"]
        files[4]["selection"]["referenced_by"] = []
        build(self.out("bad1"), files)
        problems = packet.check_dataset(packet.load_dataset(self.out("bad1")), verify_checksums=False)
        self.assertTrue(any("without referenced_by" in p for p in problems))

    def test_unknown_provenance_reference_rejected(self):
        files = json.loads((self.root / "cases/c/case.json").read_text())["files"]
        files[2]["selection"]["referenced_by"] = ["X9"]
        build(self.out("bad2"), files)
        problems = packet.check_dataset(packet.load_dataset(self.out("bad2")), verify_checksums=False)
        self.assertTrue(any("referenced_by X9" in p for p in problems))

    def test_selection_only_on_review_time_files(self):
        files = json.loads((self.root / "cases/c/case.json").read_text())["files"]
        files[0]["selection"] = {"basis": "primary", "method": "test"}
        build(self.out("bad3"), files)
        problems = packet.check_dataset(packet.load_dataset(self.out("bad3")), verify_checksums=False)
        self.assertTrue(any("not review_time" in p for p in problems))

    def test_invalid_basis_rejected_by_schema(self):
        files = json.loads((self.root / "cases/c/case.json").read_text())["files"]
        files[2]["selection"]["basis"] = "tertiary"
        build(self.out("bad4"), files)
        with self.assertRaises(SchemaError):
            packet.load_dataset(self.out("bad4"))

    def test_dotfile_snapshot_is_declared_and_sealed(self):
        files = json.loads((self.root / "cases/c/case.json").read_text())["files"]
        files.append(snapshot("evidence/files/rev1/.env", "rev1", T_REV1, "primary", ["I1"]))
        root = build(self.out("dot"), files)
        write(root / "cases/c", "evidence/files/rev1/.env", "KEY=value\n")
        write(root / "cases/c", ".DS_Store", "x")
        ds = packet.load_dataset(root)
        self.assertEqual(packet.check_dataset(ds, verify_checksums=False), [])
        packet.seal(ds)
        self.assertIn("evidence/files/rev1/.env", (root / "cases/c/checksums.sha256").read_text())
        self.assertEqual(packet.check_dataset(packet.load_dataset(root)), [])

    def test_unknown_audience_rejected(self):
        with self.assertRaises(ValueError):
            packet.export_view(self.case, "I1", self.out("x"), "public")


if __name__ == "__main__":
    unittest.main()
