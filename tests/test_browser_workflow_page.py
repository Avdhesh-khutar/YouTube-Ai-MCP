import pathlib
import unittest
from html.parser import HTMLParser


ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "browser-workflow" / "index.html"


class BrowserPageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.script_sources = []
        self.form_seen = False
        self.inputs = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "script" and attrs.get("src"):
            self.script_sources.append(attrs["src"])
        if tag == "form":
            self.form_seen = True
        if tag in {"input", "select", "textarea"} and "id" in attrs:
            self.inputs.add(attrs["id"])


class BrowserWorkflowPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")
        cls.parser = BrowserPageParser()
        cls.parser.feed(cls.html)

    def test_topic_and_planning_controls_exist(self):
        self.assertTrue(self.parser.form_seen)
        self.assertTrue({"topic", "audience", "style", "notes"} <= self.parser.inputs)
        self.assertIn("output", self.parser.ids)
        self.assertIn("Planning brief banao", self.html)

    def test_no_remote_scripts_or_api_calls(self):
        self.assertEqual([], self.parser.script_sources)
        self.assertNotIn("fetch(", self.html)
        self.assertNotIn("XMLHttpRequest", self.html)
        self.assertNotIn("WebSocket(", self.html)

    def test_browser_only_and_private_upload_disclaimer_present(self):
        self.assertIn("koi installation", self.html.lower())
        self.assertIn("Private only", self.html)
        self.assertIn("video generator nahi", self.html)

    def test_topic_is_required_and_length_limited(self):
        self.assertIn('id="topic" required maxlength="180"', self.html)


if __name__ == "__main__":
    unittest.main()
