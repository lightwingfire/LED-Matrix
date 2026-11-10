import unittest
from unittest.mock import patch

from ser import ser


class DisplayHealthTests(unittest.TestCase):
    def test_health_requires_recent_display_frames(self):
        server = ser()
        client = server.app.test_client()
        self.assertEqual(client.get('/health').status_code, 503)
        with patch('ser.time.monotonic', return_value=100):
            server.reportFrame()
            response = client.get('/health')
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json['displayRunning'])
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
        with patch('ser.time.monotonic', return_value=104):
            self.assertEqual(client.get('/health').status_code, 503)
