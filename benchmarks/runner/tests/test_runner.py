import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ceebench import checksums, cli, packet, wordcount
from ceebench.schema import SchemaError, validate

T0 = "2030-01-01T10:00:00Z"
T1 = "2030-01-01T11:00:00Z"
T2 = "2030-01-02T09:00:00Z"


def write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def build(root: Path) -> Path:
    case = root / "cases" / "demo-1"
    write(case, "generator/items/C1.md", "[P2] Guard against a missing `user` before reading `name`.")
    write(case, "generator/items/R1.md", "Fixed in `abc1234`.")
    write(case, "evidence/diffs/rev1.diff", "+ return user.name\n")
    write(case, "evidence/diffs/rev2.diff", "+ if user is None: return None\n")
    write(case, "reference/sample.json", json.dumps({
        "schema": "ceebench/sample/1", "case_id": "demo-1", "status": "reported_judgment",
        "samples": [{"sample_id": "baseline", "items": [
            {"item_id": "C1", "group": "finding"}, {"item_id": "R1", "group": "author_reply"}]}]}))
    write(case, "reference/variants/v1/C1.md", "[P2] `user` can be null.\n\n```py\nif user is None:\n    return\n```\n")
    write(case, "reference/variants/v1/R1.md", "Implemented in `abc1234`.")
    write(case, "reference/variants/v1/variant.json", json.dumps({
        "schema": "ceebench/variant/1", "case_id": "demo-1", "variant_id": "v1", "status": "reported_output",
        "cee_version": "0.0.0", "items": [
            {"item_id": "C1", "path": "reference/variants/v1/C1.md", "reported_words": 5},
            {"item_id": "R1", "path": "reference/variants/v1/R1.md", "reported_words": 99}]}))
    write(case, "outcomes/merge.json", json.dumps({"merged": True}))
    files = [
        {"path": "generator/items/C1.md", "tier": "generator_input", "kind": "original", "available_at": T0, "item_ids": ["C1"]},
        {"path": "generator/items/R1.md", "tier": "generator_input", "kind": "original", "available_at": T1, "item_ids": ["R1"]},
        {"path": "evidence/diffs/rev1.diff", "tier": "review_time", "kind": "diff", "available_at": T0},
        {"path": "evidence/diffs/rev2.diff", "tier": "review_time", "kind": "diff", "available_at": T1},
        {"path": "reference/sample.json", "tier": "evaluator_only", "kind": "sample"},
        {"path": "reference/variants/v1/C1.md", "tier": "evaluator_only", "kind": "variant_text"},
        {"path": "reference/variants/v1/R1.md", "tier": "evaluator_only", "kind": "variant_text"},
        {"path": "reference/variants/v1/variant.json", "tier": "evaluator_only", "kind": "variant"},
        {"path": "outcomes/merge.json", "tier": "outcome", "kind": "merge"},
    ]
    write(case, "case.json", json.dumps({
        "schema": "ceebench/case/1", "case_id": "demo-1", "publishable": True,
        "source": {"system": "synthetic", "repository": "example/repo", "change_id": "1"},
        "items": [
            {"item_id": "C1", "comment_id": "1", "role": "review_comment", "author_role": "reviewer",
             "posted_at": T0, "reviewed_revision": "rev1", "original": "generator/items/C1.md", "task": "rewrite"},
            {"item_id": "R1", "comment_id": "2", "parent_item": "C1", "role": "author_reply", "author_role": "author",
             "posted_at": T1, "reviewed_revision": "rev2", "original": "generator/items/R1.md", "task": "rewrite"}],
        "files": files,
        "snapshots": [{"snapshot_id": "s2", "repository": "example/repo", "revision": "rev2", "available_at": T1}],
        "retrieval_log": [{"target": "ticket", "status": "not_retrieved"}]}))
    write(root, "dataset.json", json.dumps({
        "schema": "ceebench/dataset/1", "dataset_id": "demo", "publishable": True,
        "cases": [{"case_id": "demo-1", "path": "cases/demo-1"}]}))
    packet.seal(packet.load_dataset(root))
    return root


