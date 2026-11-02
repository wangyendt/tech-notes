"""Keep the Android concept articles discoverable and the case anonymous."""
from datetime import date
from pathlib import Path
import unittest

import yaml

from scripts.build_site import FORBIDDEN
from scripts.content_index import dates, metadata, title


ROOT = Path(__file__).resolve().parents[1]
SYSTEMS = ROOT / "content/systems"
CONCEPTS = (
    "android-accessibility-service",
    "android-shizuku",
    "android-bluetooth-hci-btsnoop",
)
CASE = "android-wearable-heart-rate"


def nav_targets(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from nav_targets(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from nav_targets(item)


class AndroidArticleTests(unittest.TestCase):
    def test_concepts_have_complete_article_metadata(self):
        for slug in CONCEPTS:
            with self.subTest(article=slug):
                path = SYSTEMS / slug / "README.md"
                meta = metadata(path)
                self.assertEqual(meta["type"], "article")
                self.assertTrue(meta["description"])
                self.assertIsInstance(meta["tags"], list)
                self.assertIn("Android", meta["tags"])
                self.assertEqual(meta["date"], date(2026, 11, 2))
                self.assertIsNotNone(dates(meta)["updated"])
                self.assertIn(f"# {title(path)}\n", path.read_text())

    def test_topic_and_navigation_include_each_article_once(self):
        topic = (SYSTEMS / "README.md").read_text()
        config = yaml.safe_load((ROOT / "mkdocs.yml").read_text())
        targets = list(nav_targets(config["nav"]))
        for slug in (*CONCEPTS, CASE):
            with self.subTest(article=slug):
                self.assertEqual(topic.count(f"]({slug}/README.md)"), 1)
                self.assertEqual(targets.count(f"systems/{slug}/index.md"), 1)

    def test_case_and_concepts_link_in_both_directions(self):
        case = (SYSTEMS / CASE / "README.md").read_text()
        for slug in CONCEPTS:
            with self.subTest(article=slug):
                self.assertIn(f"](../{slug}/README.md)", case)
                self.assertIn(f"](../{CASE}/README.md)",
                              (SYSTEMS / slug / "README.md").read_text())

    def test_case_keeps_creation_date_and_records_revision(self):
        meta = metadata(SYSTEMS / CASE / "README.md")
        self.assertEqual(meta["date"], date(2026, 10, 26))
        self.assertGreaterEqual(meta["updated"], date(2026, 11, 2))

    def test_new_articles_do_not_leak_private_identifiers(self):
        for slug in (*CONCEPTS, CASE):
            with self.subTest(article=slug):
                text = (SYSTEMS / slug / "README.md").read_text()
                self.assertIsNone(FORBIDDEN.search(text))
                self.assertNotIn("/Users/", text)
                self.assertNotIn("-----BEGIN PRIVATE KEY", text)


if __name__ == "__main__":
    unittest.main()
