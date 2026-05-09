import unittest
from pathlib import Path
import sys
import re

from flask import Flask

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.station_routes import register_station_routes


class _ScorerStub:
    def __init__(self):
        self.called = False

    def update_station(self, lat, lon, modes):
        self.called = True


class StationRoutesTest(unittest.TestCase):
    def setUp(self):
        self.scorer = _ScorerStub()
        app = Flask(__name__)
        app.testing = True
        register_station_routes(
            app,
            {'log': lambda msg: None, 're_module': re, 'get_scorer': lambda: self.scorer},
        )
        self.client = app.test_client()

    def test_station_get_returns_config(self):
        resp = self.client.get('/api/user/station')
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertIn('callsign', data)
        self.assertIn('grid', data)

    def test_station_put_rejects_invalid_callsign(self):
        payload = {'callsign': '??', 'grid': 'PN35HS', 'lat': 45.8, 'lon': 126.5, 'power': 100}
        resp = self.client.put('/api/user/station', json=payload)
        data = resp.get_json()

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(data['error'], 'Invalid callsign format')


if __name__ == '__main__':
    unittest.main()
