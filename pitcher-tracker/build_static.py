"""Build the shared Supabase dashboard without embedding report data or secrets."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def build(output=None):
    output = Path(output) if output else ROOT / 'static'
    output.mkdir(parents=True, exist_ok=True)
    public = json.loads((ROOT / 'supabase-public.json').read_text(encoding='utf-8'))
    url = os.environ.get('SUPABASE_URL', public.get('url', '')).rstrip('/')
    key = os.environ.get('SUPABASE_PUBLISHABLE_KEY', public.get('publishableKey', ''))
    if key.startswith('sb_secret_'):
        raise ValueError('Use a Supabase publishable key, never a secret key')
    if key.startswith('eyJ'):
        import base64
        payload = json.loads(base64.urlsafe_b64decode(key.split('.')[1] + '==='))
        if payload.get('role') != 'anon':
            raise ValueError('Only an anon or publishable key can be included in browser assets')
    if bool(url) != bool(key):
        raise ValueError('Set both SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY')
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert html.count('<script>') == 1
    html = html.replace('<script>', '<script src="./supabase-config.js"></script>\n<script src="./supabase-adapter.js"></script>\n<script>', 1)
    (output / 'index.html').write_text(html, encoding='utf-8')
    (output / 'supabase-config.js').write_text('window.BEVSTATS_SUPABASE=' + json.dumps({'url':url,'publishableKey':key,'editorEmails':public['editorEmails']}) + ';\n', encoding='utf-8')
    for name in ('supabase-adapter.js','favicon.svg'):
        (output / name).write_bytes((ROOT / name).read_bytes())
    obsolete = output / 'static-demo.js'
    if obsolete.exists():
        obsolete.unlink()
    return output


if __name__ == '__main__':
    print('Supabase dashboard built at ' + str(build()))
