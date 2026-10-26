"""Dependency-free shared sales tracker. Run: python server.py"""
import json
import os
import sqlite3
import hashlib
import hmac
import secrets
import time
import threading
import sys
import getpass
import tempfile
from http.cookies import SimpleCookie
from contextlib import contextmanager
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

ROOT = Path(__file__).resolve().parent
DEMO_MODE = os.environ.get('BEVSTATS_DEMO_MODE') == '1'
DB = Path(os.environ.get('BEVTRACKER_DB', str(Path(tempfile.gettempdir()) / 'bevstats-demo.sqlite3' if DEMO_MODE else ROOT / 'sales.sqlite3')))

SAMPLES = [
 ('The Corner Tap',1848,2400,'North','Corey'), ('Lakeside Social',1368,2400,'North','Jordan'),
 ('Main Street Grill',2184,2400,'Central','Corey'), ('The Yard',864,2400,'South','Alex'),
 ('Riverfront Tavern',3120,3000,'Central','Jordan'), ('Oak & Barrel',2760,2400,'North','Alex'),
 ('Sunset Sports Bar',2496,3000,'West','Morgan'), ('Union House',2016,2400,'Central','Corey'),
 ('The Blue Anchor',1920,2400,'East','Jordan'), ('Westside Pub',1680,2400,'West','Morgan'),
 ('Parkside Kitchen',1440,2400,'South','Alex'), ('Station 12',1200,1800,'East','Jordan'),
 ('The Copper Kettle',1080,1800,'North','Corey'), ('Highway Roadhouse',960,2400,'West','Morgan'),
 ('Harbor Grill',720,1800,'East','Alex'), ('Southgate Social',480,1800,'South','Morgan'),
 ('The Dugout',240,1200,'Central','Corey'), ('Prairie House',0,1200,'West','Alex')
]
LOGIN_ATTEMPTS = {}
AUTH_LOCK = threading.Lock()

def password_hash(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600000).hex()

def configure_demo_account():
    """Restore a private demo login after Render discards its temporary disk."""
    username = os.environ.get('BEVSTATS_LOGIN_USERNAME', '').strip()
    password = os.environ.get('BEVSTATS_LOGIN_PASSWORD', '')
    display = os.environ.get('BEVSTATS_LOGIN_NAME', username).strip()
    if not 1 <= len(username) <= 80 or not 1 <= len(display) <= 80 or not 4 <= len(password) <= 256:
        raise ValueError('Demo mode requires BEVSTATS_LOGIN_USERNAME and BEVSTATS_LOGIN_PASSWORD (4-256 characters); optional BEVSTATS_LOGIN_NAME must be 1-80 characters.')
    with connect() as db:
        user = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        if user and hmac.compare_digest(password_hash(password, user['salt']), user['password_hash']):
            db.execute('UPDATE users SET display_name=? WHERE id=?', (display, user['id']))
            return
        salt = secrets.token_hex(16)
        hashed = password_hash(password, salt)
        if user:
            db.execute('UPDATE users SET display_name=?,salt=?,password_hash=? WHERE id=?', (display, salt, hashed, user['id']))
            db.execute('DELETE FROM sessions WHERE user_id=?', (user['id'],))
        else:
            db.execute('INSERT INTO users(username,display_name,salt,password_hash) VALUES (?,?,?,?)', (username, display, salt, hashed))

def seed_samples():
    with connect() as db:
        if not db.execute('SELECT sample FROM settings WHERE id=1').fetchone()[0]:
            raise ValueError('Sample seeding is disabled for real sales data')
        for row in SAMPLES:
            if not db.execute('SELECT 1 FROM locations WHERE name=?', (row[0],)).fetchone():
                db.execute('INSERT INTO locations(name,cans,goal,region,salesperson) VALUES (?,?,?,?,?)', row)
            else:
                db.execute("UPDATE locations SET region=CASE WHEN region='' THEN ? ELSE region END, salesperson=CASE WHEN salesperson='' THEN ? ELSE salesperson END WHERE name=?", (row[3], row[4], row[0]))

@contextmanager
def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()

