import sys
import os
import unittest
import hashlib
from unittest.mock import patch

this_dir = os.path.dirname(os.path.abspath(__file__))
software_dir = os.path.dirname(this_dir)
visualiser_dir = os.path.join(software_dir, 'visualiser')
simulator_dir = os.path.join(software_dir, 'simulator')
sys.path.insert(0, simulator_dir)

# Import simulator app to verify endpoint protection
from app import app as simulator_app

class TestAPIAuth(unittest.TestCase):
    def setUp(self):
        # Configure test client on simulator app
        self.client = simulator_app.test_client()
        self.test_uri = "mongodb+srv://admin:secretPass123@cluster0.mongodb.net/"
        self.expected_secret = hashlib.sha256(self.test_uri.encode('utf-8')).hexdigest()

    @patch.dict(os.environ, {"MONGODB_URI": "mongodb+srv://admin:secretPass123@cluster0.mongodb.net/"})
    def test_api_unauthorized_without_key_external_ip(self):
        """Requesting Simulator API control endpoints must fail with 401 when a remote MONGODB_URI is set and request is from an external IP."""
        response = self.client.post('/api/control', json={}, environ_overrides={'REMOTE_ADDR': '192.168.1.100'})
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('Unauthorized', data['message'])

    @patch.dict(os.environ, {"MONGODB_URI": "mongodb+srv://admin:secretPass123@cluster0.mongodb.net/"})
    def test_api_authorized_with_header_external_ip(self):
        """Requesting Simulator API control endpoints with correct X-API-Key header from an external IP must succeed."""
        response = self.client.post('/api/control', json={}, headers={"X-API-Key": self.expected_secret}, environ_overrides={'REMOTE_ADDR': '192.168.1.100'})
        self.assertEqual(response.status_code, 200)

    @patch.dict(os.environ, {"MONGODB_URI": "mongodb+srv://admin:secretPass123@cluster0.mongodb.net/"})
    def test_api_authorized_with_query_param_external_ip(self):
        """Requesting Simulator API control endpoints with correct api_key query param from an external IP must succeed."""
        response = self.client.post(f'/api/control?api_key={self.expected_secret}', json={}, environ_overrides={'REMOTE_ADDR': '192.168.1.100'})
        self.assertEqual(response.status_code, 200)

    @patch.dict(os.environ, {"MONGODB_URI": "mongodb+srv://admin:secretPass123@cluster0.mongodb.net/"})
    def test_api_bypasses_auth_for_localhost(self):
        """Simulator API control requests must bypass auth and succeed with 200 (without keys) if originating from local loopback (127.0.0.1)."""
        response = self.client.post('/api/control', json={}, environ_overrides={'REMOTE_ADDR': '127.0.0.1'})
        self.assertEqual(response.status_code, 200)

    @patch.dict(os.environ, {"MONGODB_URI": "mongodb://localhost:27017/"})
    def test_api_fails_open_when_localhost_uri(self):
        """Simulator API control requests must succeed with 200 (fails-open) if MONGODB_URI points to localhost even from an external IP."""
        response = self.client.post('/api/control', json={}, environ_overrides={'REMOTE_ADDR': '192.168.1.100'})
        self.assertEqual(response.status_code, 200)

    def test_health_endpoint_reports_service_status(self):
        """The simulator should expose a health endpoint with readiness metadata."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['service'], 'battery-simulator')
        self.assertTrue(data['ready'])
        self.assertIn('uptime_seconds', data)
        self.assertIn('database', data)

if __name__ == '__main__':
    unittest.main()
