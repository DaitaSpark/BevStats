"""Run with: python -m unittest -v"""
import hashlib
import http.cookiejar
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

import server


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original_db = server.DB
        server.DB = Path(self.temp.name) / 'test.sqlite3'
        server.LOGIN_ATTEMPTS.clear()
        server.initialize()
        self.http = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.base = 'http://127.0.0.1:' + str(self.http.server_port)
        self.cookies = http.cookiejar.CookieJar()
        self.client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join()
        server.DB = self.original_db
        self.temp.cleanup()

    def request(self, path, data=None, headers=None):
        request = urllib.request.Request(self.base + path, data=json.dumps(data).encode() if data is not None else None, headers={'Content-Type': 'application/json', **(headers or {})})
        try:
            response = self.client.open(request)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.code, json.load(response), response.headers

    def test_authentication_and_protected_sales(self):
        account = {'username': 'corey', 'password': 'test'}
        self.assertTrue(self.request('/api/session')[1]['setup_required'])
        self.assertEqual(self.request('/api/locations')[0], 401)
        self.assertEqual(self.request('/api/locations', {'locations': []})[0], 401)
        self.assertEqual(self.request('/api/setup', {**account, 'password': 'abc'})[0], 400)
        code, body, headers = self.request('/api/setup', account)
        self.assertEqual(code, 200)
        self.assertEqual(body['user']['display_name'], 'corey')
        self.assertIn('HttpOnly', headers['Set-Cookie'])
        self.assertIn('SameSite=Strict', headers['Set-Cookie'])
        self.assertNotIn('password', body['user'])
        self.assertFalse(self.request('/api/session')[1]['setup_required'])
        self.assertEqual(self.request('/api/setup', account)[0], 409)
        locations = self.request('/api/locations')[1]['locations']
        self.assertEqual(len(locations), 18)
        self.assertTrue(all(r['region'] and r['salesperson'] for r in locations))
        self.assertTrue(any(r['cans'] >= r['goal'] for r in locations))
        rows = [{'name': f'Location {i}', 'cans': i*12, 'goal': 2400, 'region': 'North', 'salesperson': 'Corey'} for i in range(400)]
        self.assertEqual(self.request('/api/locations', {'locations': rows, 'sample': False})[0], 200)
        self.assertEqual(len(self.request('/api/locations')[1]['locations']), 400)
        self.assertEqual(self.request('/api/locations', {'locations': []}, {'Origin': 'https://other.example'})[0], 403)
        with server.connect() as db:
            user = dict(db.execute('SELECT * FROM users').fetchone())
            self.assertNotEqual(user['password_hash'], account['password'])
            self.assertEqual(user['password_hash'], server.password_hash(account['password'], user['salt']))
        self.assertEqual(self.request('/api/logout', {})[0], 200)
        self.assertEqual(self.request('/api/locations')[0], 401)
        self.assertEqual(self.request('/api/login', {**account, 'password': 'wrong'})[0], 401)
        self.assertEqual(self.request('/api/login', {**account, 'username': 'COREY'})[0], 200)
        with server.connect() as db:
            db.execute('UPDATE sessions SET expires=0')
        self.assertEqual(self.request('/api/locations')[0], 401)

    def test_sample_seeding_preserves_edits_and_real_data(self):
        with server.connect() as db:
            db.execute("UPDATE locations SET cans=999,region='Custom' WHERE name='The Corner Tap'")
            db.execute("DELETE FROM locations WHERE name='Prairie House'")
        server.seed_samples()
        server.initialize()
        with server.connect() as db:
            row = db.execute("SELECT * FROM locations WHERE name='The Corner Tap'").fetchone()
            self.assertEqual((row['cans'], row['region']), (999, 'Custom'))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM locations').fetchone()[0], 18)
            db.execute('UPDATE settings SET sample=0')
        with self.assertRaises(ValueError):
            server.seed_samples()

    def test_login_rate_limit(self):
        for _ in range(10):
            self.assertEqual(self.request('/api/login', {'username': 'unknown', 'password': 'bad'})[0], 401)
        self.assertEqual(self.request('/api/login', {'username': 'unknown', 'password': 'bad'})[0], 429)

    def test_demo_recovers_samples_and_login_after_storage_loss(self):
        config = {'BEVSTATS_LOGIN_USERNAME': 'demo-user', 'BEVSTATS_LOGIN_PASSWORD': 'demo test password 123', 'BEVSTATS_LOGIN_NAME': 'Demo Viewer'}
        with patch.object(server, 'DEMO_MODE', True), patch.dict(server.os.environ, config):
            server.initialize()
            self.assertFalse(self.request('/api/session')[1]['setup_required'])
            credentials = {'username': 'demo-user', 'password': config['BEVSTATS_LOGIN_PASSWORD']}
            self.assertEqual(self.request('/api/login', credentials)[0], 200)
            self.assertEqual(self.request('/api/locations', {'locations': [], 'sample': False})[0], 200)
            server.DB.unlink()
            server.initialize()
            self.cookies.clear()
            self.assertEqual(self.request('/api/login', credentials)[0], 200)
            self.assertEqual(len(self.request('/api/locations')[1]['locations']), 18)
            self.assertEqual(self.request('/api/session')[1]['user']['display_name'], 'Demo Viewer')
            self.assertTrue(self.request('/api/session')[1]['demo_mode'])
            with patch.dict(server.os.environ, {'BEVSTATS_LOGIN_PASSWORD': 'abc'}):
                with self.assertRaises(ValueError):
                    server.configure_demo_account()


if __name__ == '__main__':
    unittest.main()
