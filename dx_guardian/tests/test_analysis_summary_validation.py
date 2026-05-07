"""Validation tests for /api/analysis/summary query parameters."""

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app import app


class AnalysisSummaryValidationTest(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    def test_invalid_source_returns_400(self):
        resp = self.client.get('/api/analysis/summary?source=invalid_source')
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data['success'])
        self.assertIn('无效的数据源', data['error'])

    def test_non_integer_days_returns_400(self):
        resp = self.client.get('/api/analysis/summary?source=current&days=abc')
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data['success'])
        self.assertIn('days 必须是整数', data['error'])

    def test_out_of_range_days_returns_400(self):
        resp = self.client.get('/api/analysis/summary?source=current&days=9999')
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data['success'])
        self.assertIn('days 超出允许范围', data['error'])


if __name__ == '__main__':
    unittest.main()
