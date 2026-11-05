"""Renders every page of the shipped config against a sample snapshot. Run: python -m unittest discover tests"""
import json, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from collector.config import Config
from collector.web import render_page

HERE = os.path.dirname(__file__)


class T(unittest.TestCase):
    def test_pages_render(self):
        c = Config(os.path.join(HERE, "..", "config", "dashboard.yaml"))
        self.assertIsNone(c.error)
        snap = json.load(open(os.path.join(HERE, "sample_snapshot.json")))
        for p in c.get()["pages"]:
            h = render_page(c.get(), c.error, p["id"], snap, None, None)
            self.assertIn(p["title"], h)
            self.assertNotIn("failed", h)

    def test_bad_config_keeps_last_good(self):
        import tempfile
        d = tempfile.mkdtemp(); f = os.path.join(d, "c.yaml")
        open(f, "w").write(open(os.path.join(HERE, "..", "config", "dashboard.yaml")).read())
        c = Config(f); n = len(c.get()["pages"])
        import time; time.sleep(0.02); open(f, "w").write("pages: [{id: a, title: A, widgets: [{type: nope}]}]")
        os.utime(f, (time.time() + 5, time.time() + 5))
        self.assertEqual(len(c.get()["pages"]), n); self.assertIn("unknown widget", c.error)


unittest.main() if __name__ == "__main__" else None
