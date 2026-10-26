"""Check that the published static files match the dashboard sources."""
from pathlib import Path
import tempfile
import unittest
from html.parser import HTMLParser

import build_static


class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources = []

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.sources.append(dict(attrs).get('src', 'inline'))


class StaticBuildTests(unittest.TestCase):
    def test_committed_static_artifacts_are_current_and_standalone(self):
        with tempfile.TemporaryDirectory() as tmp:
            build_static.build(tmp)
            expected_files = {'index.html', 'static-demo.js', 'favicon.svg'}
            self.assertEqual({p.name for p in Path(tmp).iterdir()}, expected_files)
            for name in expected_files:
                self.assertEqual((Path(tmp) / name).read_bytes(), (build_static.ROOT / 'static' / name).read_bytes(), f'Rebuild static files: {name}')
            page = (Path(tmp) / 'index.html').read_text(encoding='utf-8')
            scripts = Scripts()
            scripts.feed(page)
            self.assertEqual(scripts.sources, ['./static-demo.js', 'inline'])
            self.assertNotIn('BEVSTATS_LOGIN_PASSWORD', page)
            bundle = (Path(tmp) / 'static-demo.js').read_text(encoding='utf-8')
            self.assertNotIn('BEVSTATS_LOGIN_PASSWORD', bundle)
            self.assertEqual(len(build_static.SAMPLES), 18)


if __name__ == '__main__':
    unittest.main()
