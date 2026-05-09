import json
import unittest
from unittest.mock import patch
from pathlib import Path
import sys

from flask import Flask

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.wavelog_routes import register_wavelog_routes


class _DummyResponse:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class WavelogRoutesTest(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.testing = True
        register_wavelog_routes(
            app,
            {
                'log': lambda msg: None,
                'external_api_error': lambda service, err: None,
                'external_failure_payload': lambda message='外部服务暂时不可用': {
                    'ok': False,
                    'error': message,
                },
                'my_call': 'BG2ENW',
                'wavelog_url': 'https://example.com',
                'wavelog_api_key': 'test-key',
            },
        )
        self.client = app.test_client()

    @patch('urllib.request.urlopen')
    def test_wavelog_station_returns_active_station(self, mock_urlopen):
        payload = json.dumps(
            [
                {
                    'station_active': '1',
                    'station_callsign': 'BG2ENW',
                    'station_gridsquare': 'PN35HS',
                    'station_city': 'Harbin',
                    'station_profile_name': 'Main',
                }
            ]
        ).encode('utf-8')
        mock_urlopen.return_value = _DummyResponse(200, payload)

        resp = self.client.get('/api/wavelog_station')
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['callsign'], 'BG2ENW')
        self.assertEqual(data['grid'], 'PN35HS')

    @patch('urllib.request.urlopen', side_effect=Exception('boom'))
    def test_wavelog_stats_masks_internal_error(self, _mock_urlopen):
        resp = self.client.get('/api/wavelog_stats')
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], '外部服务暂时不可用')


if __name__ == '__main__':
    unittest.main()
