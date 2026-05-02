import unittest
from pathlib import Path
import sys

from flask import Flask

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.push_routes import register_push_routes


class PushRoutesTest(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.testing = True
        register_push_routes(
            app,
            {
                'log': lambda msg: None,
                'external_api_error': lambda service, err: None,
                'vapid_public_key': 'public-key-for-test',
                'vapid_private_key_pem': '-----BEGIN PRIVATE KEY-----\\nabc\\n-----END PRIVATE KEY-----\\n',
                'vapid_email': 'mailto:test@example.com',
            },
        )
        self.client = app.test_client()

    def test_public_key_available_from_env_deps(self):
        resp = self.client.get('/api/push/public_key')
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['public_key'], 'public-key-for-test')

    def test_subscribe_rejects_invalid_payload(self):
        resp = self.client.post('/api/push/subscribe', json={})
        data = resp.get_json()

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(data['error'], '无效订阅数据')


if __name__ == '__main__':
    unittest.main()
