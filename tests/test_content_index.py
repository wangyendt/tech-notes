import tempfile
import unittest
from pathlib import Path

from scripts import content_index as index


class ContentIndexTests(unittest.TestCase):
    def fixture(self, root):
        content = root / "content"
        (content / "systems").mkdir(parents=True)
        (content / "systems/README.md").write_text("# 系统与工程\n")
        book = root / "upstream"
        book.mkdir()
        (book / "README.md").write_text("# Source book\n\nOriginal book body.\n")
        return content, book, {"mount": "systems/source-book", "title": "Stale local title"}

    def article(self, content, name, text):
        path = content / "systems" / name / "README.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def test_source_book_title_is_authoritative_and_topic_pages_are_not_entries(self):
        with tempfile.TemporaryDirectory() as temp:
            content, book, spec = self.fixture(Path(temp))
            rows = index.entries(content, book, spec)
            self.assertEqual(rows, [{"title": "Source book", "type": "book", "topic": "systems", "href": "systems/source-book/index.md", "date": None, "updated": None}])
            self.assertIn("书籍", index.render(content, book, spec))
            self.assertNotIn("Original book body", index.render(content, book, spec))

    def test_new_article_update_and_delete_need_no_home_edit(self):
        with tempfile.TemporaryDirectory() as temp:
            content, book, spec = self.fixture(Path(temp))
            template = "# Home\n\n" + index.MARKER
            home = Path(temp) / "index.md"
            article = self.article(content, "new", "---\ntype: article\ntitle: First title\n---\n# Body title\nPrivate summary not for the home page.")
            home.write_text(template)
            index.update_home(home, content, book, spec)
            self.assertIn("[First title](systems/new/index.md)", home.read_text())
            self.assertNotIn("Private summary", home.read_text())
            article.write_text(article.read_text().replace("First title", "Revised title"))
            home.write_text(template)
            index.update_home(home, content, book, spec)
            self.assertIn("Revised title", home.read_text())
            self.assertNotIn("First title", home.read_text())
            article.unlink()
            self.assertNotIn("Revised title", index.render(content, book, spec))

    def test_local_book_and_article_use_the_same_list_markup(self):
        with tempfile.TemporaryDirectory() as temp:
            content, book, spec = self.fixture(Path(temp))
            self.article(content, "book", "---\ntype: book\n---\n# Local book\n")
            self.article(content, "article", "---\ntype: article\n---\n# Local article\n")
            rendered = index.render(content, book, spec)
            self.assertEqual(rendered.count('<span class="content-kind">'), 3)
            self.assertIn("[Local book]", rendered)
            self.assertIn("[Local article]", rendered)
            self.assertNotIn("book-entry", rendered)

    def test_unknown_type_or_missing_topic_fails_instead_of_silent_omission(self):
        with tempfile.TemporaryDirectory() as temp:
            content, book, spec = self.fixture(Path(temp))
            path = self.article(content, "oops", "---\ntype: articel\n---\n# Oops")
            with self.assertRaises(ValueError):
                index.render(content, book, spec)
            path.write_text("---\ntype: article\n---\n# Oops")
            (content / "systems/README.md").unlink()
            with self.assertRaises(ValueError):
                index.render(content, book, spec)

    def test_titles_and_paths_are_escaped_and_order_is_stable(self):
        with tempfile.TemporaryDirectory() as temp:
            content, book, spec = self.fixture(Path(temp))
            self.article(content, "a file", "---\ntype: article\n---\n# [x] <unsafe>\n")
            rendered = index.render(content, book, spec)
            self.assertIn(r"\[x\] &lt;unsafe&gt;", rendered)
            self.assertIn("systems/a%20file/index.md", rendered)
            self.assertEqual(rendered, index.render(content, book, spec))

    def test_dates_render_and_updated_defaults_to_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            content, book, spec = self.fixture(Path(temp))
            self.article(content, "dated", "---\ntype: article\ndate: 2026-10-01\n---\n# Dated\n")
            row = next(r for r in index.entries(content, book, spec) if r["type"] == "article")
            self.assertEqual(row["date"], "2026-10-01")
            self.assertEqual(row["updated"], "2026-10-01")
            rendered = index.render(content, book, spec)
            self.assertIn('<time datetime="2026-10-01">2026-10-01</time>', rendered)
            self.assertIn("未填写", rendered)  # Undated source fixture is not assigned today's date.

    def test_sort_is_updated_then_created_then_title_and_missing_dates_last(self):
        with tempfile.TemporaryDirectory() as temp:
            content, book, spec = self.fixture(Path(temp))
            for name, created, updated in [("Z newest", "2026-10-01", "2026-10-26"),
                                            ("B later creation", "2026-10-10", "2026-10-25"),
                                            ("A earlier creation", "2026-10-01", "2026-10-25"),
                                            ("C earlier creation", "2026-10-01", "2026-10-25")]:
                self.article(content, name, f"---\ntype: article\ndate: {created}\nupdated: {updated}\n---\n# {name}\n")
            names = [r["title"] for r in index.entries(content, book, spec)]
            self.assertEqual(names, ["Z newest", "B later creation", "A earlier creation", "C earlier creation", "Source book"])

    def test_source_metadata_dates_override_git_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            content, book, spec = self.fixture(Path(temp))
            fallback = {"date": "2026-06-18", "updated": "2026-07-30"}
            row = index.entries(content, book, spec, fallback)[0]
            self.assertEqual(row["date"], "2026-06-18")
            (book / "README.md").write_text("---\ndate: 2026-01-01\nupdated: 2026-08-01\n---\n# Source book")
            row = index.entries(content, book, spec, fallback)[0]
            self.assertEqual((row["date"], row["updated"]), ("2026-01-01", "2026-08-01"))

    def test_invalid_or_reversed_dates_fail(self):
        for meta in [{"date": "2026-02-30"}, {"date": "yesterday"}, {"date": False},
                     {"date": "2026-10-26", "updated": "2026-10-25"}]:
            with self.subTest(meta=meta), self.assertRaises(ValueError):
                index.dates(meta)

    def test_home_marker_must_be_present_exactly_once(self):
        with tempfile.TemporaryDirectory() as temp:
            content, book, spec = self.fixture(Path(temp))
            home = Path(temp) / "index.md"
            for template in ["# Missing", index.MARKER + index.MARKER]:
                home.write_text(template)
                with self.assertRaises(ValueError):
                    index.update_home(home, content, book, spec)


if __name__ == "__main__":
    unittest.main()
