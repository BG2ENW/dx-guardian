"""Minimal tests for log routes."""

import unittest
from pathlib import Path
import sys

from flask import Flask

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.log_routes import register_log_routes


class LogRoutesTest(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.testing = True

        def dummy_getter():
            return None

        register_log_routes(
            app,
            {
                'log': lambda msg: None,
                'get_scorer': dummy_getter,
                'lock': None,
                'get_spot_history': lambda: [],
                'get_band_counts': lambda: {},
                'get_total_spots': lambda: 0,
                'solar_data_getter': dummy_getter,
                'get_dxcc_cn': lambda dxcc: '',
            },
        )
        self.client = app.test_client()

    def test_logs_get_returns_success(self):
        resp = self.client.get('/api/user/logs')
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data['success'])
        self.assertIn('logs', data)

    def test_validate_returns_success_when_no_logs(self):
        resp = self.client.get('/api/score/validate')
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data['success'])


if __name__ == '__main__':
    unittest.main()