def initialize():
    with connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, name TEXT NOT NULL, cans INTEGER NOT NULL, goal INTEGER NOT NULL, updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
        db.execute('CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, sample INTEGER NOT NULL)')
        columns = {row['name'] for row in db.execute('PRAGMA table_info(locations)')}
        for column in ('region', 'salesperson'):
            if column not in columns:
                db.execute(f"ALTER TABLE locations ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
        db.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE COLLATE NOCASE, display_name TEXT NOT NULL, salt TEXT NOT NULL, password_hash TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires REAL NOT NULL)')
        if not db.execute('SELECT 1 FROM settings').fetchone():
            db.execute('INSERT INTO settings VALUES (1,1)')
            db.executemany('INSERT INTO locations(name,cans,goal,region,salesperson) VALUES (?,?,?,?,?)', SAMPLES)
    if DEMO_MODE:
        configure_demo_account()

class Handler(BaseHTTPRequestHandler):
    def send(self, status, value, content_type='application/json', cookie=None):
        data = value.encode() if isinstance(value, str) else json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type + '; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(data)

    def token_hash(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
            token = cookie['bev_session'].value if 'bev_session' in cookie else ''
        except Exception:
            token = ''
        return hashlib.sha256(token.encode()).hexdigest()

    def user(self):
        with connect() as db:
            row = db.execute('SELECT u.id,u.username,u.display_name FROM sessions s JOIN users u ON s.user_id=u.id WHERE s.token_hash=? AND s.expires>?', (self.token_hash(), time.time())).fetchone()
            return dict(row) if row else None

    def auth_state(self):
        with connect() as db:
            setup = not bool(db.execute('SELECT 1 FROM users LIMIT 1').fetchone())
        return {'user': self.user(), 'setup_required': setup, 'demo_mode': DEMO_MODE}

    def session_cookie(self, token, age=28800):
        secure = self.headers.get('X-Forwarded-Proto') == 'https'
        return f'bev_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={age}' + ('; Secure' if secure else '')

    def authenticate(self, body):
        address = self.client_address[0]
        with AUTH_LOCK:
            count, since = LOGIN_ATTEMPTS.get(address, (0, time.time()))
            if time.time() - since > 600:
                count, since = 0, time.time()
            if count >= 10:
                return self.send(429, {'error': 'Too many attempts. Try again in 10 minutes.'})
            LOGIN_ATTEMPTS[address] = (count + 1, since)
        username, password = body.get('username', ''), body.get('password', '')
        if not isinstance(username, str) or not isinstance(password, str) or len(username) > 80 or len(password) > 256:
            return self.send(400, {'error': 'Invalid sign-in details'})
        username = username.strip()
        with connect() as db:
            if self.path == '/api/setup':
                display = body.get('display_name', username)
                if not username or not isinstance(display, str) or not 1 <= len(display.strip()) <= 80 or len(password) < 4:
                    return self.send(400, {'error': 'Enter a username and a password of at least 4 characters.'})
                salt = secrets.token_hex(16)
                hashed = password_hash(password, salt)
                db.execute('BEGIN IMMEDIATE')
                if db.execute('SELECT 1 FROM users LIMIT 1').fetchone():
                    return self.send(409, {'error': 'An account already exists. Please sign in.'})
                db.execute('INSERT INTO users(username,display_name,salt,password_hash) VALUES (?,?,?,?)', (username, display.strip(), salt, hashed))
            row = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
            salt = row['salt'] if row else '00' * 16
            valid = hmac.compare_digest(password_hash(password, salt), row['password_hash'] if row else '00' * 32)
            if not row or not valid:
                return self.send(401, {'error': 'Incorrect username or password.'})
            token = secrets.token_urlsafe(32)
            db.execute('DELETE FROM sessions WHERE expires<=?', (time.time(),))
            db.execute('INSERT INTO sessions VALUES (?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), row['id'], time.time()+28800))
            user = {key: row[key] for key in ('id', 'username', 'display_name')}
        with AUTH_LOCK:
            LOGIN_ATTEMPTS.pop(address, None)
        self.send(200, {'user': user}, cookie=self.session_cookie(token))

    def do_GET(self):
        if self.path == '/api/session':
            return self.send(200, self.auth_state())
        if self.path == '/api/locations':
            if not self.user():
                return self.send(401, {'error': 'Please sign in.'})
            with connect() as db:
                self.send(200, {'locations': [dict(r) for r in db.execute('SELECT * FROM locations ORDER BY id')], 'sample': bool(db.execute('SELECT sample FROM settings WHERE id=1').fetchone()[0])})
        elif self.path in ('/', '/index.html'):
            self.send(200, (ROOT / 'index.html').read_text(encoding='utf-8'), 'text/html')
        else:
            self.send(404, {'error': 'Not found'})

    def do_POST(self):
        # Same-origin writes and HttpOnly same-site sessions protect authenticated APIs.
        origin = self.headers.get('Origin')
        if origin and origin.split('://')[-1] != self.headers.get('Host'):
            return self.send(403, {'error': 'Origin not allowed'})
        if self.path == '/api/logout':
            with connect() as db:
                db.execute('DELETE FROM sessions WHERE token_hash=?', (self.token_hash(),))
            return self.send(200, {'ok': True}, cookie=self.session_cookie('', 0))
        if self.path not in ('/api/locations', '/api/login', '/api/setup'):
            return self.send(404, {'error': 'Not found'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 1048576:
                raise ValueError('Invalid request size')
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError('Expected an object')
            if self.path in ('/api/login', '/api/setup'):
                return self.authenticate(body)
            if not self.user():
                return self.send(401, {'error': 'Please sign in.'})
            rows = body['locations']
            if not isinstance(rows, list) or len(rows) > 1000:
                raise ValueError('Use up to 1,000 locations')
            cleaned = []
            for row in rows:
                name, cans, goal = row['name'], row['cans'], row['goal']
                if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
                    raise ValueError('Location names must have 1–80 characters')
                if type(cans) is not int or type(goal) is not int or not 0 <= cans <= 100000000 or not 1 <= goal <= 100000000:
                    raise ValueError('Cans must be a whole number ≥ 0; goals must be ≥ 1 (maximum 100 million)')
                region, salesperson = row.get('region', ''), row.get('salesperson', '')
                if any(not isinstance(v, str) or len(v) > 80 for v in (region, salesperson)):
                    raise ValueError('Region and salesperson must be text up to 80 characters')
                cleaned.append((name.strip(), cans, goal, region.strip(), salesperson.strip()))
            with connect() as db:
                db.execute('DELETE FROM locations')
                db.executemany('INSERT INTO locations(name,cans,goal,region,salesperson) VALUES (?,?,?,?,?)', cleaned)
                db.execute('UPDATE settings SET sample=? WHERE id=1', (int(bool(body.get('sample', False))),))
            self.send(200, {'ok': True})
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            self.send(400, {'error': str(exc)})

if __name__ == '__main__':
    if DEMO_MODE and os.environ.get('BEVTRACKER_DB', '').startswith('/var/data/'):
        sys.exit('For free demo hosting, remove BEVTRACKER_DB from Render Environment; no mounted disk is required.')
    initialize()
    if '--create-user' in sys.argv:
        username = input('Username: ').strip()
        display_name = input('Display name: ').strip()
        password = getpass.getpass('Password (4+ characters): ')
        if not 1 <= len(username) <= 80 or not 1 <= len(display_name) <= 80 or not 4 <= len(password) <= 256:
            sys.exit('Invalid name or password length.')
        if password != getpass.getpass('Confirm password: '):
            sys.exit('Passwords do not match.')
        salt = secrets.token_hex(16)
        try:
            with connect() as db:
                db.execute('INSERT INTO users(username,display_name,salt,password_hash) VALUES (?,?,?,?)', (username, display_name, salt, password_hash(password, salt)))
        except sqlite3.IntegrityError:
            sys.exit('Username already exists.')
        print('User created.')
        sys.exit(0)
    if '--seed-samples' in sys.argv:
        seed_samples()
        print('Sample locations added without replacing existing records.')
        sys.exit(0)
    port = int(os.environ.get('PORT', '8000'))
    print(f'Fill the Pitcher: http://localhost:{port}', flush=True)
    ThreadingHTTPServer((os.environ.get('HOST', '127.0.0.1'), port), Handler).serve_forever()
