import unittest
from pathlib import Path
import sys

from flask import Flask

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.score_routes import register_score_routes


class DummyScorer:
    def score(self, spot, band_counts, total_spots, solar_data, dxcc_count):
        return {
            'total': 77,
            'recommendation': 'test',
            'factors': {
                'payload_mode': {
                    'score': 1,
                    'max': 1,
                    'detail': 'ok',
                }
            },
            'spot_echo': spot,
        }


class ScoreRoutesTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.scorer = DummyScorer()

        deps = {
            'log': lambda _msg: None,
            'get_scorer': lambda: self.scorer,
            'init_scorer': lambda: None,
            'lock': type('L', (), {'__enter__': lambda s: None, '__exit__': lambda s, a, b, c: False})(),
            'get_spot_history': lambda: [],
            'get_band_counts': lambda: {},
            'get_total_spots': lambda: 0,
            'get_solar_data': lambda: {},
            'get_dxcc_cn': lambda dxcc: dxcc,
        }
        register_score_routes(self.app, deps)
        self.client = self.app.test_client()

    def test_score_spot_with_nested_payload(self):
        resp = self.client.post(
            '/api/score/spot',
            json={'spot': {'callsign': 'JA1ABC', 'band': '20m', 'mode': 'FT8'}},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['score']['spot_echo']['callsign'], 'JA1ABC')

    def test_score_spot_with_flat_payload(self):
        resp = self.client.post(
            '/api/score/spot',
            json={'callsign': 'K1XYZ', 'band': '15m', 'mode': 'CW', 'frequency': 21074.0},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['score']['spot_echo']['callsign'], 'K1XYZ')
        self.assertEqual(data['score']['spot_echo']['band'], '15m')

    def test_score_spot_rejects_missing_callsign(self):
        resp = self.client.post('/api/score/spot', json={'band': '20m'})
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertIn('error', data)


if __name__ == '__main__':
    unittest.main()
