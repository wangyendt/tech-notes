import copy
import unittest
from pathlib import Path
from types import SimpleNamespace

import yaml
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]


class EngagementTemplateTests(unittest.TestCase):
    def setUp(self):
        self.config = yaml.safe_load((ROOT / "mkdocs.yml").read_text())
        self.config["extra"]["book"] = {
            "mount": "calibration/kalibr-cam-imu", "commit": "a" * 40,
        }
        self.env = Environment(loader=ChoiceLoader([
            FileSystemLoader(ROOT / "overrides"),
            DictLoader({"base.html": "{% block extrahead %}{% endblock %}{% block content %}BODY{% endblock %}"}),
        ]), autoescape=select_autoescape())
        self.env.filters["url"] = lambda path: "/tech-notes/" + path

    def render(self, path, meta=None, config=None):
        page = SimpleNamespace(url=path, meta=meta or {},
                               canonical_url="https://wangyendt.github.io/tech-notes/" + path)
        return self.env.get_template("main.html").render(page=page, config=config or self.config)

    def test_article_has_counter_and_comments_after_body(self):
        html = self.render("systems/example/", {"type": "article"})
        self.assertEqual(html.count('id="busuanzi_value_page_pv"'), 1)
        self.assertIn('data-canonical="https://wangyendt.github.io/tech-notes/systems/example/"', html)
        self.assertLess(html.index("BODY"), html.index('class="engagement"'))
        self.assertIn("interaction-privacy", html)

    def test_landing_and_asset_pages_do_not_get_widgets(self):
        for path in ["", "systems/", "calibration/", "about/", "sources/",
                     "calibration/kalibr-cam-imu/assets/figure_generation_prompts/",
                     "other/calibration/kalibr-cam-imu/chapter/"]:
            with self.subTest(path=path):
                self.assertNotIn('class="engagement"', self.render(path))

    def test_book_entry_chapters_append_widgets_after_provenance(self):
        for path in ["calibration/kalibr-cam-imu/", "calibration/kalibr-cam-imu/chapter01/"]:
            html = self.render(path)
            self.assertLess(html.index('class="source-caption"'), html.index('class="engagement"'))
        self.assertIn('class="engagement"', self.render("systems/book/", {"type": "book"}))

    def test_explicit_opt_out(self):
        self.assertNotIn('class="engagement"', self.render("systems/example/", {"type": "article", "comments": False}))

    def test_disabled_and_missing_configuration_is_not_a_fake_widget(self):
        config = copy.deepcopy(self.config)
        config["extra"]["engagement"]["pageviews"] = False
        config["extra"]["engagement"]["giscus"].update(enabled=False, category_id="")
        html = self.render("systems/example/", {"type": "article"}, config)
        self.assertNotIn('id="busuanzi_value_page_pv"', html)
        self.assertIn("评论与点赞尚未启用", html)
        self.assertNotIn("https://giscus.app/client.js", html)

    def test_public_config_is_html_escaped(self):
        config = copy.deepcopy(self.config)
        config["extra"]["engagement"]["giscus"]["category"] = '\"<script>alert(1)</script>'
        html = self.render("systems/example/", {"type": "article"}, config)
        self.assertNotIn("<script>alert(1)</script>", html)


if __name__ == "__main__":
    unittest.main()
