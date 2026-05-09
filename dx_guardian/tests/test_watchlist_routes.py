import unittest
from pathlib import Path
import sys

from flask import Flask

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.watchlist_routes import register_watchlist_routes


class WatchlistRoutesTest(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.testing = True
        register_watchlist_routes(app, {'log': lambda msg: None})
        self.client = app.test_client()

    def test_watchlist_get_returns_success(self):
        resp = self.client.get('/api/user/watchlist')
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data['success'])
        self.assertIn('items', data)

    def test_watchlist_post_rejects_missing_target_value(self):
        resp = self.client.post('/api/user/watchlist', json={'target_type': 'callsign'})
        data = resp.get_json()

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(data['error'], 'target_value is required')


if __name__ == '__main__':
    unittest.main()
