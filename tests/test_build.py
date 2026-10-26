import importlib.util
import json
import sys
import tempfile
import subprocess
import zipfile
import hashlib
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("site_builder", ROOT / "scripts/build_site.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BuilderTests(unittest.TestCase):
    def test_readme_links_only(self):
        text = "[a](../README.md#hello) [b](https://example.com/README.md) `README.md` [c](book.md)"
        result = builder.rewrite_links(text)
        self.assertIn("../index.md#hello", result)
        self.assertIn("https://example.com/README.md", result)
        self.assertIn("`README.md`", result)
        self.assertIn("(book.md)", result)

    def test_source_reading_order_and_new_chapter(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "README.md").write_text("# Guide\n[a](02.md)\n[b](01.md)")
            for name in ["01.md", "02.md", "03.md"]:
                (root / name).write_text("# " + name)
            nav = builder.book_navigation(root, "book")
            self.assertEqual([next(iter(x.values())) for x in nav], ["book/index.md", "book/02.md", "book/01.md", "book/03.md"])

    def test_missing_chapter_is_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "README.md").write_text("# Book\n[a](missing.md)")
            with self.assertRaises(ValueError):
                builder.book_navigation(root, "book")

    def test_symlink_is_never_published(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            source.mkdir()
            (source / "link.md").symlink_to(root / "private.md")
            with self.assertRaises(ValueError):
                builder.copy_tree(source, root / "output")

    def test_copy_is_derived_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            source.mkdir()
            original = "# Book\n\n[back](README.md)\n"
            (source / "README.md").write_text(original)
            meta = {"base_url": "https://example.com/book/", "commit": "a" * 40}
            builder.copy_tree(source, root / "output", meta)
            self.assertEqual((source / "README.md").read_text(), original)
            self.assertIn("index.md", (root / "output/index.md").read_text())
            self.assertEqual((root / "output/index.md").read_text(), builder.rewrite_links(original))
            self.assertNotIn("源项目同步章节", (root / "output/index.md").read_text())

    def test_full_original_archive_is_byte_exact_and_reproducible(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "book"
            (source / "assets").mkdir(parents=True)
            originals = {"README.md": b"# Book\r\n[home](README.md)\r\n",
                         "assets/notes.md": b"# Original image notes\n",
                         "章节.md": "# 原始章节\n".encode(),
                         "assets/image.png": bytes(range(256))}
            for name, raw in originals.items():
                (source / name).write_bytes(raw)
            def git(*args):
                return subprocess.check_output(["git", *args], cwd=root, text=True).strip()
            git("init", "-q")
            git("add", "book")
            git("-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "fixture")
            meta = {"repository": "test/book", "commit": git("rev-parse", "HEAD"), "path": "book"}
            first = builder.archive_book(source, root / "out1", meta)
            second = builder.archive_book(source, root / "out2", meta)
            self.assertEqual(first, second)
            with zipfile.ZipFile(root / "out1" / first["archive"]) as bundle:
                self.assertEqual(set(bundle.namelist()), set(originals))
                for name, raw in originals.items():
                    self.assertEqual(bundle.read(name), raw)
                    self.assertEqual(first["files"][name]["sha256"], hashlib.sha256(raw).hexdigest())
            builder.copy_tree(source, root / "web", meta)
            self.assertTrue((root / "web/assets/notes.md").exists())

    def test_anonymization(self):
        case = ROOT / "content/systems/android-wearable-heart-rate"
        for path in case.rglob("*"):
            if path.suffix in {".md", ".svg", ".py"}:
                self.assertIsNone(builder.FORBIDDEN.search(path.read_text()), path)

    def test_remote_unchanged_and_fetch_failure(self):
        with patch.object(builder, "download", return_value=b'{"fingerprint":"same"}'):
            self.assertTrue(builder.is_current("https://example.com", "same"))
            self.assertFalse(builder.is_current("https://example.com", "changed"))
        with patch.object(builder, "download", side_effect=OSError):
            self.assertFalse(builder.is_current("https://example.com", "same"))

    def test_canonical_github_markdown_links(self):
        for path in (ROOT / "content").rglob("*.md"):
            for match in builder.LINK.finditer(path.read_text()):
                target = match[2].split(' "', 1)[0]
                parsed = builder.urllib.parse.urlsplit(target)
                if parsed.scheme or target.startswith("#"):
                    continue
                resolved = (path.parent / builder.urllib.parse.unquote(parsed.path)).resolve()
                self.assertTrue(resolved.exists(), f"{path.name}: {target}")

    def test_bytecode_is_not_published(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            (source / "__pycache__").mkdir(parents=True)
            (source / "__pycache__/example.pyc").write_bytes(b"not public content")
            (source / "README.md").write_text("# Example")
            builder.copy_tree(source, root / "output")
            self.assertFalse((root / "output/__pycache__").exists())
            self.assertTrue((root / "output/index.md").exists())

    def test_book_tree_change_changes_fingerprint(self):
        self.assertNotEqual(builder.fingerprint("tree-before"), builder.fingerprint("tree-after"))

    def test_quality_example_is_synthetic_and_preserves_gaps(self):
        path = ROOT / "content/systems/android-wearable-heart-rate/examples/quality_check.py"
        module_spec = importlib.util.spec_from_file_location("quality_example", path)
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        info = module.summarize([(0, 0), (1000, 80), (1000, 80), (2000, 81), (7000, 82)])
        self.assertEqual(info["records"], 5)
        self.assertEqual(info["duplicate_timestamp_extras"], 1)
        self.assertEqual(info["raw_zero_records"], 1)
        self.assertEqual(info["long_gaps"], 1)
        self.assertFalse(info["packet_loss_proven"])


if __name__ == "__main__":
    unittest.main()
