"""Create a dependency-free, serverless demo from the same dashboard source."""
import json
from pathlib import Path
from server import SAMPLES

ROOT = Path(__file__).resolve().parent


def build(output=None):
    output = Path(output) if output else ROOT / 'static'
    output.mkdir(parents=True, exist_ok=True)
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    # Load the browser data adapter after the page markup and before the dashboard JS.
    assert html.count('<script>') == 1
    html = html.replace('<script>', '<script src="./static-demo.js"></script>\n<script>', 1)
    rows = [dict(zip(('name', 'cans', 'goal', 'region', 'salesperson'), row)) for row in SAMPLES]
    bundle = 'window.BEVSTATS_SAMPLE_LOCATIONS=' + json.dumps(rows) + ';\n'
    bundle += (ROOT / 'static-demo.js').read_text(encoding='utf-8')
    (output / 'index.html').write_text(html, encoding='utf-8')
    (output / 'static-demo.js').write_text(bundle, encoding='utf-8')
    (output / 'favicon.svg').write_text((ROOT / 'favicon.svg').read_text(encoding='utf-8'), encoding='utf-8')
    return output


if __name__ == '__main__':
    print('Static demo built at ' + str(build()))