class WordCountTests(unittest.TestCase):
    def test_fenced_and_images_excluded_by_default(self):
        text = "One two\n```php\nnot counted here\n```\n![](http://x/y.png){: a='b' }\nthree `code`"
        c = wordcount.count(text)
        self.assertEqual(c.words, 4)
        self.assertEqual(c.fenced_blocks, 1)
        self.assertEqual(c.images, 1)
        self.assertEqual(c.image_tokens, 3)

    def test_include_options(self):
        text = "a\n````md\nb ```inner``` c\n````\n![x](u)"
        self.assertEqual(wordcount.count(text).words, 1)
        self.assertEqual(wordcount.count(text, wordcount.Options(fenced_code="include")).words, 6)
        self.assertEqual(wordcount.count(text, wordcount.Options(images="include")).words, 2)

    def test_tilde_fence_and_unclosed(self):
        self.assertEqual(wordcount.count("x\n~~~\ny z\n~~~\nw").words, 2)
        self.assertEqual(wordcount.count("x\n```\ny z").words, 1)

    def test_crlf(self):
        self.assertEqual(wordcount.count("a\r\nb\rc").words, 3)


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = build(Path(self.tmp.name))

    def tearDown(self):
        for p in Path(self.tmp.name).rglob("*"):
            if p.is_file():
                os.chmod(p, stat.S_IRUSR | stat.S_IWUSR)
        self.tmp.cleanup()

    def test_valid_dataset(self):
        self.assertEqual(packet.check_dataset(packet.load_dataset(self.root)), [])

    def test_checksum_tamper_detected(self):
        (self.root / "cases/demo-1/evidence/diffs/rev1.diff").write_text("changed", encoding="utf-8")
        problems = packet.check_dataset(packet.load_dataset(self.root))
        self.assertTrue(any("checksum mismatch" in p for p in problems))

    def test_undeclared_file_detected(self):
        write(self.root / "cases/demo-1", "evidence/extra.txt", "x")
        problems = packet.check_dataset(packet.load_dataset(self.root), verify_checksums=False)
        self.assertTrue(any("not declared" in p for p in problems))

    def test_tier_directory_mismatch_detected(self):
        case_json = self.root / "cases/demo-1/case.json"
        data = json.loads(case_json.read_text())
        data["files"][2]["tier"] = "evaluator_only"
        case_json.write_text(json.dumps(data))
        problems = packet.check_dataset(packet.load_dataset(self.root), verify_checksums=False)
        self.assertTrue(any("declares tier evaluator_only" in p for p in problems))

    def test_schema_rejects_unknown_property(self):
        with self.assertRaises(SchemaError):
            validate({"schema": "ceebench/dataset/1", "dataset_id": "d", "publishable": False, "cases": [], "x": 1}, "dataset")

    def test_view_is_time_bounded_and_excludes_evaluator_tiers(self):
        case = packet.load_dataset(self.root).cases["demo-1"]
        out = Path(self.tmp.name) / "view-c1"
        packet.export_view(case, "C1", out)
        files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
        self.assertIn("files/generator/items/C1.md", files)
        self.assertIn("files/evidence/diffs/rev1.diff", files)
        self.assertNotIn("files/evidence/diffs/rev2.diff", files)
        self.assertNotIn("files/generator/items/R1.md", files)
        self.assertFalse(any("reference" in f or "outcomes" in f for f in files))
        view = json.loads((out / "view.json").read_text())
        self.assertEqual([i["item_id"] for i in view["items"]], ["C1"])
        self.assertEqual(view["snapshots"], [])
        self.assertEqual(checksums.verify_manifest(out), [])

    def test_view_for_reply_includes_earlier_context(self):
        case = packet.load_dataset(self.root).cases["demo-1"]
        out = Path(self.tmp.name) / "view-r1"
        packet.export_view(case, "R1", out)
        view = json.loads((out / "view.json").read_text())
        self.assertEqual([i["item_id"] for i in view["items"]], ["C1", "R1"])
        self.assertEqual(len(view["snapshots"]), 1)

    def test_view_refuses_non_empty_output(self):
        case = packet.load_dataset(self.root).cases["demo-1"]
        out = Path(self.tmp.name) / "busy"
        write(out, "x", "y")
        with self.assertRaises(FileExistsError):
            packet.export_view(case, "C1", out)

    def test_metrics_reproduction_and_generation(self):
        gen = Path(self.tmp.name) / "generation.json"
        gen.write_text(json.dumps({
            "schema": "ceebench/generation/1", "case_id": "demo-1", "variant_id": "v2",
            "cee": {"version": "0.2.0", "spec_commit": None}, "model": {"name": "m", "id": "m-1"},
            "generated_at": T2, "publishable": False,
            "items": [{"item_id": "C1", "text": "[P2] `user` may be null; check it.", "decision": "publish"}]}))
        self.assertEqual(cli.main(["freeze", str(gen), "--schema", "generation"]), 0)
        out = Path(self.tmp.name) / "m.json"
        rc = cli.main(["metrics", str(self.root), "--case", "demo-1", "--generation", str(gen),
                       "--require-frozen", "--out", str(out)])
        self.assertEqual(rc, 1)
        self.assertFalse(out.exists())
        rc = cli.main(["metrics", str(self.root), "--case", "demo-1", "--generation", str(gen),
                       "--require-frozen", "--allow-legacy", "--out", str(out)])
        self.assertEqual(rc, 0)
        m = json.loads(out.read_text())
        self.assertIn("legacy import", next(v for v in m["variants"] if v["variant_id"] == "v2")["binding"])
        validate(m, "metrics")
        self.assertFalse(m["publishable"])
        self.assertEqual(m["reproduction"]["checked"], 2)
        self.assertEqual(m["reproduction"]["matched"], 1)
        self.assertEqual(m["reproduction"]["mismatches"][0]["item_id"], "R1")
        words = m["totals"]["baseline"]["all"]["words"]
        self.assertEqual(words["original"], 9 + 3)
        self.assertIsNone(words["v2"])
        self.assertEqual(m["totals"]["baseline"]["finding"]["words"]["v2"], 7)

    def test_freeze_is_write_once(self):
        f = Path(self.tmp.name) / "g.txt"
        f.write_text("x")
        checksums.freeze(f)
        self.assertEqual(checksums.verify_frozen(f), [])
        with self.assertRaises(FileExistsError):
            checksums.freeze(f)

    def test_cli_validate(self):
        self.assertEqual(cli.main(["validate", str(self.root)]), 0)


if __name__ == "__main__":
    unittest.main()
